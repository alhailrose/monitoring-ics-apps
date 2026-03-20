import pytest

from backend.checks.huawei.ecs_utilization import HuaweiECSUtilizationChecker


def _first_non_empty_line(lines):
    return next((line for line in lines if line.strip()), "")


def test_checker_supports_consolidated_mode_metadata_is_set():
    checker = HuaweiECSUtilizationChecker()

    assert checker.supports_consolidated is True
    assert isinstance(checker.report_section_title, str)
    assert checker.report_section_title.strip()
    assert isinstance(checker.issue_label, str)
    assert checker.issue_label.strip()


def test_render_section_includes_title_and_handles_mixed_success_no_data_and_errors():
    checker = HuaweiECSUtilizationChecker()

    all_results = {
        "acct-hot": {
            "status": "success",
            "account_id": "111111111111",
            "util": {
                "top_mem_hot": [
                    {"name": "prod-db-1", "peak": 91.2, "behavior": "SPIKE"},
                ]
            },
        },
        "acct-empty": {
            "status": "success",
            "account_id": "222222222222",
            "util": {"top_mem_hot": []},
        },
    }
    errors = [("acct-fail", "hcloud timeout")]

    lines = checker.render_section(all_results, errors)
    rendered = "\n".join(lines)

    assert lines
    assert _first_non_empty_line(lines) == checker.report_section_title

    # Every input profile should be represented at account-level output.
    assert any("acct-hot" in line for line in lines)
    assert any("acct-empty" in line for line in lines)
    assert any("acct-fail" in line for line in lines)

    # Success details and no-data should both be present.
    assert "prod-db-1" in rendered
    assert "no data" in rendered.lower()

    # Errors should be explicitly separated/represented.
    assert any("error" in line.lower() for line in lines)
    assert "hcloud timeout" in rendered


def test_render_section_boundary_with_empty_results_and_no_errors():
    checker = HuaweiECSUtilizationChecker()

    lines = checker.render_section({}, [])
    rendered = "\n".join(lines)

    assert lines
    assert _first_non_empty_line(lines) == checker.report_section_title
    assert "no data" in rendered.lower()


def test_render_section_boundary_with_only_errors():
    checker = HuaweiECSUtilizationChecker()

    errors = [("acct-a", "request timeout"), ("acct-b", "auth failed")]

    lines = checker.render_section({}, errors)
    rendered = "\n".join(lines)

    assert lines
    assert _first_non_empty_line(lines) == checker.report_section_title
    assert any("error" in line.lower() for line in lines)
    assert any("acct-a" in line for line in lines)
    assert any("acct-b" in line for line in lines)
    assert "request timeout" in rendered
    assert "auth failed" in rendered


def test_render_section_boundary_with_only_successes_and_malformed_util_payloads():
    checker = HuaweiECSUtilizationChecker()

    all_results = {
        "acct-missing-util": {"status": "success", "account_id": "111"},
        "acct-util-none": {"status": "success", "account_id": "222", "util": None},
        "acct-hot-not-list": {
            "status": "success",
            "account_id": "333",
            "util": {"top_mem_hot": "invalid"},
        },
    }

    lines = checker.render_section(all_results, [])
    rendered = "\n".join(lines)

    assert lines
    assert _first_non_empty_line(lines) == checker.report_section_title
    assert any("acct-missing-util" in line for line in lines)
    assert any("acct-util-none" in line for line in lines)
    assert any("acct-hot-not-list" in line for line in lines)
    assert "no data" in rendered.lower()


def test_count_issues_counts_hot_memory_findings_from_top_mem_hot():
    checker = HuaweiECSUtilizationChecker()

    success_result = {
        "status": "success",
        "util": {
            "top_mem_hot": [
                {"name": "db-a", "peak": 88.0, "behavior": "SPIKE"},
                {"name": "db-b", "peak": 92.1, "behavior": "HIGH_STABLE"},
                {"name": "db-c", "peak": 85.3, "behavior": "SPIKE"},
            ]
        },
    }

    assert checker.count_issues(success_result) == 3
    assert checker.count_issues({"status": "error", "error": "boom"}) == 0


@pytest.mark.parametrize(
    "result",
    [
        {"status": "success"},
        {"status": "success", "util": {}},
        {"status": "success", "util": {"top_mem_hot": None}},
        {"status": "success", "util": {"top_mem_hot": "not-a-list"}},
    ],
)
def test_count_issues_returns_zero_for_missing_or_invalid_top_mem_hot(result):
    checker = HuaweiECSUtilizationChecker()

    assert checker.count_issues(result) == 0


def test_count_issues_counts_entries_when_top_mem_hot_list_contains_non_dict_items():
    checker = HuaweiECSUtilizationChecker()

    # Contract: count_issues is aggregation-focused and counts list entries when
    # top_mem_hot exists as a list, regardless of item shape.
    result = {
        "status": "success",
        "util": {"top_mem_hot": ["bad-row", 123, {"name": "db-ok", "peak": 81.0}]},
    }

    assert checker.count_issues(result) == 3
