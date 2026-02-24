"""Base class for all AWS checks"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.checks.common.aws_errors import classify_aws_error, is_credential_error


class BaseChecker(ABC):
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
