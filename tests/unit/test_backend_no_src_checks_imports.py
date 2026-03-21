from pathlib import Path


def test_backend_runtime_has_no_direct_src_checks_imports():
    runtime_roots = [
        Path("backend") / "interfaces",
        Path("backend") / "domain",
        Path("backend") / "infra",
        Path("backend") / "config",
    ]
    offenders = []

    src_from = "from " + "src.checks"
    src_import = "import " + "src.checks"

    for root in runtime_roots:
        for py_file in root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            if src_from in text or src_import in text:
                offenders.append(str(py_file))

    assert offenders == []


def test_src_checks_has_no_python_modules():
    src_checks_root = Path("src") / "checks"
    offenders = [str(path) for path in src_checks_root.rglob("*.py")]

    assert offenders == []
