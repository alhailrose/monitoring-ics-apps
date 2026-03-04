"""Worker process bootstrap."""

import os
from time import sleep

import redis

from src.app.services.queue import RedisJobQueue
from src.app.settings import get_settings
from src.app.worker.executor import WorkerRunner, run_job
from src.db.repositories.job_repository import JobRepository
from src.db.session import build_session_factory


def start_worker(queue, repo, runner, poll_interval: float = 1.0, max_jobs: int | None = None):
    """Consume queue payloads and execute jobs until limit is reached."""
    processed = 0
    failed = 0
    while True:
        if max_jobs is not None and processed >= max_jobs:
            break

        payload = queue.dequeue()
        if payload is None:
            sleep(poll_interval)
            continue

        try:
            run_job(payload=payload, repo=repo, runner=runner)
        except Exception:
            failed += 1
        processed += 1

    return {"status": "stopped", "processed": processed, "failed": failed}


def main():
    settings = get_settings()
    session_factory = build_session_factory(settings.database_url)
    session = session_factory()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    queue = RedisJobQueue(redis_client=redis_client, queue_name="jobs")
    repo = JobRepository(session)
    runner = WorkerRunner(region=os.getenv("AWS_REGION", "ap-southeast-3"))
    try:
        return start_worker(
            queue=queue,
            repo=repo,
            runner=runner,
            poll_interval=1.0,
            max_jobs=None,
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
