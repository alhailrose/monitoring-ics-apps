"""Customer management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.config.settings import get_settings
from backend.infra.cloud.aws.clients import get_session as get_aws_session
from backend.interfaces.api.dependencies import get_customer_service, require_role

router = APIRouter(prefix="/customers", tags=["customers"])


# -- Request/Response schemas --


class CreateCustomerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)
    checks: list[str] = Field(default_factory=list)
    slack_webhook_url: str | None = None
    slack_channel: str | None = None
    slack_enabled: bool = False
    sso_session: str | None = None
    report_mode: str = Field(default="summary", pattern="^(simple|summary|detailed)$")
    label: str | None = Field(default=None, max_length=256)


class UpdateCustomerRequest(BaseModel):
    display_name: str | None = None
    checks: list[str] | None = None
    slack_webhook_url: str | None = None
    slack_channel: str | None = None
    slack_enabled: bool | None = None
    sso_session: str | None = None
    report_mode: str | None = Field(default=None, pattern="^(simple|summary|detailed)$")
    label: str | None = None


class AddAccountRequest(BaseModel):
    profile_name: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)
    config_extra: dict | None = None
    region: str | None = None
    alarm_names: list[str] | None = None
    auth_method: str = Field(
        default="profile", pattern="^(profile|access_key|assumed_role)$"
    )
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    role_arn: str | None = None
    external_id: str | None = None


class UpdateAccountRequest(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    config_extra: dict | None = None
    region: str | None = None
    alarm_names: list[str] | None = None
    auth_method: str | None = Field(
        default=None, pattern="^(profile|access_key|assumed_role)$"
    )
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None  # None = don't update
    role_arn: str | None = None
    external_id: str | None = None


class UpsertAccountCheckConfigRequest(BaseModel):
    config: dict = Field(default_factory=dict)


# -- Endpoints --


@router.get("")
def list_customers(service=Depends(get_customer_service)):
    return {"customers": service.list_customers()}


@router.get("/{customer_id}")
def get_customer(customer_id: str, service=Depends(get_customer_service)):
    customer = service.get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("", status_code=201, dependencies=[Depends(require_role("super_user"))])
def create_customer(
    payload: CreateCustomerRequest, service=Depends(get_customer_service)
):
    try:
        return service.create_customer(
            name=payload.name,
            display_name=payload.display_name,
            checks=payload.checks,
            slack_webhook_url=payload.slack_webhook_url,
            slack_channel=payload.slack_channel,
            slack_enabled=payload.slack_enabled,
            sso_session=payload.sso_session,
            report_mode=payload.report_mode,
            label=payload.label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/{customer_id}", dependencies=[Depends(require_role("super_user"))])
def update_customer(
    customer_id: str,
    payload: UpdateCustomerRequest,
    service=Depends(get_customer_service),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = service.update_customer(customer_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


@router.delete(
    "/{customer_id}",
    status_code=204,
    dependencies=[Depends(require_role("super_user"))],
)
def delete_customer(customer_id: str, service=Depends(get_customer_service)):
    if not service.delete_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")


# -- Account sub-routes --


@router.post(
    "/{customer_id}/accounts",
    status_code=201,
    dependencies=[Depends(require_role("super_user"))],
)
def add_account(
    customer_id: str,
    payload: AddAccountRequest,
    service=Depends(get_customer_service),
):
    try:
        return service.add_account(
            customer_id=customer_id,
            profile_name=payload.profile_name,
            display_name=payload.display_name,
            config_extra=payload.config_extra,
            region=payload.region,
            alarm_names=payload.alarm_names,
            auth_method=payload.auth_method,
            aws_access_key_id=payload.aws_access_key_id,
            aws_secret_access_key=payload.aws_secret_access_key,
            role_arn=payload.role_arn,
            external_id=payload.external_id,
            app_secret=get_settings().jwt_secret,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch(
    "/accounts/{account_id}", dependencies=[Depends(require_role("super_user"))]
)
def update_account(
    account_id: str,
    payload: UpdateAccountRequest,
    service=Depends(get_customer_service),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = service.update_account(
        account_id, app_secret=get_settings().jwt_secret, **updates
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@router.delete(
    "/accounts/{account_id}",
    status_code=204,
    dependencies=[Depends(require_role("super_user"))],
)
def delete_account(account_id: str, service=Depends(get_customer_service)):
    if not service.delete_account(account_id):
        raise HTTPException(status_code=404, detail="Account not found")


@router.get("/accounts/{account_id}/check-configs")
def list_account_check_configs(account_id: str, service=Depends(get_customer_service)):
    try:
        return {"items": service.list_account_check_configs(account_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/accounts/{account_id}/check-configs/{check_name}")
def upsert_account_check_config(
    account_id: str,
    check_name: str,
    payload: UpsertAccountCheckConfigRequest,
    service=Depends(get_customer_service),
):
    try:
        return service.set_account_check_config(
            account_id=account_id,
            check_name=check_name,
            config=payload.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/accounts/{account_id}/check-configs/{check_name}", status_code=204)
def delete_account_check_config(
    account_id: str,
    check_name: str,
    service=Depends(get_customer_service),
):
    try:
        if not service.delete_account_check_config(account_id, check_name):
            raise HTTPException(status_code=404, detail="Check config not found")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/accounts/{account_id}/alarms/discover",
    dependencies=[Depends(require_role("super_user"))],
)
def discover_account_alarms(account_id: str, service=Depends(get_customer_service)):
    """Discover CloudWatch alarm names for an account and save them to DB."""
    try:
        alarm_names = service.discover_account_alarms(account_id)
        return {"alarm_names": alarm_names, "count": len(alarm_names)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to discover alarms: {exc}")


@router.post(
    "/accounts/{account_id}/discover-full",
    dependencies=[Depends(require_role("super_user"))],
)
def discover_account_full(account_id: str, service=Depends(get_customer_service)):
    """Discover AWS account ID, alarms, EC2, and RDS resources. Saves to DB."""
    try:
        result = service.discover_account_full(account_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {exc}")


@router.get("/accounts/{account_id}/discovery-snapshot")
def get_discovery_snapshot(account_id: str, service=Depends(get_customer_service)):
    """Return last saved discovery snapshot from DB (no AWS call)."""
    account = service.repo.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    snapshot = (account.config_extra or {}).get("_discovery")
    if snapshot is None:
        return {"snapshot": None}
    return {
        "snapshot": {
            **snapshot,
            "aws_account_id": account.account_id,
            "alarm_names": account.alarm_names or [],
        }
    }


@router.post(
    "/accounts/{account_id}/test-connection",
    dependencies=[Depends(require_role("super_user"))],
)
def test_account_connection(account_id: str, service=Depends(get_customer_service)):
    """Test AWS connectivity for an account using its stored credentials."""
    from backend.domain.services.check_executor import _build_creds_for_account

    account_data = service.repo.get_account(account_id)
    if account_data is None:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        creds = _build_creds_for_account(
            account_data,
            aws_config_file=service.aws_config_file,
            sso_cache_dir=service.sso_cache_dir,
        )
        if creds is None:
            # profile auth — use profile directly
            session = get_aws_session(
                profile_name=account_data.profile_name,
                aws_config_file=service.aws_config_file,
                sso_cache_dir=service.sso_cache_dir,
            )
        else:
            session = get_aws_session(
                aws_access_key_id=creds["aws_access_key_id"],
                aws_secret_access_key=creds["aws_secret_access_key"],
                aws_session_token=creds.get("aws_session_token"),
                aws_config_file=service.aws_config_file,
                sso_cache_dir=service.sso_cache_dir,
            )
        sts = session.client("sts", region_name="us-east-1")
        identity = sts.get_caller_identity()
        return {
            "ok": True,
            "account_id": identity.get("Account"),
            "arn": identity.get("Arn"),
            "auth_method": getattr(account_data, "auth_method", "profile"),
            "key_id_stored": getattr(account_data, "aws_access_key_id", None),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "auth_method": getattr(account_data, "auth_method", "profile"),
            "key_id_stored": getattr(account_data, "aws_access_key_id", None),
        }


@router.post("/{customer_id}/reimport")
def reimport_customer(customer_id: str, service=Depends(get_customer_service)):
    """Re-import customer config from YAML file and update DB."""
    from backend.config.loader import load_customer_config

    try:
        config = load_customer_config(customer_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"No YAML config found for '{customer_id}'"
        )
    result = service.import_from_yaml(config)
    return result
