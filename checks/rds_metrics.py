"""RDS metric checker (ACU/CPU/FreeableMemory/Connections) with thresholds per account."""
import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from .base import BaseChecker


JKT = ZoneInfo("Asia/Jakarta")
WINDOW_HOURS = 12
PERIOD_SECONDS = 300


# Thresholds per account key/profile
ACCOUNT_CONFIG = {
    "connect-prod": {
        "account_name": "CONNECT Prod (Non CIS)",
        "cluster_id": "noncis-prod-rds",
        "instances": {"writer": None},  # auto-detect writer
        "thresholds": {
            "FreeableMemory": 10 * 1024 ** 3,
            "ACUUtilization": 75,
            "CPUUtilization": 75,
            "DatabaseConnections": 1500,
        },
    },
    "cis-erha": {
        "account_name": "CIS ERHA",
        "cluster_id": "cis-prod-rds",
        "instances": {
            "writer": "cis-prod-rds-instance",
            "reader": "cis-prod-rds-instance-reader",
        },
        "thresholds": {
            "FreeableMemory": 20 * 1024 ** 3,
            "ACUUtilization": 75,
            "CPUUtilization": 75,
            "DatabaseConnections": 3000,
        },
    },
}

METRICS = [
    ("ACUUtilization", "Percent"),
    ("CPUUtilization", "Percent"),
    ("FreeableMemory", "Bytes"),
    ("DatabaseConnections", "Count"),
]


def now_jkt():
    return datetime.now(timezone.utc).astimezone(JKT)


def human_bytes(b):
    return f"{b / (1024**3):.1f} GB"


def get_writer_instance(rds_client, cluster_id):
    try:
        clusters = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)["DBClusters"]
        for cluster in clusters:
            for member in cluster["DBClusterMembers"]:
                if member.get("IsClusterWriter"):
                    return member.get("DBInstanceIdentifier")
    except Exception:
        pass
    return None


def build_metric_query(id_base, metric_name, instance_id, stat):
    return {
        "Id": f"{id_base}_{metric_name.lower()}_{stat.lower()}".replace("-", "_"),
        "MetricStat": {
            "Metric": {
                "Namespace": "AWS/RDS",
                "MetricName": metric_name,
                "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": instance_id}],
            },
            "Period": PERIOD_SECONDS,
            "Stat": stat,
        },
        "ReturnData": True,
    }


