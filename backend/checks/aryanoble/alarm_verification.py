"""Alarm verification checker for specific CloudWatch alarm names."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import boto3

from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error


WIB = timezone(timedelta(hours=7))

OPERATOR_MAP = {
    "GreaterThanThreshold": ">",
    "GreaterThanOrEqualToThreshold": ">=",
    "LessThanThreshold": "<",
    "LessThanOrEqualToThreshold": "<=",
}


def _format_wib(value: Optional[datetime]) -> str:
    if value is None:
        return "unknown"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(WIB).strftime("%H:%M WIB")


class AlarmVerificationChecker(BaseChecker):
    def __init__(
        self,
        region: str = "ap-southeast-3",
        min_duration_minutes: int = 10,
        alarm_names=None,
        **kwargs,
    ):
        super().__init__(region, **kwargs)
        self.min_duration_minutes = min_duration_minutes
        if isinstance(alarm_names, str):
            parsed = [x.strip() for x in alarm_names.split(",")]
            self.alarm_names = [x for x in parsed if x]
        else:
            self.alarm_names = [
                str(x).strip() for x in (alarm_names or []) if str(x).strip()
            ]

    def _find_transition(self, history: List[Dict], marker: str) -> Optional[datetime]:
        for item in history:
            summary = item.get("HistorySummary") or item.get("history_summary") or ""
            if marker in summary:
                return item.get("Timestamp") or item.get("timestamp")
        return None

    def _find_start_before_end(
        self, history: List[Dict], end_time: datetime
    ) -> Optional[datetime]:
        for item in history:
            summary = item.get("HistorySummary") or item.get("history_summary") or ""
            ts = item.get("Timestamp") or item.get("timestamp")
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if "from OK to ALARM" in summary and ts <= end_time:
                return ts
        return None

    def _threshold_text(self, alarm: Dict) -> str:
        operator = OPERATOR_MAP.get(alarm.get("ComparisonOperator", ""), "")
        threshold = alarm.get("Threshold")
        unit = alarm.get("Unit")
        if threshold is None:
            return "N/A"
        if isinstance(threshold, float) and threshold.is_integer():
            threshold = int(threshold)
        return f"{operator} {threshold}{(' ' + unit) if unit else ''}".strip()

    def _greeting(self) -> str:
        hour = datetime.now(WIB).hour
        if 5 <= hour < 11:
            return "Selamat Pagi"
        if 11 <= hour < 15:
            return "Selamat Siang"
        if 15 <= hour < 18:
            return "Selamat Sore"
        return "Selamat Malam"

    def _ongoing_message(
        self,
        alarm_name: str,
        threshold_text: str,
        start_time: datetime,
        ongoing_minutes: int,
    ) -> str:
        return (
            f"{self._greeting()}, kami informasikan pada *{alarm_name}* sedang melewati "
            f"threshold {threshold_text} sejak {_format_wib(start_time)} "
            f"(status: ongoing {ongoing_minutes} menit)."
        )

    def _build_alarm_result(
        self,
        alarm_name: str,
        alarm_state: str,
        threshold_text: str,
        reason: str,
        history: List[Dict],
        now_utc: datetime,
    ) -> Dict:
        start_time = None
        end_time = None
        ongoing_minutes = 0
        breach_duration_minutes = 0
        should_report = False
        message = ""
        action = "MONITOR"

        if alarm_state == "ALARM":
            start_time = self._find_transition(history, "from OK to ALARM")
            if start_time is None:
                start_time = self._find_transition(history, "to ALARM")

            if start_time is not None:
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                ongoing_minutes = max(
                    1, int((now_utc - start_time).total_seconds() // 60)
                )

            should_report = ongoing_minutes >= self.min_duration_minutes
            action = "REPORT_NOW" if should_report else "MONITOR"
            if should_report and start_time is not None:
                message = self._ongoing_message(
                    alarm_name, threshold_text, start_time, ongoing_minutes
                )
        else:
            end_time = self._find_transition(history, "from ALARM to OK")
            if end_time is not None:
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
                start_time = self._find_start_before_end(history, end_time)
                if start_time is not None:
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    breach_duration_minutes = max(
                        1, int((end_time - start_time).total_seconds() // 60)
                    )

            action = (
                "NO_REPORT_RECOVERED"
                if breach_duration_minutes >= self.min_duration_minutes
                else "NO_REPORT_TRANSIENT"
            )

        return {
            "alarm_name": alarm_name,
            "status": "ok",
            "alarm_state": alarm_state,
            "current_state": "ALARM" if alarm_state == "ALARM" else "OK",
            "threshold_text": threshold_text,
            "breach_start_time": _format_wib(start_time),
            "breach_end_time": _format_wib(end_time),
            "ongoing_minutes": ongoing_minutes,
            "breach_duration_minutes": breach_duration_minutes,
            "should_report": should_report,
            "recommended_action": action,
            "reason": reason,
            "message": message,
        }

    def check(self, profile, account_id):
        if not self.alarm_names:
            return {
                "status": "skipped",
                "profile": profile,
                "account_id": account_id,
                "reason": "Alarm name wajib diisi (tidak mengambil semua alarm).",
            }

        try:
            session = self._get_session(profile)
            cw = session.client("cloudwatch", region_name=self.region)
            now_utc = datetime.now(timezone.utc)
            history_start = now_utc - timedelta(hours=24)
            alarms_result = []

            for alarm_name in self.alarm_names:
                described = cw.describe_alarms(AlarmNames=[alarm_name])
                metric_alarms = described.get("MetricAlarms", [])

                if not metric_alarms:
                    alarms_result.append(
                        {
                            "alarm_name": alarm_name,
                            "status": "error",
                            "alarm_state": "NOT_FOUND",
                            "error": f"Alarm '{alarm_name}' tidak ditemukan di CloudWatch",
                            "ongoing_minutes": 0,
                            "should_report": False,
                            "recommended_action": "CHECK_CONFIG",
                            "message": "",
                        }
                    )
                    continue

                alarm = metric_alarms[0]
                alarm_state = alarm.get("StateValue", "INSUFFICIENT_DATA")
                threshold_text = self._threshold_text(alarm)
                history = cw.describe_alarm_history(
                    AlarmName=alarm_name,
                    HistoryItemType="StateUpdate",
                    StartDate=history_start,
                    EndDate=now_utc,
                    ScanBy="TimestampDescending",
                ).get("AlarmHistoryItems", [])

                alarms_result.append(
                    self._build_alarm_result(
                        alarm_name=alarm_name,
                        alarm_state=alarm_state,
                        threshold_text=threshold_text,
                        reason=alarm.get("StateReason", ""),
                        history=history,
                        now_utc=now_utc,
                    )
                )

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "min_alarm_minutes": self.min_duration_minutes,
                "alarms": alarms_result,
            }
        except Exception as exc:
            if is_credential_error(exc):
                return self._error_result(exc, profile, account_id)
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(exc),
            }

    def format_report(self, results):
        if results.get("status") == "error":
            return f"ERROR: {results.get('error')}"
        if results.get("status") == "skipped":
            return f"SKIPPED: {results.get('reason')}"

        alarms = results.get("alarms", [])
        if not alarms:
            return "No alarm data."

        min_minutes = results.get("min_alarm_minutes", 10)
        account = str(results.get("profile", "-")).replace("-", " ").upper()

        def _clip(value: str, width: int) -> str:
            text = str(value or "-")
            return text if len(text) <= width else text[: width - 3] + "..."

        def _row_status(item: Dict) -> tuple[int, str]:
            if item.get("status") == "error" or item.get("alarm_state") == "NOT_FOUND":
                return 3, "🔴 Error / Tidak Ditemukan"
            action = item.get("recommended_action")
            if action == "REPORT_NOW":
                return 0, "🔴 Report Now"
            if action == "CHECK_CONFIG":
                return 3, "🔴 Tidak Ditemukan"
            if action == "MONITOR":
                return 1, "🟡 Monitor"
            return 2, "🟢 OK"

        table_rows = []
        report_lines = []
        for item in alarms:
            priority, label = _row_status(item)
            alarm_name = item.get("alarm_name", "N/A")
            threshold = item.get("threshold_text", "N/A")

            if item.get("status") == "error" or item.get("alarm_state") == "NOT_FOUND":
                err_msg = item.get("error", "Tidak ditemukan di CloudWatch")
                table_rows.append(
                    {
                        "priority": priority,
                        "status": label,
                        "account": account,
                        "alarm_name": alarm_name,
                        "state": "NOT_FOUND",
                        "threshold": "N/A",
                        "time_range": err_msg,
                        "duration": "-",
                    }
                )
                continue

            state = item.get("alarm_state", "UNKNOWN")
            if state == "ALARM":
                time_range = f"{item.get('breach_start_time', 'unknown')} - now"
                duration = f"ongoing {item.get('ongoing_minutes', 0)} menit"
            else:
                time_range = (
                    f"{item.get('breach_start_time', 'unknown')} - "
                    f"{item.get('breach_end_time', 'unknown')}"
                )
                duration = f"durasi {item.get('breach_duration_minutes', 0)} menit"

            table_rows.append(
                {
                    "priority": priority,
                    "status": label,
                    "account": account,
                    "alarm_name": alarm_name,
                    "state": state,
                    "threshold": threshold,
                    "time_range": time_range,
                    "duration": duration,
                }
            )

            if item.get("recommended_action") == "REPORT_NOW" and item.get("message"):
                report_lines.append(item.get("message"))

        table_rows.sort(
            key=lambda r: (
                int(r["priority"]),
                str(r["alarm_name"]),
            )
        )

        lines = [
            "Alarm Verification Data",
            "Data source: CloudWatch alarm history 24 jam ke belakang (rolling).",
            f"Rule: Pelaporan hanya untuk alarm ALARM ongoing >= {min_minutes} menit.",
            "",
            f"{'Status':<15}{'Account':<12}{'Alarm Name':<36}{'State':<7}{'Threshold':<11}{'Time Range':<27}Duration",
        ]

        for row in table_rows:
            lines.append(
                f"{_clip(row['status'], 15):<15}{_clip(row['account'], 12):<12}{_clip(row['alarm_name'], 36):<36}{_clip(row['state'], 7):<7}{_clip(row['threshold'], 11):<11}{_clip(row['time_range'], 27):<27}{row['duration']}"
            )

        if report_lines:
            lines.extend(["", "Pelaporan:"])
            for msg in report_lines:
                lines.append(f"- {msg}")
        else:
            lines.extend(
                ["", "Pelaporan:", "- Tidak ada alarm yang perlu dilaporkan saat ini."]
            )

        return "\n".join(lines)
