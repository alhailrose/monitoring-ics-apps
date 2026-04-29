#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_ENV="$ROOT_DIR/frontend/.env.local"

if [[ -z "${JWT_SECRET:-}" ]]; then
  if [[ -f "$FRONTEND_ENV" ]]; then
    JWT_SECRET="$(python - "$FRONTEND_ENV" <<'PY'
import sys
from pathlib import Path
env = Path(sys.argv[1]).read_text().splitlines()
for line in env:
    if line.startswith('JWT_SECRET='):
        print(line.split('=', 1)[1].strip())
        break
PY
)"
  fi
fi

if [[ -z "${JWT_SECRET:-}" ]]; then
  echo "JWT_SECRET is missing. Set it in frontend/.env.local or export JWT_SECRET first."
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://monitor:monitor@localhost:5432/monitoring}"
export JWT_SECRET

exec uv run uvicorn backend.interfaces.api.main:app --host 0.0.0.0 --port 8000
