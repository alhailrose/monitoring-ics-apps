"""Status helpers for AWS utilization 3-core checks."""

from __future__ import annotations

from typing import Any


DEFAULT_THRESHOLDS = {
    "cpu_warning": 70.0,
    "cpu_critical": 85.0,
    "memory_warning": 75.0,
    "memory_critical": 90.0,
    "disk_free_warning": 20.0,
    "disk_free_critical": 10.0,
}


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def classify_instance_status(
    cpu_peak: float | None,
    memory_peak: float | None,
    disk_free_min: float | None,
    thresholds: dict[str, float] | None = None,
) -> str:
    """Classify instance status from CPU, memory, and disk-free metrics."""
    th = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        th.update(thresholds)

    cpu = _as_float(cpu_peak)
    mem = _as_float(memory_peak)
    disk = _as_float(disk_free_min)

    if cpu is not None and cpu >= th["cpu_critical"]:
        return "CRITICAL"
    if mem is not None and mem >= th["memory_critical"]:
        return "CRITICAL"
    if disk is not None and disk <= th["disk_free_critical"]:
        return "CRITICAL"

    if cpu is not None and cpu >= th["cpu_warning"]:
        return "WARNING"
    if mem is not None and mem >= th["memory_warning"]:
        return "WARNING"
    if disk is not None and disk <= th["disk_free_warning"]:
        return "WARNING"

    if cpu is not None and mem is not None and disk is not None:
        return "NORMAL"

    return "PARTIAL_DATA"
