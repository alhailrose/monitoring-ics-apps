"""Customer management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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


class UpdateCustomerRequest(BaseModel):
    display_name: str | None = None
    checks: list[str] | None = None
    slack_webhook_url: str | None = None
    slack_channel: str | None = None
    slack_enabled: bool | None = None
    sso_session: str | None = None


class AddAccountRequest(BaseModel):
    profile_name: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)
    config_extra: dict | None = None
    region: str | None = None
    alarm_names: list[str] | None = None


class UpdateAccountRequest(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    config_extra: dict | None = None
    region: str | None = None
    alarm_names: list[str] | None = None


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


@router.delete("/{customer_id}", status_code=204, dependencies=[Depends(require_role("super_user"))])
def delete_customer(customer_id: str, service=Depends(get_customer_service)):
    if not service.delete_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")


# -- Account sub-routes --


@router.post("/{customer_id}/accounts", status_code=201, dependencies=[Depends(require_role("super_user"))])
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
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/accounts/{account_id}", dependencies=[Depends(require_role("super_user"))])
def update_account(
    account_id: str,
    payload: UpdateAccountRequest,
    service=Depends(get_customer_service),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = service.update_account(account_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@router.delete("/accounts/{account_id}", status_code=204, dependencies=[Depends(require_role("super_user"))])
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
