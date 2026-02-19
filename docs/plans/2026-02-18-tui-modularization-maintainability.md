# TUI Modularization Maintainability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce complexity of TUI layer by splitting `src/app/tui/interactive.py` into cohesive modules while preserving existing CLI/TUI behavior.

**Architecture:** Keep `src/app/tui/interactive.py` as a thin orchestration entrypoint and move large feature flows into separate modules (`arbel`, `cost`, `nabati`, `settings`, `dashboard`). Share stable helper functions through a small `common` module and maintain imports only inside `src/app/tui`.

**Tech Stack:** Python 3.12, pytest, questionary, rich.

---

### Task 1: Add regression tests for current TUI entry behavior

**Files:**
- Modify: `tests/unit/test_interactive_v2.py`
- Test: `tests/integration/test_cli_entrypoints.py`

**Step 1: Write the failing test**
- Add assertions that `run_interactive` and `run_interactive_v2` remain callable and delegated through `src.app.tui.bootstrap`.

**Step 2: Run test to verify it fails**
- Run: `uv run --with pytest pytest tests/unit/test_interactive_v2.py tests/integration/test_cli_entrypoints.py -v`

**Step 3: Write minimal implementation**
- Keep bootstrap API unchanged while refactoring internals.

**Step 4: Run test to verify it passes**
- Run same command and confirm PASS.

### Task 2: Extract reusable TUI helpers from oversized interactive module

**Files:**
- Create: `src/app/tui/common.py`
- Modify: `src/app/tui/interactive.py`

**Step 1: Write the failing test**
- Add/update tests that patch helper functions (`_select_prompt`, `_pause`) and verify flow behavior still works.

**Step 2: Run test to verify it fails**
- Run targeted TUI unit tests.

**Step 3: Write minimal implementation**
- Move shared prompt/interrupt/selection helpers to `common.py`.
- Re-export needed helper symbols in `interactive.py` for compatibility with existing tests.

**Step 4: Run test to verify it passes**
- Run: `uv run --with pytest pytest tests/unit/test_interactive_v2.py -v`

### Task 3: Move feature-specific TUI flows into dedicated modules

**Files:**
- Create: `src/app/tui/flows/arbel.py`
- Create: `src/app/tui/flows/cloudwatch_cost.py`
- Create: `src/app/tui/flows/nabati.py`
- Create: `src/app/tui/flows/settings.py`
- Modify: `src/app/tui/interactive.py`

**Step 1: Write the failing test**
- Add/adjust test assertions for menu dispatch function boundaries.

**Step 2: Run test to verify it fails**
- Run `tests/unit/test_interactive_v2.py`.

**Step 3: Write minimal implementation**
- Move each flow function out of `interactive.py`.
- Keep function names and menu choices unchanged.
- Keep imports local and avoid behavior changes.

**Step 4: Run test to verify it passes**
- Run: `uv run --with pytest pytest tests/unit/test_interactive_v2.py -v`

### Task 4: Full verification and runtime smoke

**Files:**
- Verify only

**Step 1: Run complete test suite**
- Run: `uv run --with pytest pytest`

**Step 2: Run CLI and TUI smoke checks**
- Run: `uv run monitoring-hub --version`
- Run: `timeout 5s script -q -c "uv run monitoring-hub --interactive" /dev/null`

**Step 3: Commit**
- `git add ...`
- `git commit -m "refactor: modularize TUI flows for maintainability"`
