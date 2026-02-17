# Full Src Runtime Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `src` the runtime source of truth, remove runtime `src` imports of `monitoring_hub.*` and `checks.*`, preserve CLI/TUI behavior, and keep tests/smokes green.

**Architecture:** Promote current adapter modules under `src/` into canonical implementations by moving runtime logic from legacy roots into `src` mirrors. Convert legacy root modules to compatibility wrappers that import from `src`. Keep user-facing command behavior unchanged while flipping packaging/entrypoint to src-first.

**Tech Stack:** Python, pytest, setuptools/pyproject, uv, rich/questionary.

---

### Task 1: Add migration guardrail tests first

**Files:**
- Modify: `tests/integration/test_project_structure.py`
- Modify: `tests/integration/test_cli_entrypoints.py`

1. Add a failing integration test that scans `src/**/*.py` and fails if any file imports `monitoring_hub.` or `checks.`.
2. Add/adjust test expectations for src-first CLI entrypoint metadata.
3. Run targeted tests and verify failure occurs for current adapters.

### Task 2: Migrate src runtime implementations

**Files:**
- Modify: `src/app/cli/main.py`
- Modify: `src/app/cli/bootstrap.py`
- Modify: `src/app/tui/interactive.py`
- Modify: `src/checks/common/base.py`
- Modify: `src/checks/generic/*.py`
- Modify: `src/checks/aryanoble/*.py`
- Modify: `src/core/formatting/reports.py`
- Create: `src/core/runtime/config.py`, `src/core/runtime/config_loader.py`, `src/core/runtime/utils.py`, `src/core/runtime/ui.py`, `src/core/runtime/runners.py`, `src/core/runtime/reports.py` (or equivalent src runtime module set)

1. Replace src adapter imports with src-native code paths.
2. Keep behavior by reusing existing runtime logic in src modules.
3. Preserve exported names used by CLI/TUI and existing tests.
4. Run targeted tests incrementally after each migrated area.

### Task 3: Convert legacy roots to wrappers

**Files:**
- Modify: `monitoring_hub/*.py` (runtime-facing modules used by CLI/TUI)
- Modify: `checks/*.py`

1. Keep backward compatibility by making legacy modules import and re-export src implementations.
2. Ensure no cyclic import between legacy wrappers and src modules.
3. Re-run integration/unit tests covering wrappers.

### Task 4: Flip packaging/entrypoint and docs

**Files:**
- Modify: `pyproject.toml`
- Modify: `docs/architecture/migration-status.md`

1. Update script entrypoint to src runtime module.
2. Ensure package discovery reflects src-first runtime while retaining compatibility packages if required.
3. Update migration status doc to reflect completed state and compatibility posture.

### Task 5: Full verification and commit

**Files:**
- All changed files above

1. Run full test suite: `uv run --with pytest pytest`.
2. Run smoke checks:
   - `uv run monitoring-hub --version`
   - `timeout 5s script -q -c "uv run monitoring-hub --interactive" /dev/null`
3. Confirm clean import guardrails and no regressions.
4. Commit with clear migration message.
