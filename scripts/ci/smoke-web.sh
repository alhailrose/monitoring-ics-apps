#!/usr/bin/env bash
set -euo pipefail

WEB_BASE_URL="${WEB_BASE_URL:-}"

if [[ -z "${WEB_BASE_URL}" ]]; then
  echo "WEB_BASE_URL is required (example: https://monitoring.example.com)" >&2
  exit 2
fi

curl -fsSI "${WEB_BASE_URL}/" >/dev/null

echo "Web smoke check passed for ${WEB_BASE_URL}"
