from backend.interfaces.cli.flows import arbel
from backend.interfaces.cli import common


def test_parse_alarm_input_supports_newline_and_comma_and_dedup():
    raw = "alarm-a, alarm-b\nalarm-a\n alarm-c "
    assert arbel._parse_alarm_input(raw) == ["alarm-a", "alarm-b", "alarm-c"]


def test_alarm_helper_can_pick_alarm_from_account(monkeypatch):
    monkeypatch.setattr(
        arbel,
        "load_customer_config",
        lambda _customer: {
            "accounts": [
                {
                    "profile": "dermies-max",
                    "alarm_names": [
                        "dc-dwh-olap-memory-above-70",
                        "dc-dwh-olap-cpu-above-70",
                    ],
                }
            ]
        },
    )

    selected = iter(["alarm-name", "from-account"])
    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selected)
    )

    def fake_checkbox(message, choices, **kwargs):
        if "akun Arbel" in message:
            return ["dermies-max"]
        if "nama alarm" in message.lower():
            return ["dc-dwh-olap-memory-above-70", "dc-dwh-olap-cpu-above-70"]
        return []

    monkeypatch.setattr(common, "_checkbox_prompt", fake_checkbox)

    calls = []
    monkeypatch.setattr(
        arbel,
        "run_group_specific",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    arbel.run_arbel_check(lambda: False)

    assert calls
    assert calls[0][0][0] == "alarm_verification"
    assert calls[0][1]["check_kwargs"]["alarm_names"] == [
        "dc-dwh-olap-memory-above-70",
        "dc-dwh-olap-cpu-above-70",
    ]


def test_alarm_helper_can_use_pasted_alarm_names(monkeypatch):
    monkeypatch.setattr(
        arbel,
        "load_customer_config",
        lambda _customer: {
            "accounts": [
                {
                    "profile": "dermies-max",
                    "alarm_names": ["dc-dwh-olap-memory-above-70"],
                },
                {
                    "profile": "dwh",
                    "alarm_names": ["dc-dwh-olap-cpu-above-70"],
                },
            ]
        },
    )

    selected = iter(["alarm-name", "paste-input"])
    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selected)
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
            return "dc-dwh-olap-memory-above-70\ndc-dwh-olap-cpu-above-70"

    monkeypatch.setattr(
        arbel.questionary, "text", lambda *args, **kwargs: _DummyPrompt()
    )

    calls = []
    monkeypatch.setattr(
        arbel,
        "run_group_specific",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    arbel.run_arbel_check(lambda: False)

    assert calls
    assert calls[0][0][0] == "alarm_verification"
    assert calls[0][0][1] == ["dermies-max", "dwh"]
    assert calls[0][1]["check_kwargs"]["alarm_names"] == [
        "dc-dwh-olap-memory-above-70",
        "dc-dwh-olap-cpu-above-70",
    ]


def test_alarm_verification_prompts_method_before_account_picker(monkeypatch):
    monkeypatch.setattr(
        arbel,
        "load_customer_config",
        lambda _customer: {
            "accounts": [
                {
                    "profile": "dermies-max",
                    "alarm_names": ["dc-dwh-olap-memory-above-70"],
                }
            ]
        },
    )

    state = {"method_selected": False}

    def fake_select(message, *args, **kwargs):
        if "Pilih Mode Operasi" in message:
            return "alarm-name"
        if "Pilih Metode" in message:
            state["method_selected"] = True
            return None
        return None

    def fake_checkbox(message, *args, **kwargs):
        assert state["method_selected"] is True
        return ["dermies-max"]

    monkeypatch.setattr(common, "_select_prompt", fake_select)
    monkeypatch.setattr(common, "_checkbox_prompt", fake_checkbox)

    arbel.run_arbel_check(lambda: False)
