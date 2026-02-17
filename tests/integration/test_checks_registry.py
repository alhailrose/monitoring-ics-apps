from pathlib import Path


def test_config_imports_checks_from_src_layers():
    source = Path("monitoring_hub/config.py").read_text(encoding="utf-8")

    assert "from src.checks.generic" in source
    assert "from src.checks.aryanoble" in source
