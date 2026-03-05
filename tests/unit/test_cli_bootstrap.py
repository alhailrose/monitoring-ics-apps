import pytest

from src.app.cli import bootstrap


def test_customer_list_dispatches_without_exit(monkeypatch):
    called = {"list": False}

    monkeypatch.setattr(
        "src.app.cli.customer_commands.customer_list",
        lambda: called.__setitem__("list", True),
    )

    bootstrap._handle_customer_subcommand(["list"])

    assert called["list"] is True


def test_customer_scan_dispatches_without_exit(monkeypatch):
    called = {"scan": False}

    monkeypatch.setattr(
        "src.app.cli.customer_commands.customer_scan",
        lambda: called.__setitem__("scan", True),
    )

    bootstrap._handle_customer_subcommand(["scan"])

    assert called["scan"] is True


def test_customer_init_requires_customer_id():
    with pytest.raises(SystemExit) as exc:
        bootstrap._handle_customer_subcommand(["init"])

    assert exc.value.code == 1


def test_customer_assign_requires_customer_id():
    with pytest.raises(SystemExit) as exc:
        bootstrap._handle_customer_subcommand(["assign"])

    assert exc.value.code == 1


def test_customer_checks_requires_customer_id():
    with pytest.raises(SystemExit) as exc:
        bootstrap._handle_customer_subcommand(["checks"])

    assert exc.value.code == 1


def test_customer_assign_dispatches_and_exits_by_status(monkeypatch):
    monkeypatch.setattr("src.app.cli.customer_commands.customer_assign", lambda _cid: True)

    with pytest.raises(SystemExit) as exc:
        bootstrap._handle_customer_subcommand(["assign", "acme"])

    assert exc.value.code == 0


def test_customer_checks_dispatches_and_exits_by_status(monkeypatch):
    monkeypatch.setattr("src.app.cli.customer_commands.customer_checks", lambda _cid: False)

    with pytest.raises(SystemExit) as exc:
        bootstrap._handle_customer_subcommand(["checks", "acme"])

    assert exc.value.code == 1


def test_unknown_customer_action_exits_with_error():
    with pytest.raises(SystemExit) as exc:
        bootstrap._handle_customer_subcommand(["oops"])

    assert exc.value.code == 1
