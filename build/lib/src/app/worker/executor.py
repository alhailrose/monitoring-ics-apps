"""Worker execution helpers."""

from src.core.runtime.runners import run_check_headless
from src.core.runtime.config import ALL_MODE_CHECKS, ALL_MODE_CHECKS_NO_BACKUP_RDS


class WorkerRunner:
    def __init__(self, region: str):
        self.region = region

    def run(self, payload: dict):
        check_name = payload.get("check_name") or payload.get("check")
        profiles = payload.get("profiles") or []
        if not check_name:
            raise ValueError("Missing check_name in payload")
        if not profiles:
            raise ValueError("Missing profiles in payload")

        items = []
        checks_to_run = [check_name]
        
        if check_name == "all":
            checks_to_run = list(ALL_MODE_CHECKS.keys())
        elif check_name == "all-light":
            checks_to_run = list(ALL_MODE_CHECKS_NO_BACKUP_RDS.keys())

        for profile in profiles:
            for single_check in checks_to_run:
                normalized = run_check_headless(
                    check_name=single_check,
                    profile=profile,
                    region=self.region,
                )
                items.append(
                    {
                        "profile": f"{profile} [{single_check}]" if check_name in ("all", "all-light") else profile,
                        "status": normalized.get("status", "error"),
                        "normalized": normalized,
                    }
                )
        return items


def run_job(payload: dict, repo, runner):
    """Execute one queued job and persist normalized outputs."""
    job_id = payload["job_id"]
    try:
        repo.mark_running(job_id)
        result_items = runner.run(payload)
        for item in result_items:
            repo.add_result(
                job_id=job_id,
                profile=item["profile"],
                status=item["status"],
                normalized=item["normalized"],
            )
        repo.mark_completed(job_id)
        if hasattr(repo, "commit"):
            repo.commit()
    except Exception as exc:
        if hasattr(repo, "rollback"):
            repo.rollback()
        try:
            repo.mark_failed(job_id, f"{exc.__class__.__name__}: {exc}")
            if hasattr(repo, "commit"):
                repo.commit()
        except Exception:
            if hasattr(repo, "rollback"):
                repo.rollback()
        raise
