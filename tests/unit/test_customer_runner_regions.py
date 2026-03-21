from backend.domain.runtime import customer_runner


class _FakeChecker:
    def __init__(self, region: str, **_kwargs):
        self.region = region

    def format_report(self, _result):
        return "ok"


def test_run_customer_checks_prefers_account_region(monkeypatch):
    cfg = {
        "customer_id": "frisianflag",
        "display_name": "Frisian Flag Indonesia",
        "checks": ["cloudwatch"],
        "accounts": [
            {
                "profile": "frisianflag",
                "account_id": "315897480848",
                "display_name": "Frisian Flag Indonesia",
                "region": "ap-southeast-1",
            }
        ],
    }

    captured_regions: list[str] = []

    def _fake_run(_check_name, _profile, _account_id, region, check_kwargs=None):
        captured_regions.append(region)
        return {"status": "success"}

    monkeypatch.setattr(customer_runner, "load_customer_config", lambda _id: cfg)
    monkeypatch.setattr(customer_runner, "_run_check_for_account", _fake_run)
    monkeypatch.setitem(customer_runner.AVAILABLE_CHECKS, "cloudwatch", _FakeChecker)

    result = customer_runner.run_customer_checks(
        customer_id="frisianflag",
        region="ap-southeast-3",
        workers=1,
    )

    assert result is not None
    assert captured_regions == ["ap-southeast-1"]
