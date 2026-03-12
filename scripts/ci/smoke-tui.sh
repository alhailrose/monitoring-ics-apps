#!/usr/bin/env bash
set -euo pipefail

if command -v monitoring-hub >/dev/null 2>&1; then
  monitoring-hub --help >/dev/null
else
  uv run monitoring-hub --help >/dev/null
fi

echo "TUI smoke check passed"
