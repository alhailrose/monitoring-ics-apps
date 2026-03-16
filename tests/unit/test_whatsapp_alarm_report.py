from src.core.runtime.reports import build_whatsapp_alarm


def test_alarm_whatsapp_contains_only_report_lines():
    all_results = {
        "dermies-max": {
            "alarm_verification": {
                "status": "success",
                "account_id": "637423567244",
                "alarms": [
                    {
                        "status": "ok",
                        "alarm_name": "dc-dwh-olap-memory-above-70",
                        "alarm_state": "ALARM",
                        "recommended_action": "REPORT_NOW",
                        "breach_start_time": "08:57 WIB",
                        "ongoing_minutes": 26,
                        "threshold_text": "> 75 Percent",
                        "message": "Selamat Pagi, kami informasikan pada *dc-dwh-olap-memory-above-70* sedang melewati threshold >= 70 sejak 08:57 WIB (status: ongoing 26 menit).",
                    },
                    {
                        "status": "ok",
                        "alarm_name": "dc-dwh-olap-cpu-above-70",
                        "alarm_state": "ALARM",
                        "recommended_action": "MONITOR",
                        "breach_start_time": "09:18 WIB",
                        "ongoing_minutes": 5,
                        "threshold_text": "> 75 Percent",
                    },
                    {
                        "status": "ok",
                        "alarm_name": "dc-dwh-olap-connection-above-70",
                        "alarm_state": "OK",
                        "recommended_action": "NO_REPORT_RECOVERED",
                        "breach_start_time": "08:10 WIB",
                        "breach_end_time": "08:24 WIB",
                        "breach_duration_minutes": 14,
                        "threshold_text": "> 75 Percent",
                    },
                ],
            }
        }
    }

    text = build_whatsapp_alarm(all_results)

    assert "*Data Singkat:*" not in text
    assert "🔴 Report Now" not in text
    assert "🟡 Monitor" not in text
    assert "🟢 OK" not in text
    assert "*Pelaporan:*" not in text
    assert "kami informasikan" in text
    assert text.startswith("Selamat Pagi, kami informasikan")
    assert "Selamat Pagi Team 👋" not in text
    assert "*Arbel Alarm Verification* |" not in text
    assert "Summary: REPORT_NOW" not in text
    assert "OK_NOW" not in text


def test_alarm_whatsapp_hides_pelaporan_if_no_report_now():
    all_results = {
        "dermies-max": {
            "alarm_verification": {
                "status": "success",
                "account_id": "637423567244",
                "alarms": [
                    {
                        "status": "ok",
                        "alarm_name": "dc-dwh-olap-cpu-above-70",
                        "alarm_state": "ALARM",
                        "recommended_action": "MONITOR",
                        "breach_start_time": "09:18 WIB",
                        "ongoing_minutes": 5,
                        "threshold_text": "> 75 Percent",
                    },
                    {
                        "status": "ok",
                        "alarm_name": "dc-dwh-olap-connection-above-70",
                        "alarm_state": "OK",
                        "recommended_action": "NO_REPORT_RECOVERED",
                        "breach_start_time": "08:10 WIB",
                        "breach_end_time": "08:24 WIB",
                        "breach_duration_minutes": 14,
                        "threshold_text": "> 75 Percent",
                    },
                ],
            }
        }
    }

    text = build_whatsapp_alarm(all_results)

    assert "*Data Singkat:*" not in text
    assert "🟡 Monitor" not in text
    assert "🟢 OK" not in text
    assert "kami informasikan" not in text
    assert text.strip() == "Tidak ada alarm yang perlu dilaporkan saat ini."
