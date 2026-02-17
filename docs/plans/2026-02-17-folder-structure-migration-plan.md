# Folder Structure Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the monitoring app into a clean, scalable app architecture before new feature development continues.

**Architecture:** Use an incremental strangler migration: keep current runtime stable while moving modules into `src/` by layer (`app`, `core`, `providers`, `checks`, `configs`). Each batch introduces adapters first, then switches imports, then removes legacy duplicates only after tests pass.

**Tech Stack:** Python 3.12, setuptools, pytest, existing `monitoring_hub` and `checks` modules.

---

### Task 1: Freeze architecture contract and migration rules

**Files:**
- Create: `docs/architecture/target-structure-contract.md`
- Modify: `docs/architecture/migration-status.md`
- Test: `tests/test_project_structure.py`

**Step 1: Write the failing test**

Add assertions that the contract doc exists and required top-level target directories exist.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_project_structure.py::test_target_src_structure_exists -v`
Expected: FAIL when contract/doc/path is missing.

**Step 3: Write minimal implementation**

Create architecture contract doc defining:
- canonical runtime path target (`src/...`)
- no-feature rule during migration
- compatibility shim lifecycle and removal criteria

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_project_structure.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add docs/architecture/target-structure-contract.md docs/architecture/migration-status.md tests/test_project_structure.py
git commit -m "docs: define folder migration contract and guardrails"
```


### Task 2: Canonicalize `src/` package entrypoints (no behavior changes)

**Files:**
- Modify: `src/app/cli/main.py`
- Modify: `src/app/tui/interactive.py`
- Modify: `src/core/engine/jobs.py`
- Modify: `src/core/formatting/reports.py`
- Test: `tests/unit/test_src_adapters.py`

**Step 1: Write the failing test**

Add tests that `src` adapters expose expected callables/classes and mirror legacy behavior signatures.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/unit/test_src_adapters.py -v`
Expected: FAIL for missing tests/modules/signatures.

**Step 3: Write minimal implementation**

Align adapter modules so all imports resolve through `src` namespace reliably.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/unit/test_src_adapters.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app src/core tests/unit/test_src_adapters.py
git commit -m "refactor: stabilize src adapter entrypoints"
```


### Task 3: Move business models and runner store to canonical `src/core`

**Files:**
- Create: `src/core/models/job_models.py`
- Create: `src/core/engine/job_store.py`
- Create: `src/core/engine/executor.py`
- Modify: `monitoring_hub/runner/job_models.py`
- Modify: `monitoring_hub/runner/job_store.py`
- Modify: `monitoring_hub/runner/executor.py`
- Test: `tests/unit/test_runner_core.py`

**Step 1: Write the failing test**

