from backend.domain.runtime import runners


class _FakeChecker:
    def __init__(self, issue_label="issues"):
        self.issue_label = issue_label

    def count_issues(self, result):
        return int(result.get("count", 0) or 0)


class _FakeUtilChecker:
    issue_label = "utilization warning/critical instances"

    def count_issues(self, result):
        summary = result.get("summary", {}) or {}
        return int(summary.get("warning", 0) or 0) + int(
            summary.get("critical", 0) or 0
        )


def test_summary_mode_prints_all_is_ok_when_no_findings(capsys):
    profiles = ["programa"]
    checks = {"aws-utilization-3core": object(), "cloudwatch": object()}
    checkers = {
        "aws-utilization-3core": _FakeUtilChecker(),
        "cloudwatch": _FakeChecker(issue_label="infrastructure alerts"),
    }
    all_results = {
        "programa": {
            "aws-utilization-3core": {
                "status": "success",
                "summary": {
                    "normal": 1,
                    "warning": 0,
                    "critical": 0,
                    "partial_data": 0,
                },
                "instances": [
                    {
                        "instance_id": "i-1",
                        "name": "app",
                        "cpu_avg_12h": 18.0,
                        "cpu_peak_12h": 22.0,
                        "memory_avg_12h": 27.0,
                        "memory_peak_12h": 33.0,
                        "disk_free_min_percent": 44.0,
                        "status": "NORMAL",
                    }
                ],
            },
            "cloudwatch": {"status": "success", "count": 0},
        }
    }

    runners._print_consolidated_report(
        profiles=profiles,
        all_results=all_results,
        checks=checks,
        checkers=checkers,
        check_errors=[],
        clean_accounts=["programa"],
        errors_by_check={"aws-utilization-3core": [], "cloudwatch": []},
        region="ap-southeast-3",
        group_name="Demo",
        output_mode="summary",
    )

    out = capsys.readouterr().out
    assert "Selamat " in out
    assert "Team" in out
    assert "Berikut Alert Monitoring" in out
    assert "Utilisasi 12 Jam (CPU/MEM/DISK)" in out
    assert "N=" not in out
    assert "app | CPU(avg)=18.00% | MEM(avg)=27.00% | DISK=44.00%" in out
    assert "i-1" not in out
    assert "All Is Ok" in out


def test_summary_mode_shows_findings_and_missing_metric_notes(capsys):
    profiles = ["techmeister"]
    checks = {"aws-utilization-3core": object(), "cloudwatch": object()}
    checkers = {
        "aws-utilization-3core": _FakeUtilChecker(),
        "cloudwatch": _FakeChecker(issue_label="infrastructure alerts"),
    }
    all_results = {
        "techmeister": {
            "aws-utilization-3core": {
                "status": "success",
                "summary": {
                    "normal": 0,
                    "warning": 1,
                    "critical": 0,
                    "partial_data": 1,
                },
                "instances": [
                    {
                        "instance_id": "i-1",
                        "name": "node-a",
                        "cpu_avg_12h": 31.0,
                        "cpu_peak_12h": 72.0,
                        "memory_peak_12h": None,
                        "disk_free_min_percent": None,
                        "status": "WARNING",
                    }
                ],
            },
            "cloudwatch": {"status": "success", "count": 2},
        }
    }

    runners._print_consolidated_report(
        profiles=profiles,
        all_results=all_results,
        checks=checks,
        checkers=checkers,
        check_errors=[],
        clean_accounts=[],
        errors_by_check={"aws-utilization-3core": [], "cloudwatch": []},
        region="ap-southeast-3",
        group_name="Demo",
        output_mode="summary",
    )

    out = capsys.readouterr().out
    assert "Temuan Penting" in out
    assert "- Alarm CloudWatch: ada temuan" in out
    assert "- Alarm CloudWatch -" in out
    assert "2 alarm aktif" in out
    assert "Catatan Alert:" in out
    assert "CPU node-a sempat tinggi 72.00%" in out
    assert "avg=31.00%" in out
    assert "Data Tidak Tersedia" not in out
    assert "i-1 (node-a)" not in out
    assert "WARNING:" not in out
    assert "node-a | CPU(avg)=31.00%" in out
    assert "MEM=N/A" not in out
    assert "DISK=N/A" not in out
    assert "All Is Ok" not in out


def test_summary_mode_cloudwatch_only_renders_alarm_names_only(capsys):
    profiles = ["frisianflag"]
    checks = {"cloudwatch": object()}
    checkers = {
        "cloudwatch": _FakeChecker(issue_label="infrastructure alerts"),
    }
    all_results = {
        "frisianflag": {
            "cloudwatch": {
                "status": "success",
                "count": 2,
                "details": [
                    {"name": "FFI-microservice-RDS-CPUUtilization > 90%"},
                    {"name": "FFI-Legal-Prod-EC2-DiskUtilization-C > 90%"},
                ],
            }
        }
    }

    runners._print_consolidated_report(
        profiles=profiles,
        all_results=all_results,
        checks=checks,
        checkers=checkers,
        check_errors=[],
        clean_accounts=[],
        errors_by_check={"cloudwatch": []},
        region="ap-southeast-1",
        group_name="Frisian Flag Indonesia",
        output_mode="summary",
    )

    out = capsys.readouterr().out
    assert "Berikut Alert" in out
    assert "FFI-microservice-RDS-CPUUtilization > 90%" in out
    assert "FFI-Legal-Prod-EC2-DiskUtilization-C > 90%" in out
    assert "Ringkasan Check Lain" not in out
