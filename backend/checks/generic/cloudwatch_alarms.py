"""AWS CloudWatch Alarms checker"""

import boto3
from datetime import timezone, timedelta
from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))


class CloudWatchAlarmChecker(BaseChecker):
    report_section_title = "CLOUDWATCH ALARMS"
    issue_label = "infrastructure alerts"
    recommendation_text = "INFRASTRUCTURE REVIEW: Address CloudWatch alarms"

    def check(self, profile, account_id):
        """Check CloudWatch alarms currently in ALARM state"""
        try:
            session = self._get_session(profile)
            cloudwatch = session.client("cloudwatch", region_name=self.region)

            alarms = cloudwatch.describe_alarms(StateValue="ALARM")
            alarm_list = alarms.get("MetricAlarms", [])

            details = []
            for alarm in alarm_list:
                updated_time = alarm.get("StateUpdatedTimestamp")
                if hasattr(updated_time, "astimezone"):
                    # Convert to WIB
                    dt_wib = updated_time.astimezone(WIB)
                    updated_str = dt_wib.strftime("%Y-%m-%d %H:%M WIB")
                else:
                    updated_str = str(updated_time)

                details.append(
                    {
                        "name": alarm.get("AlarmName", "N/A"),
                        "reason": alarm.get("StateReason", "N/A"),
                        "updated": updated_str,
                    }
                )

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "count": len(alarm_list),
                "details": details,
            }

        except Exception as e:
            if is_credential_error(e):
                return self._error_result(e, profile, account_id)
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(e),
            }

    def format_report(self, results):
        """Format CloudWatch alarms — full detail for specific/single check mode."""
        if results["status"] == "error":
            return f"ERROR: {results['error']}"

        from datetime import datetime
        profile = results["profile"]
        account_id = results.get("account_id", "Unknown")
        now_wib = datetime.now(WIB).strftime("%d %b %Y %H:%M WIB")
        count = results.get("count", 0)
        details = results.get("details", [])

        lines = []
        lines.append("┌─ CLOUDWATCH ALARMS CHECK")
        lines.append(f"│  Profil     : {profile} ({account_id})")
        lines.append(f"│  Diperiksa  : {now_wib}")
        lines.append(f"│  Alarm Aktif: {count}")

        if count == 0:
            lines.append("└─ Status: ✓ Semua sistem monitoring normal")
            return "\n".join(lines)

        lines.append(f"└─ Status: ⚠ {count} alarm dalam kondisi ALARM")
        lines.append("")

        for idx, alarm in enumerate(details, 1):
            lines.append(f"  [{idx}] {alarm.get('name', 'N/A')}")
            lines.append(f"      Updated   : {alarm.get('updated', 'N/A')}")
            lines.append(f"      Reason    : {alarm.get('reason', 'N/A')}")
            lines.append("")

        return "\n".join(lines).rstrip()

    def count_issues(self, result: dict) -> int:
        if result.get("status") == "error":
            return 0
        return int(result.get("count", 0) or 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render CLOUDWATCH ALARMS section for consolidated report."""
        lines = []
        lines.append("")
        lines.append("CLOUDWATCH ALARMS")

        if errors:
            lines.append("Status: ERROR - CloudWatch check failed")
            lines.append("Errors:")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            if len(errors) > 5:
                lines.append(f"  ... and {len(errors) - 5} more")
            return lines

        total = sum(self.count_issues(r) for r in all_results.values())
        if total == 0:
            lines.append("Status: All monitoring systems normal")
        else:
            lines.append(f"Status: {total} alarms in ALARM state")
            lines.append("")
            lines.append("Active Alarms:")
            for profile, result in all_results.items():
                if result.get("count", 0) > 0:
                    account_id = result.get("account_id", "Unknown")
                    lines.append(
                        f"  * {profile} ({account_id}): {result['count']} active alarms"
                    )
                    for detail in result.get("details", [])[:3]:
                        lines.append(f"    - Alarm: {detail.get('name', 'N/A')}")
                        lines.append(f"    - Date: {detail.get('updated', 'N/A')}")
        return lines
