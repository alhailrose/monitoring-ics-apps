from pathlib import Path


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
