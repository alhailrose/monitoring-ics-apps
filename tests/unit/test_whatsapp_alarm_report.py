from src.core.runtime.reports import build_whatsapp_alarm


def test_ok_now_section_contains_client_friendly_metric_highlight():
    all_results = {
        "dermies-max": {
            "alarm_verification": {
                "status": "success",
                "account_id": "637423567244",
                "alarms": [
                    {
                        "status": "ok",
                        "alarm_name": "dermies-prod-rds-reader-freeable-memory-alarm",
                        "recommended_action": "NO_REPORT_RECOVERED",
                        "breach_start_time": "11:03 WIB",
                        "breach_end_time": "11:13 WIB",
                        "breach_duration_minutes": 10,
                        "threshold_text": "> 75 Percent",
                        "reason": "Threshold Crossed",
                    },
                    {
                        "status": "ok",
                        "alarm_name": "dermies-prod-rds-reader-cpu-alarm",
                        "recommended_action": "NO_REPORT_RECOVERED",
                        "breach_start_time": "11:03 WIB",
                        "breach_end_time": "11:13 WIB",
                        "breach_duration_minutes": 10,
                        "threshold_text": "> 75 Percent",
                        "reason": "Threshold Crossed",
                    },
                    {
                        "status": "ok",
                        "alarm_name": "dermies-prod-rds-reader-acu-alarm",
                        "recommended_action": "NO_REPORT_RECOVERED",
                        "breach_start_time": "11:03 WIB",
                        "breach_end_time": "11:13 WIB",
                        "breach_duration_minutes": 10,
                        "threshold_text": "> 75 Percent",
                        "reason": "Threshold Crossed",
                    },
                ],
            }
        }
    }

    text = build_whatsapp_alarm(all_results)

    assert "Kami informasikan bahwa pada akun *DERMIES MAX*" in text
    assert (
        "*Freeable Memory (Reader), CPU Utilization (Reader), serta ACU Utilization (Reader)*"
        in text
    )
    assert "*alert melebihi > 75 Percent*" in text
    assert "*11:03 WIB - 11:13 WIB*" in text
    assert "Saat ini status alarm sudah *OK*" in text
