from backend.domain.engine.executor import JobExecutor
from backend.domain.engine.job_store import JobStore
from backend.domain.models.job_models import JobRecord


def test_src_core_runner_types_exist():
    assert JobExecutor is not None
    assert JobStore is not None
    assert JobRecord is not None
