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
        """Format cost anomalies — full detail for specific/single check mode."""
        if results["status"] == "error":
            return f"ERROR: {results['error']}"

        profile = results["profile"]
        account_id = results.get("account_id", "Unknown")
        anomalies = results.get("anomalies", [])
        now_wib = datetime.now(_WIB).strftime("%d %b %Y %H:%M WIB")

        lines = []
        lines.append(f"┌─ COST ANOMALY CHECK")
        lines.append(f"│  Profil     : {profile} ({account_id})")
        lines.append(f"│  Diperiksa  : {now_wib}")
        lines.append(f"│  Monitor    : {results['total_monitors']} aktif")
        lines.append(f"│  Anomali    : {results['total_anomalies']} terdeteksi "
                     f"(hari ini: {results.get('today_anomaly_count', 0)}, "
                     f"kemarin: {results.get('yesterday_anomaly_count', 0)})")

        if not anomalies:
            lines.append("└─ Status: ✓ Tidak ada anomali biaya")
            return "\n".join(lines)

        total_impact = sum(
            float(a.get("Impact", {}).get("TotalImpact", 0))
            for a in anomalies
        )
        lines.append(f"│  Total Dampak: ${total_impact:,.2f}")
        lines.append("└─ Status: ⚠ Anomali ditemukan — detail di bawah")
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
            linked_accounts = _linked_accounts(root_causes)

            lines.append(f"  [{idx}] {anomaly.get('MonitorName', 'N/A')}")
            lines.append(f"      Periode   : {_fmt_date_range(start_date, end_date)}")
            lines.append(f"      Dampak    : ${impact_val:,.2f}" +
                         (f" (+{impact_pct:.1f}%)" if impact_pct else "") +
                         (f" | Puncak: ${float(max_impact):,.2f}/hari" if max_impact else ""))
            lines.append(f"      Skor      : {score} ({_score_label(score)})")

            # Linked accounts — penting untuk payer account
            if linked_accounts:
                if len(linked_accounts) == 1:
                    a = linked_accounts[0]
                    label = f"{a['name']} ({a['id']})" if a['name'] else a['id']
                    lines.append(f"      Akun      : {label}")
                else:
                    lines.append(f"      Akun ({len(linked_accounts)}):")
                    for a in linked_accounts:
                        label = f"{a['name']} ({a['id']})" if a['name'] else a['id']
                        lines.append(f"        • {label}")

            # Root causes
            if root_causes:
                seen_services = set()
                service_details = []
                for rc in root_causes:
                    svc = rc.get("Service", "")
                    region = rc.get("Region", "")
                    usage = rc.get("UsageType", "")
                    key = f"{svc}|{usage}"
                    if key not in seen_services:
                        seen_services.add(key)
                        parts = [svc]
                        if region:
                            parts.append(region)
                        if usage:
                            parts.append(usage)
                        service_details.append(" / ".join(p for p in parts if p))

                lines.append(f"      Penyebab  :")
                for detail in service_details[:5]:
                    lines.append(f"        • {detail}")
                if len(service_details) > 5:
                    lines.append(f"        ... dan {len(service_details) - 5} lainnya")

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
        """Render COST ANOMALIES section for consolidated (bundled) report."""
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
            lines.append(f"Status: ATTENTION REQUIRED - {total_anomalies} anomalies detected")
            lines.append("")
            lines.append("Detected Anomalies:")
            for profile, cost_data in all_results.items():
                if cost_data.get("total_anomalies", 0) == 0:
                    continue
                account_id = cost_data.get("account_id", "Unknown")
                lines.append(f"  * {profile} ({account_id}): {cost_data['total_anomalies']} anomali")
                for anomaly in cost_data.get("anomalies", [])[:3]:
                    impact = anomaly.get("Impact", {})
                    impact_val = float(impact.get("TotalImpact", 0))
                    impact_pct = impact.get("TotalImpactPercentage")
                    start = anomaly.get("AnomalyStartDate", "N/A")
                    end = anomaly.get("AnomalyEndDate") or start
                    root_causes = anomaly.get("RootCauses", [])
                    linked_accounts = _linked_accounts(root_causes)

                    pct_str = f" (+{impact_pct:.1f}%)" if impact_pct else ""
                    lines.append(f"    - Monitor : {anomaly.get('MonitorName', 'N/A')}")
                    lines.append(f"    - Periode : {_fmt_date_range(start, end)}")
                    lines.append(f"    - Dampak  : ${impact_val:,.2f}{pct_str}")

                    # Linked accounts untuk payer
                    if linked_accounts:
                        acct_labels = []
                        for a in linked_accounts[:3]:
                            acct_labels.append(f"{a['name']} ({a['id']})" if a['name'] else a['id'])
                        lines.append(f"    - Akun    : {', '.join(acct_labels)}")
                        if len(linked_accounts) > 3:
                            lines.append(f"               ... dan {len(linked_accounts) - 3} akun lain")

                    if root_causes:
                        services = list(dict.fromkeys(
                            rc.get("Service", "N/A") for rc in root_causes if rc.get("Service")
                        ))
                        top = root_causes[0]
                        lines.append(f"    - Service : {', '.join(services[:3])}")
                        usage = top.get("UsageType", "")
                        if usage:
                            lines.append(f"    - Usage   : {usage}")
                    lines.append("")

        return lines
