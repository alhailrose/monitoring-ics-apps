# Dual Interface Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-ready single-server platform where TUI remains available and a new Webapp can manually trigger checks and view historical normalized results.

**Architecture:** Keep `src/checks` and current runtime logic as shared core. Add a service layer used by both TUI and API, then add API + worker + PostgreSQL persistence for normalized outputs. Add Web UI for manual trigger and historical dashboard; scheduler is explicitly deferred.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy, Alembic, Redis + RQ (or compatible queue), PostgreSQL, React/Next.js, Docker Compose, pytest.

---

### Task 1: Add runtime settings and dependency baseline

**Files:**
- Modify: `pyproject.toml`
- Create: `src/app/settings.py`
- Test: `tests/unit/test_settings_runtime.py`

**Step 1: Write the failing test**

```python
from src.app.settings import get_settings


def test_runtime_settings_load_defaults():
    s = get_settings()
    assert s.database_url
    assert s.redis_url
    assert s.execution_mode in {"local", "api"}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_settings_runtime.py -v`
Expected: FAIL because `src.app.settings` does not exist.

**Step 3: Write minimal implementation**

```python
# src/app/settings.py
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    execution_mode: str


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "postgresql+psycopg://monitor:monitor@postgres:5432/monitoring"),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        execution_mode=os.getenv("EXECUTION_MODE", "local"),
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_settings_runtime.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml src/app/settings.py tests/unit/test_settings_runtime.py
git commit -m "chore: add runtime settings for api and worker"
```


### Task 2: Add PostgreSQL models for normalized job history

**Files:**
- Create: `src/db/models.py`
- Create: `src/db/session.py`
- Create: `src/db/repositories/job_repository.py`
- Test: `tests/unit/test_job_repository.py`

**Step 1: Write the failing test**

```python
from src.db.repositories.job_repository import JobRepository


def test_create_job_and_append_normalized_result(db_session):
    repo = JobRepository(db_session)
    job = repo.create_job(customer_id="aryanoble", check_name="daily-arbel", requested_by="web")
    repo.add_result(job.id, profile="sfa", status="OK", normalized={"metrics": [{"name": "CPUUtilization", "last": 42.0}]})

    loaded = repo.get_job(job.id)
    assert loaded is not None
    assert len(loaded.results) == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_job_repository.py -v`
Expected: FAIL because db repository does not exist.

**Step 3: Write minimal implementation**

```python
# model shape (normalized only)
class Job(Base):
    id: UUID
    customer_id: str
    check_name: str
    status: str
    requested_by: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobResult(Base):
    id: UUID
    job_id: UUID
    profile: str
    status: str
    normalized: dict
    created_at: datetime
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_job_repository.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/db/models.py src/db/session.py src/db/repositories/job_repository.py tests/unit/test_job_repository.py
git commit -m "feat: persist normalized job history in postgres"
```


### Task 3: Add application service for manual trigger and execution

**Files:**
- Create: `src/app/services/run_service.py`
- Modify: `src/core/runtime/runners.py`
- Test: `tests/unit/test_run_service.py`

**Step 1: Write the failing test**

```python
from src.app.services.run_service import RunService


def test_manual_run_builds_job_payload_without_rendered_message(fake_repo, fake_queue):
    svc = RunService(repo=fake_repo, queue=fake_queue)
    job_id = svc.enqueue_manual_run(customer_id="aryanoble", check_name="daily-arbel", profiles=["sfa"])

    queued = fake_queue.items[0]
    assert queued["job_id"] == str(job_id)
    assert "message" not in queued
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_run_service.py -v`
Expected: FAIL because service does not exist.

**Step 3: Write minimal implementation**

```python
class RunService:
    def __init__(self, repo, queue):
        self.repo = repo
        self.queue = queue

    def enqueue_manual_run(self, customer_id: str, check_name: str, profiles: list[str]):
        job = self.repo.create_job(customer_id=customer_id, check_name=check_name, requested_by="web")
        self.queue.enqueue({"job_id": str(job.id), "customer_id": customer_id, "check_name": check_name, "profiles": profiles})
        return job.id
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_run_service.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app/services/run_service.py src/core/runtime/runners.py tests/unit/test_run_service.py
git commit -m "feat: add shared manual-run service for tui and api"
```


### Task 4: Build API endpoints (manual run + job/history)

**Files:**
- Create: `src/app/api/main.py`
- Create: `src/app/api/routes/jobs.py`
- Create: `src/app/api/routes/history.py`
- Test: `tests/unit/test_api_jobs.py`

**Step 1: Write the failing test**

```python
def test_post_jobs_enqueues_and_returns_job_id(client):
    resp = client.post("/api/v1/jobs", json={"customer_id": "aryanoble", "check_name": "daily-arbel", "profiles": ["sfa"]})
    assert resp.status_code == 202
    assert "job_id" in resp.json()


def test_get_job_history_returns_normalized_records(client):
    resp = client.get("/api/v1/history?customer_id=aryanoble")
    assert resp.status_code == 200
    assert isinstance(resp.json()["items"], list)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_api_jobs.py -v`
