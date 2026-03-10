from src.app.tui.flows import customer
from src.app.tui import common


def test_aryanoble_back_from_account_to_mode(monkeypatch):
    """Escape di akun picker harus kembali ke mode picker, bukan keluar."""
    cfg = {
        "customer_id": "aryanoble",
        "accounts": [
            {"profile": "dermies-max", "daily_arbel": True},
            {"profile": "cis-erha", "daily_arbel": True},
        ],
    }

    # First: pick "rds" mode, then None (escape account), then pick "backup" mode (exits)
    mode_calls = iter(["rds", "backup"])

    def fake_select(msg, choices, **kw):
        if "Mode" in msg or "Arbel" in msg:
            return next(mode_calls)
        return None  # escape everything else

    monkeypatch.setattr(common, "_select_prompt", fake_select)
    monkeypatch.setattr(common, "_checkbox_prompt", lambda *a, **kw: None)  # escape account

    backup_calls = []
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda check, *a, **kw: backup_calls.append(check),
    )

    result = customer._run_aryanoble_subflow(cfg)

    # backup mode runs without account picker, so it should have been called
    assert "backup" in backup_calls


def test_aryanoble_back_from_rds_window_to_account(monkeypatch):
    """Escape di RDS window picker harus kembali ke akun picker."""
    cfg = {
        "customer_id": "aryanoble",
        "accounts": [
            {"profile": "dermies-max", "daily_arbel": True},
            {"profile": "cis-erha", "daily_arbel": True},
        ],
    }

    window_escape_count = {"n": 0}
    run_calls = []

    def fake_select(msg, choices, **kw):
        if "Mode" in msg or "Arbel" in msg:
            return "rds"
        if "Window" in msg:
            window_escape_count["n"] += 1
            if window_escape_count["n"] == 1:
                return None  # escape first time
            return (3, "3 Hours")  # pick on second time
        return None

    monkeypatch.setattr(common, "_select_prompt", fake_select)
    monkeypatch.setattr(
        common, "_checkbox_prompt", lambda *a, **kw: ["dermies-max"]
    )
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda check, *a, **kw: run_calls.append(check),
    )

    customer._run_aryanoble_subflow(cfg)

    assert window_escape_count["n"] == 2
    assert "daily-arbel" in run_calls
