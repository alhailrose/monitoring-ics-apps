from src.core.engine.executor import JobExecutor
from src.core.engine.job_store import JobStore
from src.core.models.job_models import JobRecord


def test_src_core_runner_types_exist():
    assert JobExecutor is not None
    assert JobStore is not None
    assert JobRecord is not None
