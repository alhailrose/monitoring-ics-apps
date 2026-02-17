"""AWS GuardDuty checker"""
import boto3
from datetime import datetime, timezone, timedelta
from src.checks.common.base import BaseChecker

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))

class GuardDutyChecker(BaseChecker):
    def check(self, profile, account_id):
        """Check GuardDuty findings for the account/profile"""
        try:
            session = boto3.Session(profile_name=profile)
            guardduty = session.client('guardduty', region_name=self.region)

            detectors = guardduty.list_detectors().get('DetectorIds', [])
            if not detectors:
                return {
                    'status': 'disabled',
                    'profile': profile,
                    'account_id': account_id,
                    'findings': 0,
                    'details': []
                }

            detector_id = detectors[0]

            today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
            today_end = int(datetime.now().replace(hour=23, minute=59, second=59, microsecond=999).timestamp() * 1000)

            findings = guardduty.list_findings(
                DetectorId=detector_id,
                FindingCriteria={
                    'Criterion': {
                        'updatedAt': {
                            'Gte': today_start,
                            'Lte': today_end
                        }
                    }
                }
            )

            finding_ids = findings.get('FindingIds', [])
            finding_count = len(finding_ids)
            details_out = []

            if finding_ids:
                details = guardduty.get_findings(
                    DetectorId=detector_id,
                    FindingIds=finding_ids[:5]
                )
                for finding in details.get('Findings', []):
                    updated_time = finding.get('UpdatedAt')
                    if isinstance(updated_time, str):
                        # Parse ISO string and convert to WIB
                        try:
                            dt = datetime.fromisoformat(updated_time.replace('Z', '+00:00'))
                            dt_wib = dt.astimezone(WIB)
                            updated_str = dt_wib.strftime('%Y-%m-%d %H:%M WIB')
                        except:
                            updated_str = updated_time
                    else:
                        # datetime object, convert to WIB
                        dt_wib = updated_time.astimezone(WIB)
                        updated_str = dt_wib.strftime('%Y-%m-%d %H:%M WIB')

                    severity_num = finding.get('Severity', 0)
                    if severity_num >= 9.0:
                        severity_text = 'CRITICAL'
                    elif severity_num >= 7.0:
                        severity_text = 'HIGH'
                    elif severity_num >= 4.0:
                        severity_text = 'MEDIUM'
                    else:
                        severity_text = 'LOW'

                    details_out.append({
                        'type': finding.get('Type', 'N/A'),
                        'severity': severity_text,
                        'title': finding.get('Title', 'N/A'),
                        'updated': updated_str
                    })

            return {
                'status': 'success',
                'profile': profile,
                'account_id': account_id,
                'findings': finding_count,
                'details': details_out
            }

        except Exception as e:
            return {
                'status': 'error',
                'profile': profile,
                'account_id': account_id,
                'error': str(e)
            }

    def format_report(self, results):
        """Format GuardDuty findings into readable report"""
        if results['status'] == 'error':
            return f"ERROR: {results['error']}"
        if results['status'] == 'disabled':
            return "GuardDuty is not enabled for this account."

        now = self.timestamp
        date_str = now.strftime('%B %d, %Y')
        time_str = now.strftime('%H:%M WIB')

        lines = []
        lines.append("AWS GUARDDUTY REPORT")
        lines.append(f"Date: {date_str} | Time: {time_str}")
        lines.append(f"Account: {results['profile']} ({results['account_id']})")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("EXECUTIVE SUMMARY")

        if results['findings'] == 0:
            lines.append("GuardDuty monitoring completed. No new findings today.")
        else:
            lines.append(f"GuardDuty monitoring completed. {results['findings']} finding(s) detected today.")

        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("ASSESSMENT RESULTS")

        if results['findings'] == 0:
            lines.append("Status: CLEAR - No findings detected today")
            lines.append("")
            lines.append("=" * 80)
            return "\n".join(lines)

        lines.append(f"Status: ATTENTION REQUIRED - {results['findings']} findings")
        lines.append("")
        lines.append("Recent Findings (up to 5):")
        for idx, detail in enumerate(results['details'], 1):
            lines.append(f"\n• Finding #{idx}")
            lines.append(f"  Type: {detail['type']}")
            lines.append(f"  Title: {detail['title']}")
            lines.append(f"  Severity: {detail['severity']}")
            lines.append(f"  Updated: {detail['updated']}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("RECOMMENDATIONS")
        lines.append("1. Review and remediate the listed findings promptly")
        lines.append("2. Validate GuardDuty alerts are integrated with your incident workflow")
        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)
