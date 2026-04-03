"""Proxy endpoints to the gmail-alert-forwarder service."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from backend.config.settings import get_settings
from backend.interfaces.api.dependencies import get_check_executor, require_auth

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
    return JSONResponse(
        _post(f"/alarms/{urllib.parse.quote(alarm_name)}/resolve{params}")
    )


@router.post("/{alarm_name}/verify", dependencies=[Depends(require_auth)])
def verify_alarm(alarm_name: str, executor=Depends(get_check_executor)):
    """Run alarm_verification instantly for one alarm mapped in customer accounts."""
    alarm_name = alarm_name.strip()
    if not alarm_name:
        raise HTTPException(status_code=400, detail="alarm_name is required")

    normalized = alarm_name.casefold()
    matched_customer_ids: set[str] = set()
    matched_account_ids: list[str] = []
    account_alarm_names: dict[str, list[str]] = {}

    customers = executor.customer_repo.list_customers()
    for customer in customers:
        for account in getattr(customer, "accounts", []) or []:
            if not getattr(account, "is_active", False):
                continue
            alarm_names = getattr(account, "alarm_names", []) or []
            has_match = any(str(name).casefold() == normalized for name in alarm_names)
            if not has_match:
                continue

            matched_customer_ids.add(customer.id)
            matched_account_ids.append(account.id)
            account_alarm_names[account.id] = [alarm_name]

    if not matched_account_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                "Alarm belum termapping di account customer. "
                "Tambahkan alarm_name di Customers terlebih dahulu."
            ),
        )

    result = executor.execute(
        customer_ids=sorted(matched_customer_ids),
        mode="single",
        check_name="alarm_verification",
        account_ids=matched_account_ids,
        send_slack=False,
        check_params={"account_alarm_names": account_alarm_names},
        run_source="api",
        persist_mode="normalized",
    )

    counts = {"OK": 0, "ALARM": 0, "WARN": 0, "ERROR": 0, "NO_DATA": 0}
    for item in result.get("results", []):
        status = str(item.get("status") or "NO_DATA")
        counts[status] = counts.get(status, 0) + 1

    check_runs = result.get("check_runs") or []
    check_run_id = check_runs[0].get("check_run_id") if check_runs else None

    return {
        "alarm_name": alarm_name,
        "mapped_customers": len(matched_customer_ids),
        "mapped_accounts": len(matched_account_ids),
        "counts": counts,
        "check_run_id": check_run_id,
    }
