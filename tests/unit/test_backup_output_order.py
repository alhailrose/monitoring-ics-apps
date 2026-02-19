import src.core.runtime.runners as runners


class _DummyProgress:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add_task(self, *args, **kwargs):
        return 1

    def update(self, *args, **kwargs):
        return None


class _DummyFuture:
    def __init__(self, profile):
        self.profile = profile

    def result(self):
        return {
            "status": "success",
            "account_id": "111122223333",
            "region": "ap-southeast-1",
            "checked_at_utc": "2026-02-19T00:00:00Z",
            "window_start_utc": "2026-02-18T00:00:00Z",
            "total_jobs": 1,
            "completed_jobs": 1,
            "failed_jobs": 0,
            "expired_jobs": 0,
            "job_details": [],
            "backup_plans": [],
            "vaults": [],
        }


class _DummyExecutor:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, _fn, _check_name, profile, _region, _check_kwargs):
        return _DummyFuture(profile)


def test_backup_output_prints_detail_before_whatsapp(monkeypatch, capsys):
    monkeypatch.setattr(runners, "Progress", _DummyProgress)
    monkeypatch.setattr(runners, "ThreadPoolExecutor", _DummyExecutor)
    monkeypatch.setattr(runners, "as_completed", lambda futures: list(futures.keys()))
    monkeypatch.setattr(runners, "print_group_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(runners, "build_whatsapp_backup", lambda *_: "WA-MSG")
    monkeypatch.setattr(runners, "get_account_id", lambda _profile: "111122223333")

    runners.run_group_specific(
        "backup",
        ["ffi"],
        "ap-southeast-1",
        group_name="FFI",
        workers=1,
    )

    out = capsys.readouterr().out
    assert out.index("DETAIL PER ACCOUNT") < out.index("WHATSAPP MESSAGE")
