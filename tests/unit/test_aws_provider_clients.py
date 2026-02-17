import src.providers.aws.auth as auth
import src.providers.aws.clients as clients
import src.providers.aws.services.cloudwatch as cw_service


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
        lambda profile_name=None, region_name=None: _Session(),
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
