import pytest
from sqlalchemy.exc import IntegrityError

from src.db.repositories.job_repository import JobRepository
from src.db.session import build_session_factory


def test_create_job_and_append_normalized_result(tmp_path):
    db_path = tmp_path / "jobs.db"
    session_factory = build_session_factory(f"sqlite:///{db_path}")

    with session_factory() as session:
        repo = JobRepository(session)
        job = repo.create_job(
            customer_id="aryanoble",
            check_name="daily-arbel",
            requested_by="web",
        )
        repo.add_result(
            job_id=job.id,
            profile="sfa",
            status="OK",
            normalized={
                "metrics": [
                    {
                        "name": "CPUUtilization",
                        "last": 42.0,
                        "threshold": 70.0,
                        "state": "ok",
                    }
                ]
            },
        )

        loaded = repo.get_job(job.id)

    assert loaded is not None
    assert loaded.customer_id == "aryanoble"
    assert loaded.check_name == "daily-arbel"
    assert len(loaded.results) == 1
    assert loaded.results[0].profile == "sfa"
    assert loaded.results[0].normalized["metrics"][0]["name"] == "CPUUtilization"


def test_get_job_returns_none_for_missing_id(tmp_path):
    db_path = tmp_path / "jobs.db"
    session_factory = build_session_factory(f"sqlite:///{db_path}")

    with session_factory() as session:
        repo = JobRepository(session)
        loaded = repo.get_job("missing-id")

    assert loaded is None


def test_add_result_fails_for_unknown_job_id(tmp_path):
    db_path = tmp_path / "jobs.db"
    session_factory = build_session_factory(f"sqlite:///{db_path}")

    with session_factory() as session:
        repo = JobRepository(session)
        with pytest.raises(IntegrityError):
            repo.add_result(
                job_id="does-not-exist",
                profile="sfa",
                status="ok",
                normalized={"metrics": []},
            )
        session.rollback()
