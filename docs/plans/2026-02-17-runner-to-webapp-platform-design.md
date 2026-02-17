# Runner-to-WebApp Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-ready, centralized monitoring platform that starts as a Slack-triggered runner and evolves into a full multi-customer web app without breaking current monitoring flows.

**Architecture:** Keep the existing check engine as core domain logic, then add an application layer for job orchestration and delivery channels. Phase 1 deploys a central runner with Slack command trigger and persisted run history. Phase 2 adds a web API and dashboard that reads from the same job model and execution pipeline.

**Tech Stack:** Python 3.12, existing `monitoring_hub` package, FastAPI (phase 2), Slack Bolt/Events API (phase 1+), SQLite/PostgreSQL (phase 1 minimal -> phase 2 production), pytest.

---

### Task 1: Define target folder structure and migration map

**Files:**
- Create: `docs/architecture/folder-structure.md`
- Modify: `README.md`

**Step 1: Write the failing test**

Create a doc-validation test that expects architecture docs to exist.

```python
def test_architecture_doc_exists():
    from pathlib import Path
    assert Path("docs/architecture/folder-structure.md").exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_architecture_docs.py::test_architecture_doc_exists -v`
Expected: FAIL because file does not exist.

**Step 3: Write minimal implementation**

Create `docs/architecture/folder-structure.md` with:
- Current structure inventory
- Target structure (`app/`, `core/`, `providers/`, `checks/`, `configs/`, `tests/`)
- Migration rules (no behavioral change in pure move commits)

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_architecture_docs.py::test_architecture_doc_exists -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_architecture_docs.py docs/architecture/folder-structure.md README.md
git commit -m "docs: define target architecture and migration map"
```


### Task 2: Externalize customer/account/check config (remove hardcoded tenant behavior)

**Files:**
- Create: `monitoring_hub/customers/schema.py`
- Create: `monitoring_hub/customers/loader.py`
- Create: `configs/customers/aryanoble.yaml`
- Modify: `checks/daily_arbel.py`
- Modify: `checks/daily_budget.py`
- Test: `tests/test_customer_config_loader.py`

**Step 1: Write the failing test**

Add test that loads `configs/customers/aryanoble.yaml` and verifies:
- account list present
- alarm mappings present
- display name lookup returns expected label.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_customer_config_loader.py -v`
Expected: FAIL (`loader` missing).

**Step 3: Write minimal implementation**

Implement typed loader (`dataclass` or pydantic) and update Arbel/Budget checks to read config by `customer_id` + `account_id` instead of hardcoded profile constants.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_customer_config_loader.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add monitoring_hub/customers checks/daily_arbel.py checks/daily_budget.py configs/customers/aryanoble.yaml tests/test_customer_config_loader.py
git commit -m "refactor: move customer mappings into external config"
```


### Task 3: Add centralized job runner primitives (queue + run record)

**Files:**
- Create: `monitoring_hub/runner/job_models.py`
- Create: `monitoring_hub/runner/job_store.py`
- Create: `monitoring_hub/runner/executor.py`
- Test: `tests/test_runner_jobs.py`

**Step 1: Write the failing test**

Add tests for:
- enqueue job
- transition `queued -> running -> completed/failed`
- persist output summary text.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_runner_jobs.py -v`
Expected: FAIL (`job_store`/`executor` missing).

**Step 3: Write minimal implementation**

Implement local SQLite-backed job store and synchronous executor that wraps existing `run_group_specific` / `run_all_checks` flows.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_runner_jobs.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add monitoring_hub/runner tests/test_runner_jobs.py
git commit -m "feat: add centralized runner job model and persistence"
```


### Task 4: Slack-triggered runner interface (phase 1 deployment path)

**Files:**
- Create: `monitoring_hub/integrations/slack/app.py`
- Create: `monitoring_hub/integrations/slack/commands.py`
- Create: `scripts/run-slack-runner.py`
- Modify: `README.md`
- Test: `tests/test_slack_commands.py`

**Step 1: Write the failing test**

Add parser tests for commands like:
- `/monitor run arbel rds --window 12h`
- `/monitor run arbel budget`
- `/monitor status <job_id>`

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_slack_commands.py -v`
Expected: FAIL (parser missing).

