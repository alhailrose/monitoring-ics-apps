import unittest
from datetime import datetime, timedelta, timezone
from src.checks.aryanoble.alarm_verification import AlarmVerificationChecker


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


if __name__ == "__main__":
    unittest.main()
