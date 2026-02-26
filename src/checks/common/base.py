"""Base class for all AWS checks"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.checks.common.aws_errors import classify_aws_error, is_credential_error


class BaseChecker(ABC):
    """Base class for all AWS checkers.

    Subclasses MUST implement check() and format_report().

    To participate in the consolidated daily monitoring report, subclasses
    should also set report_section_title / issue_label and override
    count_issues() and render_section().
    """

    # -- Consolidated report metadata --
    # Set these in subclasses that should appear in the consolidated report.
    report_section_title: str = ""   # e.g. "COST ANOMALIES"
    issue_label: str = ""            # e.g. "cost anomalies" (for Executive Summary)
    recommendation_text: str = ""    # e.g. "COST REVIEW: Investigate cost anomalies"

    def __init__(self, region="ap-southeast-3", **kwargs):
        self.region = region
        self.timestamp = datetime.now()

    @abstractmethod
    def check(self, profile, account_id) -> dict[str, Any]:
        """Execute the check and return results"""
        pass

    @abstractmethod
    def format_report(self, results: dict[str, Any]) -> str:
        """Format results into readable report"""
        pass

    # -- Consolidated report methods --

    @property
    def supports_consolidated(self) -> bool:
        """Whether this checker can render a section in the consolidated report."""
        return bool(self.report_section_title)

    def count_issues(self, result: dict) -> int:
        """Count issues from a single profile's result dict.

        Used by the runner to build the Executive Summary.
        Return 0 if no issues found or result is an error.
        """
        return 0

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render this check's section for the consolidated daily report.

        Args:
            all_results: {profile: result_dict} for this check only.
            errors: [(profile, error_msg)] for this check.

        Returns:
            List of text lines for this section.
        """
        return []

    def _error_result(self, exc: BaseException, profile: str, account_id: str) -> dict:
        """Build a structured error result dict from an exception.

        Automatically detects credential/token errors and provides
        user-friendly messages. Preserves the standard result shape.
        """
        info = classify_aws_error(exc, profile)
        return {
            "status": "error",
            "profile": profile,
            "account_id": account_id,
            "error": info["error"],
            "error_type": info["error_type"],
            "is_credential_error": info["is_credential_error"],
        }
