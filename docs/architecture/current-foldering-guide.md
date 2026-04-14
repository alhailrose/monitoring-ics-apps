# Current Foldering Guide

Dokumen ini menjelaskan struktur folder runtime yang berlaku saat ini. Wajib dibaca sebelum memulai sesi pengembangan.

## Prinsip Utama

- `backend/*` adalah **satu-satunya** namespace runtime Python (source of truth)
- `src/*` sudah dihapus penuh dari runtime — jangan kembalikan
- `frontend/*` adalah runtime Next.js
- Semua import di kode dan test wajib mengarah ke `backend.*`

## Entry Points

| Interface | File | Persistence |
|---|---|---|
| API (web) | `backend/interfaces/api/main.py:app` | DB-persistent |
| TUI/CLI | `backend/interfaces/cli/main.py:main` | Non-persistent |
| Packaging | `monitoring-hub → backend.interfaces.cli.main:main` | — |

## Struktur Runtime Backend

```
backend/
  checks/           # Semua AWS checker (lokasi kanonis)
    common/         # BaseChecker, error helpers
    generic/        # Checker universal
    aryanoble/      # Checker khusus Aryanoble
    huawei/         # Checker Huawei Cloud
  domain/
    engine/         # JobExecutor, JobStore (async job management)
    formatting/     # Report builder functions (reusable)
    models/         # Job models
    runtime/        # AVAILABLE_CHECKS registry, customer runner, reports
    services/       # check_executor.py — engine utama eksekusi
  infra/
    database/       # SQLAlchemy models + repositories
    notifications/  # Slack notifier
    aws/            # AWS session builder
  interfaces/
    api/            # FastAPI app, routes, dependencies
    cli/            # TUI (Textual)
  config/           # Settings, defaults
  utils/            # Helpers
```

## Cutover Policy

1. Semua import runtime dan test menggunakan `backend.*`
2. Jangan tambahkan kembali namespace `src.*`
3. Setiap perubahan struktur wajib diikuti verifikasi test

## Quality Gates (Wajib Sebelum Push)

```bash
# Backend tests
uv run --with pytest --with httpx pytest \
  tests/unit/test_api_main.py \
  tests/unit/test_checks_route.py \
  tests/unit/test_check_executor.py \
  tests/unit/test_settings_runtime.py \
  tests/unit/test_src_adapters.py -q

# App import check
uv run python -c "from backend.interfaces.api.main import create_app; create_app()"

# Frontend typecheck
npm run --prefix frontend typecheck
```

## Referensi Dokumentasi

- `docs/PROJECT.md` — Index utama + gambaran sistem
- `docs/backend/README.md` — Backend lengkap (semua checks, API, DB schema)
- `docs/frontend/README.md` — Frontend lengkap (semua halaman, komponen, alur)
- `docs/operations/` — Deploy, release checklist
- `docs/development/backend-development-plan.md` — Phase plan (living doc)
