#!/usr/bin/env bash
set -euo pipefail

uv run --with pytest --with httpx pytest \
  tests/unit/test_api_main.py \
  tests/unit/test_checks_route.py \
  tests/unit/test_check_executor.py \
  tests/unit/test_settings_runtime.py \
  tests/unit/test_src_adapters.py -q
uv run python -c "from backend.interfaces.api.main import create_app; app = create_app(); print(app.title)"
