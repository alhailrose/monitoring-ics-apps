import src.configs.loader as loader
from src.configs.loader import load_customer_config


def test_load_customer_config_works_without_repo_configs(monkeypatch, tmp_path):
    monkeypatch.setattr(loader, "_repo_root", lambda: tmp_path)

    cfg = load_customer_config("aryanoble")

    assert cfg["customer_id"] == "aryanoble"
    assert any(a["account_id"] == "620463044477" for a in cfg["accounts"])