Expected: FAIL because API app/routes do not exist.

**Step 3: Write minimal implementation**

```python
@router.post("/jobs", status_code=202)
def create_job(payload: CreateJobRequest, service: RunService = Depends(get_run_service)):
    job_id = service.enqueue_manual_run(payload.customer_id, payload.check_name, payload.profiles)
    return {"job_id": str(job_id)}


@router.get("/history")
def history(customer_id: str, repo: JobRepository = Depends(get_repo)):
    return {"items": repo.list_history(customer_id=customer_id)}
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_api_jobs.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app/api/main.py src/app/api/routes/jobs.py src/app/api/routes/history.py tests/unit/test_api_jobs.py
git commit -m "feat: add manual-run and history api endpoints"
```


### Task 5: Add worker to execute queued runs and persist normalized outputs

**Files:**
- Create: `src/app/worker/main.py`
- Create: `src/app/worker/executor.py`
- Test: `tests/unit/test_worker_executor.py`

**Step 1: Write the failing test**

```python
def test_worker_executes_job_and_persists_normalized_result(fake_repo, fake_runner):
    job_id = fake_repo.seed_job(customer_id="aryanoble", check_name="daily-arbel")
    run_job(job_id=str(job_id), repo=fake_repo, runner=fake_runner)

    job = fake_repo.get_job(job_id)
    assert job.status == "completed"
    assert job.results[0].normalized["metrics"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_worker_executor.py -v`
Expected: FAIL because worker executor does not exist.

**Step 3: Write minimal implementation**

```python
def run_job(job_id: str, repo: JobRepository, runner):
    repo.mark_running(job_id)
    result = runner.run(job_id)
    repo.add_result(job_id, profile=result["profile"], status=result["status"], normalized=result["normalized"])
    repo.mark_completed(job_id)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_worker_executor.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app/worker/main.py src/app/worker/executor.py tests/unit/test_worker_executor.py
git commit -m "feat: add worker execution pipeline for normalized results"
```


### Task 6: Add Webapp UI (manual trigger + dashboard history)

**Files:**
- Create: `web/package.json`
- Create: `web/src/app/page.tsx`
- Create: `web/src/app/jobs/page.tsx`
- Create: `web/src/app/history/page.tsx`
- Test: `web/src/__tests__/history.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react"
import HistoryPage from "../app/history/page"

test("renders history heading", () => {
  render(<HistoryPage />)
  expect(screen.getByText(/History/i)).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm test -- history.test.tsx`
Expected: FAIL because web app is not scaffolded.

**Step 3: Write minimal implementation**

```tsx
export default function HistoryPage() {
  return (
    <main>
      <h1>History</h1>
    </main>
  )
}
```

Then add:
- Run form (customer/check/profiles)
- Jobs table (queued/running/completed/failed)
- History list from `/api/v1/history`

**Step 4: Run test to verify it passes**

Run: `cd web && npm test -- history.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add web
git commit -m "feat: add web ui for manual run and history dashboard"
```


### Task 7: Add Docker single-server deployment

**Files:**
- Create: `infra/docker/docker-compose.yml`
- Create: `infra/docker/.env.example`
- Create: `infra/docker/nginx.conf`
- Create: `docs/operations/single-server-deploy.md`
- Test: `tests/integration/test_docker_compose_exists.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_docker_compose_exists_for_single_server_stack():
    assert Path("infra/docker/docker-compose.yml").exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_docker_compose_exists.py -v`
Expected: FAIL because compose file does not exist.

**Step 3: Write minimal implementation**

Compose must define at least:
- `postgres`
- `redis`
- `api`
- `worker`
- `nginx`

with healthchecks and persistent volumes.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_docker_compose_exists.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add infra/docker docs/operations/single-server-deploy.md tests/integration/test_docker_compose_exists.py
git commit -m "chore: add single-server docker deployment stack"
```


### Task 8: Final verification gate

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md` (if present)

**Step 1: Run backend tests**

Run: `python -m pytest tests/ -v`
Expected: PASS.

**Step 2: Run web tests**

Run: `cd web && npm test`
Expected: PASS.

**Step 3: Run local compose smoke**

Run: `docker compose -f infra/docker/docker-compose.yml config`
Expected: Valid compose output.

**Step 4: Manual API smoke**

Run: `curl http://localhost:8000/health`
Expected: `200` + health payload.

**Step 5: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: finalize dual-interface platform rollout guide"
```


## Delivery Notes

- Scheduler is intentionally deferred.
- Only normalized structured outputs are persisted.
- Rendered report text remains runtime/UI concern.
- Keep customer config precedence:
  1) local `configs/customers/*.yaml`
  2) packaged defaults.
