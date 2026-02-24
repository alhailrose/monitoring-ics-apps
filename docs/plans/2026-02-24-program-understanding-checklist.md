# Monitoring Hub Program Understanding Notes

Goal: establish shared understanding of the current codebase before new feature development.

## 1) What this program is

- Python CLI app (`monitoring-hub`) for multi-account AWS monitoring and reporting.
- Main value: operational checks + formatted outputs for console, WhatsApp-ready text, and optional Slack delivery.
- Current architecture is `src/`-first and migration-oriented (CLI/TUI stable, API layer still placeholder).

## 2) Runtime architecture snapshot

- Entrypoint:
  - `pyproject.toml` -> `monitoring-hub = "src.app.cli.main:main"`
  - `src/app/cli/main.py` re-exports `src/app/cli/bootstrap.py:main`
- CLI orchestration:
  - argument parsing + mode routing in `src/app/cli/bootstrap.py`
  - routes to `run_individual_check`, `run_group_specific`, `run_all_checks`
- Interactive UI:
  - `src/app/tui/interactive.py` menu flows (single/all/arbel/settings)
  - uses same runner functions as non-interactive mode
- Core runtime:
  - `src/core/runtime/config.py` check registry + profile groups proxy
  - `src/core/runtime/config_loader.py` external config merge (`~/.monitoring-hub/config.yaml`)
  - `src/core/runtime/runners.py` parallel execution + report assembly
  - `src/core/runtime/reports.py` WA-ready message builders
- Checks:
  - generic checks: `src/checks/generic/*`
  - customer-specific checks: `src/checks/aryanoble/*`
  - checker pattern via `BaseChecker` in `src/checks/common/base.py`
- Integrations:
  - Slack notifier via webhook routes in `src/integrations/slack/notifier.py`
- Runner-ready foundation:
  - `src/core/engine/job_store.py` (SQLite job state)
  - `src/core/engine/executor.py` (handler-based job execution)
  - dev helper `scripts/run-slack-runner.py`

## 3) Current maturity by area

- Stable/active:
  - CLI checks, multi-profile execution, TUI flow, Slack routing, report formatting.
- In transition:
  - config source split between repo `configs/customers/` and `src/configs/defaults/customers/` via loader fallback.
- Not yet implemented:
  - API app (`src/app/api/main.py`) still returns placeholder.

## 4) Behavior conventions to keep

- `--all` mode excludes backup/RDS unless `--include-backup-rds` is set.
- Region resolution priority: CLI override -> first profile session region -> fallback `ap-southeast-3`.
- `backup`, `daily-arbel`, and some operational checks support multi-profile group execution.
- WhatsApp text formatting and wording are operational output contracts; changes here are high-impact.

## 5) Risk/hotspot map (before changing code)

- `src/core/runtime/runners.py` is large and mixes orchestration + output formatting.
- `src/checks/aryanoble/daily_arbel.py` is large and contains complex threshold + alarm period logic.
- Many checks return free-form dict payloads; schema drift risk between `check()` and `format_report()`.
- Some logic depends on static account/profile mappings; customer config consistency is critical.

## 6) Pre-development checklist

Use this before implementing any new feature/changes:

1. Define exact scope: CLI mode only, TUI only, or both.
2. Identify impacted check(s) and output channel(s): console, WA, Slack.
3. Confirm whether behavior is generic or customer-specific (`generic` vs `aryanoble`).
4. Confirm configuration source:
   - global runtime config (`~/.monitoring-hub/config.yaml`) or
   - customer YAML (`configs/customers/*.yaml` / `src/configs/defaults/customers/*.yaml`).
5. Add/adjust tests first in `tests/unit` and/or `tests/integration`.
6. Keep imports `src.*` only (no legacy package paths).
7. Verify locally:
   - `uv run --with pytest pytest`
   - `monitoring-hub --help`
8. If architecture changes occur, update `docs/architecture/migration-status.md`.

## 7) Suggested next technical cleanup (optional)

- Split `runners.py` into orchestration vs formatter modules.
- Add typed result models (dataclasses/pydantic) per check to reduce dict-shape coupling.
- Define explicit contract tests for WA output builders in `src/core/runtime/reports.py`.
- Implement real API app in `src/app/api` using existing `core/engine` primitives.

## 8) Prioritized roadmap (quick wins vs high-risk refactors)

### Quick wins (low risk, high impact)

