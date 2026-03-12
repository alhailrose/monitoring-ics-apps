#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-}"

if [[ -z "${API_BASE_URL}" ]]; then
  echo "API_BASE_URL is required (example: https://monitoring-api.example.com)" >&2
  exit 2
fi

curl -fsS "${API_BASE_URL}/health/liveness" >/dev/null
curl -fsS "${API_BASE_URL}/health/readiness" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/checks/available" >/dev/null

echo "API smoke check passed for ${API_BASE_URL}"
