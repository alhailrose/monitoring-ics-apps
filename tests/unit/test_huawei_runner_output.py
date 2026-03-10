from src.core.runtime import runners


def test_huawei_legacy_mode_prints_single_report_only(monkeypatch, capsys):
    monkeypatch.setattr(
        runners,
        "build_huawei_legacy_consolidated_report",
        lambda **_kwargs: "CONSOLIDATED-REPORT",
    )

    runners._print_consolidated_report(
        profiles=["demo-ro"],
        all_results={"demo-ro": {"huawei-ecs-util": {"status": "success"}}},
        checks={"huawei-ecs-util": object()},
        checkers={},
        check_errors=[],
        clean_accounts=[],
        errors_by_check={},
        region="ap-southeast-4",
        group_name="Huawei",
        output_mode="huawei_legacy",
    )

    out = capsys.readouterr().out
    assert "CONSOLIDATED-REPORT" in out
    assert "WHATSAPP MESSAGE (READY TO SEND)" not in out
    assert "--huawei" not in out
