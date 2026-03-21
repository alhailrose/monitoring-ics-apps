from pathlib import Path


def test_config_imports_checks_from_backend_layers():
    source = Path("backend/domain/runtime/config.py").read_text(encoding="utf-8")

    assert "from backend.checks.generic" in source
    assert "from backend.checks.aryanoble" in source
    assert "from backend.checks.huawei" in source


def test_available_checks_contains_aws_utilization_3core_key():
    source = Path("backend/domain/runtime/config.py").read_text(encoding="utf-8")

    assert '"aws-utilization-3core"' in source
