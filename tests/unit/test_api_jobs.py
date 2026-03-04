import pytest
from fastapi.testclient import TestClient

from src.app import settings as app_settings
from src.app.api import dependencies as api_dependencies
from src.app.api.dependencies import get_job_repository, get_run_service
from src.app.api.main import app


@pytest.fixture(autouse=True)
def _clear_overrides():
    app_settings.get_settings.cache_clear()
    if hasattr(api_dependencies, "_get_session_factory"):
        api_dependencies._get_session_factory.cache_clear()
    if hasattr(api_dependencies, "_get_queue"):
        api_dependencies._get_queue.cache_clear()
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    app_settings.get_settings.cache_clear()
    if hasattr(api_dependencies, "_get_session_factory"):
        api_dependencies._get_session_factory.cache_clear()
    if hasattr(api_dependencies, "_get_queue"):
        api_dependencies._get_queue.cache_clear()


class _FakeRunService:
    def enqueue_manual_run(self, customer_id: str, check_name: str, profiles: list[str]):
        assert customer_id == "aryanoble"
        assert check_name == "daily-arbel"
        assert profiles == ["sfa"]
        return "job-abc"


class _FakeRepo:
    def list_history(self, customer_id: str):
        assert customer_id == "aryanoble"
        return [
            {
                "job_id": "job-abc",
                "customer_id": "aryanoble",
                "check_name": "daily-arbel",
                "status": "completed",
                "results": [
                    {
                        "profile": "sfa",
                        "status": "ok",
                        "normalized": {"metrics": [{"name": "CPUUtilization", "last": 44.0}]},
                    }
                ],
            }
        ]


class _FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeApiModeRepo:
    def __init__(self, _session):
        self.commits = 0
        self.rollbacks = 0

    def create_job(self, customer_id: str, check_name: str, requested_by: str):
        assert customer_id == "aryanoble"
        assert check_name == "daily-arbel"
        assert requested_by == "web"
        return type("Job", (), {"id": "job-api-1"})()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _FakeRedisClient:
    def __init__(self):
        self.enqueued = []

    def rpush(self, _queue_name: str, payload: str):
        self.enqueued.append(payload)


def test_post_jobs_enqueues_and_returns_job_id():
    app.dependency_overrides[get_run_service] = lambda: _FakeRunService()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/jobs",
        json={
            "customer_id": "aryanoble",
            "check_name": "daily-arbel",
            "profiles": ["sfa"],
        },
    )

    assert resp.status_code == 202
    assert resp.json()["job_id"] == "job-abc"


def test_get_job_history_returns_normalized_records():
    app.dependency_overrides[get_job_repository] = lambda: _FakeRepo()
    client = TestClient(app)

    resp = client.get("/api/v1/history?customer_id=aryanoble")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["items"], list)
    assert data["items"][0]["results"][0]["normalized"]["metrics"][0]["name"] == "CPUUtilization"


def test_post_jobs_returns_503_when_dependency_not_configured():
    client = TestClient(app)

    resp = client.post(
        "/api/v1/jobs",
        json={
            "customer_id": "aryanoble",
            "check_name": "daily-arbel",
            "profiles": ["sfa"],
        },
    )

    assert resp.status_code == 503


def test_post_jobs_rejects_empty_profiles_with_422():
    app.dependency_overrides[get_run_service] = lambda: _FakeRunService()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/jobs",
        json={
            "customer_id": "aryanoble",
            "check_name": "daily-arbel",
            "profiles": [],
        },
    )

    assert resp.status_code == 422


def test_post_jobs_uses_real_wiring_in_api_mode(monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "api")

    fake_redis = _FakeRedisClient()
    monkeypatch.setattr(api_dependencies, "JobRepository", _FakeApiModeRepo)
    monkeypatch.setattr(api_dependencies, "build_session_factory", lambda _url: lambda: _FakeSession())
    monkeypatch.setattr(api_dependencies.redis, "from_url", lambda _url, **_kwargs: fake_redis)

    client = TestClient(app)
    resp = client.post(
        "/api/v1/jobs",
        json={
            "customer_id": "aryanoble",
            "check_name": "daily-arbel",
            "profiles": ["sfa"],
        },
    )

    assert resp.status_code == 202
    assert resp.json()["job_id"] == "job-api-1"
    assert len(fake_redis.enqueued) == 1
