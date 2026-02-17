# Stabilize Refactor and Pipx Install Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring current refactor workspace to a stable state where tests pass and `pipx` install/reinstall can launch interactive CLI reliably.

**Architecture:** Keep canonical runtime paths in `src/*`, preserve compatibility wrappers in `monitoring_hub/*`, and make CLI resilient when TUI dependency is absent. Validate behavior with targeted unit tests first, then full-suite and `pipx` smoke verification.

**Tech Stack:** Python 3.12, pytest, setuptools/pyproject, pipx, rich/questionary CLI stack.

---

### Task 1: Fix test expectation drift for release version

**Files:**
- Modify: `tests/unit/test_cli_without_tui_dependency.py`
- Reference: `pyproject.toml`

**Step 1: Write the failing test**

Existing failing assertion expects `v1.4.1` while project metadata is `1.4.0`.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli_without_tui_dependency.py::test_cli_version_works_without_questionary_installed -v`
Expected: FAIL at version assertion.

**Step 3: Write minimal implementation**

Update assertion to expected current version (`v1.4.0`) so test reflects package metadata.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_cli_without_tui_dependency.py -v`
Expected: all tests in file PASS.

### Task 2: Verify CLI fallback without TUI dependency

**Files:**
- Verify: `src/app/cli/bootstrap.py`
- Verify: `monitoring_hub/config.py`
- Test: `tests/unit/test_cli_without_tui_dependency.py`

**Step 1: Write the failing test**

Use existing no-questionary tests as regression for fallback behavior.

**Step 2: Run test to verify it fails**

Run same command from Task 1 if needed.

**Step 3: Write minimal implementation**

Keep lazy import + error message path in CLI interactive launcher and fallback style object in config module.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_cli_without_tui_dependency.py -v`
Expected: PASS with no traceback output.

### Task 3: Validate pipx install/reinstall interactive startup

**Files:**
- Runtime verify only (no source edits required if green)

**Step 1: Run install path**

Run: `pipx uninstall monitoring-hub || true && pipx install "/home/heilrose/workspace/monitoring-apps"`
Expected: package installed from local repo.

**Step 2: Verify command availability**

Run: `monitoring-hub --version`
Expected: prints current app version.

**Step 3: Verify interactive startup smoke**

Run: `timeout 5s script -q -c "monitoring-hub --interactive" /dev/null`
Expected: banner/menu renders before timeout.

**Step 4: Verify reinstall path**

Run: `pipx reinstall monitoring-hub && monitoring-hub --version`
Expected: reinstall succeeds and command still runs.

### Task 4: End-to-end verification

**Files:**
- Verify entire repo behavior

**Step 1: Run full test suite**

Run: `uv run pytest`
Expected: all tests PASS.

**Step 2: Report exact outcomes**

Document test count, pass/fail state, and `pipx` install/reinstall evidence.