Add tests that import from `src.core` and validate lifecycle (`queued -> running -> completed/failed`).

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/unit/test_runner_core.py -v`
Expected: FAIL because canonical modules are missing.

**Step 3: Write minimal implementation**

Move implementation to `src/core/*`; make legacy `monitoring_hub/runner/*` thin compatibility re-export shims.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/unit/test_runner_core.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/core monitoring_hub/runner tests/unit/test_runner_core.py
git commit -m "refactor: make src.core canonical for runner models and store"
```


### Task 4: Move customer config loading to canonical `src/configs` + `src/core`

**Files:**
- Create: `src/configs/loader.py`
- Create: `src/configs/schema/validator.py`
- Modify: `src/configs/defaults/customers/aryanoble.yaml`
- Modify: `monitoring_hub/customers/loader.py`
- Modify: `monitoring_hub/customers/schema.py`
- Test: `tests/unit/test_customer_config_loader.py`

**Step 1: Write the failing test**

Add tests that use `src.configs.loader` as canonical import and validate customer/account lookup.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/unit/test_customer_config_loader.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Move loading/validation to `src/configs`; keep legacy modules as re-export wrappers.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/unit/test_customer_config_loader.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/configs monitoring_hub/customers tests/unit/test_customer_config_loader.py
git commit -m "refactor: canonicalize customer config loading under src.configs"
```


### Task 5: Split checks by domain into `src/checks/*`

**Files:**
- Create: `src/checks/aryanoble/daily_arbel.py`
- Create: `src/checks/aryanoble/alarm_verification.py`
- Create: `src/checks/generic/{health,cost,guardduty,cloudwatch,notifications,backup,ec2}.py`
- Modify: `checks/*.py` (shim re-exports)
- Modify: `monitoring_hub/config.py`
- Test: `tests/integration/test_checks_registry.py`

**Step 1: Write the failing test**

Add test that registry resolves canonical checks from `src.checks` and produces same check names.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/integration/test_checks_registry.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Move check implementations into `src/checks`; legacy `checks/*` become compatibility shims.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/integration/test_checks_registry.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/checks checks monitoring_hub/config.py tests/integration/test_checks_registry.py
git commit -m "refactor: split checks by domain under src.checks"
```


### Task 6: Canonicalize provider layer under `src/providers/aws`

**Files:**
- Modify: `src/providers/aws/clients.py`
- Modify: `src/providers/aws/auth.py`
- Modify: `src/providers/aws/services/{cloudwatch,budgets,rds}.py`
- Modify: check modules now using direct boto3 sessions
- Test: `tests/unit/test_aws_provider_clients.py`

**Step 1: Write the failing test**

Add tests for provider factory behavior and service client creation with profile/region arguments.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/unit/test_aws_provider_clients.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Route AWS client creation through provider layer; remove duplicate session creation patterns from business modules.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/unit/test_aws_provider_clients.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/providers src/checks tests/unit/test_aws_provider_clients.py
git commit -m "refactor: centralize aws client creation in provider layer"
```


### Task 7: Move app entrypoints to `src/app` and add stable wrappers

**Files:**
- Modify: `monitoring_hub/cli.py`
- Modify: `monitoring_hub/interactive.py`
- Modify: `monitoring_hub/runners.py`
- Create: `src/app/cli/bootstrap.py`
- Create: `src/app/tui/bootstrap.py`
- Test: `tests/integration/test_cli_entrypoints.py`

**Step 1: Write the failing test**

Add tests that `monitoring-hub` script entrypoint still works while canonical logic lives under `src/app`.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/integration/test_cli_entrypoints.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Move logic into `src/app` modules and keep legacy files as wrappers only.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/integration/test_cli_entrypoints.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app monitoring_hub tests/integration/test_cli_entrypoints.py
git commit -m "refactor: move app entrypoints to src.app with stable wrappers"
```


### Task 8: Restructure tests into `tests/unit` and `tests/integration`

**Files:**
- Move: `tests/test_*.py` -> `tests/unit/` or `tests/integration/`
- Modify: `pyproject.toml`
- Create: `tests/conftest.py` (if needed)

**Step 1: Write the failing test**

Add collection test asserting no direct `tests/test_*.py` files remain outside new folders.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_project_structure.py -v`
Expected: FAIL until files moved.

**Step 3: Write minimal implementation**

Move tests and update paths/imports; ensure CI command still `uv run --with pytest pytest`.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests pyproject.toml
git commit -m "test: organize suite into unit and integration structure"
```


### Task 9: Finalize migration checkpoint and freeze for feature work

**Files:**
- Modify: `docs/architecture/migration-status.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Step 1: Run full verification**

Run: `uv run --with pytest pytest`
Expected: all tests pass.

**Step 2: Run CLI smoke test**

Run: `monitoring-hub --help`
Expected: command works without regressions.

**Step 3: Update docs**

Document:
- canonical module paths
- remaining wrappers
- “ready for next feature development” checkpoint

**Step 4: Commit**

```bash
git add docs README.md CHANGELOG.md
git commit -m "docs: finalize folder migration checkpoint for next development phase"
```
