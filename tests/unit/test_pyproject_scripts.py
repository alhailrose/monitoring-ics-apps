from pathlib import Path


def test_monitoring_hub_script_uses_new_namespace():
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'monitoring-hub = "monitoring_hub.interfaces.cli.main:main"' in content
    assert 'monitoring-hub-dev = "monitoring_hub.interfaces.cli.main:main"' in content


def test_setuptools_includes_new_namespace_package():
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'include = ["src*", "monitoring_hub*"]' in content
