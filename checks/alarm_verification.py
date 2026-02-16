"""
CloudWatch Alarm Verification Checker (Duration Check)
Based on cloudwatch-evidence-bot logic.
Checks if an alarm has been in ALARM state for >= 10 minutes.
"""

import boto3
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple

from .base import BaseChecker

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))


def format_wib_time(dt: datetime) -> str:
    """Format datetime to WIB string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB).strftime("%H:%M WIB")


class AlarmVerificationChecker(BaseChecker):
    def __init__(
        self, region: str = "ap-southeast-3", min_duration_minutes: int = 10, **kwargs
    ):
        super().__init__(region, **kwargs)
        self.min_duration_minutes = min_duration_minutes

    def _find_transition_to_alarm(self, history: List[Dict]) -> Optional[datetime]:
        """Find the timestamp when the alarm transitioned from OK to ALARM."""
        # Sort history by timestamp descending (newest first)
        sorted_history = sorted(history, key=lambda x: x["Timestamp"], reverse=True)

        for item in sorted_history:
            summary = item.get("HistorySummary", "")
            if "from OK to ALARM" in summary:
                return item.get("Timestamp")

            # If we hit an ALARM to OK transition, we continue searching
            # because we want the start of the current alarm period
            if "from ALARM to OK" in summary:
                continue

        # If not found in history, maybe it's been in alarm for longer than the history window?
        # Or maybe it started as ALARM (insufficient data -> alarm).
        for item in sorted_history:
            summary = item.get("HistorySummary", "")
            if "to ALARM" in summary:  # Catch INSUFFICIENT_DATA -> ALARM too
                return item.get("Timestamp")

        return None

    def _generate_alert_message(self, alarm_data: Dict) -> str:
        """Generate alert message similar to cloudwatch-evidence-bot."""
        alarm_name = alarm_data["name"]
        start_time_str = alarm_data["start_time_obj"]

        # Format time if available
        if start_time_str:
            start_text = format_wib_time(start_time_str)
        else:
            start_text = "Unknown time"

        greeting = "Selamat Pagi"  # Default greeting, can be improved
        now_wib = datetime.now(WIB)
        if 5 <= now_wib.hour < 11:
            greeting = "Selamat Pagi"
        elif 11 <= now_wib.hour < 15:
            greeting = "Selamat Siang"
        elif 15 <= now_wib.hour < 18:
            greeting = "Selamat Sore"
        else:
            greeting = "Selamat Malam"

        # Construct message based on bot format
        # {greeting}, izin menginformasikan pada {alarm_name} sedang melewati
        # threshold {threshold_text} sejak {start_text} (status: ongoing).

        return (
            f"{greeting}, izin menginformasikan pada *{alarm_name}* sedang melewati "
            f"threshold sejak {start_text} (status: ongoing)."
        )

    def check(self, profile: str, account_id: str):
        try:
            session = boto3.Session(profile_name=profile, region_name=self.region)
            cw = session.client("cloudwatch", region_name=self.region)

            # 1. Get all alarms in ALARM state
            paginator = cw.get_paginator("describe_alarms")
            active_alarms = []
            for page in paginator.paginate(StateValue="ALARM"):
                active_alarms.extend(page["MetricAlarms"])

            results = []
            now_utc = datetime.now(timezone.utc)

            # History window: check last 24 hours to find when it started
            history_start = now_utc - timedelta(hours=24)

            for alarm in active_alarms:
                alarm_name = alarm["AlarmName"]

                # 2. Get alarm history to find start time
                history_resp = cw.describe_alarm_history(
                    AlarmName=alarm_name,
                    HistoryItemType="StateUpdate",
                    StartDate=history_start,
                    EndDate=now_utc,
                    ScanBy="TimestampDescending",
                )
                history_items = history_resp.get("AlarmHistoryItems", [])

                start_time = self._find_transition_to_alarm(history_items)

                duration_minutes = 0
                start_time_str = "Unknown ( > 24h )"

                if start_time:
                    # Ensure start_time is timezone-aware
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)

                    duration = now_utc - start_time
                    duration_minutes = int(duration.total_seconds() / 60)
                    start_time_wib = start_time.astimezone(WIB)
                    start_time_str = start_time_wib.strftime("%H:%M WIB")

                is_reportable = duration_minutes >= self.min_duration_minutes

                # Basic data for result
                alarm_res = {
                    "name": alarm_name,
                    "reason": alarm.get("StateReason", "N/A"),
                    "start_time": start_time_str,
                    "start_time_obj": start_time,
                    "duration_minutes": duration_minutes,
                    "is_reportable": is_reportable,
                    "threshold": self.min_duration_minutes,
                }

                # Generate bot-style message if reportable
                if is_reportable:
                    alarm_res["message"] = self._generate_alert_message(alarm_res)

                results.append(alarm_res)

            # Sort by reportable first, then duration descending
            results.sort(key=lambda x: (not x["is_reportable"], -x["duration_minutes"]))

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "alarms": results,
                "checked_at": now_utc.isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(e),
            }

    def format_report(self, results):
        if results.get("status") == "error":
            return f"ERROR: {results.get('error')}"

        alarms = results.get("alarms", [])
        if not alarms:
            return "Status: No active alarms found."

        lines = []
        lines.append(f"ALARM VERIFICATION REPORT ({len(alarms)} active alarms)")
        lines.append(f"Threshold for reporting: >= {self.min_duration_minutes} minutes")
        lines.append("")

        reportable = [a for a in alarms if a["is_reportable"]]
        pending = [a for a in alarms if not a["is_reportable"]]

        if reportable:
            lines.append("🚨 REPORTABLE ALARMS (Confirmed > 10 mins):")
            for a in reportable:
                lines.append(f"• {a['name']}")
                lines.append(
                    f"  Duration: {a['duration_minutes']} minutes (since {a['start_time']})"
                )
                lines.append(f"  Reason: {a['reason']}")
                if "message" in a:
                    lines.append(f"  [Bot Format]: {a['message']}")
                lines.append(f"  Action: ESCALATE / REPORT NOW")
                lines.append("")

        if pending:
            lines.append("⏳ PENDING ALARMS (Wait, < 10 mins):")
            for a in pending:
                remaining = max(0, self.min_duration_minutes - a["duration_minutes"])
                lines.append(f"• {a['name']}")
                lines.append(
                    f"  Duration: {a['duration_minutes']} minutes (since {a['start_time']})"
                )
                lines.append(f"  Reason: {a['reason']}")
                lines.append(f"  Action: WAIT {remaining} minutes and re-check")
                lines.append("")

        return "\n".join(lines)
