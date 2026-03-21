from pathlib import Path
import re


def test_target_backend_structure_exists():
    required_paths = [
        "backend/interfaces/cli",
        "backend/interfaces/api",
        "backend/domain/engine",
        "backend/domain/models",
        "backend/domain/formatting",
        "backend/infra/cloud/aws/services",
        "backend/checks/common",
        "backend/checks/aryanoble",
        "backend/checks/generic",
        "backend/config/defaults/customers",
        "backend/config/schema",
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


def test_backend_runtime_has_no_legacy_imports():
    forbidden = re.compile(r"^\s*(from|import)\s+(monitoring_hub|checks)(\.|\s|$)")
    violations = []

    for path in Path("backend").rglob("*.py"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if forbidden.search(line):
                violations.append(f"{path}:{lineno}:{line.strip()}")

    assert not violations, "backend runtime imports legacy modules:\n" + "\n".join(
        violations
    )


def test_legacy_top_level_packages_removed():
    assert not Path("monitoring_hub").exists()
    assert not Path("checks").exists()


def test_src_namespace_has_no_runtime_modules():
    src_root = Path("src")
    if not src_root.exists():
        return

    offenders = [str(path) for path in src_root.rglob("*.py")]
    assert offenders == []
