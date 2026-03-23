"""AWS Cost Anomalies Checker"""

import logging
import boto3
from datetime import datetime, timedelta
from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)


class CostAnomalyChecker(BaseChecker):
    report_section_title = "COST ANOMALIES"
    issue_label = "cost anomalies"
    recommendation_text = "COST REVIEW: Investigate cost anomalies"

    def __init__(self, region="us-east-1", **kwargs):
        super().__init__(region, **kwargs)

    def check(self, profile, account_id):
        """Check cost anomalies"""
        try:
            session = boto3.Session(profile_name=profile)
            ce = session.client("ce", region_name="us-east-1")

            # Get anomaly monitors
            monitors = ce.get_anomaly_monitors()
            monitor_list = monitors.get("AnomalyMonitors", [])

            # Get anomalies from yesterday and today (last 2 days)
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            all_anomalies = []
            for monitor in monitor_list:
                monitor_arn = monitor["MonitorArn"]
                try:
                    anomalies_response = ce.get_anomalies(
                        MonitorArn=monitor_arn,
                        DateInterval={"StartDate": yesterday, "EndDate": today},
                        MaxResults=100,
                    )
                    anomalies = anomalies_response.get("Anomalies", [])

                    for anomaly in anomalies:
                        anomaly["MonitorName"] = monitor["MonitorName"]
                        all_anomalies.append(anomaly)
                except Exception as e:
                    if is_credential_error(e):
                        raise
                    logger.warning(
                        "Failed to get anomalies for monitor %s: %s",
                        monitor.get("MonitorName", monitor_arn),
                        e,
                    )

            today_anomaly_count = 0
            yesterday_anomaly_count = 0
            for anomaly in all_anomalies:
                anomaly_start = anomaly.get("AnomalyStartDate", "")
                if anomaly_start == today:
                    today_anomaly_count += 1
                elif anomaly_start == yesterday:
                    yesterday_anomaly_count += 1

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "monitors": monitor_list,
                "anomalies": all_anomalies,
                "total_monitors": len(monitor_list),
                "total_anomalies": len(all_anomalies),
                "today_anomaly_count": today_anomaly_count,
                "yesterday_anomaly_count": yesterday_anomaly_count,
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
        """Format cost anomalies — concise per-account data output."""
        if results["status"] == "error":
            return f"ERROR: {results['error']}"

        lines = []
        lines.append(f"Cost Anomaly | {results['profile']} ({results['account_id']})")
        lines.append(f"Monitors: {results['total_monitors']} | Anomalies: {results['total_anomalies']} (today: {results.get('today_anomaly_count', 0)}, yesterday: {results.get('yesterday_anomaly_count', 0)})")

        if not results["anomalies"]:
            lines.append("Status: Clear")
            return "\n".join(lines)

        total_impact = sum(
            float(a.get("Impact", {}).get("TotalImpact", 0))
            for a in results["anomalies"]
        )
        lines.append(f"Total Impact: ${total_impact:.2f}")

        for idx, anomaly in enumerate(results["anomalies"], 1):
            impact = anomaly.get("Impact", {})
            impact_val = float(impact.get("TotalImpact", 0))
            start_date = anomaly.get("AnomalyStartDate", "N/A")
            end_date = anomaly.get("AnomalyEndDate", "N/A")
            score = anomaly.get("AnomalyScore", {}).get("CurrentScore", "N/A")

            root_causes = anomaly.get("RootCauses", [])
            services = list(set(rc.get("Service", "N/A") for rc in root_causes))

            lines.append(
                f"  {idx}. {anomaly.get('MonitorName', 'N/A')} | {start_date}~{end_date} | ${impact_val:.2f} | score={score}"
            )
            if services:
                lines.append(f"     Services: {', '.join(services[:5])}")

        return "\n".join(lines)

    def count_issues(self, result: dict) -> int:
        """Count cost anomalies from a single profile's result."""
        if result.get("status") == "error":
            return 0
        return int(result.get("total_anomalies", 0) or 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render COST ANOMALIES section for consolidated report."""
        lines = []
        lines.append("")
        lines.append("COST ANOMALIES")

        if errors:
            lines.append("Status: ERROR - Cost Anomaly check failed")
            lines.append("Errors:")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            if len(errors) > 5:
                lines.append(f"  ... and {len(errors) - 5} more")
            return lines

        total_anomalies = sum(self.count_issues(r) for r in all_results.values())

        if total_anomalies == 0:
            lines.append("Status: CLEAR - No cost anomalies detected")
        else:
            lines.append(
                f"Status: ATTENTION REQUIRED - {total_anomalies} anomalies detected"
            )
            lines.append("")
            lines.append("Detected Anomalies:")
            for profile, cost_data in all_results.items():
                if cost_data.get("total_anomalies", 0) > 0:
                    account_id = cost_data.get("account_id", "Unknown")
                    lines.append(
                        f"  * {profile} ({account_id}): {cost_data['total_anomalies']} anomalies"
                    )
                    for anomaly in cost_data.get("anomalies", [])[:3]:
                        impact = anomaly.get("Impact", {}).get("TotalImpact", "0")
                        anomaly_start = anomaly.get("AnomalyStartDate", "N/A")
                        anomaly_end = anomaly.get("AnomalyEndDate", "N/A")
                        lines.append(f"    - Monitor: {anomaly.get('MonitorName', 'N/A')}")
                        lines.append(f"    - Impact: ${impact}")
                        lines.append(f"    - Date: {anomaly_start} to {anomaly_end}")

                        root_causes = anomaly.get("RootCauses", [])
                        if root_causes:
                            services = list(
                                set([rc.get("Service", "N/A") for rc in root_causes])
                            )
                            lines.append(
                                f"    - Affected Services: {', '.join(services[:3])}"
                            )
                            if len(services) > 3:
                                lines.append(
                                    f"      ... and {len(services) - 3} more services"
                                )
                            top_cause = root_causes[0]
                            lines.append(
                                f"    - Top Root Cause: {top_cause.get('Service', 'N/A')} - {top_cause.get('UsageType', 'N/A')}"
                            )

        return lines
