import backend.config.loader as loader

load_customer_config = getattr(loader, "load_customer_config")
list_customers = getattr(loader, "list_customers")


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


def test_env_override_configs_override_packaged_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(loader, "_repo_root", lambda: tmp_path / "repo-missing")
    monkeypatch.setenv("MONITORING_HUB_CONFIG_DIR", str(tmp_path))

    local_dir = tmp_path / "configs" / "customers"
    local_dir.mkdir(parents=True)
    local_cfg = local_dir / "asg.yaml"
    local_cfg.write_text(
        """
customer_id: asg
display_name: ASG LOCAL
accounts:
  - profile: asg-local
    account_id: "123"
""".lstrip(),
        encoding="utf-8",
    )

    cfg = load_customer_config("asg")
    assert cfg["display_name"] == "ASG LOCAL"
    assert cfg["accounts"][0]["profile"] == "asg-local"


def test_load_customer_config_falls_back_to_repo_configs(monkeypatch, tmp_path):
    monkeypatch.setattr(loader, "_module_defaults_dir", lambda: tmp_path / "missing")

    cfg = load_customer_config("aryanoble")

    assert cfg["customer_id"] == "aryanoble"
    assert len(cfg["accounts"]) > 0
