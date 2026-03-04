from src.app.services.run_service import RunService
from src.app.services.queue import RedisJobQueue
from src.core.runtime.runners import run_check_headless


class _FakeRepo:
    def __init__(self):
        self.created = []
        self.commits = 0
        self.rollbacks = 0

    def create_job(self, customer_id: str, check_name: str, requested_by: str):
        job = type("Job", (), {"id": "job-123"})()
        self.created.append(
            {
                "customer_id": customer_id,
                "check_name": check_name,
                "requested_by": requested_by,
            }
        )
        return job

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _FakeQueue:
    def __init__(self):
        self.items = []

    def enqueue(self, payload: dict):
        self.items.append(payload)


class _FailingQueue:
    def enqueue(self, _payload: dict):
        raise RuntimeError("queue unavailable")


class _FakeRedis:
    def __init__(self):
        self.items = []

    def rpush(self, _key: str, value: str):
        self.items.append(value)

    def lpop(self, _key: str):
        if not self.items:
            return None
        return self.items.pop(0)


def test_manual_run_builds_job_payload_without_rendered_message():
    repo = _FakeRepo()
    queue = _FakeQueue()
    svc = RunService(repo=repo, queue=queue)

    job_id = svc.enqueue_manual_run(
        customer_id="aryanoble",
        check_name="daily-arbel",
        profiles=["sfa"],
    )

    assert job_id == "job-123"
    assert repo.created[0]["requested_by"] == "web"

    queued = queue.items[0]
    assert queued["job_id"] == "job-123"
    assert queued["customer"] == "aryanoble"
    assert queued["check"] == "daily-arbel"
    assert queued["customer_id"] == "aryanoble"
    assert queued["check_name"] == "daily-arbel"
    assert queued["profiles"] == ["sfa"]
    assert "message" not in queued
    assert repo.commits == 1
    assert repo.rollbacks == 0


def test_manual_run_rolls_back_when_queue_enqueue_fails():
    repo = _FakeRepo()
    svc = RunService(repo=repo, queue=_FailingQueue())

    try:
        svc.enqueue_manual_run(
            customer_id="aryanoble",
            check_name="daily-arbel",
            profiles=["sfa"],
        )
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "queue unavailable" in str(exc)

    assert repo.commits == 0
    assert repo.rollbacks == 1


def test_redis_job_queue_serializes_payload_dict_roundtrip():
    redis_client = _FakeRedis()
    queue = RedisJobQueue(redis_client=redis_client, queue_name="jobs")

    queue.enqueue({"job_id": "job-1", "check_name": "daily-arbel", "profiles": ["sfa"]})

    payload = queue.dequeue()
    assert payload == {"job_id": "job-1", "check_name": "daily-arbel", "profiles": ["sfa"]}
    assert queue.dequeue() is None


def test_run_check_headless_handles_unknown_check_gracefully():
    result = run_check_headless(
        check_name="nonexistent-check",
        profile="dummy",
        region="ap-southeast-3",
    )

    assert result["status"] == "error"
    assert "Unknown check" in result["error"]
