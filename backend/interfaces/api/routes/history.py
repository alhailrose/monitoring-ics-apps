"""History endpoints for check run records."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.interfaces.api.dependencies import get_check_repository
from backend.domain.runtime.config import AVAILABLE_CHECKS

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def list_history(
    customer_id: str,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    check_mode: str | None = Query(None),
    check_name: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo=Depends(get_check_repository),
):
    runs, total = repo.list_history(
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date,
        check_mode=check_mode,
        check_name=check_name,
        limit=limit,
        offset=offset,
    )

    items = []
    for run in runs:
        ok = sum(1 for r in run.results if r.status == "OK")
        warn = sum(1 for r in run.results if r.status in ("WARN", "ALARM"))
        error = sum(1 for r in run.results if r.status == "ERROR")

        items.append(
            {
                "check_run_id": run.id,
                "check_mode": run.check_mode,
                "check_name": run.check_name,
                "created_at": run.created_at.isoformat(),
                "execution_time_seconds": run.execution_time_seconds,
                "slack_sent": run.slack_sent,
                "results_summary": {
                    "total": len(run.results),
                    "ok": ok,
                    "warn": warn,
                    "error": error,
                },
            }
        )

    return {"total": total, "items": items}


@router.get("/{check_run_id}")
def get_check_run_detail(check_run_id: str, repo=Depends(get_check_repository)):
    run = repo.get_check_run(check_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Check run not found")

    return {
        "check_run_id": run.id,
        "customer": {
            "id": run.customer.id,
            "name": run.customer.name,
            "display_name": run.customer.display_name,
        },
        "check_mode": run.check_mode,
        "check_name": run.check_name,
        "created_at": run.created_at.isoformat(),
        "execution_time_seconds": run.execution_time_seconds,
        "slack_sent": run.slack_sent,
        "results": [
            {
                "account": {
                    "id": r.account.id,
                    "profile_name": r.account.profile_name,
                    "display_name": r.account.display_name,
                },
                "check_name": r.check_name,
                "status": r.status,
                "summary": r.summary,
                "output": r.output,
                "details": r.details,
                "created_at": r.created_at.isoformat(),
            }
            for r in run.results
        ],
    }


@router.get("/{check_run_id}/report")
def get_check_run_report(check_run_id: str, repo=Depends(get_check_repository)):
    """Regenerate consolidated report from stored history data.

    Rebuilds the full report text on-the-fly from the stored details,
    using the same checker render_section() logic as live execution.
    """
    run = repo.get_check_run(check_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Check run not found")

    from backend.domain.services.check_executor import _build_consolidated_report

    # Collect profiles and results from stored data
    profiles = []
    all_results = {}  # {profile: {check_name: details_dict}}
    check_names_seen = set()
    check_errors = []
    errors_by_check = {}

    for r in run.results:
        profile = r.account.profile_name
        if profile not in all_results:
            profiles.append(profile)
            all_results[profile] = {}

        # Use stored details as the raw result (this is what checkers work with)
        result_data = r.details or {}
        all_results[profile][r.check_name] = result_data
        check_names_seen.add(r.check_name)

        if r.status == "ERROR":
            err_msg = r.summary or "Unknown error"
            check_errors.append((profile, r.check_name, err_msg))
            errors_by_check.setdefault(r.check_name, []).append((profile, err_msg))

    # Instantiate checkers for each check type
    checkers = {}
    region = "ap-southeast-3"
    for chk_name in check_names_seen:
        checker_class = AVAILABLE_CHECKS.get(chk_name)
        if checker_class:
            checkers[chk_name] = checker_class(region=region)

    # Determine clean accounts
    clean_accounts = []
    for profile in profiles:
        has_issues = False
        for chk_name, checker in checkers.items():
            result = all_results.get(profile, {}).get(chk_name, {})
            if result.get("status") == "error" or checker.count_issues(result) > 0:
                has_issues = True
                break
        if not has_issues:
            clean_accounts.append(profile)

    if run.check_mode in ("all", "arbel"):
        report_text = _build_consolidated_report(
            profiles=profiles,
            all_results=all_results,
            checks=list(check_names_seen),
            checkers=checkers,
            check_errors=check_errors,
            clean_accounts=clean_accounts,
            errors_by_check=errors_by_check,
            region=region,
            group_name=run.customer.display_name,
        )
    else:
        # Single mode: concatenate per-account outputs
        parts = []
        for r in run.results:
            header = f"=== {r.account.display_name} ({r.account.profile_name}) ==="
            parts.append(header)
            parts.append(r.output or r.summary or "")
            parts.append("")
        report_text = "\n".join(parts)

    return {
        "check_run_id": run.id,
        "check_mode": run.check_mode,
        "check_name": run.check_name,
        "created_at": run.created_at.isoformat(),
        "report": report_text,
    }
