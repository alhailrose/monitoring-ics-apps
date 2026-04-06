from types import SimpleNamespace

from backend.domain.services.session_health import ProfileStatus, SessionHealthService


def _account(
    profile_name: str,
    *,
    auth_method: str,
    is_active: bool = True,
    display_name: str | None = None,
):
    return SimpleNamespace(
        profile_name=profile_name,
        auth_method=auth_method,
        is_active=is_active,
        display_name=display_name or profile_name,
    )


def test_check_all_skips_non_profile_auth_accounts(monkeypatch):
    from backend.domain.services import session_health as module

    repo = SimpleNamespace(
        list_customers=lambda: [
            SimpleNamespace(
                display_name="Demo Customer",
                accounts=[
                    _account("connect-prod", auth_method="profile"),
                    _account("NIKP", auth_method="access_key"),
                    _account("ops-role", auth_method="assumed_role"),
                ],
            )
        ]
    )

    called_profiles: list[str] = []

    def _fake_check_profile_health(profile_name, *_args, **_kwargs):
        called_profiles.append(profile_name)
        return ProfileStatus(
            profile_name=profile_name, status="ok", sso_session="sadewa-sso"
        )

    monkeypatch.setattr(module, "_check_profile_health", _fake_check_profile_health)

    service = SessionHealthService(repo, max_workers=1)
    report = service.check_all()

    assert called_profiles == ["connect-prod"]
    assert report.total_profiles == 1
    assert report.ok == 1
    assert [p.profile_name for p in report.profiles] == ["connect-prod"]


def test_check_all_non_profile_only_returns_empty_report(monkeypatch):
    from backend.domain.services import session_health as module

    repo = SimpleNamespace(
        list_customers=lambda: [
            SimpleNamespace(
                display_name="Demo Customer",
                accounts=[
                    _account("NIKP", auth_method="access_key"),
                    _account("ops-role", auth_method="assumed_role"),
                ],
            )
        ]
    )

    def _should_not_be_called(*_args, **_kwargs):
        raise AssertionError(
            "_check_profile_health should not run for non-profile auth"
        )

    monkeypatch.setattr(module, "_check_profile_health", _should_not_be_called)

    service = SessionHealthService(repo, max_workers=1)
    report = service.check_all()

    assert report.total_profiles == 0
    assert report.ok == 0
    assert report.expired == 0
    assert report.error == 0
    assert report.profiles == []


def test_check_profile_health_uses_aws_login_for_login_session(monkeypatch, tmp_path):
    from backend.domain.services import session_health as module

    cfg = tmp_path / "config"
    cfg.write_text(
        "[profile nikp]\n"
        "login_session = arn:aws:sts::038361715485:assumed-role/ics-awsc-msw/bagus\n"
        "region = ap-southeast-1\n",
        encoding="utf-8",
    )

    sts_client = SimpleNamespace(
        get_caller_identity=lambda: {"Account": "038361715485"}
    )
    session = SimpleNamespace(client=lambda *_args, **_kwargs: sts_client)
    monkeypatch.setattr(module, "get_aws_session", lambda **_kwargs: session)

    result = module._check_profile_health(
        "nikp",
        aws_config_path=cfg,
        aws_config_file=str(cfg),
        sso_cache_dir=str(tmp_path / "sso" / "cache"),
    )

    assert result.status == "ok"
    assert result.account_id == "038361715485"
    assert (
        result.sso_session
        == "arn:aws:sts::038361715485:assumed-role/ics-awsc-msw/bagus"
    )
    assert result.login_command == "aws login --profile nikp --remote"
