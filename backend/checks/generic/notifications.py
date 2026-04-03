"""AWS User Notifications checker"""

import boto3
from datetime import datetime, timedelta, timezone
from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

_WIB = timezone(timedelta(hours=7))


def _fmt_ts(ts) -> str:
    """Convert a datetime or ISO string to WIB human-readable format."""
    if not ts or ts == "N/A":
        return "N/A"
    try:
        if isinstance(ts, datetime):
            return ts.astimezone(_WIB).strftime("%d %b %Y %H:%M WIB")
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.astimezone(_WIB).strftime("%d %b %Y %H:%M WIB")
    except Exception:
        return str(ts)


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
            session = self._get_session(profile)
            client = session.client("notifications", region_name=self.region)

            # Get notifications from last 12 hours (UTC-aware)
            now = datetime.now(timezone.utc)
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
        """Format notifications — full detail for specific/single check mode."""
        if results["status"] == "error":
            return f"ERROR: {results['error']}"

        profile = results["profile"]
        account_id = results.get("account_id", "Unknown")
        now_wib = datetime.now(_WIB).strftime("%d %b %Y %H:%M WIB")
        recent_count = results.get("recent_count", 0)
        total_managed = results.get("total_managed", 0)
        regular_count = results.get("regular_count", 0)

        lines = []
        lines.append("┌─ NOTIFICATION CENTER CHECK")
        lines.append(f"│  Profil     : {profile} ({account_id})")
        lines.append(f"│  Diperiksa  : {now_wib}")
        lines.append(f"│  12 Jam     : {recent_count} notifikasi baru")
        lines.append(f"│  Total      : {total_managed} managed | {regular_count} regular")

        if recent_count == 0 and total_managed == 0 and regular_count == 0:
            lines.append("└─ Status: Tidak ada data notifikasi")
            return "\n".join(lines)

        if recent_count == 0:
            lines.append("└─ Status: ✓ Tidak ada notifikasi baru dalam 12 jam terakhir")
            all_events = results.get("all_events") or []
            if all_events:
                lines.append("")
                lines.append("  Notifikasi terbaru (referensi):")
                for event in all_events[:5]:
                    notif_event = event.get("notificationEvent", {})
                    event_type = notif_event.get("sourceEventMetadata", {}).get("eventType", "N/A")
                    headline = notif_event.get("messageComponents", {}).get("headline", "N/A")
                    created = _fmt_ts(event.get("creationTime", "N/A"))
                    lines.append(f"  • [{created}] {event_type}")
                    lines.append(f"    {headline}")
            return "\n".join(lines)

        lines.append(f"└─ Status: ⚠ {recent_count} notifikasi baru dalam 12 jam terakhir")
        lines.append("")
        lines.append("  Notifikasi Baru (12 jam):")

        for idx, event in enumerate(results.get("recent_events", []), 1):
            notif_event = event.get("notificationEvent", {})
            event_type = notif_event.get("sourceEventMetadata", {}).get("eventType", "N/A")
            headline = notif_event.get("messageComponents", {}).get("headline", "N/A")
            created = _fmt_ts(event.get("creationTime", "N/A"))
            lines.append(f"  [{idx}] {event_type}")
            lines.append(f"      Waktu     : {created}")
            lines.append(f"      Headline  : {headline}")
            lines.append("")

        recent_events = results.get("recent_events") or []
        if len(recent_events) < recent_count:
            lines.append(f"  ... dan {recent_count - len(recent_events)} notifikasi lainnya")

        return "\n".join(lines).rstrip()

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

            lines.append("")
            lines.append("Recent notifications by account:")
            for profile, result in all_results.items():
                if result.get("status") != "success":
                    continue
                recent_count = int(result.get("recent_count", 0) or 0)
                if recent_count <= 0:
                    continue

                lines.append(f"  * {profile}: {recent_count} new notification(s)")
                events = result.get("recent_events") or []
                if not isinstance(events, list):
                    continue

                for event in events[:3]:
                    notif_event = event.get("notificationEvent", {})
                    event_type = notif_event.get("sourceEventMetadata", {}).get(
                        "eventType", "N/A"
                    )
                    headline = notif_event.get("messageComponents", {}).get(
                        "headline", "N/A"
                    )
                    created = event.get("creationTime", "N/A")
                    lines.append(f"    - [{created}] {event_type}: {headline}")

        return lines
