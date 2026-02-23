from src.core.runtime import config_loader


def test_get_slack_report_config_returns_empty_when_disabled(monkeypatch):
    monkeypatch.setattr(
        config_loader,
        "_config",
        type("_Cfg", (), {"slack": {"enabled": False, "reports": {}}})(),
    )

    route = config_loader.get_slack_report_config("daily-budget")

    assert route == {}


def test_get_slack_report_config_returns_route_when_enabled(monkeypatch):
    monkeypatch.setattr(
        config_loader,
        "_config",
        type(
            "_Cfg",
            (),
            {
                "slack": {
                    "enabled": True,
                    "reports": {
                        "daily-budget": {
                            "webhook_url": "https://hooks.slack.com/services/T/A/B"
                        }
                    },
                }
            },
        )(),
    )

    route = config_loader.get_slack_report_config("daily-budget")

    assert route["webhook_url"] == "https://hooks.slack.com/services/T/A/B"


def test_get_slack_report_config_prefers_client_override(monkeypatch):
    monkeypatch.setattr(
        config_loader,
        "_config",
        type(
            "_Cfg",
            (),
            {
                "slack": {
                    "enabled": True,
                    "reports": {
                        "daily-budget": {
                            "webhook_url": "https://hooks.slack.com/services/T/A/B",
                            "channel": "#default-budget",
                            "clients": {
                                "cis-erha": {
                                    "channel": "#cis-budget",
                                    "webhook_url": "https://hooks.slack.com/services/T/CIS/ROUTE",
                                }
                            },
                        }
                    },
                }
            },
        )(),
    )

    route = config_loader.get_slack_report_config("daily-budget", client_key="cis-erha")

    assert route["webhook_url"] == "https://hooks.slack.com/services/T/CIS/ROUTE"
    assert route["channel"] == "#cis-budget"
