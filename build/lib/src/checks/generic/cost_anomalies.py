"""AWS Cost Anomalies Checker"""

import boto3
from datetime import datetime, timedelta
from src.checks.common.base import BaseChecker


class CostAnomalyChecker(BaseChecker):
    def __init__(self, region="us-east-1"):
        super().__init__(region)

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
                    pass

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
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(e),
            }

    def format_report(self, results):
        """Format cost anomalies into readable report"""
        if results["status"] == "error":
            return f"ERROR: {results['error']}"

        now = self.timestamp
        date_str = now.strftime("%B %d, %Y")
        time_str = now.strftime("%H:%M WIB")

        lines = []
        lines.append("AWS COST ANOMALY DETECTION REPORT")
        lines.append(f"Date: {date_str} | Time: {time_str}")
        lines.append(f"Account: {results['profile']} ({results['account_id']})")
        lines.append(f"Period: Last 2 days (today and yesterday)")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("EXECUTIVE SUMMARY")

        today_count = results.get("today_anomaly_count", 0)
        yesterday_count = results.get("yesterday_anomaly_count", 0)

        if results["total_anomalies"] == 0:
            lines.append(
                f"Cost monitoring completed. {results['total_monitors']} monitor(s) active."
            )
            lines.append("No cost anomalies detected in the last 2 days.")
        else:
            lines.append(
                f"Cost monitoring completed. {results['total_monitors']} monitor(s) active."
            )
            lines.append(
                f"{results['total_anomalies']} cost anomalies detected requiring review."
            )

        lines.append(f"Today anomalies: {today_count}")
        lines.append(f"Yesterday anomalies: {yesterday_count}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("ASSESSMENT RESULTS")
        lines.append("")
        lines.append("COST ANOMALY MONITORS")

        if not results["monitors"]:
            lines.append("Status: No monitors configured")
            lines.append("")
            lines.append("=" * 80)
            return "\n".join(lines)

        lines.append(f"Status: {results['total_monitors']} active monitor(s)")
        lines.append("")
        lines.append("Active Monitors:")

        for monitor in results["monitors"]:
            lines.append(f"\n• {monitor['MonitorName']}")
            lines.append(f"  Type: {monitor['MonitorType']}")
            lines.append(f"  Dimension: {monitor.get('MonitorDimension', 'N/A')}")
            lines.append(
                f"  Services Tracked: {monitor.get('DimensionalValueCount', 0)}"
            )
            lines.append(f"  Last Evaluated: {monitor.get('LastEvaluatedDate', 'N/A')}")

        # Show anomalies
        if results["anomalies"]:
            lines.append("")
            sorted_anomalies = sorted(
                results["anomalies"],
                key=lambda x: (
                    x.get("AnomalyStartDate", ""),
                    x.get("AnomalyEndDate", ""),
                ),
                reverse=True,
            )

            latest = sorted_anomalies[0]
            latest_impact = float(latest.get("Impact", {}).get("TotalImpact", 0) or 0)
            lines.append("Latest anomaly snapshot")
            lines.append(
                f"- {latest.get('AnomalyStartDate', 'N/A')} | {latest.get('MonitorName', 'N/A')} | Impact ${latest_impact:.2f}"
            )

            prev_candidates = sorted_anomalies[1:]
            if prev_candidates:
                prev = prev_candidates[0]
                prev_impact = float(prev.get("Impact", {}).get("TotalImpact", 0) or 0)
                lines.append("Previous-day context")
                lines.append(
                    f"- {prev.get('AnomalyStartDate', 'N/A')} | {prev.get('MonitorName', 'N/A')} | Impact ${prev_impact:.2f}"
                )

            lines.append("")
            lines.append("DETECTED ANOMALIES")
            if results["total_anomalies"] > 0:
                total_impact = sum(
                    float(a.get("Impact", {}).get("TotalImpact", 0))
                    for a in results["anomalies"]
                )
                lines.append(
                    f"Status: {results['total_anomalies']} anomalies detected (Total Impact: ${total_impact:.2f})"
                )
            else:
                lines.append("Status: No anomalies detected")

            lines.append("")
            lines.append("Anomaly Details:")

            for idx, anomaly in enumerate(results["anomalies"], 1):
                impact = anomaly.get("Impact", {})
                total_impact_val = float(impact.get("TotalImpact", 0))

                # Calculate duration
                start_date = anomaly.get("AnomalyStartDate", "N/A")
                end_date = anomaly.get("AnomalyEndDate", "N/A")
                duration_days = 0
                if start_date != "N/A" and end_date != "N/A":
                    try:
                        from datetime import datetime

                        start = datetime.strptime(start_date, "%Y-%m-%d")
                        end = datetime.strptime(end_date, "%Y-%m-%d")
                        duration_days = (end - start).days + 1
                    except:
                        duration_days = 0

                lines.append(f"\n• Anomaly #{idx}: {anomaly.get('MonitorName', 'N/A')}")
                lines.append("  " + "=" * 76)
                lines.append(f"  Anomaly ID: {anomaly.get('AnomalyId', 'N/A')}")
                lines.append(
                    f"  Date Range: {start_date} to {end_date} ({duration_days} days)"
                )
                lines.append(
                    f"  Anomaly Score: {anomaly.get('AnomalyScore', {}).get('CurrentScore', 'N/A')}/100"
                )
                lines.append("")
                lines.append(f"  FINANCIAL IMPACT:")
                lines.append(f"    Total Impact: ${total_impact_val:.2f}")
                if duration_days > 0:
                    avg_daily = total_impact_val / duration_days
                    lines.append(f"    Average Daily Impact: ${avg_daily:.2f}")
                lines.append(
                    f"    Total Actual Spend: ${float(impact.get('TotalActualSpend', 0)):.2f}"
                )
                lines.append(
                    f"    Total Expected Spend: ${float(impact.get('TotalExpectedSpend', 0)):.2f}"
                )
                lines.append(
                    f"    Impact Percentage: {impact.get('TotalImpactPercentage', 0)}%"
                )

                # Daily breakdown
                daily_breakdown = anomaly.get("DailyBreakdown", [])
                if daily_breakdown:
                    lines.append("")
                    lines.append(f"  DAILY COST BREAKDOWN:")
                    for day_data in daily_breakdown:
                        day_start = day_data.get("TimePeriod", {}).get("Start", "N/A")
                        day_cost = float(
                            day_data.get("Total", {})
                            .get("UnblendedCost", {})
                            .get("Amount", 0)
                        )
                        lines.append(f"    {day_start}: ${day_cost:.2f}")

                # Root causes
                root_causes = anomaly.get("RootCauses", [])
                if root_causes:
                    lines.append("")
                    lines.append(f"  ROOT CAUSES ({len(root_causes)} identified):")
                    for rc_idx, rc in enumerate(root_causes, 1):
                        contribution = rc.get("Impact", {}).get("Contribution", 0)
                        lines.append(
                            f"    {rc_idx}. Service: {rc.get('Service', 'N/A')} (Impact: ${contribution:.2f})"
                        )
                        lines.append(f"       Region: {rc.get('Region', 'N/A')}")
                        if rc.get("UsageType"):
                            lines.append(f"       Usage Type: {rc.get('UsageType')}")
                        if rc.get("LinkedAccount"):
                            account_name = rc.get(
                                "LinkedAccountName", rc.get("LinkedAccount")
                            )
                            lines.append(f"       Linked Account: {account_name}")

                lines.append("")
        else:
            lines.append("")
            lines.append("DETECTED ANOMALIES")
            lines.append("Status: CLEAR - No anomalies detected in the last 2 days")

        # Recommendations
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("RECOMMENDATIONS")

        rec_count = 1
        if results["total_anomalies"] > 0:
            high_impact = [
                a
                for a in results["anomalies"]
                if float(a.get("Impact", {}).get("TotalImpact", 0)) > 50
            ]
            if high_impact:
                lines.append(
                    f"{rec_count}. IMMEDIATE REVIEW: Investigate high-impact anomalies"
                )
                lines.append(f"   {len(high_impact)} anomaly(ies) with impact > $50")
                rec_count += 1

            lines.append(
                f"{rec_count}. COST ANALYSIS: Review root causes and optimize spending"
            )
            lines.append(f"   Check Cost Explorer for detailed breakdown")
            rec_count += 1
        else:
            lines.append(
                f"{rec_count}. ROUTINE MONITORING: Continue cost anomaly monitoring"
            )

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)
