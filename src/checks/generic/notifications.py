"""AWS User Notifications checker"""

import boto3
from datetime import datetime, timedelta
from src.checks.common.base import BaseChecker
from src.checks.common.aws_errors import is_credential_error


class NotificationChecker(BaseChecker):
    report_section_title = "NOTIFICATION CENTER"
    issue_label = "new notifications"
    recommendation_text = "REVIEW NOTIFICATIONS: Check new AWS notifications"

    def __init__(self, region=None, **kwargs):
        # Notification Center is only in us-east-1; ignore custom region
        super().__init__("us-east-1", **kwargs)

    def check(self, profile, account_id):
        """Check AWS User Notifications (Notification Center) - last 12 hours"""
        try:
            session = boto3.Session(profile_name=profile)
            client = session.client("notifications", region_name=self.region)

            # Get notifications from last 12 hours
            now = datetime.now()
            twelve_hours_ago = now - timedelta(hours=12)

            recent_events = client.list_managed_notification_events(
                startTime=twelve_hours_ago, endTime=now
            ).get("managedNotificationEvents", [])

            all_events = client.list_managed_notification_events().get(
                "managedNotificationEvents", []
            )
            regular_events = client.list_notification_events().get(
                "notificationEvents", []
            )

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "recent_events": recent_events,
                "all_events": all_events,
                "regular_events": regular_events,
                "recent_count": len(recent_events),
                "total_managed": len(all_events),
                "regular_count": len(regular_events),
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
        if results["status"] == "error":
            return f"ERROR: {results['error']}"

        lines = []
        lines.append("AWS NOTIFICATION CENTER")
        lines.append(
            f"Last 12h: {results['recent_count']} new | Total: {results['total_managed']}"
        )

        # Show recent events if any
        if results["recent_events"]:
            lines.append("")
            lines.append("🔴 Recent notifications (12h):")
            for event in results["recent_events"][:5]:
                notif_event = event.get("notificationEvent", {})
                event_type = notif_event.get("sourceEventMetadata", {}).get(
                    "eventType", "N/A"
                )
                headline = notif_event.get("messageComponents", {}).get(
                    "headline", "N/A"
                )
                created = event.get("creationTime", "N/A")

                lines.append(f"\n• [{created}] {event_type}")
                lines.append(f"  {headline[:150]}...")

        # Always show latest 3 for context
        elif results["all_events"]:
            lines.append("")
            lines.append("Latest notifications (for reference):")
            for event in results["all_events"][:3]:
                notif_event = event.get("notificationEvent", {})
                event_type = notif_event.get("sourceEventMetadata", {}).get(
                    "eventType", "N/A"
                )
                headline = notif_event.get("messageComponents", {}).get(
                    "headline", "N/A"
                )
                created = event.get("creationTime", "N/A")

                lines.append(f"\n• [{created}] {event_type}")
                lines.append(f"  {headline[:150]}...")

        return "\n".join(lines)

    def count_issues(self, result: dict) -> int:
        if result.get("status") == "error":
            return 0
        return int(result.get("recent_count", 0) or 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render NOTIFICATION CENTER section for consolidated report."""
        lines = []
        lines.append("")
        lines.append("NOTIFICATION CENTER")

        if errors:
            lines.append("Status: ERROR - Notification Center check failed")
            lines.append("Errors:")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            if len(errors) > 5:
                lines.append(f"  ... and {len(errors) - 5} more")
            return lines

        # Aggregate notification data across all profiles
        total_recent = 0
        total_managed_all = 0
        for profile, result in all_results.items():
            if result.get("status") == "success":
                total_recent += result.get("recent_count", 0)
                total_managed_all += result.get("total_managed", 0)

        if total_recent == 0 and total_managed_all == 0:
            lines.append("Status: No data")
            return lines

        if total_recent == 0:
            lines.append(
                f"Status: No new notifications in last 12h ({total_managed_all} existing available)"
            )
        else:
            lines.append(
                f"Status: {total_recent} new notifications detected in last 12h"
            )

        return lines
