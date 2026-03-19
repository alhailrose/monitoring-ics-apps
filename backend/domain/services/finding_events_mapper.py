"""Map raw check outputs into normalized finding event rows."""

from __future__ import annotations

from backend.domain.finding_events import (
    FINDING_EVENT_CHECK_CLOUDWATCH,
    FINDING_EVENT_CHECK_GUARDDUTY,
    FINDING_EVENT_CHECK_NOTIFICATIONS,
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
    return _map_notifications(account_id, raw_result)
