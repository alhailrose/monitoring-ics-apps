from src.app.services.metric_samples_mapper import map_check_metric_samples


def test_map_daily_arbel_instances_to_metric_samples():
    raw = {
        "status": "ATTENTION REQUIRED",
        "service_type": "rds",
        "instances": {
            "writer": {
                "instance_id": "cis-prod-rds-instance",
                "metrics": {
                    "CPUUtilization": {
                        "status": "warn",
                        "message": "CPU Utilization: 88% (di atas 75%)",
                    },
                    "DatabaseConnections": {
                        "status": "ok",
                        "message": "DB Connections: 126 (normal)",
                    },
                    "FreeableMemory": {
                        "status": "past-warn",
                        "message": "Freeable Memory: 8.5 GB (sekarang normal)",
                    },
                },
            }
        },
    }

    rows = map_check_metric_samples(
        check_name="daily-arbel",
        account_id="acct-1",
        raw_result=raw,
    )

    assert len(rows) == 3
    cpu = next(row for row in rows if row["metric_name"] == "CPUUtilization")
    assert cpu["metric_status"] == "warn"
    assert cpu["value_num"] == 88.0
    assert cpu["unit"] == "Percent"
    assert cpu["resource_id"] == "cis-prod-rds-instance"

    memory = next(row for row in rows if row["metric_name"] == "FreeableMemory")
    assert memory["metric_status"] == "past-warn"
    assert memory["unit"] == "Bytes"
    assert memory["value_num"] == 8.5 * (1024**3)


def test_map_daily_arbel_extra_sections_to_metric_samples():
    raw = {
        "status": "OK",
        "service_type": "rds",
        "instances": {},
        "extra_sections": [
            {
                "section_name": "CIS ERHA EC2",
                "service_type": "ec2",
                "instances": {
                    "rabbitmq": {
                        "instance_id": "i-076e1d2c0c3478c21",
                        "instance_name": "aws-prod-rabbitmq",
                        "metrics": {
                            "CPUUtilization": {
                                "status": "ok",
                                "message": "CPU Utilization: 21% (normal)",
                            }
                        },
                    }
                },
            }
        ],
    }

    rows = map_check_metric_samples(
        check_name="daily-arbel",
        account_id="acct-2",
        raw_result=raw,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["service_type"] == "ec2"
    assert row["section_name"] == "CIS ERHA EC2"
    assert row["resource_name"] == "aws-prod-rabbitmq"


def test_map_check_metric_samples_returns_empty_for_unsupported_or_error_result():
    unsupported = map_check_metric_samples(
        check_name="guardduty",
        account_id="acct-3",
        raw_result={"status": "success", "instances": {}},
    )
    failed = map_check_metric_samples(
        check_name="daily-arbel",
        account_id="acct-4",
        raw_result={"status": "error", "error": "boom"},
    )

    assert unsupported == []
    assert failed == []
