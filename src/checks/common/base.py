"""Base class for all AWS checks"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


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