class RDSMetricsChecker(BaseChecker):
    def __init__(self, region: str = "ap-southeast-3"):
        super().__init__(region)

    def _fetch_metrics(self, cw_client, instance_id):
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=WINDOW_HOURS)

        queries = []
        id_base = instance_id.replace("-", "_").replace(".", "_")
        for m, _ in METRICS:
            queries.append(build_metric_query(id_base, m, instance_id, "Average"))

        resp = cw_client.get_metric_data(
            MetricDataQueries=queries,
            StartTime=start,
            EndTime=end,
            ScanBy="TimestampDescending",
        )

        results = {m: {"values": [], "timestamps": []} for m, _ in METRICS}

        for item in resp.get("MetricDataResults", []):
            mid = item.get("Id", "")
            metric_name = next((m for m, _ in METRICS if m.lower() in mid), None)
            if not metric_name:
                continue

            times = item.get("Timestamps", [])
            vals = item.get("Values", [])
            pairs = [(t, v) for t, v in zip(times, vals) if start <= t <= end]
            if not pairs:
                continue

            pairs.sort(key=lambda x: x[0])
            ts, vs = zip(*pairs)
            results[metric_name]["timestamps"] = list(ts)
            results[metric_name]["values"] = list(vs)
            results[metric_name]["last"] = vs[-1]
            results[metric_name]["avg"] = sum(vs) / len(vs)
            results[metric_name]["max"] = max(vs)

        return results

    def _evaluate_metric(self, metric, info, thresholds):
        vals = info.get("values") or []
        if not vals:
            return "no-data", "Data tidak tersedia"

        last = info.get("last")
        thr = thresholds[metric]

        if metric in ("ACUUtilization", "CPUUtilization"):
            label = "ACU Utilization" if metric == "ACUUtilization" else "CPU Utilization"
            above = [v for v in vals if v > thr]
            if last > thr:
                return "warn", f"{label}: {last:.0f}% (di atas {int(thr)}%)"
            if above and last <= thr:
                return "past-warn", f"{label}: {last:.0f}% (sempat > {int(thr)}% tapi sudah normal)"
            return "ok", f"{label}: {last:.0f}% (normal)"

        if metric == "FreeableMemory":
            label = "Freeable Memory"
            below = [v for v in vals if v < thr]
            if last < thr:
                return "warn", f"{label}: {human_bytes(last)} (rendah < {human_bytes(thr)})"
            if below and last >= thr:
                return "past-warn", f"{label}: {human_bytes(last)} (sempat < {human_bytes(thr)} tapi sudah normal)"
            return "ok", f"{label}: {human_bytes(last)} (normal)"

        if metric == "DatabaseConnections":
            label = "DB Connections"
            above = [v for v in vals if v > thr]
            if last > thr:
                return "warn", f"{label}: {int(last)} (di atas {thr})"
            if above and last <= thr:
                return "past-warn", f"{label}: {int(last)} (sempat > {thr} tapi sudah normal)"
            return "ok", f"{label}: {int(last)} (normal)"

        return "no-data", f"{metric}: Data tidak tersedia"

    def check(self, profile, account_id):
        if profile not in ACCOUNT_CONFIG:
            return {
                "status": "skipped",
                "reason": "profile not configured",
                "profile": profile,
                "account_id": account_id,
            }

        cfg = ACCOUNT_CONFIG[profile]
        try:
            session = boto3.Session(profile_name=profile, region_name=self.region)
            rds = session.client("rds", region_name=self.region)
            cw = session.client("cloudwatch", region_name=self.region)

            # Resolve instances (auto-detect writer if None)
            instances = dict(cfg["instances"])
            if instances.get("writer") is None and cfg.get("cluster_id"):
                instances["writer"] = get_writer_instance(rds, cfg["cluster_id"])

            instance_reports = {}
            any_warn = False

            for role, inst_id in instances.items():
                if not inst_id:
                    instance_reports[role] = {"status": "no-data", "message": "Instance not found"}
                    continue

                metrics_info = self._fetch_metrics(cw, inst_id)
                evaluations = {}
                for metric_name, _ in METRICS:
                    status, msg = self._evaluate_metric(metric_name, metrics_info.get(metric_name, {}), cfg["thresholds"])
                    evaluations[metric_name] = {"status": status, "message": msg}
                    if status == "warn":
                        any_warn = True

                instance_reports[role] = {
                    "instance_id": inst_id,
                    "metrics": evaluations,
                }

            status = "ATTENTION REQUIRED" if any_warn else "OK"

            return {
                "status": status,
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "account_name": cfg.get("account_name", profile),
                "instances": instance_reports,
            }

        except Exception as e:  # pragma: no cover
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(e),
            }

    def format_report(self, results):
        if results.get("status") == "skipped":
            return f"RDS metrics skipped: {results.get('reason')}"
        if results.get("status") == "error":
            return f"ERROR: {results.get('error')}"

        lines: List[str] = []
        lines.append("AWS RDS METRICS (last 12h)")
        lines.append(f"Region: {results.get('region')}")
        lines.append(f"Account: {results.get('account_name', results.get('profile'))}")

        instances = results.get("instances", {})
        for role, data in instances.items():
            lines.append("")
            lines.append(f"{role.capitalize()} ({data.get('instance_id', 'N/A')}):")
            metrics = data.get("metrics", {})
            for metric_name, info in metrics.items():
                lines.append(f"- {info.get('message')}")

        if results.get("status") == "OK":
            lines.append("")
            lines.append("Status: All monitored RDS metrics are within thresholds")
        else:
            lines.append("")
            lines.append("Status: Attention required on metrics above thresholds")

        return "\n".join(lines)
