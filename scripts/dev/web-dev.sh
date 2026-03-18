#!/usr/bin/env bash
set -euo pipefail

export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:8000}"

npm --prefix web run dev
