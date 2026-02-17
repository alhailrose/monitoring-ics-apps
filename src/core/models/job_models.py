from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class JobRecord:
    job_id: str
    kind: str
    payload: dict
    status: str
    requested_by: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    summary: Optional[str]
    error: Optional[str]
