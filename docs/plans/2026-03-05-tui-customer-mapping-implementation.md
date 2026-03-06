# TUI Customer Mapping and Check Assignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add TUI/CLI customer setup workflow for scanning profiles, assigning accounts, and configuring default checks using YAML configs only, while improving customer report selection UX (no auto-select, explicit select-all/clear, search).

**Architecture:** Keep YAML in `configs/customers/*.yaml` as the only TUI data source. Extend CLI customer subcommands for setup operations and reuse TUI common prompt helpers for searchable selection patterns. Preserve existing run/check execution paths and only change selection and management UX.

**Tech Stack:** Python 3, questionary, PyYAML, pytest, existing TUI and CLI modules.

---

### Task 1: Add tests for customer setup command behaviors

**Files:**
- Create: `tests/unit/test_customer_commands_setup.py`
- Modify: `src/app/cli/customer_commands.py`

**Step 1: Write the failing tests**

```python
def test_scan_profiles_returns_mapped_unmapped(...):
    ...

def test_assign_profile_appends_account_to_customer_yaml(...):
    ...

def test_assign_profile_blocks_duplicate_mapping_without_override(...):
    ...

def test_set_checks_persists_only_available_checks(...):
    ...
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/unit/test_customer_commands_setup.py -v`
Expected: FAIL for missing command helpers/handlers.

**Step 3: Write minimal implementation in command module**

- Add pure helper functions for:
  - mapping classification (`mapped`, `unmapped`)
  - YAML account upsert by profile
  - checks sanitization against `AVAILABLE_CHECKS`
- Keep file writes isolated and deterministic for testability.

**Step 4: Run tests to verify passes**

Run: `pytest tests/unit/test_customer_commands_setup.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/test_customer_commands_setup.py src/app/cli/customer_commands.py
git commit -m "test+feat: add customer setup command helpers with coverage"
```

### Task 2: Expose new customer CLI subcommands (scan, assign, checks)

**Files:**
- Modify: `src/app/cli/bootstrap.py`
- Modify: `src/app/cli/customer_commands.py`
- Test: `tests/unit/test_cli_bootstrap.py` (create if absent)

**Step 1: Write failing CLI dispatch tests**

```python
def test_customer_subcommand_scan_dispatches(...):
    ...

def test_customer_subcommand_assign_requires_customer_id(...):
    ...

def test_customer_subcommand_checks_requires_customer_id(...):
    ...
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/unit/test_cli_bootstrap.py -v`
Expected: FAIL because actions are not recognized.

**Step 3: Implement dispatch and help text changes**

- Extend `_handle_customer_subcommand()` for:
  - `scan`
  - `assign <customer_id>`
  - `checks <customer_id>`
- Update usage/help examples in parser epilog.

**Step 4: Run tests to verify passes**

Run: `pytest tests/unit/test_cli_bootstrap.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app/cli/bootstrap.py src/app/cli/customer_commands.py tests/unit/test_cli_bootstrap.py
git commit -m "feat: add customer scan assign checks subcommands"
```

### Task 3: Add reusable searchable multi-select flow with select-all/clear

**Files:**
- Modify: `src/app/tui/common.py`
- Create: `tests/unit/test_tui_common_selection.py`

**Step 1: Write failing tests for selection helper behavior**

```python
def test_filter_choices_case_insensitive_contains(...):
    ...

def test_select_all_returns_all_visible_values(...):
    ...

def test_clear_all_returns_empty_selection(...):
    ...
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/unit/test_tui_common_selection.py -v`
Expected: FAIL due to missing helper functions.

**Step 3: Implement minimal reusable helper APIs**

- Add small, testable functions:
  - `filter_choice_values(values, query)`
  - `apply_bulk_action(values, action)` for `select_all` / `clear_all`
- Add an interactive wrapper used by TUI flows.

**Step 4: Run tests to verify passes**

Run: `pytest tests/unit/test_tui_common_selection.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app/tui/common.py tests/unit/test_tui_common_selection.py
git commit -m "feat: add searchable multi-select helpers for TUI"
```

### Task 4: Update customer flow UX (mapping-only, no auto-select)

**Files:**
- Modify: `src/app/tui/flows/customer.py`
- Modify: `src/app/tui/interactive.py`
- Test: `tests/unit/test_tui_customer_flow.py` (create if absent)

**Step 1: Write failing tests for new selection defaults and source restrictions**

```python
def test_customer_checks_default_unselected(...):
    ...

def test_customer_accounts_default_unselected(...):
    ...

def test_customer_report_uses_customer_mapping_source_only(...):
    ...
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/unit/test_tui_customer_flow.py -v`
Expected: FAIL because flow still preselects items and still allows local-source path.

**Step 3: Implement minimal customer flow changes**

- In customer report flow:
  - remove local profile source in this path
  - default all multi-select checkboxes to unchecked
  - add pre-selection controls: search + select all + clear all
- Keep existing run behavior after final selections are confirmed.

**Step 4: Run tests to verify passes**

Run: `pytest tests/unit/test_tui_customer_flow.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app/tui/flows/customer.py src/app/tui/interactive.py tests/unit/test_tui_customer_flow.py
git commit -m "feat: improve customer report selection UX and mapping-only source"
```

### Task 5: Docs + regression verification

**Files:**
- Modify: `README.md`
- Modify: `docs/PROJECT.md`

**Step 1: Add docs for new customer setup flow**

- Add commands:
  - `monitoring-hub customer scan`
  - `monitoring-hub customer assign <customer_id>`
  - `monitoring-hub customer checks <customer_id>`
- Document selection behavior changes (default unselected, select-all/clear, search).

**Step 2: Run focused regression suite**

Run:
`pytest tests/unit/test_customer_commands_setup.py tests/unit/test_cli_bootstrap.py tests/unit/test_tui_common_selection.py tests/unit/test_tui_customer_flow.py tests/test_e2e_api.py -v`

Expected: PASS.

**Step 3: Manual smoke checks**

Run:

```bash
monitoring-hub customer scan
monitoring-hub customer assign aryanoble
monitoring-hub customer checks aryanoble
monitoring-hub customer validate aryanoble
monitoring-hub
```

Expected:
- scan shows mapped/unmapped profiles
- assign writes YAML accounts correctly
- checks updates YAML checks list
- customer report selection starts empty and supports search/select-all/clear

**Step 4: Commit**

```bash
git add README.md docs/PROJECT.md
git commit -m "docs: add customer setup and TUI selection workflow guidance"
```
