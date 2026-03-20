import unittest
from datetime import datetime, timedelta, timezone
from backend.checks.aryanoble.alarm_verification import AlarmVerificationChecker


class AlarmVerificationCheckerTests(unittest.TestCase):
    def setUp(self):
        self.checker = AlarmVerificationChecker(min_duration_minutes=10)
        self.now = datetime(2026, 2, 16, 3, 0, tzinfo=timezone.utc)

    def test_report_when_alarm_ongoing_over_threshold(self):
        history = [
            {
                "Timestamp": self.now - timedelta(minutes=15),
                "HistorySummary": "State updated from OK to ALARM",
            }
        ]

        result = self.checker._build_alarm_result(
            alarm_name="example-alarm",
            alarm_state="ALARM",
            threshold_text="> 75 %",
            reason="high cpu",
            history=history,
            now_utc=self.now,
        )

        self.assertTrue(result["should_report"])
        self.assertEqual("REPORT_NOW", result["recommended_action"])
        self.assertEqual(15, result["ongoing_minutes"])
        self.assertEqual("ALARM", result["current_state"])

    def test_report_when_alarm_ongoing_exactly_10m(self):
        history = [
            {
                "Timestamp": self.now - timedelta(minutes=10),
                "HistorySummary": "State updated from OK to ALARM",
            }
        ]

        result = self.checker._build_alarm_result(
            alarm_name="example-alarm",
            alarm_state="ALARM",
            threshold_text="> 75 %",
            reason="high cpu",
            history=history,
            now_utc=self.now,
        )

        self.assertTrue(result["should_report"])
        self.assertEqual("REPORT_NOW", result["recommended_action"])
        self.assertEqual(10, result["ongoing_minutes"])

    def test_no_report_when_alarm_recovered_after_10m(self):
        history = [
            {
                "Timestamp": self.now - timedelta(minutes=2),
                "HistorySummary": "State updated from ALARM to OK",
            },
            {
                "Timestamp": self.now - timedelta(minutes=14),
                "HistorySummary": "State updated from OK to ALARM",
            },
        ]

        result = self.checker._build_alarm_result(
            alarm_name="example-alarm",
            alarm_state="OK",
            threshold_text="> 75 %",
            reason="recovered",
            history=history,
            now_utc=self.now,
        )

        self.assertFalse(result["should_report"])
        self.assertEqual("NO_REPORT_RECOVERED", result["recommended_action"])
        self.assertEqual(12, result["breach_duration_minutes"])
        self.assertEqual("OK", result["current_state"])

    def test_no_report_when_alarm_recovered_under_10m(self):
        history = [
            {
                "Timestamp": self.now - timedelta(minutes=2),
                "HistorySummary": "State updated from ALARM to OK",
            },
            {
                "Timestamp": self.now - timedelta(minutes=8),
                "HistorySummary": "State updated from OK to ALARM",
            },
        ]

        result = self.checker._build_alarm_result(
            alarm_name="example-alarm",
            alarm_state="OK",
            threshold_text="> 75 %",
            reason="recovered",
            history=history,
            now_utc=self.now,
        )

        self.assertFalse(result["should_report"])
        self.assertEqual("NO_REPORT_TRANSIENT", result["recommended_action"])
        self.assertEqual(6, result["breach_duration_minutes"])

    def test_format_report_displays_alarm_verification_data_table(self):
        results = {
            "status": "success",
            "profile": "dwh",
            "account_id": "123456789012",
            "min_alarm_minutes": 10,
            "alarms": [
                {
                    "status": "ok",
                    "alarm_name": "dc-dwh-olap-memory-above-70",
                    "alarm_state": "ALARM",
                    "recommended_action": "REPORT_NOW",
                    "threshold_text": ">= 70",
                    "breach_start_time": "08:57 WIB",
                    "ongoing_minutes": 26,
                    "message": "Selamat Pagi, kami informasikan pada *dc-dwh-olap-memory-above-70* sedang melewati threshold >= 70 sejak 08:57 WIB (status: ongoing 26 menit).",
                },
                {
                    "status": "ok",
                    "alarm_name": "dc-dwh-olap-cpu-above-70",
                    "alarm_state": "ALARM",
                    "recommended_action": "MONITOR",
                    "threshold_text": ">= 70",
                    "breach_start_time": "09:18 WIB",
                    "ongoing_minutes": 5,
                },
                {
                    "status": "ok",
                    "alarm_name": "dc-dwh-olap-latency-above-70",
                    "alarm_state": "OK",
                    "recommended_action": "NO_REPORT_RECOVERED",
                    "threshold_text": ">= 70",
                    "breach_start_time": "08:10 WIB",
                    "breach_end_time": "08:24 WIB",
                    "breach_duration_minutes": 14,
                },
            ],
        }

        text = self.checker.format_report(results)

        self.assertIn("Alarm Verification Data", text)
        self.assertIn(
            "Data source: CloudWatch alarm history 24 jam ke belakang (rolling).", text
        )
        self.assertIn(
            "Rule: Pelaporan hanya untuk alarm ALARM ongoing >= 10 menit.", text
        )
        self.assertIn("Status", text)
        self.assertIn("🔴 Report Now", text)
        self.assertIn("🟡 Monitor", text)
        self.assertIn("🟢 OK", text)
        self.assertIn("Pelaporan:", text)
        self.assertNotIn("|", text)


if __name__ == "__main__":
    unittest.main()
