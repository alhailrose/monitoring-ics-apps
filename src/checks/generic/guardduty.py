"""AWS GuardDuty checker"""
import logging
import boto3
from datetime import datetime, timezone, timedelta
from src.checks.common.base import BaseChecker
from src.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))

class GuardDutyChecker(BaseChecker):
    report_section_title = "GUARDDUTY FINDINGS"
    issue_label = "new security findings"
    recommendation_text = "IMMEDIATE ACTION REQUIRED: Investigate GuardDuty findings"

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
                        except (ValueError, TypeError):
                            logger.warning("Failed to parse GuardDuty timestamp: %s", updated_time)
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
            if is_credential_error(e):
                return self._error_result(e, profile, account_id)
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

    def count_issues(self, result: dict) -> int:
        if result.get("status") in ("error", "disabled"):
            return 0
        return int(result.get("findings", 0) or 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render GUARDDUTY FINDINGS section for consolidated report."""
        lines = []
        lines.append("")
        lines.append("GUARDDUTY FINDINGS")

        if errors:
            lines.append("Status: ERROR - GuardDuty check failed")
            lines.append("Errors:")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            if len(errors) > 5:
                lines.append(f"  ... and {len(errors) - 5} more")
            return lines

        total_findings = sum(self.count_issues(r) for r in all_results.values())
        guardduty_disabled = [p for p, r in all_results.items() if r.get("status") == "disabled"]

        if total_findings > 0 or guardduty_disabled:
            if total_findings > 0:
                lines.append(f"Status: ATTENTION REQUIRED - {total_findings} new findings detected")
                lines.append("")
                lines.append("Current Findings:")
                for profile, result in all_results.items():
                    if result.get("findings", 0) > 0:
                        account_id = result.get("account_id", "Unknown")
                        lines.append(f"  * {profile} ({account_id}): {result['findings']} fin")
                        for detail in result.get("details", [])[:3]:
                            lines.append(f"    - Type: {detail.get('type', 'N/A')}")
                            lines.append(f"    - Severity: {detail.get('severity', 'N/A')}")
                            lines.append(f"    - Date: {detail.get('updated', 'N/A')}")

            if guardduty_disabled:
                if total_findings > 0:
                    lines.append("")
                lines.append("GuardDuty NOT ENABLED:")
                for profile in guardduty_disabled:
                    account_id = all_results[profile].get("account_id", "Unknown")
                    lines.append(f"  * {profile} ({account_id})")
        else:
            lines.append("Status: CLEAR - No new security findings detected")

        return lines
