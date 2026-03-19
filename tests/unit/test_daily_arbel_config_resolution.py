from src.checks.aryanoble.daily_arbel import DailyArbelChecker
from src.configs.loader import load_customer_config


def test_resolve_account_config_uses_customer_mapping_by_account_id(monkeypatch):
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=3)

    monkeypatch.setattr(
        "src.checks.aryanoble.daily_arbel.find_customer_account",
        lambda customer_id, account_id: {
            "account_id": account_id,
            "display_name": "Custom Alias",
            "daily_arbel": {
                "instances": {"writer": "my-instance"},
                "metrics": ["CPUUtilization"],
                "thresholds": {"CPUUtilization": 75},
            },
        },
    )

    cfg = checker._resolve_account_config("some-local-profile", "123456789012")

    assert cfg is not None
    assert cfg["account_name"] == "Custom Alias"
    assert cfg["instances"]["writer"] == "my-instance"


def test_resolve_account_config_falls_back_to_legacy_profile_map():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=3)

    cfg = checker._resolve_account_config("connect-prod", "620463044477")

    assert cfg is not None
    assert cfg["account_name"] == "CONNECT Prod (Non CIS)"


def test_resolve_account_config_loads_extra_sections_from_customer_mapping(monkeypatch):
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=3)

    monkeypatch.setattr(
        "src.checks.aryanoble.daily_arbel.find_customer_account",
        lambda customer_id, account_id: {
            "account_id": account_id,
            "display_name": "CIS ERHA",
            "daily_arbel": {
                "cluster_id": "cis-prod-rds",
                "instances": {"writer": "cis-prod-rds-instance"},
                "metrics": ["CPUUtilization"],
                "thresholds": {"CPUUtilization": 75},
            },
            "daily_arbel_extra": [
                {
                    "section_name": "CIS ERHA EC2",
                    "service_type": "ec2",
                    "instances": {"rabbitmq": "i-076e1d2c0c3478c21"},
                    "metrics": ["CPUUtilization"],
                    "thresholds": {"CPUUtilization": 75},
                }
            ],
        },
    )

    cfg = checker._resolve_account_config("cis-erha", "451916275465")

    assert cfg is not None
    assert len(cfg.get("extra_sections", [])) == 1
    assert cfg["extra_sections"][0]["service_type"] == "ec2"


def test_cis_erha_daily_arbel_extra_contains_ec2_memory_alarm():
    cfg = load_customer_config("aryanoble")
    cis = next(a for a in cfg["accounts"] if a.get("profile") == "cis-erha")
    extras = cis.get("daily_arbel_extra") or []

    assert extras
    rabbitmq = next(s for s in extras if s.get("section_name") == "CIS ERHA EC2")
    assert rabbitmq.get("metrics") == ["CPUUtilization", "NetworkIn", "NetworkOut"]
    assert rabbitmq.get("alarm_thresholds", {}).get("rabbitmq") == [
        "CIS RabbitMQ - Memory Alarm"
    ]


def test_resolve_account_config_applies_runtime_overrides_from_check_config(
    monkeypatch,
):
    checker = DailyArbelChecker(
        region="ap-southeast-3",
        window_hours=3,
        daily_arbel={
            "instances": {"writer": "override-instance"},
            "thresholds": {"CPUUtilization": 65},
            "metrics": ["CPUUtilization"],
        },
    )

    monkeypatch.setattr(
        "src.checks.aryanoble.daily_arbel.find_customer_account",
        lambda customer_id, account_id: {
            "account_id": account_id,
            "display_name": "Custom Alias",
            "daily_arbel": {
                "instances": {"writer": "base-instance"},
                "metrics": ["CPUUtilization"],
                "thresholds": {"CPUUtilization": 75},
            },
        },
    )

    cfg = checker._resolve_account_config("connect-prod", "620463044477")

    assert cfg is not None
    assert cfg["instances"]["writer"] == "override-instance"
    assert cfg["thresholds"]["CPUUtilization"] == 65
