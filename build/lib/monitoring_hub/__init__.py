"""
AWS Monitoring Hub
Centralized monitoring for AWS security and operations
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("monitoring-hub")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0.dev"

__author__ = "AWS Monitoring Team"


def main():
    from .cli import main as cli_main

    return cli_main()


__all__ = ["main", "__version__"]
