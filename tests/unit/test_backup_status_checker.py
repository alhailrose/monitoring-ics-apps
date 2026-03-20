from backend.checks.generic.backup_status import BackupStatusChecker


def test_vault_activity_uses_configured_vault_names_override():
    checker = BackupStatusChecker(vault_names=["custom-vault-a", "custom-vault-b"])

    class _BackupClient:
        def __init__(self):
            self.described = []

        def describe_backup_vault(self, BackupVaultName):
            self.described.append(BackupVaultName)
            return {"NumberOfRecoveryPoints": 1}

        def list_recovery_points_by_backup_vault(
            self, BackupVaultName, ByCreatedAfter, NextToken=None
        ):
            return {"RecoveryPoints": []}

    class _Session:
        def __init__(self):
            self.client_stub = _BackupClient()

        def client(self, service_name, region_name=None):
            assert service_name == "backup"
            return self.client_stub

    session = _Session()
    checker._vault_activity(session, profile="backup-hris")

    assert session.client_stub.described == ["custom-vault-a", "custom-vault-b"]


def test_check_skips_rds_snapshot_check_when_disabled(monkeypatch):
    checker = BackupStatusChecker(monitor_rds_snapshots=False)

    monkeypatch.setattr(
        "backend.checks.generic.backup_status.boto3.Session",
        lambda profile_name, region_name=None: object(),
    )
    monkeypatch.setattr(checker, "_list_backup_jobs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(checker, "_list_backup_plans", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(checker, "_vault_activity", lambda *_args, **_kwargs: [])

    called = {"rds": False}

    def _fake_rds(*_args, **_kwargs):
        called["rds"] = True
        return 0

    monkeypatch.setattr(checker, "_rds_snapshots_24h", _fake_rds)

    result = checker.check(profile="iris-prod", account_id="123456789012")

    assert result["status"] == "OK"
    assert result["monitor_rds_snapshots"] is False
    assert called["rds"] is False
