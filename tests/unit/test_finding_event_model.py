from backend.infra.database.models import FindingEvent

from backend.domain.finding_events import FINDING_EVENT_CHECK_NAMES


def test_finding_event_model_has_expected_basic_columns():
    columns = set(FindingEvent.__table__.columns.keys())

    assert "id" in columns
    assert "check_run_id" in columns
    assert "account_id" in columns
    assert "check_name" in columns
    assert "finding_key" in columns
    assert "severity" in columns
    assert "title" in columns
    assert "description" in columns
    assert "raw_payload" in columns
    assert "created_at" in columns


def test_finding_event_check_name_constant_has_expected_values():
    assert "guardduty" in FINDING_EVENT_CHECK_NAMES
    assert "cloudwatch" in FINDING_EVENT_CHECK_NAMES
    assert "notifications" in FINDING_EVENT_CHECK_NAMES
    assert "backup" in FINDING_EVENT_CHECK_NAMES
