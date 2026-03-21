from pathlib import Path


def test_pyproject_scripts_point_to_backend_entrypoint():
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'monitoring-hub = "backend.interfaces.cli.main:main"' in content
    assert 'monitoring-hub-dev = "backend.interfaces.cli.main:main"' in content


def test_setuptools_includes_backend_namespace_package_only():
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'include = ["backend*"]' in content
