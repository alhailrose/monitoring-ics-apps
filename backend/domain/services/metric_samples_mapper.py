"""Map raw check outputs into normalized metric sample rows."""

from __future__ import annotations

import re

from backend.domain.metric_samples import (
    METRIC_SAMPLE_CHECK_AWS_UTILIZATION,
    METRIC_SAMPLE_CHECKS,
)


_FIRST_NUMBER_PATTERN = re.compile(r":\s*(-?\d+(?:\.\d+)?)")


def _status(value: object) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"ok", "warn", "past-warn", "no-data", "error"}:
        return raw
    return "unknown"


# Map AWS CloudWatch metric names → (snake_case_name, unit)
_AWS_METRIC_MAP: dict[str, tuple[str, str | None]] = {
    "CPUUtilization":              ("cpu_utilization",              "percent"),
    "ACUUtilization":              ("acu_utilization",              "percent"),
    "BufferCacheHitRatio":         ("buffer_cache_hit_ratio",       "percent"),
    "FreeableMemory":              ("freeable_memory_bytes",        "bytes"),
    "FreeStorageSpace":            ("free_storage_bytes",           "bytes"),
    "DatabaseConnections":         ("database_connections",         "count"),
    "ServerlessDatabaseCapacity":  ("serverless_capacity",         "count"),
    "NetworkIn":                   ("network_in_bytes",             "bytes"),
    "NetworkOut":                  ("network_out_bytes",            "bytes"),
    "NetworkReceiveThroughput":    ("network_receive_bytes_per_s",  "bytes/s"),
    "NetworkTransmitThroughput":   ("network_transmit_bytes_per_s", "bytes/s"),
}


def _extract_value_unit(
    metric_name: str, message: str
) -> tuple[float | None, str | None, str]:
    """Returns (value, unit, normalized_name)."""
    match = _FIRST_NUMBER_PATTERN.search(message)
    value = float(match.group(1)) if match else None

    normalized, unit = _AWS_METRIC_MAP.get(metric_name, (metric_name.lower(), None))

    # FreeableMemory / FreeStorageSpace are reported in GB, convert to bytes
    if metric_name in {"FreeableMemory", "FreeStorageSpace"} and value is not None:
        value = value * (1024 ** 3)

    return value, unit, normalized


def _collect_rows_for_section(
    *,
    check_name: str,
    account_id: str,
    raw_result: dict,
    section_instances: dict,
    section_name: str | None,
    service_type: str | None,
) -> list[dict]:
    rows: list[dict] = []

    for role, instance_info in section_instances.items():
        if not isinstance(instance_info, dict):
            continue

        metrics = instance_info.get("metrics")
        if not isinstance(metrics, dict):
            continue

        for metric_name, metric_info in metrics.items():
            if not isinstance(metric_info, dict):
                continue

            status = _status(metric_info.get("status"))
            message = str(metric_info.get("message") or "")
            value_num, unit, normalized_name = _extract_value_unit(metric_name, message)

            # For metrics where message is empty (e.g. NetworkIn/NetworkOut), fall
            # back to the avg or last value attached directly to metric_info.
            if value_num is None:
                raw_val = metric_info.get("avg") or metric_info.get("last")
                if raw_val is not None:
                    try:
                        value_num = float(raw_val)
                    except (TypeError, ValueError):
                        pass

            rows.append(
                {
                    "check_name": check_name,
                    "account_id": account_id,
                    "metric_name": normalized_name,
                    "metric_status": status,
                    "value_num": value_num,
                    "unit": unit,
                    "resource_role": str(role),
                    "resource_id": str(instance_info.get("instance_id") or ""),
                    "resource_name": str(instance_info.get("instance_name") or role),
                    "service_type": str(
                        service_type or raw_result.get("service_type") or ""
                    ),
                    "section_name": section_name,
                    "raw_payload": metric_info,
                }
            )

    return rows


def _inst_status_to_metric_status(inst_status: str) -> str:
    s = inst_status.lower()
    if s in ("ok", "normal"):
        return "ok"
    if s in ("warning", "warn"):
        return "warn"
    if s in ("critical", "error"):
        return "error"
    return "ok"


def _map_aws_utilization(account_id: str, raw_result: dict) -> list[dict]:
    """Map aws-utilization-3core flat instance list to metric samples."""
    rows: list[dict] = []
    instances = raw_result.get("instances")
    if not isinstance(instances, list):
        return rows

    for inst in instances:
        if not isinstance(inst, dict):
            continue

        resource_id = str(inst.get("instance_id") or "")
        resource_name = str(inst.get("name") or resource_id or "")
        inst_status = _inst_status_to_metric_status(str(inst.get("status") or "ok"))

        metric_fields = [
            ("cpu_avg_12h",          "cpu_utilization_avg",     "percent"),
            ("cpu_peak_12h",         "cpu_utilization_peak",    "percent"),
            ("memory_avg_12h",       "memory_utilization_avg",  "percent"),
            ("memory_peak_12h",      "memory_utilization_peak", "percent"),
            ("disk_free_min_percent","disk_free_percent",       "percent"),
        ]
        for field, metric_name, unit in metric_fields:
            value = inst.get(field)
            if value is None:
                continue
            rows.append({
                "check_name": METRIC_SAMPLE_CHECK_AWS_UTILIZATION,
                "account_id": account_id,
                "metric_name": metric_name,
                "metric_status": inst_status,
                "value_num": float(value),
                "unit": unit,
                "resource_role": str(inst.get("service_type") or inst.get("type") or ""),
                "resource_id": resource_id,
                "resource_name": resource_name,
                "service_type": str(inst.get("service_type") or inst.get("type") or ""),
                "section_name": None,
                "raw_payload": inst,
            })

    return rows


