from monitoring_hub import interactive_v2


class _Prompt:
    def __init__(self, value):
        self._value = value

    def ask(self):
        return self._value


def test_select_check_menu_uses_questionary_select(monkeypatch):
    monkeypatch.setattr(
        interactive_v2.questionary,
        "select",
        lambda *args, **kwargs: _Prompt("cloudwatch"),
    )

    def _unexpected_console_input(*args, **kwargs):
        raise AssertionError("numeric console input should not be used")

    monkeypatch.setattr(interactive_v2.console, "input", _unexpected_console_input)

    selected = interactive_v2._select_check_menu()

    assert selected == "cloudwatch"


def test_run_arbel_check_v2_uses_select_prompt_for_mode_and_window(monkeypatch):
    prompts = iter(["rds", (3, "3 Hours")])
    captured = {}

    monkeypatch.setattr(interactive_v2, "print_mini_banner", lambda: None)
    monkeypatch.setattr(
        interactive_v2, "print_section_header", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        interactive_v2,
        "_multi_select_numbered",
        lambda *args, **kwargs: ["connect-prod"],
    )
    monkeypatch.setattr(
        interactive_v2, "_select_prompt", lambda *args, **kwargs: next(prompts)
    )

    def _unexpected_console_input(*args, **kwargs):
        raise AssertionError("numeric console input should not be used")

    monkeypatch.setattr(interactive_v2.console, "input", _unexpected_console_input)

    def _fake_run_group_specific(
        check, profiles, region, group_name=None, check_kwargs=None
    ):
        captured["check"] = check
        captured["profiles"] = profiles
        captured["region"] = region
        captured["group_name"] = group_name
        captured["check_kwargs"] = check_kwargs

    monkeypatch.setattr(interactive_v2, "run_group_specific", _fake_run_group_specific)

    interactive_v2._run_arbel_check_v2()

    assert captured == {
        "check": "daily-arbel",
        "profiles": ["connect-prod"],
        "region": "ap-southeast-3",
        "group_name": "Aryanoble (3 Hours)",
        "check_kwargs": {"window_hours": 3},
    }


def test_render_v2_header_mentions_focus_mode():
    with interactive_v2.console.capture() as capture:
        interactive_v2._render_v2_header()

    out = capture.get()

    assert "Mode fokus" in out


def test_run_interactive_v2_pauses_after_action(monkeypatch):
    choices = iter(["single", "exit"])
    calls = {"single": 0, "pause": 0}

    monkeypatch.setattr(interactive_v2.console, "clear", lambda: None)
    monkeypatch.setattr(
        interactive_v2, "_render_v2_header", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(interactive_v2, "_select_main_menu", lambda: next(choices))
    monkeypatch.setattr(
        interactive_v2,
        "_run_single_check_v2",
        lambda: calls.__setitem__("single", calls["single"] + 1),
    )
    monkeypatch.setattr(
        interactive_v2, "_pause", lambda: calls.__setitem__("pause", calls["pause"] + 1)
    )
    monkeypatch.setattr(interactive_v2, "print_success", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        interactive_v2.sys,
        "exit",
        lambda code=0: (_ for _ in ()).throw(SystemExit(code)),
    )

    try:
        interactive_v2.run_interactive_v2()
    except SystemExit as exc:
        assert exc.code == 0

    assert calls["single"] == 1
    assert calls["pause"] == 1


def test_run_focus_action_adds_completion_info_and_pause(monkeypatch):
    calls = {"action": 0, "pause": 0}
    infos = []

    monkeypatch.setattr(interactive_v2.console, "clear", lambda: None)
    monkeypatch.setattr(
        interactive_v2,
        "print_info",
        lambda msg: infos.append(msg),
    )
    monkeypatch.setattr(
        interactive_v2,
        "_pause",
        lambda: calls.__setitem__("pause", calls["pause"] + 1),
    )

    def _action():
        calls["action"] += 1

    interactive_v2._run_focus_action("single", _action)

    assert calls["action"] == 1
    assert calls["pause"] == 1
    assert infos
    assert "Selesai" in infos[0]


def test_render_v2_header_uses_compact_core_menu():
    with interactive_v2.console.capture() as capture:
        interactive_v2._render_v2_header()

    out = capture.get()

    assert "Core Menu" in out


def test_render_v2_header_does_not_show_budget_or_session():
    with interactive_v2.console.capture() as capture:
        interactive_v2._render_v2_header()

    out = capture.get()

    assert "Daily Budget" not in out
    assert "Session Left" not in out
