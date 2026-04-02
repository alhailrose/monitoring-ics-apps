"""Proxy endpoints to the gmail-alert-forwarder service."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from backend.config.settings import get_settings
from backend.interfaces.api.dependencies import require_auth

router = APIRouter(prefix="/alarms", tags=["alarms"])


def _forwarder_url() -> str:
    url = get_settings().alert_forwarder_url.rstrip("/")
    if not url:
        raise HTTPException(
            status_code=503,
            detail="Alert forwarder not configured (ALERT_FORWARDER_URL missing)",
        )
    return url


def _get(path: str) -> dict | list:
    base = _forwarder_url()
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=exc.code, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Forwarder unreachable: {exc}")


def _post(path: str, body: dict | None = None) -> dict:
    base = _forwarder_url()
    data = json.dumps(body or {}).encode() if body else None
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=exc.code, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Forwarder unreachable: {exc}")


@router.get("", dependencies=[Depends(require_auth)])
def list_alarms():
    """Return active CloudWatch alarms from the forwarder."""
    return JSONResponse(_get("/alarms-json"))


@router.get("/stats", dependencies=[Depends(require_auth)])
def alarm_stats():
    """Return email processing stats from the forwarder."""
    return JSONResponse(_get("/stats"))


@router.get("/health", dependencies=[Depends(require_auth)])
def forwarder_health():
    """Return forwarder service health."""
    return JSONResponse(_get("/health"))


@router.post("/{alarm_name}/resolve", dependencies=[Depends(require_auth)])
def resolve_alarm(alarm_name: str, notes: str = ""):
    """Manually resolve an active alarm via the forwarder."""
    params = f"?notes={urllib.parse.quote(notes)}" if notes else ""
    return JSONResponse(_post(f"/alarms/{urllib.parse.quote(alarm_name)}/resolve{params}"))
