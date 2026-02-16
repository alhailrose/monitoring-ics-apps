import importlib.util
import pathlib
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone


def _load_checker_class():
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    checks_dir = repo_root / "checks"

    if "boto3" not in sys.modules:
        sys.modules["boto3"] = types.ModuleType("boto3")

    if "checks" not in sys.modules:
        pkg = types.ModuleType("checks")
        pkg.__path__ = [str(checks_dir)]
        sys.modules["checks"] = pkg

    base_spec = importlib.util.spec_from_file_location(
        "checks.base", checks_dir / "base.py"
    )
    base_mod = importlib.util.module_from_spec(base_spec)
    sys.modules["checks.base"] = base_mod
    base_spec.loader.exec_module(base_mod)

    alarm_spec = importlib.util.spec_from_file_location(
        "checks.alarm_verification", checks_dir / "alarm_verification.py"
    )
    alarm_mod = importlib.util.module_from_spec(alarm_spec)
    sys.modules["checks.alarm_verification"] = alarm_mod
    alarm_spec.loader.exec_module(alarm_mod)
    return alarm_mod.AlarmVerificationChecker


AlarmVerificationChecker = _load_checker_class()


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
