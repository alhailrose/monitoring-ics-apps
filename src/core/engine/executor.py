class JobExecutor:
    def __init__(self, store, handlers=None):
        self.store = store
        self.handlers = handlers or {}

    def run_once(self, job_id):
        job = self.store.get_job(job_id)
        if not job:
            raise ValueError(f"job not found: {job_id}")

        handler = self.handlers.get(job.kind)
        if not handler:
            self.store.set_failed(job_id, f"no handler for job kind: {job.kind}")
            return

        self.store.set_running(job_id)
        try:
            summary = handler(job.payload)
            self.store.set_completed(job_id, str(summary))
        except Exception as exc:
            self.store.set_failed(job_id, str(exc))
