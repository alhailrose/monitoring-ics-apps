from backend.infra.database.models import MetricSample

from backend.domain.metric_samples import METRIC_SAMPLE_CHECK_NAMES


def test_metric_sample_model_has_expected_basic_columns():
    columns = set(MetricSample.__table__.columns.keys())

    assert "id" in columns
    assert "check_run_id" in columns
    assert "account_id" in columns
    assert "check_name" in columns
    assert "metric_name" in columns
    assert "metric_status" in columns
    assert "value_num" in columns
    assert "unit" in columns
    assert "resource_role" in columns
    assert "resource_id" in columns
    assert "resource_name" in columns
    assert "service_type" in columns
    assert "section_name" in columns
    assert "raw_payload" in columns
    assert "created_at" in columns


def test_metric_sample_check_name_constraint_matches_shared_constant():
    table_constraints = MetricSample.__table__.constraints
    check_constraint = next(
        constraint
        for constraint in table_constraints
        if getattr(constraint, "name", "") == "ck_metric_samples_check_name_valid"
    )

    check_sql = str(check_constraint.sqltext)
    expected = "check_name in ('daily-arbel')"

    assert check_sql == expected
    assert METRIC_SAMPLE_CHECK_NAMES == ("daily-arbel",)
