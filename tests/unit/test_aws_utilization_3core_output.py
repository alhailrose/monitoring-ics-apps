from backend.checks.generic.aws_utilization_3core import AWSUtilization3CoreChecker


def _first_non_empty_line(lines):
    return next((line for line in lines if line.strip()), "")


def test_render_section_shows_account_summary_counts():
    checker = AWSUtilization3CoreChecker()

    lines = checker.render_section(
        {
            "programa": {
                "status": "success",
                "account_id": "779060063462",
                "summary": {
                    "normal": 2,
                    "warning": 1,
                    "critical": 0,
                    "partial_data": 0,
                },
                "instances": [],
            }
        },
        [],
    )

    rendered = "\n".join(lines)
    assert _first_non_empty_line(lines) == checker.report_section_title
    assert "programa" in rendered
    assert "normal=2" in rendered
    assert "warning=1" in rendered


def test_render_section_shows_per_instance_with_status_labels():
    checker = AWSUtilization3CoreChecker()

    lines = checker.render_section(
        {
            "ucoal-prod": {
                "status": "success",
                "account_id": "637423564327",
                "summary": {
                    "normal": 0,
                    "warning": 1,
                    "critical": 1,
                    "partial_data": 0,
                },
                "instances": [
                    {
                        "instance_id": "i-1",
                        "name": "gateway",
                        "os_type": "linux",
                        "region": "ap-southeast-3",
                        "cpu_peak_12h": 88.0,
                        "memory_peak_12h": 50.0,
                        "disk_free_min_percent": 9.0,
                        "status": "CRITICAL",
                    },
                    {
                        "instance_id": "i-2",
                        "name": "worker",
                        "os_type": "linux",
                        "region": "ap-southeast-3",
                        "cpu_peak_12h": 72.0,
                        "memory_peak_12h": 62.0,
                        "disk_free_min_percent": 30.0,
                        "status": "WARNING",
                    },
                ],
            }
        },
        [],
    )

    rendered = "\n".join(lines)
    assert "status=CRITICAL" in rendered
    assert "status=WARNING" in rendered
    assert "i-1" in rendered
    assert "i-2" in rendered


def test_render_section_shows_memory_na_when_missing():
    checker = AWSUtilization3CoreChecker()

    lines = checker.render_section(
        {
            "edot": {
                "status": "success",
                "account_id": "261622543538",
                "summary": {
                    "normal": 0,
                    "warning": 0,
                    "critical": 0,
                    "partial_data": 1,
                },
                "instances": [
                    {
                        "instance_id": "i-na",
                        "name": "batch",
                        "os_type": "linux",
                        "region": "ap-southeast-1",
                        "cpu_peak_12h": 33.0,
                        "memory_peak_12h": None,
                        "disk_free_min_percent": 45.0,
                        "status": "PARTIAL_DATA",
                    }
                ],
            }
        },
        [],
    )

    rendered = "\n".join(lines)
    assert "MEM peak=N/A" in rendered
    assert "status=PARTIAL_DATA" in rendered


def test_count_issues_counts_warning_and_critical_only():
    checker = AWSUtilization3CoreChecker()
    result = {
        "status": "success",
        "instances": [
            {"status": "NORMAL"},
            {"status": "PARTIAL_DATA"},
            {"status": "WARNING"},
            {"status": "CRITICAL"},
        ],
    }

    assert checker.count_issues(result) == 2
