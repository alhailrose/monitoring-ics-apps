from monitoring_hub.runner.executor import JobExecutor
from monitoring_hub.runner.job_store import JobStore


def test_job_store_persists_created_job(tmp_path):
    store = JobStore(tmp_path / "jobs.db")
    created = store.create_job("arbel-rds", {"window": "12h"}, requested_by="slack")

    loaded = store.get_job(created.job_id)

    assert loaded is not None
    assert loaded.kind == "arbel-rds"
    assert loaded.payload["window"] == "12h"
    assert loaded.status == "queued"


def test_job_executor_moves_job_to_completed(tmp_path):
    store = JobStore(tmp_path / "jobs.db")
    created = store.create_job("arbel-budget", {"group": "Aryanoble"})

    def _handler(payload):
        return f"ok:{payload['group']}"

    executor = JobExecutor(store, handlers={"arbel-budget": _handler})
    executor.run_once(created.job_id)

    loaded = store.get_job(created.job_id)
    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.summary == "ok:Aryanoble"
    assert loaded.started_at is not None
    assert loaded.completed_at is not None


def test_job_executor_moves_job_to_failed_on_exception(tmp_path):
    store = JobStore(tmp_path / "jobs.db")
    created = store.create_job("arbel-rds", {"window": "1h"})

    def _handler(_payload):
        raise RuntimeError("boom")

    executor = JobExecutor(store, handlers={"arbel-rds": _handler})
    executor.run_once(created.job_id)

    loaded = store.get_job(created.job_id)
    assert loaded is not None
    assert loaded.status == "failed"
    assert "boom" in (loaded.error or "")
