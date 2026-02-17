from src.core.engine.executor import JobExecutor
from src.core.engine.job_store import JobStore
from src.core.models.job_models import JobRecord

from monitoring_hub.runner.executor import JobExecutor as LegacyJobExecutor
from monitoring_hub.runner.job_store import JobStore as LegacyJobStore
from monitoring_hub.runner.job_models import JobRecord as LegacyJobRecord


def test_src_core_runner_types_exist():
    assert JobExecutor is not None
    assert JobStore is not None
    assert JobRecord is not None


def test_legacy_runner_modules_reexport_src_core_types():
    assert LegacyJobExecutor is JobExecutor
    assert LegacyJobStore is JobStore
    assert LegacyJobRecord is JobRecord
