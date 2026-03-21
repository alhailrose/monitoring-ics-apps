from pathlib import Path


def test_repository_has_no_src_namespace_python_imports():
    offenders = []
    root = Path(".")
    src_from = "from " + "src."
    src_import = "import " + "src."

    for py_file in root.rglob("*.py"):
        parts = py_file.parts
        if (
            ".venv" in parts
            or ".git" in parts
            or "build" in parts
            or ".worktrees" in parts
        ):
            continue

        text = py_file.read_text(encoding="utf-8")
        if src_from in text or src_import in text:
            offenders.append(str(py_file))

    assert offenders == []
