"""Manual run orchestration service for TUI/API entrypoints."""


class RunService:
    def __init__(self, repo, queue):
        self.repo = repo
        self.queue = queue

    def enqueue_manual_run(
        self,
        customer_id: str,
        check_name: str,
        profiles: list[str],
        requested_by: str = "web",
    ):
        try:
            job = self.repo.create_job(
                customer_id=customer_id,
                check_name=check_name,
                requested_by=requested_by,
            )

            payload = {
                "job_id": str(job.id),
                "customer": customer_id,
                "check": check_name,
                "customer_id": customer_id,
                "check_name": check_name,
                "profiles": profiles,
            }
            self.queue.enqueue(payload)
            if hasattr(self.repo, "commit"):
                self.repo.commit()
            return job.id
        except Exception:
            if hasattr(self.repo, "rollback"):
                self.repo.rollback()
            raise
