"""AWS profile detection endpoints."""

from fastapi import APIRouter, Depends

from src.app.api.dependencies import get_customer_service

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/detect")
def detect_profiles(service=Depends(get_customer_service)):
    """Scan ~/.aws/config and return mapped vs unmapped profiles."""
    return service.detect_profiles()
