"""Proxy endpoints to the gmail-alert-forwarder service."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.config.settings import get_settings
from backend.interfaces.api.dependencies import get_check_executor, require_auth

logger = logging.getLogger(__name__)

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


def _run_alarm_verification(
    alarm_names_list: list[str],
    executor,
) -> dict:
    """Common logic: find accounts, run verification, auto-resolve OK alarms.

    Returns a dict with keys: matched_customer_ids, matched_account_ids,
    result, alarm_states, auto_resolved.
    """
    alarm_map: dict[str, str] = {
        name.strip().casefold(): name.strip()
        for name in alarm_names_list
        if name.strip()
    }

    matched_customer_ids: set[str] = set()
    matched_account_ids: list[str] = []
    account_alarm_names: dict[str, list[str]] = {}

    customers = executor.customer_repo.list_customers()
    for customer in customers:
        for account in getattr(customer, "accounts", []) or []:
            if not getattr(account, "is_active", False):
                continue
            acct_alarms = getattr(account, "alarm_names", []) or []
            matched = [
                alarm_map[n.casefold()]
                for n in acct_alarms
                if n.casefold() in alarm_map
            ]
            if not matched:
                continue
            matched_customer_ids.add(customer.id)
            matched_account_ids.append(account.id)
            account_alarm_names[account.id] = matched

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

    # Extract per-alarm states and formatted outputs
    alarm_states: dict[str, str] = {}
    auto_resolved: list[str] = []
    outputs: list[dict] = []

    for item in result.get("results", []):
        for alarm_detail in (item.get("details") or {}).get("alarms") or []:
            name = alarm_detail.get("alarm_name", "")
            state = alarm_detail.get("alarm_state", "")
            if name:
                # Take worst state across accounts if multiple
                existing = alarm_states.get(name)
                if not existing or existing == "OK":
                    alarm_states[name] = state

        output_text = item.get("output", "")
        if output_text:
            outputs.append({
                "account": item.get("account", {}).get("display_name", ""),
                "output": output_text,
            })

    # Auto-resolve alarms that are confirmed OK in CloudWatch
    for alarm_name, state in alarm_states.items():
        if state == "OK":
            try:
                note = urllib.parse.quote("Auto-resolved: CloudWatch status OK")
                _post(f"/alarms/{urllib.parse.quote(alarm_name)}/resolve?notes={note}")
                auto_resolved.append(alarm_name)
                logger.info("alarm: auto-resolved '%s' (CloudWatch OK)", alarm_name)
            except Exception as exc:
                logger.debug("alarm: auto-resolve failed for '%s': %s", alarm_name, exc)

    return {
        "matched_customer_ids": matched_customer_ids,
        "matched_account_ids": matched_account_ids,
        "result": result,
        "alarm_states": alarm_states,
        "auto_resolved": auto_resolved,
        "outputs": outputs,
    }


@router.post("/{alarm_name}/verify", dependencies=[Depends(require_auth)])
def verify_alarm(alarm_name: str, executor=Depends(get_check_executor)):
    """Run alarm_verification instantly for one alarm mapped in customer accounts."""
    alarm_name = alarm_name.strip()
    if not alarm_name:
        raise HTTPException(status_code=400, detail="alarm_name is required")

    # Quick check: is alarm mapped?
    normalized = alarm_name.casefold()
    is_mapped = False
    customers = executor.customer_repo.list_customers()
    for customer in customers:
        for account in getattr(customer, "accounts", []) or []:
            if not getattr(account, "is_active", False):
                continue
            acct_alarms = getattr(account, "alarm_names", []) or []
            if any(str(n).casefold() == normalized for n in acct_alarms):
                is_mapped = True
                break
        if is_mapped:
            break

    if not is_mapped:
        raise HTTPException(
            status_code=404,
            detail=(
                "Alarm belum termapping di account customer. "
                "Tambahkan alarm_name di Customers terlebih dahulu."
            ),
        )

    data = _run_alarm_verification([alarm_name], executor)
    result = data["result"]
    matched_customer_ids = data["matched_customer_ids"]
    matched_account_ids = data["matched_account_ids"]

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
        "alarm_states": data["alarm_states"],
        "auto_resolved": data["auto_resolved"],
        "outputs": data["outputs"],
        "check_run_id": check_run_id,
    }


class BatchVerifyRequest(BaseModel):
    alarm_names: List[str]


@router.post("/verify-batch", dependencies=[Depends(require_auth)])
def verify_alarm_batch(body: BatchVerifyRequest, executor=Depends(get_check_executor)):
    """Run alarm_verification for multiple alarms at once."""
    alarm_names = [n.strip() for n in body.alarm_names if n.strip()]
    if not alarm_names:
        raise HTTPException(status_code=400, detail="alarm_names tidak boleh kosong")

    data = _run_alarm_verification(alarm_names, executor)
    matched_account_ids = data["matched_account_ids"]

    if not matched_account_ids:
        raise HTTPException(
            status_code=404,
            detail="Tidak ada alarm yang termapping di account customer.",
        )

    result = data["result"]
    counts = {"OK": 0, "ALARM": 0, "WARN": 0, "ERROR": 0, "NO_DATA": 0}
    for item in result.get("results", []):
        status = str(item.get("status") or "NO_DATA")
        counts[status] = counts.get(status, 0) + 1

    check_runs = result.get("check_runs") or []
    check_run_id = check_runs[0].get("check_run_id") if check_runs else None

    return {
        "verified": alarm_names,
        "mapped_accounts": len(matched_account_ids),
        "counts": counts,
        "alarm_states": data["alarm_states"],
        "auto_resolved": data["auto_resolved"],
        "outputs": data["outputs"],
        "check_run_id": check_run_id,
    }
