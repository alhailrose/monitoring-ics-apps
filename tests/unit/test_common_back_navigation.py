import pytest
from src.app.tui import common


def test_select_prompt_returns_none_on_keyboard_interrupt_with_allow_back(monkeypatch):
    """allow_back=True: Ctrl+C harus return None, bukan sys.exit."""
    import questionary

    def raise_interrupt(*args, **kwargs):
        class _Q:
            def ask(self):
                raise KeyboardInterrupt

        return _Q()

    monkeypatch.setattr(questionary, "select", raise_interrupt)

    result = common._select_prompt("Test", ["a", "b"], allow_back=True)
    assert result is None


def test_select_prompt_exits_on_keyboard_interrupt_without_allow_back(monkeypatch):
    """allow_back=False (default): Ctrl+C harus sys.exit."""
    import questionary

    def raise_interrupt(*args, **kwargs):
        class _Q:
            def ask(self):
                raise KeyboardInterrupt

        return _Q()

    monkeypatch.setattr(questionary, "select", raise_interrupt)
    monkeypatch.setattr(
        common, "_handle_interrupt", lambda **kw: (_ for _ in ()).throw(SystemExit(0))
    )

    with pytest.raises(SystemExit):
        common._select_prompt("Test", ["a", "b"], allow_back=False)


def test_checkbox_prompt_returns_none_on_keyboard_interrupt_with_allow_back(
    monkeypatch,
):
    """allow_back=True: Ctrl+C pada checkbox harus return None."""
    import questionary

    def raise_interrupt(*args, **kwargs):
        class _Q:
            def ask(self):
                raise KeyboardInterrupt

        return _Q()

    monkeypatch.setattr(questionary, "checkbox", raise_interrupt)

    result = common._checkbox_prompt("Test", ["a", "b"], allow_back=True)
    assert result is None


def test_checkbox_prompt_exits_on_keyboard_interrupt_without_allow_back(monkeypatch):
    """allow_back=False (default): Ctrl+C pada checkbox harus sys.exit."""
    import questionary

    def raise_interrupt(*args, **kwargs):
        class _Q:
            def ask(self):
                raise KeyboardInterrupt

        return _Q()

    monkeypatch.setattr(questionary, "checkbox", raise_interrupt)
    monkeypatch.setattr(
        common, "_handle_interrupt", lambda **kw: (_ for _ in ()).throw(SystemExit(0))
    )

    with pytest.raises(SystemExit):
        common._checkbox_prompt("Test", ["a", "b"], allow_back=False)


def test_text_prompt_returns_none_on_keyboard_interrupt_with_allow_back(monkeypatch):
    """allow_back=True: Ctrl+C pada text prompt harus return None."""
    import questionary

    def raise_interrupt(*args, **kwargs):
        class _Q:
            def ask(self):
                raise KeyboardInterrupt

        return _Q()

    monkeypatch.setattr(questionary, "text", raise_interrupt)

    result = common._text_prompt("Test", allow_back=True)
    assert result is None


def test_confirm_prompt_returns_none_on_keyboard_interrupt_with_allow_back(monkeypatch):
    """allow_back=True: Ctrl+C pada confirm prompt harus return None."""
    import questionary

    def raise_interrupt(*args, **kwargs):
        class _Q:
            def ask(self):
                raise KeyboardInterrupt

        return _Q()

    monkeypatch.setattr(questionary, "confirm", raise_interrupt)

    result = common._confirm_prompt("Test", allow_back=True)
    assert result is None
