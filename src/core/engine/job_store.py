import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.core.models.job_models import JobRecord


def _to_dt(value: Optional[str]):
    return datetime.fromisoformat(value) if value else None


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    summary TEXT,
                    error TEXT
                )
                """
            )

    def create_job(self, kind, payload, requested_by=None):
        job_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, kind, payload_json, status, requested_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, kind, json.dumps(payload), "queued", requested_by, created_at),
            )
        return self.get_job(job_id)

    def get_job(self, job_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT job_id, kind, payload_json, status, requested_by, created_at,
                       started_at, completed_at, summary, error
                FROM jobs WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if not row:
            return None
        return JobRecord(
            job_id=row[0],
            kind=row[1],
            payload=json.loads(row[2]),
            status=row[3],
            requested_by=row[4],
            created_at=datetime.fromisoformat(row[5]),
            started_at=_to_dt(row[6]),
            completed_at=_to_dt(row[7]),
            summary=row[8],
            error=row[9],
        )

    def set_running(self, job_id):
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, started_at = ? WHERE job_id = ?",
                ("running", _utc_now_iso(), job_id),
            )

    def set_completed(self, job_id, summary):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, summary = ?, completed_at = ?
                WHERE job_id = ?
                """,
                ("completed", summary, _utc_now_iso(), job_id),
            )

    def set_failed(self, job_id, error):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, error = ?, completed_at = ?
                WHERE job_id = ?
                """,
                ("failed", error, _utc_now_iso(), job_id),
            )
