"""Daily Arbel checker (ACU/CPU/FreeableMemory/Connections) with thresholds per account."""

from copy import deepcopy
import logging
import re
import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error
from backend.config.loader import find_customer_account

logger = logging.getLogger(__name__)


JKT = ZoneInfo("Asia/Jakarta")
PERIOD_SECONDS = 60  # 1 menit untuk detail lebih tinggi
ALARM_BOLD_MINUTES = 10
_DURATION_PATTERN = re.compile(r"\((\d+)\s+menit\)")
ABOVE_THRESHOLD_METRICS = {
    "ACUUtilization",
    "CPUUtilization",
    "DatabaseConnections",
    "ServerlessDatabaseCapacity",
}
BELOW_THRESHOLD_METRICS = {
    "FreeableMemory",
    "FreeStorageSpace",
    "BufferCacheHitRatio",
}


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
                "CPUUtilization": "EB-MYSQL RDS CPU Utilization > 75%",
                "DatabaseConnections": "EB-MYSQL RDS Connection > 400",
                "FreeableMemory": "EB-MYSQL RDS Free Memory < 400MB",
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
        "alarm_thresholds": {
            "mysql-prod": {
                "CPUUtilization": "WEBAPP-MYSQL RDS CPU Utilization > 75%",
                "DatabaseConnections": "WEBAPP-MYSQL RDS Connection > 80",
                "FreeableMemory": "WEBAPP-MYSQL RDS Free Memory < 400MB",
            },
            "postgre-prod": {
                "CPUUtilization": "WEBAPP-POSTGRES RDS CPU Utilization > 75%",
                "DatabaseConnections": "WEBAPP-POSTGRES RDS Connection > 10",
            },
        },
    },
    "HRIS": {
        "account_name": "HRIS",
        "service_type": "ec2",
        "instances": {
            "webserver": "i-053c5b7302686e05d",
            "database": "i-0a22fd1fc782f71dc",
            "openvpn": "i-00b46080f4270690d",
        },
        "instance_names": {
            "i-053c5b7302686e05d": "webserver",
            "i-0a22fd1fc782f71dc": "database",
            "i-00b46080f4270690d": "openvpn",
        },
        "metrics": ["CPUUtilization", "NetworkIn", "NetworkOut"],
        "thresholds": {"CPUUtilization": 80},
        "alarm_thresholds": {
            "webserver": [
                "aryanoble-prod-Window2019Base-webserver Disk C < 20%",
                "aryanoble-prod-Window2019Base-webserver Disk D < 20%",
                "aryanoble-prod-Window2019Base-webserver-mem-above-80",
            ],
            "database": [
                "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-D-above-80",
                "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-E-above-80",
                "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-F-above-80",
                "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-G-above-80",
                "aryanoble-prod-Windows2019+SQL2019Standard-database-mem-above-80",
            ],
            "openvpn": [
                "aryanoble-prod-Ubuntu20.04-openvpn-disk-above-80",
                "aryanoble-prod-Ubuntu20.04-openvpn-mem-above-80",
            ],
        },
    },
    "sfa": {
        "account_name": "SFA",
        "service_type": "ec2",
        "instances": {
            "vm-sfa": "i-0cb272299353b6831",
            "vm-database": "i-04c34bdd4784173d6",
            "vm-jobs": "i-0e94b988fa5f21e20",
            "vm-dms": "i-0acd6fd06f6ce6dd2",
            "openvpn": "i-044e682eb4257ebbc",
            "openvpn-new": "i-0e24e1e76f539d9f3",
        },
        "instance_names": {
            "i-0cb272299353b6831": "vm-sfa",
            "i-04c34bdd4784173d6": "vm-database",
            "i-0e94b988fa5f21e20": "vm-jobs",
            "i-0acd6fd06f6ce6dd2": "vm-dms",
            "i-044e682eb4257ebbc": "openvpn",
            "i-0e24e1e76f539d9f3": "openvpn-new",
        },
        "metrics": ["CPUUtilization", "NetworkIn", "NetworkOut"],
        "thresholds": {"CPUUtilization": 70},
        "alarm_thresholds": {
            "vm-sfa": [
                "vm-sfa-disk-above-70",
                "vm-sfa-mem-above-70",
            ],
            "vm-database": [
                "vm-database-disk-C:-below-30",
                "vm-database-mem-above-70",
            ],
            "vm-jobs": [
                "vm-jobs-disk-above-70",
                "vm-jobs-mem-above-70",
            ],
            "vm-dms": [
                "vm-dms-disk-C:-below-30",
                "vm-dms-mem-above-70",
            ],
            "openvpn": [
                "sfa-production-openvpn-disk-above-70",
                "sfa-production-openvpn-mem-above-70",
            ],
            "openvpn-new": [
                "sfa-production-openvpn-new-disk-above-70",
                "sfa-production-openvpn-new-mem-above-70",
            ],
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
    "NetworkReceiveThroughput": "Bytes/Second",
    "NetworkTransmitThroughput": "Bytes/Second",
    "NetworkIn": "Bytes",
    "NetworkOut": "Bytes",
}


def now_jkt():
    return datetime.now(timezone.utc).astimezone(JKT)


def human_bytes(b):
    return f"{b / (1024**3):.1f} GB"


def human_network_bytes(b):
    """Format bytes to human-readable network throughput."""
    if b >= 1024 * 1024:
        return f"{b / (1024 * 1024):.2f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b:.0f} B"


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
        logger.warning(
            "Failed to detect writer instance for cluster %s: %s", cluster_id, e
        )
    return None


def build_metric_query(id_base, metric_name, instance_id, stat, service_type="rds"):
    if service_type == "ec2":
        namespace = "AWS/EC2"
        dimension_name = "InstanceId"
    else:
        namespace = "AWS/RDS"
        dimension_name = "DBInstanceIdentifier"
    return {
        "Id": f"{id_base}_{metric_name.lower()}_{stat.lower()}".replace("-", "_"),
        "MetricStat": {
            "Metric": {
                "Namespace": namespace,
                "MetricName": metric_name,
                "Dimensions": [{"Name": dimension_name, "Value": instance_id}],
            },
            "Period": PERIOD_SECONDS,
            "Stat": stat,
        },
        "ReturnData": True,
    }


class DailyArbelChecker(BaseChecker):
    report_section_title = "DAILY ARBEL METRICS"
    issue_label = "metric warnings"
    recommendation_text = "REVIEW: Investigate RDS/EC2 metric warnings"

    def __init__(
        self,
        region: str = "ap-southeast-3",
        window_hours: int = 12,
        section_scope: str = "both",
        **kwargs,
    ):
        super().__init__(region, **kwargs)
        self.window_hours = window_hours
        normalized_scope = (section_scope or "both").strip().lower()
        if normalized_scope not in {"both", "rds", "ec2"}:
            normalized_scope = "both"
        self.section_scope = normalized_scope

        override_source = {}
        nested_override = kwargs.get("daily_arbel")
        if isinstance(nested_override, dict):
            override_source.update(nested_override)

        for key in (
            "account_name",
            "cluster_id",
            "service_type",
            "instances",
            "instance_names",
            "metrics",
            "thresholds",
            "role_thresholds",
            "alarm_thresholds",
            "extra_sections",
        ):
            if key in kwargs:
                override_source[key] = kwargs[key]

        self.account_config_override = (
            override_source if isinstance(override_source, dict) else {}
        )

    def _apply_account_config_override(self, cfg, profile):
        override = self.account_config_override
        if not override:
            return cfg

        if cfg is None:
            cfg_map: dict[str, object] = {
                "account_name": profile,
                "cluster_id": None,
                "service_type": "rds",
                "instances": {},
                "instance_names": {},
                "metrics": [],
                "thresholds": {},
                "role_thresholds": {},
                "alarm_thresholds": {},
                "extra_sections": [],
            }
        else:
            cfg_map = deepcopy(cfg)
            if not isinstance(cfg_map, dict):
                cfg_map = {}

        for key in ("account_name", "cluster_id", "service_type"):
            value = override.get(key)
            if value is not None:
                cfg_map[key] = value

        for key in (
            "instances",
            "instance_names",
            "thresholds",
            "role_thresholds",
            "alarm_thresholds",
        ):
            value = override.get(key)
            if isinstance(value, dict):
                current = cfg_map.get(key)
                if not isinstance(current, dict):
                    current = {}
                current.update(deepcopy(value))
                cfg_map[key] = current

        for key in ("metrics", "extra_sections"):
            value = override.get(key)
            if isinstance(value, list):
                cfg_map[key] = deepcopy(value)

        return cfg_map

    def _fetch_metrics(
        self, cw_client, instance_id, metric_names, profile=None, service_type="rds"
    ):
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=self.window_hours)

        queries = []
        id_base = instance_id.replace("-", "_").replace(".", "_")
        for m in metric_names:
            queries.append(
                build_metric_query(
                    id_base, m, instance_id, "Average", service_type=service_type
                )
            )

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
            logger.warning(
                "Failed to load customer config for %s/%s: %s", profile, account_id, e
            )
            customer_account = None

        if customer_account:
            daily = customer_account.get("daily_arbel") or {}
            extra_sections = customer_account.get("daily_arbel_extra") or []
            base_cfg = {
                "account_name": customer_account.get("display_name", profile),
                "cluster_id": daily.get("cluster_id"),
                "service_type": daily.get("service_type", "rds"),
                "instances": daily.get("instances", {}),
                "instance_names": daily.get("instance_names", {}),
                "metrics": daily.get("metrics", []),
                "thresholds": daily.get("thresholds", {}),
                "role_thresholds": daily.get("role_thresholds", {}),
                "alarm_thresholds": daily.get("alarm_thresholds", {}),
                "extra_sections": extra_sections,
            }
            return self._apply_account_config_override(base_cfg, profile)

        legacy = ACCOUNT_CONFIG.get(profile)
        if not legacy:
            return self._apply_account_config_override(None, profile)
        cfg = dict(legacy)
        cfg.setdefault("extra_sections", [])
        return self._apply_account_config_override(cfg, profile)

    def _alarm_threshold_for_role(
        self, cw_client, profile, role, metric_name, cfg=None
    ):
        if cfg is None:
            cfg = ACCOUNT_CONFIG.get(profile, {})
        role_alarm_map = cfg.get("alarm_thresholds", {}).get(role, {})
        # EC2 alarm_thresholds uses list format (not metric_name->alarm_name dict); skip.
        if not isinstance(role_alarm_map, dict):
            return None
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
            logger.warning(
                "Failed to resolve alarm threshold for %s/%s/%s: %s",
                profile,
                role,
                metric_name,
                e,
            )
            return None

        return None

    def _resolve_role_thresholds(
        self, cw_client, profile, role, base_thresholds, role_thresholds=None, cfg=None
    ):
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
            cfg=cfg,
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

    def _resolve_role_alarm_periods(self, cw_client, profile, role, cfg=None):
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(hours=self.window_hours)
        out = {}

        effective_cfg = cfg if cfg is not None else ACCOUNT_CONFIG.get(profile, {})
        role_metric_map = effective_cfg.get("alarm_thresholds", {}).get(role, {})
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
                logger.warning(
                    "Failed to get alarm history for %s/%s/%s: %s",
                    profile,
                    role,
                    alarm_name,
                    e,
                )
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

    def _evaluate_ec2_network(self, info, label):
        """Evaluate EC2 NetworkIn/NetworkOut — returns structured spike period list.

        Returns:
            (status, spike_periods)
            status: "ok" | "past-warn" | "no-data"
            spike_periods: list of dicts with keys:
                inst_id, inst_name, start_str, end_str, duration_min, peak_bytes
        """
        vals = info.get("values") or []
        if not vals:
            return "no-data", []

        avg = info.get("avg", 0)
        min_spike_bytes = 1 * 1024**3  # 1 GB minimum per 1-minute bucket
        spike_threshold = max(avg * 2, min_spike_bytes)
        timestamps = info.get("timestamps", [])

        spikes = [(t, v) for t, v in zip(timestamps, vals) if v > spike_threshold]

        if not spikes:
            return "ok", []

        # Group consecutive spikes (gap > 5 min = new period)
        periods = []
        current = [spikes[0]]
        for i in range(1, len(spikes)):
            gap = (spikes[i][0] - spikes[i - 1][0]).total_seconds() / 60
            if gap <= 5:
                current.append(spikes[i])
            else:
                periods.append(current)
                current = [spikes[i]]
        periods.append(current)

        inst_id = info.get("instance_id", "")
        inst_name = info.get("instance_name", "")
        spike_periods = []
        for period in periods:
            peak = max(period, key=lambda x: x[1])
            start_t = period[0][0].astimezone(JKT).strftime("%H:%M")
            end_t = period[-1][0].astimezone(JKT).strftime("%H:%M")
            duration = int((period[-1][0] - period[0][0]).total_seconds() / 60)
            if duration < 5:
                # Single-point spikes (duration=0) and very short bursts (<5 min)
                # are treated as noise and filtered out intentionally.
                continue
            spike_periods.append(
                {
                    "inst_id": inst_id,
                    "inst_name": inst_name,
                    "start_str": start_t,
                    "end_str": end_t,
                    "duration_min": duration,
                    "peak_bytes": peak[1],
                }
            )

        if not spike_periods:
            return "ok", []

        return "past-warn", spike_periods

    def _check_ec2_alarms(
        self, cw_client, profile: str, role: str, cfg=None
    ) -> list[dict]:
        """Check CloudWatch alarm states for disk/memory for a given EC2 role.

        Returns a list of dicts, one per alarm that has fired (ALARM or has alarm periods):
          {
            "alarm_name": str,
            "current_state": "ALARM" | "OK" | "INSUFFICIENT_DATA",
            "periods": list[tuple(float, start_str, end_str, duration_min)],
          }
        """
        if cfg is None:
            cfg = ACCOUNT_CONFIG.get(profile, {})
        alarm_names: list[str] = cfg.get("alarm_thresholds", {}).get(role, [])
        if not alarm_names:
            return []

        now_utc = datetime.now(timezone.utc)
        window_start_utc = now_utc - timedelta(hours=self.window_hours)
        results = []

        for alarm_name in alarm_names:
            try:
                current_state = "OK"
                described = cw_client.describe_alarms(AlarmNames=[alarm_name])
                metric_alarms = described.get("MetricAlarms", [])
                if metric_alarms:
                    current_state = metric_alarms[0].get("StateValue", "OK")

                history = cw_client.describe_alarm_history(
                    AlarmName=alarm_name,
                    HistoryItemType="StateUpdate",
                    StartDate=window_start_utc,
                    EndDate=now_utc,
                    ScanBy="TimestampDescending",
                ).get("AlarmHistoryItems", [])

                periods = self._extract_alarm_periods(
                    history,
                    now_utc,
                    window_start_utc,
                    current_state=current_state,
                )
                if current_state == "ALARM" or periods:
                    results.append(
                        {
                            "alarm_name": alarm_name,
                            "current_state": current_state,
                            "periods": periods,
                        }
                    )
            except Exception as e:
                logger.warning(
                    "Failed to check EC2 alarm %s/%s/%s: %s",
                    profile,
                    role,
                    alarm_name,
                    e,
                )

        return results

    def _evaluate_metric(self, metric, info, thresholds, profile=None):
        vals = info.get("values") or []
        if not vals:
            return "no-data", "Data tidak tersedia"

        # Gunakan nilai terbaru (real-time)
        last = info.get("last")
        thr = thresholds.get(metric)

        # Network metrics: display-only, no threshold
        if metric == "NetworkReceiveThroughput":
            label = "Network In"
            if last >= 1024 * 1024:
                val_str = f"{last / (1024 * 1024):.2f} MB/s"
            elif last >= 1024:
                val_str = f"{last / 1024:.1f} KB/s"
            else:
                val_str = f"{last:.0f} B/s"
            return "ok", f"{label}: {val_str}"

        if metric == "NetworkTransmitThroughput":
            label = "Network Out"
            if last >= 1024 * 1024:
                val_str = f"{last / (1024 * 1024):.2f} MB/s"
            elif last >= 1024:
                val_str = f"{last / 1024:.1f} KB/s"
            else:
                val_str = f"{last:.0f} B/s"
            return "ok", f"{label}: {val_str}"

        # EC2 Network metrics: display-only, no threshold, with spike detection
        if metric == "NetworkIn":
            return self._evaluate_ec2_network(info, "Network In")

        if metric == "NetworkOut":
            return self._evaluate_ec2_network(info, "Network Out")

        # All other metrics require a threshold
        if thr is None:
            return "no-data", f"{metric}: Threshold tidak dikonfigurasi"

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

    def _collect_section_report(self, session, cw, profile, cfg):
        service_type = cfg.get("service_type", "rds")
        instances = dict(cfg.get("instances") or {})

        # Resolve instances (auto-detect writer if None, RDS only)
        if service_type == "rds":
            rds = session.client("rds", region_name=self.region)
            if instances.get("writer") is None and cfg.get("cluster_id"):
                instances["writer"] = get_writer_instance(rds, cfg["cluster_id"])

        instance_names = cfg.get("instance_names") or {}
        metric_names = cfg.get("metrics") or []
        base_thresholds = cfg.get("thresholds") or {}

        instance_reports = {}
        any_warn = False
        threshold_cache = {}

        for role, inst_id in instances.items():
            if not inst_id:
                instance_reports[role] = {
                    "status": "no-data",
                    "message": "Instance not found",
                }
                continue

            metrics_info = self._fetch_metrics(
                cw,
                inst_id,
                metric_names,
                profile,
                service_type=service_type,
            )

            # Attach instance_id/name to network metrics for EC2 spike reporting
            if service_type == "ec2":
                for metric_name in ("NetworkIn", "NetworkOut"):
                    if metric_name in metrics_info:
                        metrics_info[metric_name]["instance_id"] = inst_id
                        metrics_info[metric_name]["instance_name"] = instance_names.get(
                            inst_id, role
                        )

            role_thresholds = self._resolve_role_thresholds(
                cw,
                profile,
                role,
                base_thresholds,
                role_thresholds=cfg.get("role_thresholds"),
                cfg=cfg,
            )

            # Prefer live threshold from CloudWatch alarms; fallback to configured value
            for metric_name in metric_names:
                cache_key = (
                    service_type,
                    inst_id,
                    cfg.get("cluster_id"),
                    role,
                    metric_name,
                )
                if cache_key not in threshold_cache:
                    threshold_cache[cache_key] = self._resolve_live_threshold(
                        cw,
                        service_type,
                        inst_id,
                        metric_name,
                        cluster_id=cfg.get("cluster_id"),
                        role=role,
                    )
                live_threshold = threshold_cache[cache_key]
                if live_threshold is not None:
                    role_thresholds[metric_name] = live_threshold

            if service_type == "rds":
                role_alarm_periods = self._resolve_role_alarm_periods(
                    cw, profile, role, cfg=cfg
                )
                for metric_name, periods in role_alarm_periods.items():
                    if metric_name in metrics_info:
                        metrics_info[metric_name]["alarm_periods"] = periods

            evaluations = {}
            for metric_name in metric_names:
                status, msg = self._evaluate_metric(
                    metric_name,
                    metrics_info.get(metric_name, {}),
                    role_thresholds,
                    profile,
                )
                if metric_name in ("NetworkIn", "NetworkOut"):
                    evaluations[metric_name] = {
                        "status": status,
                        "raw_data": msg,
                        "message": "",
                    }
                else:
                    evaluations[metric_name] = {"status": status, "message": msg}

                if status in ("warn", "past-warn"):
                    any_warn = True

            instance_reports[role] = {
                "instance_id": inst_id,
                "metrics": evaluations,
            }
            if service_type == "ec2":
                instance_reports[role]["instance_name"] = (
                    instance_names.get(inst_id) or role
                )

            if service_type == "ec2":
                alarm_results = self._check_ec2_alarms(cw, profile, role, cfg=cfg)
                instance_reports[role]["disk_memory_alarms"] = alarm_results
                if alarm_results:
                    any_warn = True

        return instance_reports, any_warn

    def _should_emphasize_alarm_message(self, metric_info: dict) -> bool:
        if metric_info.get("status") not in ("warn", "past-warn"):
            return False

        message = str(metric_info.get("message") or "")
        durations = [int(x) for x in _DURATION_PATTERN.findall(message)]
        return any(duration >= ALARM_BOLD_MINUTES for duration in durations)

    def _resolve_live_threshold(
        self,
        cw_client,
        service_type,
        instance_id,
        metric_name,
        cluster_id=None,
        role=None,
    ):
        if metric_name in ("NetworkIn", "NetworkOut"):
            return None

        namespace = "AWS/EC2" if service_type == "ec2" else "AWS/RDS"
        dimensions_to_try = []
        if service_type == "ec2":
            dimensions_to_try.append([{"Name": "InstanceId", "Value": instance_id}])
        else:
            dimensions_to_try.append(
                [{"Name": "DBInstanceIdentifier", "Value": instance_id}]
            )
            if cluster_id:
                dimensions_to_try.append(
                    [{"Name": "DBClusterIdentifier", "Value": cluster_id}]
                )
                if role:
                    dimensions_to_try.append(
                        [
                            {"Name": "DBClusterIdentifier", "Value": cluster_id},
                            {"Name": "Role", "Value": str(role).upper()},
                        ]
                    )

        thresholds = []
        for dimensions in dimensions_to_try:
            try:
                response = cw_client.describe_alarms_for_metric(
                    Namespace=namespace,
                    MetricName=metric_name,
                    Dimensions=dimensions,
                )
            except Exception:
                continue

            for alarm in response.get("MetricAlarms", []):
                threshold = alarm.get("Threshold")
                if isinstance(threshold, (int, float)):
                    thresholds.append(float(threshold))

        if not thresholds:
            return None

        if metric_name in ABOVE_THRESHOLD_METRICS:
            return min(thresholds)
        if metric_name in BELOW_THRESHOLD_METRICS:
            return max(thresholds)
        return thresholds[0]

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
            cw = session.client("cloudwatch", region_name=self.region)
            primary_service_type = cfg.get("service_type", "rds")
            scope = self.section_scope
            include_rds = scope in {"both", "rds"}
            include_ec2 = scope in {"both", "ec2"}

            should_run_primary = (primary_service_type == "rds" and include_rds) or (
                primary_service_type == "ec2" and include_ec2
            )

            service_type = (
                primary_service_type
                if should_run_primary
                else ("ec2" if include_ec2 else "rds")
            )
            instance_reports = {}
            extra_sections_output = []
            any_warn = False
            primary_section_name = None
            ran_sections = False

            if should_run_primary:
                instance_reports, rds_warn = self._collect_section_report(
                    session,
                    cw,
                    profile,
                    cfg,
                )
                ran_sections = True
                if rds_warn:
                    any_warn = True

            consumed_primary_ec2 = should_run_primary and primary_service_type == "ec2"
            if include_ec2:
                for idx, section in enumerate(cfg.get("extra_sections") or [], start=1):
                    if not isinstance(section, dict):
                        continue

                    section_cfg = {
                        "cluster_id": section.get("cluster_id"),
                        "service_type": section.get("service_type", "rds"),
                        "instances": section.get("instances", {}),
                        "instance_names": section.get("instance_names", {}),
                        "metrics": section.get("metrics", []),
                        "thresholds": section.get("thresholds", {}),
                        "role_thresholds": section.get("role_thresholds", {}),
                        "alarm_thresholds": section.get("alarm_thresholds", {}),
                    }

                    section_instances, section_warn = self._collect_section_report(
                        session,
                        cw,
                        profile,
                        section_cfg,
                    )
                    if section_warn:
                        any_warn = True

                    section_name = section.get("section_name") or f"Extra Section {idx}"
                    section_type = section_cfg.get("service_type", "rds")

                    if section_type == "rds" and not include_rds:
                        continue
                    if section_type == "ec2" and not include_ec2:
                        continue

                    if (
                        scope == "ec2"
                        and not consumed_primary_ec2
                        and section_type == "ec2"
                    ):
                        instance_reports = section_instances
                        primary_section_name = section_name
                        service_type = "ec2"
                        consumed_primary_ec2 = True
                        ran_sections = True
                        continue

                    ran_sections = True
                    extra_sections_output.append(
                        {
                            "section_name": section_name,
                            "service_type": section_type,
                            "instances": section_instances,
                        }
                    )

            if not ran_sections:
                return {
                    "status": "skipped",
                    "reason": "section_scope_not_configured",
                    "profile": profile,
                    "account_id": account_id,
                    "region": self.region,
                    "window_hours": self.window_hours,
                    "account_name": cfg.get("account_name", profile),
                    "service_type": service_type,
                    "instances": {},
                    "extra_sections": [],
                    "primary_section_name": None,
                }

            status = "ATTENTION REQUIRED" if any_warn else "OK"

            return {
                "status": status,
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "window_hours": self.window_hours,
                "account_name": cfg.get("account_name", profile),
                "service_type": service_type,
                "instances": instance_reports,
                "extra_sections": extra_sections_output,
                "primary_section_name": primary_section_name,
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
        window_hours = int(
            results.get("window_hours", self.window_hours) or self.window_hours
        )

        lines: List[str] = []
        lines.append(f"{greeting} Team,")

        # Tambahkan info monitoring window
        lines.append(
            f"Berikut Daily report untuk akun id {acct_name} ({acct_id}) pada {waktu} ini (Data per {time_str}, monitoring {window_hours} jam terakhir)"
        )

        lines.append(date_str)
        lines.append("")

        service_type = results.get("service_type", "rds")
        primary_section_name = results.get("primary_section_name")

        if service_type == "ec2":
            if primary_section_name:
                lines.append(f"{primary_section_name} (EC2):")
            self._format_ec2_summary(results, lines)
        else:
            self._format_rds_detail(results, lines, include_summary=True)

        for section in results.get("extra_sections") or []:
            if not isinstance(section, dict):
                continue
            lines.append("")
            section_name = section.get("section_name", "Extra Section")
            section_type = section.get("service_type", "rds")
            if section_type == "ec2":
                lines.append(f"{section_name} (EC2):")
            else:
                lines.append(f"{section_name}:")
            section_result = {"instances": section.get("instances", {})}
            if section_type == "ec2":
                self._format_ec2_summary(section_result, lines)
            else:
                self._format_rds_detail(section_result, lines, include_summary=False)

        return "\n".join(lines)

    def _format_rds_detail(self, results, lines, include_summary=True):
        """Format RDS per-instance detail report (existing format)."""
        if include_summary:
            lines.append("Summary:")
        instances = results.get("instances", {})
        for role, data in instances.items():
            lines.append("")
            lines.append(f"{role.capitalize()} ({data.get('instance_id', 'N/A')}):")
            metrics = data.get("metrics", {})
            for info in metrics.values():
                message = info.get("message") or "Data tidak tersedia"
                if self._should_emphasize_alarm_message(info):
                    lines.append(f"* *{message}*")
                else:
                    lines.append(f"* {message}")

    def _format_ec2_summary(self, results, lines):
        """Format EC2 summary-style report — 1 line per metric across all instances."""
        instances = results.get("instances", {})

        if instances:
            labels = []
            for role, data in instances.items():
                inst_name = data.get("instance_name") or role
                inst_id = data.get("instance_id", "N/A")
                labels.append(f"{inst_name} ({inst_id})")
            lines.append("Instances: " + ", ".join(labels))

        # Collect per-metric across all instances
        metric_order = []
        metric_data = {}

        for role, data in instances.items():
            inst_id = data.get("instance_id", "N/A")
            inst_name = data.get("instance_name", "") or role
            for metric_name, info in data.get("metrics", {}).items():
                if metric_name not in metric_data:
                    metric_data[metric_name] = []
                    metric_order.append(metric_name)
                metric_data[metric_name].append(
                    (
                        inst_id,
                        inst_name,
                        role,
                        info.get("status", "ok"),
                        info.get("raw_data", info.get("message", "")),
                    )
                )

        for metric_name in metric_order:
            entries = metric_data[metric_name]

            if metric_name == "CPUUtilization":
                spiked = [
                    (iid, iname, role, msg)
                    for iid, iname, role, st, msg in entries
                    if st in ("warn", "past-warn")
                ]
                if spiked:
                    parts = []
                    for iid, iname, role, msg in spiked:
                        # Extract time info from message (e.g. "pukul 08:15-08:45 WIB (30 menit)")
                        time_info = ""
                        idx = msg.find("pukul ")
                        if idx >= 0:
                            time_info = " " + msg[idx:]
                        parts.append(f"{iname}{time_info}")
                    lines.append(
                        f"- CPU utilization = Terdapat spike pada " + ", ".join(parts)
                    )
                else:
                    lines.append(
                        "- CPU utilization = Tidak terdapat spike yang signifikan"
                    )

            elif metric_name in ("NetworkIn", "NetworkOut"):
                label = metric_name
                # Collect all spike periods from all instances
                all_spike_periods = []
                for iid, iname, role, st, raw_data in entries:
                    if st == "past-warn" and isinstance(raw_data, list):
                        all_spike_periods.extend(raw_data)

                if not all_spike_periods:
                    lines.append(
                        f"- {label} spike: Tidak terdapat spike yang signifikan"
                    )
                else:
                    lines.append(f"- {label} spike:")
                    # Group by inst_id (stable key); use inst_name only for display
                    by_instance = {}
                    for sp in all_spike_periods:
                        key = sp["inst_id"]
                        if key not in by_instance:
                            by_instance[key] = []
                        by_instance[key].append(sp)
                    for inst_id_key, periods in by_instance.items():
                        inst_name = periods[0]["inst_name"] or inst_id_key
                        lines.append(f"    {inst_name}:")
                        for sp in periods:
                            lines.append(
                                f"      * {sp['start_str']}-{sp['end_str']} WIB "
                                f"({sp['duration_min']} menit, peak {human_network_bytes(sp['peak_bytes'])})"
                            )

            else:
                for iid, iname, role, st, msg in entries:
                    lines.append(f"- {msg}")

        # Disk / Memory alarms section
        any_disk_mem_alarms = False
        for role, data in instances.items():
            alarms = data.get("disk_memory_alarms") or []
            if alarms:
                any_disk_mem_alarms = True
                break

        if any_disk_mem_alarms:
            lines.append("- Disk / Memory:")
            for role, data in instances.items():
                alarms = data.get("disk_memory_alarms") or []
                if not alarms:
                    continue
                inst_name = data.get("instance_name") or role
                for alarm in alarms:
                    alarm_name = alarm["alarm_name"]
                    current_state = alarm["current_state"]
                    periods = alarm.get("periods") or []
                    if current_state == "ALARM":
                        # Aktif sekarang — tanpa detail waktu
                        lines.append(f"    {inst_name} | {alarm_name}: ALARM")
                    else:
                        # Pernah ALARM — tampilkan hanya periode >= 15 menit
                        long_periods = [(s, e, d) for _, s, e, d in periods if d >= 15]
                        if long_periods:
                            period_strs = [
                                f"{s}-{e} WIB ({d} menit)" for s, e, d in long_periods
                            ]
                            lines.append(
                                f"    {inst_name} | {alarm_name}: pernah ALARM — "
                                + ", ".join(period_strs)
                            )
        else:
            lines.append("- Disk / Memory: Semua normal")

    def count_issues(self, result: dict) -> int:
        if result.get("status") in ("error", "skipped"):
            return 0

        warn_count = 0
        sections = [{"instances": result.get("instances", {})}]
        for extra in result.get("extra_sections") or []:
            if isinstance(extra, dict):
                sections.append(extra)

        for section in sections:
            for data in (section.get("instances") or {}).values():
                for metric in data.get("metrics", {}).values():
                    if metric.get("status") in ("warn", "past-warn"):
                        warn_count += 1
        return warn_count

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render DAILY ARBEL METRICS section for consolidated report."""
        lines = []
        lines.append("")
        lines.append("DAILY ARBEL METRICS")

        if errors:
            lines.append("Status: ERROR - Daily Arbel check failed")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            return lines

        rds_warnings = []
        for profile, result in all_results.items():
            if result.get("status") == "skipped":
                continue
            warn_count = self.count_issues(result)
            if warn_count > 0:
                rds_warnings.append((profile, warn_count))

        if not rds_warnings:
            lines.append("Status: All RDS/EC2 metrics normal")
        else:
            lines.append(f"Status: {len(rds_warnings)} accounts with metric warnings")
            for profile, warn_count in rds_warnings:
                account_id = all_results[profile].get("account_id", "Unknown")
                lines.append(
                    f"  * {profile} ({account_id}): {warn_count} metric warnings"
                )

        return lines
