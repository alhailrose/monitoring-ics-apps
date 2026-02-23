import json

from src.integrations.slack import notifier


def test_send_report_to_slack_skips_when_route_missing(monkeypatch):
    monkeypatch.setattr(
        notifier,
        "get_slack_report_config",
        lambda _name, client_key=None: {},
    )

    sent, reason = notifier.send_report_to_slack("daily-budget", "hello")

    assert sent is False
    assert reason == "slack route not configured"


def test_send_report_to_slack_posts_payload(monkeypatch):
    route = {
        "webhook_url": "https://hooks.slack.com/services/T/A/B",
        "channel": "#ops",
        "username": "Monitoring Bot",
    }
    captured = {"url": None, "body": None}

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_urlopen(req, timeout=10):
        captured["url"] = req.full_url
        captured["body"] = req.data
        return _Response()

    monkeypatch.setattr(
        notifier,
        "get_slack_report_config",
        lambda _name, client_key=None: route,
    )
    monkeypatch.setattr(notifier.request, "urlopen", _fake_urlopen)

    sent, reason = notifier.send_report_to_slack("daily-budget", "report text")

    assert sent is True
    assert reason == "ok"
    assert captured["url"] == route["webhook_url"]
    assert captured["body"] is not None
    payload = json.loads(captured["body"].decode("utf-8"))
    assert payload["text"] == "report text"
    assert payload["channel"] == "#ops"
    assert payload["username"] == "Monitoring Bot"
