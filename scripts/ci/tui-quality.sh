#!/usr/bin/env bash
set -euo pipefail

uv run --with pytest pytest tests/unit/test_interactive_v2.py tests/unit/test_tui_*.py tests/unit/test_cli_without_tui_dependency.py -q
uv run monitoring-hub --help >/dev/null
