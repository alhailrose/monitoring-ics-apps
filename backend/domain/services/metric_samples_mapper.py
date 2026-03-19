"""Map raw check outputs into normalized metric sample rows."""

from __future__ import annotations

import re

from backend.domain.metric_samples import (
    METRIC_SAMPLE_CHECK_DAILY_ARBEL,
    METRIC_SAMPLE_CHECKS,
)


_FIRST_NUMBER_PATTERN = re.compile(r":\s*(-?\d+(?:\.\d+)?)")


def _status(value: object) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"ok", "warn", "past-warn", "no-data", "error"}:
        return raw
    return "unknown"


def _extract_value_unit(
    metric_name: str, message: str
) -> tuple[float | None, str | None]:
    match = _FIRST_NUMBER_PATTERN.search(message)
    if not match:
        return None, None

    value = float(match.group(1))

    if metric_name in {"FreeableMemory", "FreeStorageSpace"}:
        return value * (1024**3), "Bytes"
    if metric_name in {"CPUUtilization", "ACUUtilization", "BufferCacheHitRatio"}:
        return value, "Percent"
    if metric_name == "ServerlessDatabaseCapacity":
        return value, "Count"
    if metric_name == "DatabaseConnections":
        return value, "Count"
    return value, None


def _collect_rows_for_section(
    *,
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
            value_num, unit = _extract_value_unit(metric_name, message)

            rows.append(
                {
                    "check_name": METRIC_SAMPLE_CHECK_DAILY_ARBEL,
                    "account_id": account_id,
                    "metric_name": str(metric_name),
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

    rows: list[dict] = []
    instances = raw_result.get("instances")
    if isinstance(instances, dict):
        rows.extend(
            _collect_rows_for_section(
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
                    account_id=account_id,
                    raw_result=raw_result,
                    section_instances=section_instances,
                    section_name=str(section.get("section_name") or ""),
                    service_type=section.get("service_type"),
                )
            )

    return rows
