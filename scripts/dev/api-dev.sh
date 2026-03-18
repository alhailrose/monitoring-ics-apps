#!/usr/bin/env bash
set -euo pipefail

docker compose -f infra/docker/docker-compose.yml up -d postgres

uv run uvicorn src.app.api.main:app --host 0.0.0.0 --port 8000 --reload
