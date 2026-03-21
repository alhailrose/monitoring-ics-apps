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


def test_finding_event_check_name_constraint_matches_shared_constant():
    table_constraints = FindingEvent.__table__.constraints
    check_constraint = next(
        constraint
        for constraint in table_constraints
        if getattr(constraint, "name", "") == "ck_finding_events_check_name_valid"
    )

    check_sql = str(check_constraint.sqltext)
    expected = "check_name in ('guardduty','cloudwatch','notifications','backup')"

    assert check_sql == expected
    assert FINDING_EVENT_CHECK_NAMES == (
        "guardduty",
        "cloudwatch",
        "notifications",
        "backup",
    )
