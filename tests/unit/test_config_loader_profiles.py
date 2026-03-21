from backend.config import loader


def test_collect_customer_profiles_filters_by_sso_and_dedupes(monkeypatch):
    monkeypatch.setattr(
        loader,
        "list_customers",
        lambda: [
            {"customer_id": "diamond"},
            {"customer_id": "kki"},
            {"customer_id": "other"},
        ],
    )

    def _fake_load(customer_id):
        if customer_id == "diamond":
            return {
                "sso_session": "sadewa-sso",
                "accounts": [{"profile": "Diamond"}, {"profile": "Shared"}],
            }
        if customer_id == "kki":
            return {
                "sso_session": "sadewa-sso",
                "accounts": [{"profile": "KKI"}, {"profile": "Shared"}],
            }
        return {
            "sso_session": "other-sso",
            "accounts": [{"profile": "Other"}],
        }

    monkeypatch.setattr(loader, "load_customer_config", _fake_load)

    profiles = loader.collect_customer_profiles(sso_session="sadewa-sso")

    assert profiles == ["Diamond", "Shared", "KKI"]


def test_collect_customer_profiles_returns_all_when_no_filter(monkeypatch):
    monkeypatch.setattr(
        loader,
        "list_customers",
        lambda: [
            {"customer_id": "c1"},
            {"customer_id": "c2"},
        ],
    )
    monkeypatch.setattr(
        loader,
        "load_customer_config",
        lambda customer_id: {
            "sso_session": "any",
            "accounts": [{"profile": f"{customer_id}-p1"}],
        },
    )

    assert loader.collect_customer_profiles() == ["c1-p1", "c2-p1"]
