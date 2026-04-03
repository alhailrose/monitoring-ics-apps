import backend.infra.cloud.aws.auth as auth
import backend.infra.cloud.aws.clients as clients
import backend.infra.cloud.aws.services.cloudwatch as cw_service


def test_resolve_execution_identity_includes_execution_mode():
    identity = auth.resolve_execution_identity(
        profile_name="ops", role_arn="arn:aws:iam::123456789012:role/ReadOnly"
    )

    assert identity["execution_mode"] == "assume-role"


def test_get_client_uses_boto3_session(monkeypatch):
    calls = {}

    class _Session:
        def client(self, service_name, region_name=None):
            calls["service"] = service_name
            calls["region"] = region_name
            return {"service": service_name, "region": region_name}

    monkeypatch.setattr(
        clients.boto3,
        "Session",
        lambda **kwargs: _Session(),
        raising=False,
    )

    client = clients.get_client(
        "cloudwatch", profile_name="ops", region_name="ap-southeast-3"
    )

    assert client["service"] == "cloudwatch"
    assert calls["region"] == "ap-southeast-3"


def test_cloudwatch_service_uses_shared_client_factory(monkeypatch):
    monkeypatch.setattr(
        cw_service,
        "get_client",
        lambda service_name, profile_name=None, region_name=None: {
            "service": service_name,
            "profile": profile_name,
            "region": region_name,
        },
    )

    result = cw_service.client(profile_name="ops", region_name="ap-southeast-3")

    assert result["service"] == "cloudwatch"
    assert result["profile"] == "ops"


def test_get_session_uses_custom_aws_config_file(monkeypatch, tmp_path):
    captured = {}

    class _Session:
        def __init__(
            self,
            *,
            botocore_session=None,
            profile_name=None,
            region_name=None,
            **kwargs,
        ):
            captured["botocore_session"] = botocore_session
            captured["profile_name"] = profile_name
            captured["region_name"] = region_name

    monkeypatch.setattr(clients.boto3, "Session", _Session)

    cfg = tmp_path / "users" / "alice" / "config"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("[profile demo]\nregion=ap-southeast-3\n", encoding="utf-8")

    clients.get_session(
        profile_name="demo",
        region_name="ap-southeast-3",
        aws_config_file=str(cfg),
    )

    assert captured["profile_name"] == "demo"
    assert captured["region_name"] == "ap-southeast-3"
    assert captured["botocore_session"].get_config_variable("config_file") == str(cfg)
