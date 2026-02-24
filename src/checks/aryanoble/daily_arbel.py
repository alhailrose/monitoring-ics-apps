"""Daily Arbel checker (ACU/CPU/FreeableMemory/Connections) with thresholds per account."""

import logging
import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from src.checks.common.base import BaseChecker
from src.checks.common.aws_errors import is_credential_error
from src.configs.loader import find_customer_account

logger = logging.getLogger(__name__)


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
        "alarm_thresholds": {
            "writer": {
                "FreeableMemory": "noncis-prod-rds-freeable-memory-alarm",
            }
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
        "alarm_thresholds": {
            "writer": {
                "FreeableMemory": "cis-prod-rds-memory-writer-alarm",
            },
            "reader": {
                "FreeableMemory": "cis-prod-rds-memory-reader-alarm",
            },
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
        "alarm_thresholds": {
            "writer": {
                "FreeableMemory": "dermies-prod-rds-writer-freeable-memory-alarm",
            },
            "reader": {
                "FreeableMemory": "dermies-prod-rds-reader-freeable-memory-alarm",
            },
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
        "alarm_thresholds": {
            "prod": {
                "FreeableMemory": "erhabuddy-prod-rds-freeable-memory-alarm",
            }
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
    "ServerlessDatabaseCapacity": "Count",
    "BufferCacheHitRatio": "Percent",
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
    except Exception as e:
        logger.warning("Failed to detect writer instance for cluster %s: %s", cluster_id, e)
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
        except FileNotFoundError:
            customer_account = None
        except Exception as e:
            logger.warning("Failed to load customer config for %s/%s: %s", profile, account_id, e)
            customer_account = None

        if customer_account:
            daily = customer_account.get("daily_arbel") or {}
            return {
                "account_name": customer_account.get("display_name", profile),
                "cluster_id": daily.get("cluster_id"),
                "instances": daily.get("instances", {}),
                "metrics": daily.get("metrics", []),
                "thresholds": daily.get("thresholds", {}),
                "role_thresholds": daily.get("role_thresholds", {}),
            }

        return ACCOUNT_CONFIG.get(profile)

    def _alarm_threshold_for_role(self, cw_client, profile, role, metric_name):
        cfg = ACCOUNT_CONFIG.get(profile, {})
        role_alarm_map = cfg.get("alarm_thresholds", {}).get(role, {})
        alarm_name = role_alarm_map.get(metric_name)
        if not alarm_name:
            return None

        try:
            resp = cw_client.describe_alarms(AlarmNames=[alarm_name])
            alarms = resp.get("MetricAlarms", [])
            if not alarms:
                return None

            threshold = alarms[0].get("Threshold")
            if isinstance(threshold, (int, float)):
                return float(threshold)
        except Exception as e:
            logger.warning("Failed to resolve alarm threshold for %s/%s/%s: %s", profile, role, metric_name, e)
            return None

        return None

    def _resolve_role_thresholds(self, cw_client, profile, role, base_thresholds, role_thresholds=None):
        resolved = dict(base_thresholds)
        # Apply per-role overrides from customer config first
        if role_thresholds and role in role_thresholds:
            resolved.update(role_thresholds[role])
        # Then try alarm-based threshold (takes priority if available)
        fm_threshold = self._alarm_threshold_for_role(
            cw_client,
            profile,
            role,
            "FreeableMemory",
        )
        if fm_threshold is not None:
            resolved["FreeableMemory"] = fm_threshold
        return resolved

    def _alarm_name_for_role_metric(self, profile, role, metric_name):
        cfg = ACCOUNT_CONFIG.get(profile, {})
        return cfg.get("alarm_thresholds", {}).get(role, {}).get(metric_name)

    def _extract_alarm_periods(
        self,
        history_items,
        now_utc,
        window_start_utc,
        current_state=None,
    ):
        events = []
        for item in history_items or []:
            summary = item.get("HistorySummary", "")
            ts = item.get("Timestamp")
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            if "to ALARM" in summary:
                events.append((ts, "start"))
            elif "ALARM to OK" in summary or "to OK" in summary:
                events.append((ts, "end"))

        events.sort(key=lambda x: x[0])
        periods = []
        active_start = None

        for ts, kind in events:
            if kind == "start":
                active_start = ts
                continue

            if kind == "end":
                if active_start is None:
                    active_start = window_start_utc
                if ts < active_start:
                    continue
                duration = max(1, int((ts - active_start).total_seconds() // 60))
                periods.append(
                    (
                        0.0,
                        active_start.astimezone(JKT).strftime("%H:%M"),
                        ts.astimezone(JKT).strftime("%H:%M"),
                        duration,
                    )
                )
                active_start = None

        if active_start is not None or current_state == "ALARM":
            if active_start is None:
                active_start = window_start_utc
            duration = max(1, int((now_utc - active_start).total_seconds() // 60))
            periods.append(
                (
                    0.0,
                    active_start.astimezone(JKT).strftime("%H:%M"),
                    "now",
                    duration,
                )
            )

        return periods

    def _resolve_role_alarm_periods(self, cw_client, profile, role):
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(hours=self.window_hours)
        out = {}

        role_metric_map = (
            ACCOUNT_CONFIG.get(profile, {}).get("alarm_thresholds", {}).get(role, {})
        )
        for metric_name, alarm_name in role_metric_map.items():
            if not alarm_name:
                continue
            try:
                alarm_state = "OK"
                described = cw_client.describe_alarms(AlarmNames=[alarm_name])
                metric_alarms = described.get("MetricAlarms", [])
                if metric_alarms:
                    alarm_state = metric_alarms[0].get("StateValue", "OK")

                history = cw_client.describe_alarm_history(
                    AlarmName=alarm_name,
                    HistoryItemType="StateUpdate",
                    StartDate=start_utc,
                    EndDate=now_utc,
                    ScanBy="TimestampDescending",
                ).get("AlarmHistoryItems", [])
                out[metric_name] = self._extract_alarm_periods(
                    history,
                    now_utc,
                    start_utc,
                    current_state=alarm_state,
                )
            except Exception as e:
                logger.warning("Failed to get alarm history for %s/%s/%s: %s", profile, role, alarm_name, e)
                out[metric_name] = []

        return out

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
            alarm_periods = info.get("alarm_periods") or []
            bd = alarm_periods or self._breach_detail(
                info, thresholds, metric, "above", profile
            )
            # Filter: hanya tampilkan breach >= 10 menit
            if bd:
                bd = [p for p in bd if p[3] >= 10]

            if last > thr:
                msg = f"{label}: {last:.0f}% (di atas {int(thr)}%)"
                if bd:
                    if alarm_periods:
                        breach_info = ", ".join(
                            [
                                f"ALARM pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                                for p in bd
                            ]
                        )
                    else:
                        breach_info = ", ".join(
                            [
                                f"{p[0]:.0f}% pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                                for p in bd
                            ]
                        )
                    msg += f" | {breach_info}"
                return "warn", msg
            if bd:
                if alarm_periods:
                    breach_info = ", ".join(
                        [f"ALARM pukul {p[1]}-{p[2]} WIB ({p[3]} menit)" for p in bd]
                    )
                else:
                    breach_info = ", ".join(
                        [
                            f"{p[0]:.0f}% pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                            for p in bd
                        ]
                    )
                return (
                    "past-warn",
                    f"{label}: {last:.0f}% (sekarang normal, sempat > {int(thr)}% | {breach_info})",
                )
            return "ok", f"{label}: {last:.0f}% (normal)"

        if metric == "FreeableMemory":
            label = "Freeable Memory"
            alarm_periods = info.get("alarm_periods") or []
            bd = alarm_periods or self._breach_detail(
                info, thresholds, metric, "below", profile
            )
            # Filter: hanya tampilkan breach >= 10 menit
            if bd:
                bd = [p for p in bd if p[3] >= 10]

            if last < thr:
                msg = f"{label}: {human_bytes(last)} (rendah < {human_bytes(thr)})"
                if bd:
                    if alarm_periods:
                        breach_info = ", ".join(
                            [
                                f"ALARM pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                                for p in bd
                            ]
                        )
                    else:
                        breach_info = ", ".join(
                            [
                                f"{human_bytes(p[0])} pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                                for p in bd
                            ]
                        )
                    msg += f" | {breach_info}"
                return "warn", msg
            if bd:
                if alarm_periods:
                    breach_info = ", ".join(
                        [f"ALARM pukul {p[1]}-{p[2]} WIB ({p[3]} menit)" for p in bd]
                    )
                else:
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

        if metric == "ServerlessDatabaseCapacity":
            label = "Serverless DB Capacity"
            alarm_periods = info.get("alarm_periods") or []
            bd = alarm_periods or self._breach_detail(
                info, thresholds, metric, "above", profile
            )
            if bd:
                bd = [p for p in bd if p[3] >= 10]

            if last > thr:
                msg = f"{label}: {last:.1f} ACU (di atas {int(thr)} ACU)"
                if bd:
                    if alarm_periods:
                        breach_info = ", ".join(
                            [
                                f"ALARM pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                                for p in bd
                            ]
                        )
                    else:
                        breach_info = ", ".join(
                            [
                                f"{p[0]:.1f} ACU pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                                for p in bd
                            ]
                        )
                    msg += f" | {breach_info}"
                return "warn", msg
            if bd:
                if alarm_periods:
                    breach_info = ", ".join(
                        [f"ALARM pukul {p[1]}-{p[2]} WIB ({p[3]} menit)" for p in bd]
                    )
                else:
                    breach_info = ", ".join(
                        [
                            f"{p[0]:.1f} ACU pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                            for p in bd
                        ]
                    )
                return (
                    "past-warn",
                    f"{label}: {last:.1f} ACU (sekarang normal, sempat > {int(thr)} ACU | {breach_info})",
                )
            return "ok", f"{label}: {last:.1f} ACU (normal)"

        if metric == "BufferCacheHitRatio":
            label = "Buffer Cache Hit Ratio"
            alarm_periods = info.get("alarm_periods") or []
            bd = alarm_periods or self._breach_detail(
                info, thresholds, metric, "below", profile
            )
            if bd:
                bd = [p for p in bd if p[3] >= 10]

            if last < thr:
                msg = f"{label}: {last:.1f}% (rendah < {int(thr)}%)"
                if bd:
                    if alarm_periods:
                        breach_info = ", ".join(
                            [
                                f"ALARM pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                                for p in bd
                            ]
                        )
                    else:
                        breach_info = ", ".join(
                            [
                                f"{p[0]:.1f}% pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                                for p in bd
                            ]
                        )
                    msg += f" | {breach_info}"
                return "warn", msg
            if bd:
                if alarm_periods:
                    breach_info = ", ".join(
                        [f"ALARM pukul {p[1]}-{p[2]} WIB ({p[3]} menit)" for p in bd]
                    )
                else:
                    breach_info = ", ".join(
                        [
                            f"{p[0]:.1f}% pukul {p[1]}-{p[2]} WIB ({p[3]} menit)"
                            for p in bd
                        ]
                    )
                return (
                    "past-warn",
                    f"{label}: {last:.1f}% (sekarang normal, sempat < {int(thr)}% | {breach_info})",
                )
            return "ok", f"{label}: {last:.1f}% (normal)"

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
                role_thresholds = self._resolve_role_thresholds(
                    cw,
                    profile,
                    role,
                    cfg["thresholds"],
                    role_thresholds=cfg.get("role_thresholds"),
                )
                role_alarm_periods = self._resolve_role_alarm_periods(cw, profile, role)
                for metric_name, periods in role_alarm_periods.items():
                    if metric_name in metrics_info:
                        metrics_info[metric_name]["alarm_periods"] = periods
                evaluations = {}
                for metric_name in cfg["metrics"]:
                    status, msg = self._evaluate_metric(
                        metric_name,
                        metrics_info.get(metric_name, {}),
                        role_thresholds,
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
            if is_credential_error(e):
                return self._error_result(e, profile, account_id)
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
