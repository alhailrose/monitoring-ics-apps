"""Slack delivery helpers for report messages."""

from __future__ import annotations

import json
from urllib import error, request

from src.core.runtime.config_loader import get_slack_report_config


def send_report_to_slack(
    report_name: str, text: str, client_key: str | None = None
) -> tuple[bool, str]:
    """Send report text to Slack based on config routing.

    Returns `(sent, message)` where `sent` indicates success.
    """
    route = get_slack_report_config(report_name, client_key=client_key)
    if not route:
        return False, "slack route not configured"

    webhook_url = route.get("webhook_url")
    if not webhook_url:
        return False, "slack webhook_url missing"

    payload = {"text": text}
    if route.get("channel"):
        payload["channel"] = route["channel"]
    if route.get("username"):
        payload["username"] = route["username"]
    if route.get("icon_emoji"):
        payload["icon_emoji"] = route["icon_emoji"]

    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as resp:
            status = getattr(resp, "status", 200)
            if 200 <= status < 300:
                return True, "ok"
            return False, f"http {status}"
    except error.URLError as exc:
        return False, f"network error: {exc}"
    except Exception as exc:  # pragma: no cover
        return False, f"unexpected error: {exc}"
