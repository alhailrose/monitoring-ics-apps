"""AWS Cost Anomalies Checker"""

import logging
import boto3
from datetime import datetime, timedelta, timezone, date
from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)

_WIB = timezone(timedelta(hours=7))

_MONTH_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}


def _fmt_date(date_str: str) -> str:
    """Format 'YYYY-MM-DD' → '3 April 2026'."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return f"{d.day} {_MONTH_ID[d.month]} {d.year}"
    except Exception:
        return date_str


def _fmt_date_range(start: str, end: str) -> str:
    if start == end or not end or end == "N/A":
        return _fmt_date(start)
    return f"{_fmt_date(start)} s/d {_fmt_date(end)}"


def _score_label(score) -> str:
    try:
        s = float(score)
        if s >= 80: return "Sangat Tinggi"
        if s >= 50: return "Tinggi"
        if s >= 20: return "Sedang"
        return "Rendah"
    except Exception:
        return str(score)


def _linked_accounts(root_causes: list) -> list[dict]:
    """Extract unique linked accounts from root causes."""
    seen = set()
    accounts = []
    for rc in root_causes:
        acct_id = rc.get("LinkedAccount", "")
        if acct_id and acct_id not in seen:
            seen.add(acct_id)
            accounts.append({
                "id": acct_id,
                "name": rc.get("LinkedAccountName", ""),
            })
    return accounts


def _root_causes_by_account(root_causes: list) -> dict[str, dict]:
    """Group root causes by linked account.

    Returns {account_id: {name, services: [...]}}
    """
    grouped: dict[str, dict] = {}
    for rc in root_causes:
        acct_id = rc.get("LinkedAccount", "")
        if not acct_id:
            continue
        if acct_id not in grouped:
            grouped[acct_id] = {
                "name": rc.get("LinkedAccountName", ""),
                "services": [],
            }
        svc = rc.get("Service", "")
        region = rc.get("Region", "")
        usage = rc.get("UsageType", "")
        if svc and region and usage:
            label = f"{svc} ({region})  {usage}"
        elif svc and region:
            label = f"{svc} ({region})"
        elif svc and usage:
            label = f"{svc}  {usage}"
        else:
            label = svc or region or usage
        if label and label not in grouped[acct_id]["services"]:
            grouped[acct_id]["services"].append(label)
    return grouped


def _fetch_account_costs(ce, linked_account_ids: list[str], start: str, end: str) -> dict[str, float]:
    """Fetch actual cost per linked account for the given date range.

    Returns {account_id: total_cost_usd}.
    end date is exclusive for Cost Explorer, so add 1 day before calling.
    """
    if not linked_account_ids:
        return {}
    try:
        # Cost Explorer end date is exclusive
        end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
        end_exclusive = end_dt.strftime("%Y-%m-%d")

        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end_exclusive},
            Granularity="MONTHLY",
            Filter={
                "Dimensions": {
                    "Key": "LINKED_ACCOUNT",
                    "Values": linked_account_ids,
                }
            },
            GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
            Metrics=["UnblendedCost"],
        )
        result: dict[str, float] = {}
        for period in resp.get("ResultsByTime", []):
            for group in period.get("Groups", []):
                keys = group.get("Keys", [])
                if keys:
                    acct_id = keys[0]
                    amount = float(group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0))
                    result[acct_id] = result.get(acct_id, 0.0) + amount
        return result
    except Exception as e:
        logger.warning("Failed to fetch account cost breakdown: %s", e)
        return {}


class CostAnomalyChecker(BaseChecker):
    report_section_title = "COST ANOMALIES"
    issue_label = "cost anomalies"
    recommendation_text = "COST REVIEW: Investigate cost anomalies"

    def __init__(self, region="us-east-1", **kwargs):
        super().__init__(region, **kwargs)

    def check(self, profile, account_id):
        """Check cost anomalies"""
        try:
            session = self._get_session(profile)
            ce = session.client("ce", region_name="us-east-1")

            # Get anomaly monitors
            monitors = ce.get_anomaly_monitors()
            monitor_list = monitors.get("AnomalyMonitors", [])

            # Get anomalies from yesterday and today (UTC — Cost Explorer uses UTC dates)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

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

            # Fetch per-account cost breakdown for all anomalies
            # Collect all linked accounts and date range across all anomalies
            account_costs: dict[str, float] = {}
            if all_anomalies:
                all_linked_ids: list[str] = []
                start_dates: list[str] = []
                end_dates: list[str] = []
                for anomaly in all_anomalies:
                    root_causes = anomaly.get("RootCauses", [])
                    for rc in root_causes:
                        aid = rc.get("LinkedAccount", "")
                        if aid and aid not in all_linked_ids:
                            all_linked_ids.append(aid)
                    s = anomaly.get("AnomalyStartDate", "")
                    e = anomaly.get("AnomalyEndDate") or s
                    if s:
                        start_dates.append(s)
                    if e:
                        end_dates.append(e)

                if all_linked_ids and start_dates:
                    range_start = min(start_dates)
                    range_end = max(end_dates) if end_dates else max(start_dates)
                    account_costs = _fetch_account_costs(ce, all_linked_ids, range_start, range_end)

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
                "account_costs": account_costs,
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
        """Format cost anomalies — single/specific check notification format."""
        if results["status"] == "error":
            return f"ERROR: {results['error']}"

        anomalies = results.get("anomalies", [])
        account_costs = results.get("account_costs", {})

        # Use injected display name if available (set by executor after check completes)
        display_name = results.get("_account_display_name") or results.get("profile", "")
        aws_id = results.get("_account_aws_id") or results.get("account_id", "")

        now_jkt = datetime.now(_WIB)
        if 5 <= now_jkt.hour < 11:
            greeting = "Selamat pagi"
        elif 11 <= now_jkt.hour < 15:
            greeting = "Selamat siang"
        elif 15 <= now_jkt.hour < 18:
            greeting = "Selamat sore"
        else:
            greeting = "Selamat malam"

        account_label = f"{display_name} ({aws_id})" if aws_id else display_name

        lines = []
        lines.append(f"{greeting},")
        lines.append("")
        lines.append("Izin menginformasikan terdapat alert AWS Cost Anomaly Detection "
                     "dari AWS pada layanan di akun berikut:")
        lines.append("")
        lines.append(account_label)
        lines.append("")

        if not anomalies:
            lines.append("No cost anomalies detected.")
            return "\n".join(lines)

        total_impact = sum(
            float(a.get("Impact", {}).get("TotalImpact", 0))
            for a in anomalies
        )
        lines.append(f"Detail Anomali ({results['total_anomalies']} detected, "
                     f"total impact: ${total_impact:,.2f}):")
        lines.append("")

        for idx, anomaly in enumerate(anomalies, 1):
            impact = anomaly.get("Impact", {})
            impact_val = float(impact.get("TotalImpact", 0))
            impact_pct = impact.get("TotalImpactPercentage")
            max_impact = impact.get("MaxImpact")
            start_date = anomaly.get("AnomalyStartDate", "N/A")
            end_date = anomaly.get("AnomalyEndDate") or start_date
            score = anomaly.get("AnomalyScore", {}).get("CurrentScore", "N/A")
            root_causes = anomaly.get("RootCauses", [])
            by_account = _root_causes_by_account(root_causes)

            lines.append(f"[{idx}] {anomaly.get('MonitorName', 'N/A')}")
            lines.append(f"    Period     : {_fmt_date_range(start_date, end_date)}")
            impact_line = f"    Impact     : ${impact_val:,.2f}"
            if impact_pct:
                impact_line += f" (+{impact_pct:.1f}%)"
            if max_impact:
                impact_line += f" | Peak: ${float(max_impact):,.2f}/day"
            lines.append(impact_line)
            lines.append(f"    Score      : {score} ({_score_label(score)})")

            if by_account:
                lines.append(f"    Contributors ({len(by_account)} accounts):")
                for acct_id, info in by_account.items():
                    name = info["name"]
                    label = f"{name} ({acct_id})" if name else acct_id
                    cost = account_costs.get(acct_id)
                    cost_str = f"  →  ${cost:,.2f}" if cost is not None else ""
                    lines.append(f"      • {label}{cost_str}")
                    for svc in info["services"]:
                        lines.append(f"          - {svc}")

            lines.append("")

        return "\n".join(lines).rstrip()

    def count_issues(self, result: dict) -> int:
        """Count cost anomalies — prefer today's count, fall back to total."""
        if result.get("status") == "error":
            return 0
        today_count = result.get("today_anomaly_count", 0) or 0
        if today_count > 0:
            return int(today_count)
        return int(result.get("total_anomalies", 0) or 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render COST ANOMALIES section for consolidated (detailed) report."""
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
            return lines

        lines.append(f"Status: ATTENTION REQUIRED - {total_anomalies} anomaly(ies) detected")
        lines.append("")
        lines.append("Detected Anomalies:")

        for profile, cost_data in all_results.items():
            if cost_data.get("total_anomalies", 0) == 0:
                continue
            account_costs = cost_data.get("account_costs", {})

            for anomaly in cost_data.get("anomalies", []):
                impact = anomaly.get("Impact", {})
                impact_val = float(impact.get("TotalImpact", 0))
                impact_pct = impact.get("TotalImpactPercentage")
                max_impact = impact.get("MaxImpact")
                start = anomaly.get("AnomalyStartDate", "N/A")
                end = anomaly.get("AnomalyEndDate") or start
                score = anomaly.get("AnomalyScore", {}).get("CurrentScore", "N/A")
                root_causes = anomaly.get("RootCauses", [])
                by_account = _root_causes_by_account(root_causes)

                impact_str = f"${impact_val:,.2f}"
                if impact_pct:
                    impact_str += f" (+{impact_pct:.1f}%)"
                if max_impact:
                    impact_str += f" | Peak: ${float(max_impact):,.2f}/day"

                lines.append(f"    Monitor  : {anomaly.get('MonitorName', 'N/A')}")
                lines.append(f"    Period   : {_fmt_date_range(start, end)}")
                lines.append(f"    Impact   : {impact_str}")
                lines.append(f"    Score    : {score} ({_score_label(score)})")

                if by_account:
                    lines.append(f"    Contributors ({len(by_account)} accounts):")
                    for acct_id, info in by_account.items():
                        name = info["name"]
                        label = f"{name} ({acct_id})" if name else acct_id
                        cost = account_costs.get(acct_id)
                        cost_str = f"  →  ${cost:,.2f}" if cost is not None else ""
                        lines.append(f"      • {label}{cost_str}")
                        for svc in info["services"]:
                            lines.append(f"          - {svc}")

                lines.append("")

        return lines
