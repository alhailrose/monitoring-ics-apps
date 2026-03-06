#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILES="${1:-dh_prod_erp-ro,dh_prod_nonerp-ro}"
REGION="${REGION:-ap-southeast-4}"
WORKERS="${WORKERS:-4}"

cd "$ROOT_DIR"
PYTHONPATH="$ROOT_DIR" python3 src/app/cli/bootstrap.py \
  --check huawei-ecs-util \
  --profile "$PROFILES" \
  --region "$REGION" \
  --workers "$WORKERS"