**Step 3: Write minimal implementation**

Implement command parser + dispatcher to job runner; return immediate ack + follow-up message with result summary.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_slack_commands.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add monitoring_hub/integrations/slack scripts/run-slack-runner.py tests/test_slack_commands.py README.md
git commit -m "feat: add Slack command trigger for centralized runner"
```


### Task 5: Add scheduler entrypoint for 07:00 daily run (server-side only)

**Files:**
- Create: `monitoring_hub/runner/schedules.py`
- Create: `scripts/run-daily-aryanoble.py`
- Test: `tests/test_schedules.py`

**Step 1: Write the failing test**

Add schedule tests that ensure next trigger is 07:00 WIB and job payload is `customer=aryanoble` + configured checks.

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_schedules.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement scheduler helper (timezone-aware) and script for systemd/cron/k8s runner.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_schedules.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add monitoring_hub/runner/schedules.py scripts/run-daily-aryanoble.py tests/test_schedules.py
git commit -m "feat: add daily 07:00 WIB runner schedule"
```


### Task 6: Add API layer for dashboard-readiness (phase 2 foundation)

**Files:**
- Create: `monitoring_hub/api/main.py`
- Create: `monitoring_hub/api/routes/jobs.py`
- Create: `monitoring_hub/api/routes/runs.py`
- Test: `tests/test_api_jobs.py`

**Step 1: Write the failing test**

Add API tests for:
- `POST /jobs` (submit)
- `GET /jobs/{id}` (status)
- `GET /runs?customer=aryanoble` (history)

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_api_jobs.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Wire FastAPI routes to existing job store/executor interfaces from Task 3.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_api_jobs.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add monitoring_hub/api tests/test_api_jobs.py
git commit -m "feat: add API endpoints for job submit and run history"
```


### Task 7: Build minimal web dashboard (read-only first)

**Files:**
- Create: `web/` (frontend app, framework choice documented)
- Create: `web/src/pages/runs.*`
- Create: `web/src/pages/run-detail.*`
- Modify: `README.md`
- Test: `web` unit tests and one e2e smoke

**Step 1: Write the failing test**

Add UI tests for:
- list recent runs
- show status badge (queued/running/completed/failed)
- show formatted output blocks (backup/rds/alarm/budget)

**Step 2: Run test to verify it fails**

Run: frontend test command (document exact command after stack selection).
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement read-only pages backed by Task 6 API.

**Step 4: Run test to verify it passes**

Run: frontend test command + smoke e2e command.
Expected: PASS.

**Step 5: Commit**

```bash
git add web README.md
git commit -m "feat: add read-only dashboard for monitoring runs"
```


### Task 8: Harden deployment and operations

**Files:**
- Create: `deploy/systemd/monitoring-runner.service`
- Create: `deploy/systemd/monitoring-slack.service`
- Create: `deploy/systemd/monitoring-api.service`
- Create: `deploy/env/.env.example`
- Create: `docs/operations/deployment.md`
- Test: `tests/test_env_validation.py`

**Step 1: Write the failing test**

Add env-validation test requiring mandatory vars (Slack secrets, DB path/url, customer config path).

**Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_env_validation.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Add env loader with strict validation + deployment docs for service restart, log locations, and health checks.

**Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_env_validation.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add deploy docs/operations tests/test_env_validation.py
git commit -m "chore: add deployment units and env validation"
```


### Task 9: Final verification gate

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Step 1: Run full backend tests**

Run: `uv run --with pytest pytest`
Expected: All tests PASS.

**Step 2: Run frontend tests**

Run: frontend test command from Task 7.
Expected: PASS.

**Step 3: Smoke run in runner mode**

Run: `python scripts/run-daily-aryanoble.py --dry-run`
Expected: Job payload validated and printed.

**Step 4: Smoke run API**

Run: API startup and one health endpoint request.
Expected: healthy response.

**Step 5: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: finalize runner-to-webapp rollout guide"
```


## Notes for rollout order

1. Execute Tasks 1-5 first (runner + Slack production value).
2. Start pilot with one customer (`aryanoble`) and validate daily ops.
3. Execute Tasks 6-8 for web app readiness and shared visibility.
4. Keep customer-specific logic in config files, not code constants.
