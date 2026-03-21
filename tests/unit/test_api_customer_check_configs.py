from fastapi.testclient import TestClient


class _FakeCustomerService:
    def __init__(self):
        self.store = {}

    def list_account_check_configs(self, account_id):
        if account_id == "missing":
            raise ValueError("Account not found")
        items = []
        for check_name, config in self.store.get(account_id, {}).items():
            items.append(
                {
                    "account_id": account_id,
                    "check_name": check_name,
                    "config": config,
                }
            )
        return items

    def set_account_check_config(self, account_id, check_name, config):
        if account_id == "missing":
            raise ValueError("Account not found")
        self.store.setdefault(account_id, {})[check_name] = config
        return {
            "account_id": account_id,
            "check_name": check_name,
            "config": config,
        }

    def delete_account_check_config(self, account_id, check_name):
        if account_id == "missing":
            raise ValueError("Account not found")
        bucket = self.store.get(account_id, {})
        if check_name not in bucket:
            return False
        del bucket[check_name]
        return True


def test_account_check_config_crud_endpoints():
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.main import create_app

    fake = _FakeCustomerService()

    app = create_app()
    app.dependency_overrides[deps.get_customer_service] = lambda: fake
    client = TestClient(app)

    put_resp = client.put(
        "/api/v1/customers/accounts/acc-1/check-configs/alarm_verification",
        json={"config": {"alarm_names": ["alarm-a"], "min_duration_minutes": 10}},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["check_name"] == "alarm_verification"

    list_resp = client.get("/api/v1/customers/accounts/acc-1/check-configs")
    assert list_resp.status_code == 200
    data = list_resp.json()["items"]
    assert len(data) == 1
    assert data[0]["config"]["alarm_names"] == ["alarm-a"]

    del_resp = client.delete(
        "/api/v1/customers/accounts/acc-1/check-configs/alarm_verification"
    )
    assert del_resp.status_code == 204

    list_resp2 = client.get("/api/v1/customers/accounts/acc-1/check-configs")
    assert list_resp2.status_code == 200
    assert list_resp2.json()["items"] == []


def test_account_check_config_returns_404_for_missing_account():
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.main import create_app

    fake = _FakeCustomerService()
    app = create_app()
    app.dependency_overrides[deps.get_customer_service] = lambda: fake
    client = TestClient(app)

    resp = client.get("/api/v1/customers/accounts/missing/check-configs")
    assert resp.status_code == 404
