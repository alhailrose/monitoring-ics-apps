"""Alarm verification checker for specific CloudWatch alarm names."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import boto3

from .base import BaseChecker


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
        self, alarm_name: str, threshold_text: str, start_time: datetime
    ) -> str:
        return (
            f"{self._greeting()}, izin menginformasikan pada *{alarm_name}* sedang melewati "
            f"threshold {threshold_text} sejak {_format_wib(start_time)} (status: ongoing)."
        )

    def check(self, profile, account_id):
        if not self.alarm_names:
            return {
                "status": "skipped",
                "profile": profile,
                "account_id": account_id,
                "reason": "Alarm name wajib diisi (tidak mengambil semua alarm).",
            }

        try:
            session = boto3.Session(profile_name=profile, region_name=self.region)
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
                            "status": "not-found",
                            "alarm_state": "UNKNOWN",
                            "ongoing_minutes": 0,
                            "should_report": False,
                            "recommended_action": "MONITOR",
                            "message": "",
                        }
                    )
                    continue

                alarm = metric_alarms[0]
                alarm_state = alarm.get("StateValue", "INSUFFICIENT_DATA")
                threshold_text = self._threshold_text(alarm)
                breach_start = None
                ongoing_minutes = 0
                should_report = False
                message = ""

                if alarm_state == "ALARM":
                    history = cw.describe_alarm_history(
                        AlarmName=alarm_name,
                        HistoryItemType="StateUpdate",
                        StartDate=history_start,
                        EndDate=now_utc,
                        ScanBy="TimestampDescending",
                    ).get("AlarmHistoryItems", [])

                    breach_start = self._find_transition(history, "from OK to ALARM")
                    if breach_start is None:
                        breach_start = self._find_transition(history, "to ALARM")

                    if breach_start is not None:
                        if breach_start.tzinfo is None:
                            breach_start = breach_start.replace(tzinfo=timezone.utc)
                        ongoing_minutes = max(
                            1, int((now_utc - breach_start).total_seconds() // 60)
                        )

                    should_report = ongoing_minutes >= self.min_duration_minutes
                    if should_report and breach_start is not None:
                        message = self._ongoing_message(
                            alarm_name, threshold_text, breach_start
                        )

                alarms_result.append(
                    {
                        "alarm_name": alarm_name,
                        "status": "ok",
                        "alarm_state": alarm_state,
                        "threshold_text": threshold_text,
                        "breach_start_time": _format_wib(breach_start),
                        "ongoing_minutes": ongoing_minutes,
                        "should_report": should_report,
                        "recommended_action": "REPORT_NOW"
                        if should_report
                        else "MONITOR",
                        "reason": alarm.get("StateReason", ""),
                        "message": message,
                    }
                )

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "min_alarm_minutes": self.min_duration_minutes,
                "alarms": alarms_result,
            }
        except Exception as exc:
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

        lines = [
            f"ALARM VERIFICATION (threshold {results.get('min_alarm_minutes', 10)} menit)"
        ]
        for item in alarms:
            lines.append("")
            lines.append(f"- {item.get('alarm_name', 'N/A')}")
            lines.append(
                f"  state={item.get('alarm_state')} action={item.get('recommended_action')}"
            )
            if item.get("status") == "not-found":
                lines.append("  alarm tidak ditemukan di akun/region ini")
                continue
            lines.append(
                f"  ongoing={item.get('ongoing_minutes', 0)} menit | start={item.get('breach_start_time', 'unknown')}"
            )
            if item.get("message"):
                lines.append(f"  message: {item.get('message')}")

        return "\n".join(lines)
