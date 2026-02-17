from pathlib import Path
import re


def test_target_src_structure_exists():
    required_paths = [
        "src/app/cli",
        "src/app/tui",
        "src/app/api",
        "src/core/engine",
        "src/core/models",
        "src/core/formatting",
        "src/providers/aws/services",
        "src/checks/common",
        "src/checks/aryanoble",
        "src/checks/generic",
        "src/configs/defaults/customers",
        "src/configs/schema",
        "tests/unit",
        "tests/integration",
    ]

    for path in required_paths:
        assert Path(path).exists(), f"missing path: {path}"


def test_architecture_contract_doc_exists():
    assert Path("docs/architecture/target-structure-contract.md").exists()


def test_no_legacy_root_tests_outside_unit_integration():
    root_tests = list(Path("tests").glob("test_*.py"))
    assert not root_tests, f"legacy root tests remain: {[p.name for p in root_tests]}"


def test_src_runtime_has_no_legacy_imports():
    forbidden = re.compile(r"^\s*(from|import)\s+(monitoring_hub|checks)(\.|\s|$)")
    violations = []

    for path in Path("src").rglob("*.py"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if forbidden.search(line):
                violations.append(f"{path}:{lineno}:{line.strip()}")

    assert not violations, "src runtime imports legacy modules:\n" + "\n".join(
        violations
    )
