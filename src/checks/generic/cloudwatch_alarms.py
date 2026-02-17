"""AWS CloudWatch Alarms checker"""
import boto3
from datetime import timezone, timedelta
from src.checks.common.base import BaseChecker

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))

class CloudWatchAlarmChecker(BaseChecker):
    def check(self, profile, account_id):
        """Check CloudWatch alarms currently in ALARM state"""
        try:
            session = boto3.Session(profile_name=profile)
            cloudwatch = session.client('cloudwatch', region_name=self.region)

            alarms = cloudwatch.describe_alarms(StateValue='ALARM')
            alarm_list = alarms.get('MetricAlarms', [])

            details = []
            for alarm in alarm_list:
                updated_time = alarm.get('StateUpdatedTimestamp')
                if hasattr(updated_time, 'astimezone'):
                    # Convert to WIB
                    dt_wib = updated_time.astimezone(WIB)
                    updated_str = dt_wib.strftime('%Y-%m-%d %H:%M WIB')
                else:
                    updated_str = str(updated_time)

                details.append({
                    'name': alarm.get('AlarmName', 'N/A'),
                    'reason': alarm.get('StateReason', 'N/A'),
                    'updated': updated_str
                })

            return {
                'status': 'success',
                'profile': profile,
                'account_id': account_id,
                'count': len(alarm_list),
                'details': details
            }

        except Exception as e:
            return {
                'status': 'error',
                'profile': profile,
                'account_id': account_id,
                'error': str(e)
            }

    def format_report(self, results):
        """Format CloudWatch alarms into readable report"""
        if results['status'] == 'error':
            return f"ERROR: {results['error']}"

        lines = []
        lines.append("AWS CLOUDWATCH ALARMS")

        if results['count'] == 0:
            lines.append("Status: All monitoring systems normal")
            return "\n".join(lines)

        lines.append(f"Status: {results['count']} alarm(s) in ALARM state")
        lines.append("")
        lines.append("Active Alarms (up to 5):")
        for alarm in results['details'][:5]:
            lines.append(f"\n• {alarm['name']}")
            lines.append(f"  Reason: {alarm['reason'][:120]}...")
            lines.append(f"  Updated: {alarm['updated']}")

        return "\n".join(lines)
