"""Job submission endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.app.api.dependencies import get_run_service


class CreateJobRequest(BaseModel):
    customer_id: str
    check_name: str
    profiles: list[str] = Field(min_length=1)


router = APIRouter()


@router.post("/jobs", status_code=202)
def create_job(payload: CreateJobRequest, run_service=Depends(get_run_service)):
    job_id = run_service.enqueue_manual_run(
        customer_id=payload.customer_id,
        check_name=payload.check_name,
        profiles=payload.profiles,
    )
    return {"job_id": str(job_id)}