1. Standardize operator-facing output; remove noisy/debug strings in reporting path.
   - files: `src/core/runtime/runners.py`, `src/core/runtime/reports.py`
2. Align CLI help/docs text with current src-first architecture and behavior.
   - files: `src/app/cli/bootstrap.py`, `README.md`, `docs/architecture/folder-structure.md`
3. Add contract tests for runner/report output surface.
   - files: `tests/unit/test_runner_core.py`, `tests/unit/test_backup_output_order.py`
4. Strengthen config validation to catch bad customer/slack config early.
   - files: `src/configs/schema/validator.py`, `src/configs/schema/customer-config.schema.yaml`
5. Replace silent `except: pass` patterns with structured warning/error handling.
   - files: `src/checks/generic/cost_anomalies.py`, `src/checks/generic/backup_status.py`, `src/checks/aryanoble/daily_arbel.py`

### High-risk refactors (plan carefully)

1. Split `src/core/runtime/runners.py` into orchestration, aggregation, and rendering modules.
   - risk: output contract regression across CLI/TUI/WA/Slack.
   - mitigation: add golden/contract tests before extraction.
2. Introduce typed result contracts between `check()` and report formatters.
   - risk: dict-key compatibility break across many checks.
   - mitigation: incremental adoption with backward-compatible adapters.
3. Externalize all `daily_arbel` static account config into customer configs.
   - risk: threshold/alarm behavior drift in customer operations.
   - mitigation: migrate account-by-account with output snapshots.
4. Implement real API layer wired to `core/engine` jobs.
   - risk: concurrency and lifecycle complexity.
   - mitigation: start read-only + minimal submit/status endpoints.
5. Unify config source of truth (`configs/` vs `src/configs/defaults/`).
   - risk: precedence changes may break existing environments.
   - mitigation: explicit precedence policy + deprecation window.

### Recommended sequencing

- Phase 1: quick wins + stronger tests/contracts.
- Phase 2: controlled internal refactors (`runners` split + typed results + config extraction).
- Phase 3: platform expansion (API + config unification + dashboard readiness).

## 9) Module dependency map (current)

### Entry flow

- `pyproject.toml` -> `src.app.cli.main:main`
- `src/app/cli/main.py` -> `src/app/cli/bootstrap.py`
- `src/app/cli/bootstrap.py` -> `src/core/runtime/{config,config_loader,utils,runners,ui}.py`
- interactive path: `src/app/tui/bootstrap.py` -> `src/app/tui/interactive.py` -> `src/core/runtime/runners.py`

### Runtime/check flow

- `src/core/runtime/config.py` imports concrete check classes from `src/checks/*` and builds registry.
- `src/core/runtime/runners.py` resolves checker class -> calls `check()` -> calls `format_report()`.
- `src/core/runtime/runners.py` also imports `src/integrations/slack/notifier.py` for optional outbound delivery.
- `src/integrations/slack/notifier.py` reads routes via `src/core/runtime/config_loader.py`.

### Engine flow (currently parallel foundation)

- `src/core/engine/job_store.py` handles SQLite job persistence/state.
- `src/core/engine/executor.py` executes job handler and updates state.
- `scripts/run-slack-runner.py` demonstrates command -> job submit/status flow.
- `src/app/api/main.py` not yet wired to this engine.

### Coupling hotspots

- `src/core/runtime/runners.py`: orchestration + rendering + delivery in one module.
- `src/core/runtime/config.py`: config + concrete checker registry coupling.
- `src/configs/loader.py`: fallback path crosses `src/` boundary to root `configs/customers/`.
- some TUI flow modules contain direct operational logic instead of strict app-adapter behavior.

## 10) Best first feature recommendation

Best first feature: implement **Job API foundation** (submit/status/history) in `src/app/api`.

Why this first:

- highest architectural fit with current roadmap and migration docs.
- leverages existing `core/engine` components instead of adding parallel systems.
- unlocks both future dashboard and Slack/automation improvements with one foundation.

Minimal MVP slice:

1. `POST /jobs` to create run request.
2. `GET /jobs/{job_id}` to fetch status/detail.
3. `GET /jobs` (or `/runs`) to list recent jobs.

Likely touched files:

- `src/app/api/main.py`
- `src/core/engine/job_store.py` (listing helpers)
- `src/core/engine/executor.py` (if optional run-now behavior)
- `src/core/models/job_models.py` (serialization helpers if needed)
- tests: `tests/unit/test_runner_jobs_legacy.py` + new `tests/unit/test_api_jobs.py`
