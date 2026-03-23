"""Map raw check outputs into normalized finding event rows."""

from __future__ import annotations

from backend.domain.finding_events import (
    FINDING_EVENT_CHECK_ARBEL_EC2,
    FINDING_EVENT_CHECK_ARBEL_RDS,
    FINDING_EVENT_CHECK_BACKUP,
    FINDING_EVENT_CHECK_CLOUDWATCH,
    FINDING_EVENT_CHECK_GUARDDUTY,
    FINDING_EVENT_CHECK_NOTIFICATIONS,
    FINDING_EVENT_CHECK_UTILIZATION,
    FINDING_EVENT_CHECKS,
)


def _as_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _normalize_severity(value: str | None, fallback: str) -> str:
    normalized = (value or "").upper()
    if normalized in {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL", "ALARM"}:
        return normalized
    return fallback


def _map_guardduty(account_id: str, raw_result: dict) -> list[dict]:
    details = raw_result.get("details")
    if not isinstance(details, list):
        return []

    events = []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        finding_type = str(detail.get("type") or "guardduty")
        title = str(detail.get("title") or finding_type)
        events.append(
            {
                "check_name": FINDING_EVENT_CHECK_GUARDDUTY,
                "account_id": account_id,
                "finding_key": finding_type,
                "severity": _normalize_severity(detail.get("severity"), "MEDIUM"),
                "title": title,
                "description": str(detail.get("updated") or ""),
                "raw_payload": detail,
            }
        )
    return events


def _map_cloudwatch(account_id: str, raw_result: dict) -> list[dict]:
    details = raw_result.get("details")
    if not isinstance(details, list):
        return []

    events = []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        alarm_name = str(detail.get("name") or "cloudwatch-alarm")
        events.append(
            {
                "check_name": FINDING_EVENT_CHECK_CLOUDWATCH,
                "account_id": account_id,
                "finding_key": alarm_name,
                "severity": "ALARM",
                "title": alarm_name,
                "description": str(detail.get("reason") or ""),
                "raw_payload": detail,
            }
        )
    return events


def _map_notifications(account_id: str, raw_result: dict) -> list[dict]:
    recent_events = raw_result.get("recent_events")
    if not isinstance(recent_events, list):
        return []

    events = []
    for event in recent_events:
        if not isinstance(event, dict):
            continue
        notif_event = _as_dict(event.get("notificationEvent"))
        source_metadata = _as_dict(notif_event.get("sourceEventMetadata"))
        message_components = _as_dict(notif_event.get("messageComponents"))
        event_type = str(source_metadata.get("eventType") or "notification")
        headline = str(message_components.get("headline") or event_type)
        events.append(
            {
                "check_name": FINDING_EVENT_CHECK_NOTIFICATIONS,
                "account_id": account_id,
                "finding_key": event_type,
                "severity": "INFO",
                "title": headline,
                "description": str(event.get("creationTime") or ""),
                "raw_payload": event,
            }
        )
    return events


def _map_backup(account_id: str, raw_result: dict) -> list[dict]:
    details = raw_result.get("job_details")
    if not isinstance(details, list):
        return []

    events = []
    for index, detail in enumerate(details):
        if not isinstance(detail, dict):
            continue

        state = str(detail.get("state") or "UNKNOWN").upper()
        if state not in {"FAILED", "EXPIRED", "COMPLETED"}:
            continue

        job_id = str(detail.get("job_id") or f"unknown-{index}")
        resource_label = str(detail.get("resource_label") or "resource")
        reason = str(detail.get("reason") or "")
        created = str(detail.get("created_wib") or detail.get("created") or "")
        severity = "ALARM" if state in {"FAILED", "EXPIRED"} else "INFO"

        events.append(
            {
                "check_name": FINDING_EVENT_CHECK_BACKUP,
                "account_id": account_id,
                "finding_key": f"backup-job:{state}:{job_id}",
                "severity": severity,
                "title": f"Backup job {state} for {resource_label}",
                "description": f"reason={reason} created={created}".strip(),
                "raw_payload": detail,
            }
        )

    return events


def _map_utilization(account_id: str, raw_result: dict) -> list[dict]:
    """Map ec2_utilization WARNING/CRITICAL instances to finding events."""
    instances = raw_result.get("instances")
    if not isinstance(instances, list):
        return []

    events = []
    for inst in instances:
        if not isinstance(inst, dict):
            continue
        status = str(inst.get("status") or "").upper()
        if status not in {"WARNING", "CRITICAL"}:
            continue

        instance_id = str(inst.get("instance_id") or "unknown")
        name = str(inst.get("name") or instance_id)
        cpu_peak = inst.get("cpu_peak_12h")
        mem_peak = inst.get("memory_peak_12h")
        disk_free = inst.get("disk_free_min_percent")

        parts = []
        if cpu_peak is not None:
            parts.append(f"CPU peak {cpu_peak:.1f}%")
        if mem_peak is not None:
            parts.append(f"MEM peak {mem_peak:.1f}%")
        if disk_free is not None:
            parts.append(f"disk free {disk_free:.1f}%")

        events.append({
            "check_name": FINDING_EVENT_CHECK_UTILIZATION,
            "account_id": account_id,
            "finding_key": f"ec2_utilization:{instance_id}",
            "severity": "CRITICAL" if status == "CRITICAL" else "MEDIUM",
            "title": f"{status.capitalize()} utilization: {name}",
            "description": ", ".join(parts),
            "raw_payload": inst,
        })
    return events


_ARBEL_WARN_STATUSES = {"warn", "past-warn"}


def _map_arbel_section(check_name: str, account_id: str, section_instances: dict) -> list[dict]:
    """Collect findings from one arbel section (primary or extra)."""
    events = []
    for role, instance_info in section_instances.items():
        if not isinstance(instance_info, dict):
            continue
        instance_id = str(instance_info.get("instance_id") or role)
        instance_name = str(instance_info.get("instance_name") or instance_id)
        metrics = instance_info.get("metrics")
        if not isinstance(metrics, dict):
            continue
        for metric_name, metric_info in metrics.items():
            if not isinstance(metric_info, dict):
                continue
            status = str(metric_info.get("status") or "").lower()
            if status not in _ARBEL_WARN_STATUSES:
                continue
            message = str(metric_info.get("message") or "")
            events.append({
                "check_name": check_name,
                "account_id": account_id,
                "finding_key": f"arbel:{instance_id}:{metric_name}",
                "severity": "MEDIUM",
                "title": f"Metric warning: {metric_name} ({instance_name})",
                "description": message,
                "raw_payload": metric_info,
            })
    return events


def _map_arbel(check_name: str, account_id: str, raw_result: dict) -> list[dict]:
    events = []
    instances = raw_result.get("instances")
    if isinstance(instances, dict):
        events.extend(_map_arbel_section(check_name, account_id, instances))
    for extra_sec in raw_result.get("extra_sections") or []:
        if not isinstance(extra_sec, dict):
            continue
        extra_instances = extra_sec.get("instances")
        if isinstance(extra_instances, dict):
            events.extend(_map_arbel_section(check_name, account_id, extra_instances))
    return events


def map_check_findings(
    check_name: str, account_id: str, raw_result: dict
) -> list[dict]:
    """Return normalized finding events for supported checks."""
    if check_name not in FINDING_EVENT_CHECKS:
        return []
    if raw_result.get("status") == "error":
        return []

    if check_name == FINDING_EVENT_CHECK_GUARDDUTY:
        return _map_guardduty(account_id, raw_result)
    if check_name == FINDING_EVENT_CHECK_CLOUDWATCH:
        return _map_cloudwatch(account_id, raw_result)
    if check_name == FINDING_EVENT_CHECK_NOTIFICATIONS:
        return _map_notifications(account_id, raw_result)
    if check_name == FINDING_EVENT_CHECK_UTILIZATION:
        return _map_utilization(account_id, raw_result)
    if check_name in {FINDING_EVENT_CHECK_ARBEL_RDS, FINDING_EVENT_CHECK_ARBEL_EC2}:
        return _map_arbel(check_name, account_id, raw_result)
    return _map_backup(account_id, raw_result)