def _count_row(check_name: str, account_id: str, metric_name: str, value: float, status: str, unit: str = "count") -> dict:
    """Build a minimal aggregate count metric row."""
    return {
        "check_name": check_name,
        "account_id": account_id,
        "metric_name": metric_name,
        "metric_status": status,
        "value_num": value,
        "unit": unit,
        "resource_role": "",
        "resource_id": "",
        "resource_name": "",
        "service_type": "",
        "section_name": None,
        "raw_payload": None,
    }


def _map_cost(account_id: str, raw_result: dict) -> list[dict]:
    """Map cost-anomaly counts to metric samples."""
    total = int(raw_result.get("total_anomalies") or 0)
    today = int(raw_result.get("today_anomaly_count") or 0)
    yesterday = int(raw_result.get("yesterday_anomaly_count") or 0)
    monitors = int(raw_result.get("total_monitors") or 0)
    status = "warn" if total > 0 else "ok"
    return [
        _count_row("cost", account_id, "anomalies_total",     float(total),     status),
        _count_row("cost", account_id, "anomalies_today",     float(today),     status),
        _count_row("cost", account_id, "anomalies_yesterday", float(yesterday), status),
        _count_row("cost", account_id, "monitors_total",      float(monitors),  "ok"),
    ]


def _map_cloudwatch(account_id: str, raw_result: dict) -> list[dict]:
    """Map CloudWatch alarm count to metric samples."""
    count = int(raw_result.get("count") or 0)
    status = "warn" if count > 0 else "ok"
    return [_count_row("cloudwatch", account_id, "alarms_in_alarm", float(count), status)]


def _map_guardduty(account_id: str, raw_result: dict) -> list[dict]:
    """Map GuardDuty finding count to metric samples."""
    if raw_result.get("status") == "disabled":
        return []
    findings = int(raw_result.get("findings") or 0)
    status = "warn" if findings > 0 else "ok"
    return [_count_row("guardduty", account_id, "findings_today", float(findings), status)]


def _map_backup(account_id: str, raw_result: dict) -> list[dict]:
    """Map backup job counts to metric samples."""
    total = int(raw_result.get("total_jobs") or 0)
    completed = int(raw_result.get("completed_jobs") or 0)
    failed = int(raw_result.get("failed_jobs") or 0)
    expired = int(raw_result.get("expired_jobs") or 0)
    status = "error" if failed > 0 else ("warn" if raw_result.get("issues") else "ok")
    rows = [
        _count_row("backup", account_id, "jobs_total",     float(total),     status),
        _count_row("backup", account_id, "jobs_completed", float(completed), status),
        _count_row("backup", account_id, "jobs_failed",    float(failed),    status),
        _count_row("backup", account_id, "jobs_expired",   float(expired),   status),
    ]
    if raw_result.get("monitor_rds_snapshots"):
        rds = int(raw_result.get("rds_snapshots_24h") or 0)
        rows.append(_count_row("backup", account_id, "rds_snapshots_24h", float(rds), status))
    return rows


def _map_notifications(account_id: str, raw_result: dict) -> list[dict]:
    """Map notification counts to metric samples."""
    recent = int(raw_result.get("recent_count") or 0)
    total = int(raw_result.get("total_managed") or 0)
    regular = int(raw_result.get("regular_count") or 0)
    status = "warn" if recent > 0 else "ok"
    return [
        _count_row("notifications", account_id, "recent_12h",     float(recent),  status),
        _count_row("notifications", account_id, "managed_total",  float(total),   "ok"),
        _count_row("notifications", account_id, "regular_total",  float(regular), "ok"),
    ]


_COUNT_MAPPERS = {
    "cost":          _map_cost,
    "cloudwatch":    _map_cloudwatch,
    "guardduty":     _map_guardduty,
    "backup":        _map_backup,
    "notifications": _map_notifications,
}


def map_check_metric_samples(
    check_name: str,
    account_id: str,
    raw_result: dict,
) -> list[dict]:
    """Return normalized metric samples for supported checks."""
    if check_name not in METRIC_SAMPLE_CHECKS:
        return []
    if raw_result.get("status") == "error":
        return []

    if check_name == METRIC_SAMPLE_CHECK_AWS_UTILIZATION:
        return _map_aws_utilization(account_id, raw_result)

    if check_name in _COUNT_MAPPERS:
        return _COUNT_MAPPERS[check_name](account_id, raw_result)

    # Arbel variants (daily-arbel, daily-arbel-rds, daily-arbel-ec2)
    rows: list[dict] = []
    instances = raw_result.get("instances")
    if isinstance(instances, dict):
        rows.extend(
            _collect_rows_for_section(
                check_name=check_name,
                account_id=account_id,
                raw_result=raw_result,
                section_instances=instances,
                section_name=raw_result.get("primary_section_name"),
                service_type=raw_result.get("service_type"),
            )
        )

    extra_sections = raw_result.get("extra_sections")
    if isinstance(extra_sections, list):
        for section in extra_sections:
            if not isinstance(section, dict):
                continue
            section_instances = section.get("instances")
            if not isinstance(section_instances, dict):
                continue

            rows.extend(
                _collect_rows_for_section(
                    check_name=check_name,
                    account_id=account_id,
                    raw_result=raw_result,
                    section_instances=section_instances,
                    section_name=str(section.get("section_name") or ""),
                    service_type=section.get("service_type"),
                )
            )

    return rows
