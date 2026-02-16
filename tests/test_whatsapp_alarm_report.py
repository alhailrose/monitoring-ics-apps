import importlib.util
import pathlib
import sys
import types
import unittest


def _load_build_whatsapp_alarm():
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    mh_dir = repo_root / "monitoring_hub"

    if "monitoring_hub" not in sys.modules:
        pkg = types.ModuleType("monitoring_hub")
        pkg.__path__ = [str(mh_dir)]
        sys.modules["monitoring_hub"] = pkg

    if "monitoring_hub.utils" not in sys.modules:
        utils_mod = types.ModuleType("monitoring_hub.utils")

        def _get_account_id(profile):
            return f"acct-{profile}"

        utils_mod.get_account_id = _get_account_id
        sys.modules["monitoring_hub.utils"] = utils_mod

    if "monitoring_hub.config" not in sys.modules:
        config_mod = types.ModuleType("monitoring_hub.config")
        config_mod.BACKUP_DISPLAY_NAMES = {}
        sys.modules["monitoring_hub.config"] = config_mod

    reports_spec = importlib.util.spec_from_file_location(
        "monitoring_hub.reports", mh_dir / "reports.py"
    )
    reports_mod = importlib.util.module_from_spec(reports_spec)
    sys.modules["monitoring_hub.reports"] = reports_mod
    reports_spec.loader.exec_module(reports_mod)
    return reports_mod.build_whatsapp_alarm


build_whatsapp_alarm = _load_build_whatsapp_alarm()


class WhatsappAlarmReportTests(unittest.TestCase):
    def test_ok_now_section_contains_client_friendly_metric_highlight(self):
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

        self.assertIn("Kami informasikan bahwa pada akun *DERMIES MAX*", text)
        self.assertIn(
            "*Freeable Memory (Reader), CPU Utilization (Reader), serta ACU Utilization (Reader)*",
            text,
        )
        self.assertIn("*alert melebihi > 75 Percent*", text)
        self.assertIn("*11:03 WIB - 11:13 WIB*", text)
        self.assertIn("Saat ini status alarm sudah *OK*", text)


if __name__ == "__main__":
    unittest.main()
