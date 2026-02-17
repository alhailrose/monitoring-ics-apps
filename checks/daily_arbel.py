"""Daily Arbel checker (ACU/CPU/FreeableMemory/Connections) with thresholds per account."""

import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from .base import BaseChecker
from monitoring_hub.customers.loader import find_customer_account


JKT = ZoneInfo("Asia/Jakarta")
PERIOD_SECONDS = 60  # 1 menit untuk detail lebih tinggi


# Thresholds per account key/profile
ACCOUNT_CONFIG = {
    "connect-prod": {
        "account_name": "CONNECT Prod (Non CIS)",
        "cluster_id": "noncis-prod-rds",
        "instances": {"writer": None},  # auto-detect writer
        "metrics": [
            "ACUUtilization",
            "CPUUtilization",
            "FreeableMemory",
            "DatabaseConnections",
        ],
        "thresholds": {
            "FreeableMemory": 10 * 1024**3,
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
        "metrics": [
            "ACUUtilization",
            "CPUUtilization",
            "FreeableMemory",
            "DatabaseConnections",
        ],
        "thresholds": {
            "FreeableMemory": 20 * 1024**3,
            "ACUUtilization": 75,
            "CPUUtilization": 75,
            "DatabaseConnections": 3000,
        },
    },
    "dermies-max": {
        "account_name": "DERMIES MAX",
        "cluster_id": "dermies-prod-rds",
        "instances": {
            "writer": "dermies-prod-rds",
            "reader": "dermies-prod-rds-reader",
        },
        "metrics": [
            "ACUUtilization",
            "CPUUtilization",
            "FreeableMemory",
            "DatabaseConnections",
        ],
        "thresholds": {
            "FreeableMemory": 10 * 1024**3,
            "ACUUtilization": 75,
            "CPUUtilization": 75,
            "DatabaseConnections": 1500,
        },
    },
    "erha-buddy": {
        "account_name": "ERHA BUDDY",
        "instances": {
            "prod": "erhabuddy-prod-mysql-db",
        },
        "metrics": [
            "CPUUtilization",
            "FreeableMemory",
            "DatabaseConnections",
            "FreeStorageSpace",
        ],
        "thresholds": {
            "FreeableMemory": 800 * 1024**2,  # 800 MB (~10% of 8GB)
            "CPUUtilization": 75,
            "DatabaseConnections": 500,
            "FreeStorageSpace": 10 * 1024**3,  # 10 GB (of 178GB allocated)
        },
    },
    "public-web": {
        "account_name": "PUBLIC WEB",
        "instances": {
            "mysql-prod": "mysql-prod-instance",
            "postgre-prod": "postgre-prod-instance",
        },
        "metrics": [
            "CPUUtilization",
            "FreeableMemory",
            "DatabaseConnections",
            "FreeStorageSpace",
        ],
        "thresholds": {
            "FreeableMemory": 200 * 1024**2,  # 200 MB (~10% of 2GB, smallest instance)
            "CPUUtilization": 75,
            "DatabaseConnections": 500,
            "FreeStorageSpace": 5 * 1024**3,  # 5 GB (of 20GB allocated)
        },
    },
}

METRIC_UNITS = {
    "ACUUtilization": "Percent",
    "CPUUtilization": "Percent",
    "FreeableMemory": "Bytes",
    "DatabaseConnections": "Count",
    "FreeStorageSpace": "Bytes",
}


def now_jkt():
    return datetime.now(timezone.utc).astimezone(JKT)


def human_bytes(b):
    return f"{b / (1024**3):.1f} GB"


def get_writer_instance(rds_client, cluster_id):
    try:
        clusters = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)[
            "DBClusters"
        ]
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


