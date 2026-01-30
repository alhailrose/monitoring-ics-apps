"""AWS User Notifications checker"""
import boto3
from datetime import datetime
from .base import BaseChecker


class NotificationChecker(BaseChecker):
    def __init__(self, region=None):
        # Notification Center is only in us-east-1; ignore custom region
        super().__init__('us-east-1')

    def check(self, profile, account_id):
        """Check AWS User Notifications (Notification Center)"""
        try:
            session = boto3.Session(profile_name=profile)
            client = session.client('notifications', region_name=self.region)

            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999)

            today_events = client.list_notification_events(
                startTime=today_start,
                endTime=today_end
            ).get('notificationEvents', [])

            all_events = client.list_notification_events().get('notificationEvents', [])
            regular_events = []

            return {
                'status': 'success',
                'profile': profile,
                'account_id': account_id,
                'today_events': today_events,
                'all_events': all_events,
                'today_count': len(today_events),
                'total_managed': len(all_events)
            }

        except Exception as e:
            return {
                'status': 'error',
                'profile': profile,
                'account_id': account_id,
                'error': str(e)
            }

    def format_report(self, results):
        if results['status'] == 'error':
            return f"ERROR: {results['error']}"

        lines = []
        lines.append("AWS NOTIFICATION CENTER")
        lines.append(f"Today: {results['today_count']} new | Total: {results['total_managed']}")

        # Show today's events if any
        if results['today_events']:
            lines.append("")
            lines.append("🔴 Today's notifications:")
            for event in results['today_events'][:5]:
                event_type = event.get('sourceEventMetadata', {}).get('eventType', 'N/A')
                headline = event.get('messageComponents', {}).get('headline', 'N/A')
                created = event.get('creationTime', 'N/A')
                
                lines.append(f"\n• [{created}] {event_type}")
                lines.append(f"  {headline[:150]}...")
        
        # Always show latest 3 for context
        elif results['all_events']:
            lines.append("")
            lines.append("Latest notifications (for reference):")
            for event in results['all_events'][:3]:
                event_type = event.get('sourceEventMetadata', {}).get('eventType', 'N/A')
                headline = event.get('messageComponents', {}).get('headline', 'N/A')
                created = event.get('creationTime', 'N/A')
                
                lines.append(f"\n• [{created}] {event_type}")
                lines.append(f"  {headline[:150]}...")

        return "\n".join(lines)
