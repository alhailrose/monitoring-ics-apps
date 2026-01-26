"""
AWS Monitoring Hub
Centralized monitoring for AWS security and operations
"""

__version__ = "1.3.0"
__author__ = "AWS Monitoring Team"

from .cli import main
from .ui import VERSION

__all__ = ["main", "__version__", "VERSION"]
