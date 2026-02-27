import src.configs.loader as loader
from src.configs.loader import list_customers, load_customer_config


def test_load_customer_config_works_without_repo_configs(monkeypatch, tmp_path):
    monkeypatch.setattr(loader, "_repo_root", lambda: tmp_path)

    cfg = load_customer_config("aryanoble")

    assert cfg["customer_id"] == "aryanoble"
    assert any(a["account_id"] == "620463044477" for a in cfg["accounts"])


def test_load_other_customers_from_packaged_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(loader, "_repo_root", lambda: tmp_path)

    asg_cfg = load_customer_config("asg")

    assert asg_cfg["customer_id"] == "asg"
    assert asg_cfg["accounts"][0]["profile"] == "asg"

    customer_ids = {c["customer_id"] for c in list_customers()}
    assert "aryanoble" in customer_ids
    assert "asg" in customer_ids
