import pytest

from src.app.worker import main as worker_main
from src.app.worker import executor as worker_executor
from src.app.worker.executor import WorkerRunner, run_job
from src.app.worker.main import start_worker


class _FakeRepo:
    def __init__(self):
        self.running = []
        self.completed = []
        self.failed = []
        self.results = []
        self.commits = 0
        self.rollbacks = 0

    def mark_running(self, job_id: str):
        self.running.append(job_id)

    def add_result(self, job_id: str, profile: str, status: str, normalized: dict):
        self.results.append(
            {
                "job_id": job_id,
                "profile": profile,
                "status": status,
                "normalized": normalized,
            }
        )

    def mark_completed(self, job_id: str):
        self.completed.append(job_id)

    def mark_failed(self, job_id: str, error: str):
        self.failed.append((job_id, error))

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _FakeRunner:
    def run(self, payload: dict):
        assert payload["job_id"]
        return [
            {
                "profile": "sfa",
                "status": "ok",
                "normalized": {"metrics": [{"name": "CPUUtilization", "last": 50.0}]},
            }
        ]


class _FailingRunner:
    def run(self, _payload: dict):
        raise RuntimeError("boom")


class _TwoResultRunner:
    def run(self, _payload: dict):
        return [
            {"profile": "a", "status": "ok", "normalized": {"metrics": []}},
            {"profile": "b", "status": "ok", "normalized": {"metrics": []}},
        ]


class _FailOnSecondResultRepo(_FakeRepo):
    def add_result(self, job_id: str, profile: str, status: str, normalized: dict):
        if len(self.results) == 1:
            raise ValueError("cannot persist second result")
        super().add_result(job_id, profile, status, normalized)

    def rollback(self):
        super().rollback()
        self.results = []


class _OneJobQueue:
    def __init__(self):
        self.items = [{"job_id": "job-9"}]

    def dequeue(self):
        if self.items:
            return self.items.pop(0)
        return None


class _TwoJobQueue:
    def __init__(self):
        self.items = [{"job_id": "job-fail"}, {"job_id": "job-ok"}]

    def dequeue(self):
        if self.items:
            return self.items.pop(0)
        return None


class _FailOnceRunner:
    def __init__(self):
        self.calls = 0

    def run(self, _payload: dict):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("first job failed")
        return [{"profile": "sfa", "status": "ok", "normalized": {"metrics": []}}]


def test_worker_executes_job_and_persists_normalized_result():
    repo = _FakeRepo()
    runner = _FakeRunner()

    run_job(payload={"job_id": "job-1"}, repo=repo, runner=runner)

    assert repo.running == ["job-1"]
    assert repo.completed == ["job-1"]
    assert repo.failed == []
    assert repo.commits == 1
    assert repo.rollbacks == 0
    assert repo.results[0]["profile"] == "sfa"
    assert repo.results[0]["normalized"]["metrics"][0]["name"] == "CPUUtilization"


def test_worker_marks_job_failed_on_exception():
    repo = _FakeRepo()
    runner = _FailingRunner()

    with pytest.raises(RuntimeError, match="boom"):
        run_job(payload={"job_id": "job-2"}, repo=repo, runner=runner)

    assert repo.running == ["job-2"]
    assert repo.completed == []
    assert repo.failed == [("job-2", "RuntimeError: boom")]
    assert repo.commits == 1
    assert repo.rollbacks == 1


def test_worker_rolls_back_when_result_persistence_fails_midway():
    repo = _FailOnSecondResultRepo()
    runner = _TwoResultRunner()

    with pytest.raises(ValueError, match="cannot persist second result"):
        run_job(payload={"job_id": "job-3"}, repo=repo, runner=runner)

    assert repo.running == ["job-3"]
    assert repo.completed == []
    assert repo.results == []
    assert repo.failed == [("job-3", "ValueError: cannot persist second result")]
    assert repo.commits == 1
    assert repo.rollbacks == 1


def test_start_worker_processes_queue_payload_and_stops_on_limit():
    repo = _FakeRepo()
    runner = _FakeRunner()
    queue = _OneJobQueue()

    result = start_worker(queue=queue, repo=repo, runner=runner, poll_interval=0, max_jobs=1)

    assert result == {"status": "stopped", "processed": 1, "failed": 0}
    assert repo.completed == ["job-9"]


def test_start_worker_continues_after_failed_job():
    repo = _FakeRepo()
    runner = _FailOnceRunner()
    queue = _TwoJobQueue()

    result = start_worker(queue=queue, repo=repo, runner=runner, poll_interval=0, max_jobs=2)

    assert result == {"status": "stopped", "processed": 2, "failed": 1}
    assert repo.completed == ["job-ok"]
    assert repo.failed[0][0] == "job-fail"


def test_worker_main_bootstraps_dependencies_and_starts_loop(monkeypatch):
    class _Settings:
        database_url = "sqlite+pysqlite:///:memory:"
        redis_url = "redis://redis:6379/0"

    class _Session:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    session = _Session()
    start_args = {}

    monkeypatch.setattr(worker_main, "get_settings", lambda: _Settings())
    monkeypatch.setattr(worker_main, "build_session_factory", lambda _url: lambda: session)
    monkeypatch.setattr(worker_main.redis, "from_url", lambda _url, **_kwargs: object())
    monkeypatch.setattr(worker_main, "JobRepository", lambda _session: object())
    monkeypatch.setattr(worker_main, "WorkerRunner", lambda region: {"region": region})

    def _fake_start_worker(queue, repo, runner, poll_interval, max_jobs):
        start_args["queue"] = queue
        start_args["repo"] = repo
        start_args["runner"] = runner
        start_args["poll_interval"] = poll_interval
        start_args["max_jobs"] = max_jobs
        return {"status": "stopped", "processed": 0, "failed": 0}

    monkeypatch.setattr(worker_main, "start_worker", _fake_start_worker)

    result = worker_main.main()

    assert result == {"status": "stopped", "processed": 0, "failed": 0}
    assert start_args["poll_interval"] == 1.0
    assert start_args["max_jobs"] is None
    assert start_args["runner"] == {"region": "ap-southeast-3"}
    assert session.closed is True


def test_worker_runner_normalizes_profiles_with_run_check_headless(monkeypatch):
    calls = []

    def _fake_run_check_headless(check_name: str, profile: str, region: str):
        calls.append((check_name, profile, region))
        return {"status": "ok", "metrics": [{"name": "CPUUtilization", "last": 10.0}]}

    monkeypatch.setattr(worker_executor, "run_check_headless", _fake_run_check_headless)
    runner = WorkerRunner(region="ap-southeast-3")

    result = runner.run({"job_id": "job-10", "check_name": "daily-arbel", "profiles": ["sfa", "sfb"]})

    assert calls == [
        ("daily-arbel", "sfa", "ap-southeast-3"),
        ("daily-arbel", "sfb", "ap-southeast-3"),
    ]
    assert result[0]["profile"] == "sfa"
    assert result[0]["status"] == "ok"
    assert result[0]["normalized"]["metrics"][0]["name"] == "CPUUtilization"