class DailyArbelChecker(BaseChecker):
    def __init__(
        self, region: str = "ap-southeast-3", window_hours: int = 12, **kwargs
    ):
        super().__init__(region, **kwargs)
        self.window_hours = window_hours

    def _fetch_metrics(self, cw_client, instance_id, metric_names, profile=None):
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=self.window_hours)

        queries = []
        id_base = instance_id.replace("-", "_").replace(".", "_")
        for m in metric_names:
            queries.append(build_metric_query(id_base, m, instance_id, "Average"))

        resp = cw_client.get_metric_data(
            MetricDataQueries=queries,
            StartTime=start,
            EndTime=end,
            ScanBy="TimestampDescending",
        )

        results = {m: {"values": [], "timestamps": []} for m in metric_names}

        for item in resp.get("MetricDataResults", []):
            mid = item.get("Id", "")
            metric_name = next((m for m in metric_names if m.lower() in mid), None)
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

    def _resolve_account_config(self, profile, account_id):
        customer_account = None
        try:
            customer_account = find_customer_account("aryanoble", account_id)
        except Exception:
            customer_account = None

        if customer_account:
            daily = customer_account.get("daily_arbel") or {}
            return {
                "account_name": customer_account.get("display_name", profile),
                "cluster_id": daily.get("cluster_id"),
                "instances": daily.get("instances", {}),
                "metrics": daily.get("metrics", []),
                "thresholds": daily.get("thresholds", {}),
            }

        return ACCOUNT_CONFIG.get(profile)

    def _breach_detail(self, info, thresholds, metric, comparator, profile=None):
        """Return list of breach periods with (start_time, end_time, peak_val)."""
        vals = info.get("values", [])
        timestamps = info.get("timestamps", [])

        if comparator == "above":
            breached = [
                (t, v) for t, v in zip(timestamps, vals) if v > thresholds[metric]
            ]
        else:
            breached = [
                (t, v) for t, v in zip(timestamps, vals) if v < thresholds[metric]
            ]
        if not breached:
            return None

        # Group consecutive breaches into periods (gap > 5 menit = periode baru)
        periods = []
        current_period = [breached[0]]

        for i in range(1, len(breached)):
            time_gap = (breached[i][0] - breached[i - 1][0]).total_seconds() / 60
            if time_gap <= 5:  # Masih dalam periode yang sama
                current_period.append(breached[i])
            else:  # Periode baru
                periods.append(current_period)
                current_period = [breached[i]]
        periods.append(current_period)

        # Format setiap periode
        result = []
        for period in periods:
            if comparator == "above":
                peak = max(period, key=lambda x: x[1])
            else:
                peak = min(period, key=lambda x: x[1])

            start_time = period[0][0].astimezone(JKT).strftime("%H:%M")
            end_time = period[-1][0].astimezone(JKT).strftime("%H:%M")
            peak_val = peak[1]

            # Hitung durasi dalam menit
            duration = int((period[-1][0] - period[0][0]).total_seconds() / 60)

            result.append((peak_val, start_time, end_time, duration))

        return result

    def _evaluate_metric(self, metric, info, thresholds, profile=None):
        vals = info.get("values") or []
        if not vals:
            return "no-data", "Data tidak tersedia"

        # Gunakan nilai terbaru (real-time)
        last = info.get("last")
        thr = thresholds[metric]

        if metric in ("ACUUtilization", "CPUUtilization"):
            label = (
                "ACU Utilization" if metric == "ACUUtilization" else "CPU Utilization"
            )
            bd = self._breach_detail(info, thresholds, metric, "above", profile)
            # Filter: hanya tampilkan breach >= 10 menit
            if bd:
                bd = [p for p in bd if p[3] >= 10]

            if last > thr:
                msg = f"{label}: {last:.0f}% (di atas {int(thr)}%)"
                if bd:
                    breach_info = ", ".join(
                        [
                            f"{p[0]:.0f}% pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                            for p in bd
                        ]
                    )
                    msg += f" | {breach_info}"
                return "warn", msg
            if bd:
                breach_info = ", ".join(
                    [f"{p[0]:.0f}% pukul {p[1]}-{p[2]} WIB ({p[3]} menit)" for p in bd]
                )
                return (
                    "past-warn",
                    f"{label}: {last:.0f}% (sekarang normal, sempat > {int(thr)}% | {breach_info})",
                )
            return "ok", f"{label}: {last:.0f}% (normal)"

        if metric == "FreeableMemory":
            label = "Freeable Memory"
            bd = self._breach_detail(info, thresholds, metric, "below", profile)
            # Filter: hanya tampilkan breach >= 10 menit
            if bd:
                bd = [p for p in bd if p[3] >= 10]

            if last < thr:
                msg = f"{label}: {human_bytes(last)} (rendah < {human_bytes(thr)})"
                if bd:
                    breach_info = ", ".join(
                        [
                            f"{human_bytes(p[0])} pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                            for p in bd
                        ]
                    )
                    msg += f" | {breach_info}"
                return "warn", msg
            if bd:
                breach_info = ", ".join(
                    [
                        f"{human_bytes(p[0])} pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                        for p in bd
                    ]
                )
                return (
                    "past-warn",
                    f"{label}: {human_bytes(last)} (sekarang normal, sempat < {human_bytes(thr)} | {breach_info})",
                )
            return "ok", f"{label}: {human_bytes(last)} (normal)"

        if metric == "DatabaseConnections":
            label = "DB Connections"
            bd = self._breach_detail(info, thresholds, metric, "above", profile)
            # Filter: hanya tampilkan breach >= 10 menit
            if bd:
                bd = [p for p in bd if p[3] >= 10]

            if last > thr:
                msg = f"{label}: {int(last)} (di atas {thr})"
                if bd:
                    breach_info = ", ".join(
                        [
                            f"{int(p[0])} connections pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                            for p in bd
                        ]
                    )
                    msg += f" | {breach_info}"
                return "warn", msg
            if bd:
                breach_info = ", ".join(
                    [
                        f"{int(p[0])} connections pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                        for p in bd
                    ]
                )
                return (
                    "past-warn",
                    f"{label}: {int(last)} (sekarang normal, sempat > {thr} | {breach_info})",
                )
            return "ok", f"{label}: {int(last)} (normal)"

        if metric == "FreeStorageSpace":
            label = "Free Storage"
            bd = self._breach_detail(info, thresholds, metric, "below", profile)
            # Filter: hanya tampilkan breach >= 10 menit
            if bd:
                bd = [p for p in bd if p[3] >= 10]

            if last < thr:
                msg = f"{label}: {human_bytes(last)} (rendah < {human_bytes(thr)})"
                if bd:
                    breach_info = ", ".join(
                        [
                            f"{human_bytes(p[0])} pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                            for p in bd
                        ]
                    )
                    msg += f" | {breach_info}"
                return "warn", msg
            if bd:
                breach_info = ", ".join(
                    [
                        f"{human_bytes(p[0])} pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                        for p in bd
                    ]
                )
                return (
                    "past-warn",
                    f"{label}: {human_bytes(last)} (sekarang normal, sempat < {human_bytes(thr)} | {breach_info})",
                )
            return "ok", f"{label}: {human_bytes(last)} (normal)"

        return "no-data", f"{metric}: Data tidak tersedia"

    def check(self, profile, account_id):
        cfg = self._resolve_account_config(profile, account_id)
        if not cfg:
            return {
                "status": "skipped",
                "reason": "profile not configured",
                "profile": profile,
                "account_id": account_id,
            }

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
                    instance_reports[role] = {
                        "status": "no-data",
                        "message": "Instance not found",
                    }
                    continue

                metrics_info = self._fetch_metrics(cw, inst_id, cfg["metrics"], profile)
                evaluations = {}
                for metric_name in cfg["metrics"]:
                    status, msg = self._evaluate_metric(
                        metric_name,
                        metrics_info.get(metric_name, {}),
                        cfg["thresholds"],
                        profile,
                    )
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
                "window_hours": self.window_hours,
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
            return f"Daily Arbel skipped: {results.get('reason')}"
        if results.get("status") == "error":
            return f"ERROR: {results.get('error')}"

        now = now_jkt()
        # Perbaiki greeting: Pagi (5-11), Siang (11-15), Sore (15-18), Malam (18-5)
        if 5 <= now.hour < 11:
            greeting = "Selamat Pagi"
            waktu = "Pagi"
        elif 11 <= now.hour < 15:
            greeting = "Selamat Siang"
            waktu = "Siang"
        elif 15 <= now.hour < 18:
            greeting = "Selamat Sore"
            waktu = "Sore"
        else:
            greeting = "Selamat Malam"
            waktu = "Malam"

        date_str = now.strftime("%d-%m-%Y")
        time_str = now.strftime("%H:%M WIB")
        acct_name = results.get("account_name", results.get("profile"))
        acct_id = results.get("account_id", "")
        profile = results.get("profile", "")

        lines: List[str] = []
        lines.append(f"{greeting} Team,")

        # Tambahkan info monitoring window
        lines.append(
            f"Berikut Daily report untuk akun id {acct_name} ({acct_id}) pada {waktu} ini (Data per {time_str}, monitoring {self.window_hours} jam terakhir)"
        )

        lines.append(date_str)
        lines.append("")
        lines.append("Summary:")

        instances = results.get("instances", {})
        for role, data in instances.items():
            lines.append("")
            lines.append(f"{role.capitalize()} ({data.get('instance_id', 'N/A')}):")
            metrics = data.get("metrics", {})
            for metric_name, info in metrics.items():
                lines.append(f"* {info.get('message')}")

        return "\n".join(lines)
