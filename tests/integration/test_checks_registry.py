from pathlib import Path


def test_config_imports_checks_from_src_layers():
    source = Path("src/core/runtime/config.py").read_text(encoding="utf-8")

    assert "from src.checks.generic" in source
    assert "from src.checks.aryanoble" in source
    assert "from src.checks.huawei" in source


def test_available_checks_contains_aws_utilization_3core_key():
    source = Path("src/core/runtime/config.py").read_text(encoding="utf-8")

    assert '"aws-utilization-3core"' in source
