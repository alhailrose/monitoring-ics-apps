from backend.interfaces.cli.common import apply_bulk_action, filter_values_by_query


def test_filter_values_by_query_is_case_insensitive_contains():
    values = ["Prod-App", "staging-api", "DB-Primary", "ops"]

    assert filter_values_by_query(values, "API") == ["staging-api"]
    assert filter_values_by_query(values, "PRI") == ["DB-Primary"]


def test_filter_values_by_query_returns_all_values_for_empty_query():
    values = ["one", "two", "three"]

    assert filter_values_by_query(values, "") == values
    assert filter_values_by_query(values, "   ") == values
    assert filter_values_by_query(values, None) == values


def test_apply_bulk_action_select_all_returns_all_values():
    values = ["acc-a", "acc-b"]

    assert apply_bulk_action(values, "select_all") == values


def test_apply_bulk_action_clear_all_returns_empty_selection():
    values = ["acc-a", "acc-b"]

    assert apply_bulk_action(values, "clear_all") == []


def test_apply_bulk_action_manual_keeps_existing_selection():
    values = ["acc-a", "acc-b", "acc-c"]
    current_selection = ["acc-a", "acc-c"]

    assert apply_bulk_action(values, "manual", current_selection) == current_selection


def test_apply_bulk_action_rejects_unknown_action():
    values = ["acc-a", "acc-b"]

    try:
        apply_bulk_action(values, "unknown")
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported bulk action")
