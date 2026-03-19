from pathlib import Path


def test_backend_runtime_has_no_direct_src_checks_imports():
    runtime_roots = [
        Path("backend") / "interfaces",
        Path("backend") / "domain",
        Path("backend") / "infra",
        Path("backend") / "config",
    ]
    offenders = []

    for root in runtime_roots:
        for py_file in root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            if "from src.checks" in text or "import src.checks" in text:
                offenders.append(str(py_file))

    assert offenders == []
