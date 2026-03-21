from backend.interfaces.cli.flows import customer
from backend.interfaces.cli import common


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
    monkeypatch.setattr(
        common, "_checkbox_prompt", lambda *a, **kw: None
    )  # escape account

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
    monkeypatch.setattr(common, "_checkbox_prompt", lambda *a, **kw: ["dermies-max"])
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda check, *a, **kw: run_calls.append(check),
    )

    customer._run_aryanoble_subflow(cfg)

    assert window_escape_count["n"] == 2
    assert "daily-arbel" in run_calls


def test_aryanoble_rds_mode_passes_rds_scope(monkeypatch):
    cfg = {
        "customer_id": "aryanoble",
        "accounts": [
            {"profile": "cis-erha", "daily_arbel": True},
        ],
    }
    calls = []

    select_values = iter(["rds", (3, "3 Hours")])
    monkeypatch.setattr(
        common,
        "_select_prompt",
        lambda *args, **kwargs: next(select_values),
    )
    monkeypatch.setattr(
        common, "_checkbox_prompt", lambda *args, **kwargs: ["cis-erha"]
    )
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = customer._run_aryanoble_subflow(cfg)

    assert result == {"mode": "rds"}
    assert calls[0][0][0] == "daily-arbel"
    assert calls[0][1]["check_kwargs"]["section_scope"] == "rds"


def test_aryanoble_ec2_mode_passes_ec2_scope(monkeypatch):
    cfg = {
        "customer_id": "aryanoble",
        "accounts": [
            {
                "profile": "cis-erha",
                "daily_arbel": True,
                "daily_arbel_extra": [
                    {"section_name": "CIS ERHA EC2", "service_type": "ec2"}
                ],
            },
        ],
    }
    calls = []

    select_values = iter(["ec2", (3, "3 Hours")])
    monkeypatch.setattr(
        common,
        "_select_prompt",
        lambda *args, **kwargs: next(select_values),
    )
    monkeypatch.setattr(
        common, "_checkbox_prompt", lambda *args, **kwargs: ["cis-erha"]
    )
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = customer._run_aryanoble_subflow(cfg)

    assert result == {"mode": "ec2"}
    assert calls[0][0][0] == "daily-arbel"
    assert calls[0][1]["check_kwargs"]["section_scope"] == "ec2"


def test_aryanoble_ec2_mode_lists_primary_ec2_profiles(monkeypatch):
    cfg = {
        "customer_id": "aryanoble",
        "accounts": [
            {
                "profile": "HRIS",
                "daily_arbel": {"service_type": "ec2", "instances": {"app": "i-1"}},
            },
            {
                "profile": "cis-erha",
                "daily_arbel": {"service_type": "rds"},
                "daily_arbel_extra": [
                    {"section_name": "CIS ERHA EC2", "service_type": "ec2"}
                ],
            },
        ],
    }
    captured = {}

    select_values = iter(["ec2", (3, "3 Hours")])
    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(select_values)
    )

    def fake_checkbox(message, choices, **kwargs):
        if "akun Aryanoble" in message:
            captured["profiles"] = [choice.value for choice in choices]
            return ["HRIS"]
        return []

    monkeypatch.setattr(common, "_checkbox_prompt", fake_checkbox)
    monkeypatch.setattr(customer, "run_group_specific", lambda *args, **kwargs: None)

    customer._run_aryanoble_subflow(cfg)

    assert "HRIS" in captured["profiles"]
    assert "cis-erha" in captured["profiles"]


def test_aryanoble_alarm_helper_from_account(monkeypatch):
    cfg = {
        "customer_id": "aryanoble",
        "accounts": [
            {
                "profile": "dermies-max",
                "daily_arbel": True,
                "alarm_names": [
                    "dc-dwh-olap-memory-above-70",
                    "dc-dwh-olap-cpu-above-70",
                ],
            }
        ],
    }
    calls = []

    selected = iter(["alarm-name", "from-account"])
    monkeypatch.setattr(
        common,
        "_select_prompt",
        lambda *args, **kwargs: next(selected),
    )

    def fake_checkbox(message, choices, **kwargs):
        if "Pilih akun Aryanoble" in message:
            return ["dermies-max"]
        if "Pilih alarm" in message:
            return ["dc-dwh-olap-memory-above-70", "dc-dwh-olap-cpu-above-70"]
        return []

    monkeypatch.setattr(common, "_checkbox_prompt", fake_checkbox)
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = customer._run_aryanoble_subflow(cfg)

    assert result == {"mode": "alarm"}
    assert calls[0][0][0] == "alarm_verification"
    assert calls[0][1]["check_kwargs"]["alarm_names"] == [
        "dc-dwh-olap-memory-above-70",
        "dc-dwh-olap-cpu-above-70",
    ]


def test_aryanoble_alarm_helper_from_paste(monkeypatch):
    cfg = {
        "customer_id": "aryanoble",
        "accounts": [
            {
                "profile": "dermies-max",
                "daily_arbel": True,
                "alarm_names": ["dc-dwh-olap-memory-above-70"],
            },
            {
                "profile": "dwh",
                "daily_arbel": True,
                "alarm_names": ["dc-dwh-olap-cpu-above-70"],
            },
            {
                "profile": "connect-prod",
                "daily_arbel": True,
                "alarm_names": ["some-other-alarm"],
            },
        ],
    }
    calls = []

    selected = iter(["alarm-name", "paste-input"])
    monkeypatch.setattr(
        common,
        "_select_prompt",
        lambda *args, **kwargs: next(selected),
    )

    monkeypatch.setattr(
        common,
        "_checkbox_prompt",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("By Alarm Names tidak boleh meminta pilih account")
        ),
    )

    class _DummyPrompt:
        def ask(self):
            return "dc-dwh-olap-memory-above-70\ndc-dwh-olap-cpu-above-70,dc-dwh-olap-memory-above-70"

    monkeypatch.setattr(
        customer.questionary, "text", lambda *args, **kwargs: _DummyPrompt()
    )
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = customer._run_aryanoble_subflow(cfg)

    assert result == {"mode": "alarm"}
    assert calls[0][0][0] == "alarm_verification"
    assert calls[0][0][1] == ["dermies-max", "dwh"]
    assert calls[0][1]["check_kwargs"]["alarm_names"] == [
        "dc-dwh-olap-memory-above-70",
        "dc-dwh-olap-cpu-above-70",
    ]


def test_aryanoble_alarm_method_prompt_appears_before_account_picker(monkeypatch):
    cfg = {
        "customer_id": "aryanoble",
        "accounts": [
            {
                "profile": "dermies-max",
                "daily_arbel": True,
                "alarm_names": ["dc-dwh-olap-memory-above-70"],
            }
        ],
    }

    state = {"method_selected": False}
    mode_calls = {"n": 0}

    def fake_select(message, *args, **kwargs):
        if "Pilih Mode" in message:
            mode_calls["n"] += 1
            return "alarm-name" if mode_calls["n"] == 1 else None
        if "Pilih Metode" in message:
            state["method_selected"] = True
            return None
        return None

    def fake_checkbox(message, *args, **kwargs):
        assert state["method_selected"] is True
        return ["dermies-max"]

    monkeypatch.setattr(common, "_select_prompt", fake_select)
    monkeypatch.setattr(common, "_checkbox_prompt", fake_checkbox)

    customer._run_aryanoble_subflow(cfg)
