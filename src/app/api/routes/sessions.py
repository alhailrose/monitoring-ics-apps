"""AWS SSO session health check endpoints."""

from fastapi import APIRouter, Depends, Query

from src.app.api.dependencies import get_session_health_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/health")
def check_session_health(
    customer_id: str | None = Query(None, description="Filter by customer, or check all"),
    notify: bool = Query(False, description="Send Slack alert if sessions are expired"),
    service=Depends(get_session_health_service),
):
    """Check AWS SSO session health for all customer accounts.

    Returns per-profile status (ok/expired/error) grouped by SSO session,
    with login commands for expired sessions.
    """
    if notify:
        report = service.check_and_notify(customer_id=customer_id)
    else:
        report = service.check_all(customer_id=customer_id)

    return service.serialize_report(report)
