# ICS Monitoring Hub — Dokumentasi Utama

Platform monitoring AWS terpusat untuk multi-customer. Dibangun dengan FastAPI (backend) + Next.js 15 (frontend) + PostgreSQL.

Live: `msmonitoring.bagusganteng.app`

---

## Dokumentasi Lengkap

| Dokumen | Isi |
|---|---|
| [Backend](./backend/README.md) | Arsitektur backend, semua checks, API endpoints, database schema, cara pengembangan |
| [Frontend](./frontend/README.md) | Semua halaman, komponen, alur UI, dan cara pengembangan frontend |
| [Operations](./operations/) | Deploy, release checklist, single-server setup |
| [Setup](./setup/setup-guide-id.md) | Panduan setup environment lokal |
| [Archive](./archive/) | Dokumen lama yang sudah tidak aktif |

---

## Gambaran Singkat Sistem

```
Browser → nginx → Next.js (frontend) → FastAPI :8000 → PostgreSQL :5432
Terminal → TUI (Textual) → backend/interfaces/cli/
```

**Dua interface utama:**

1. **Web Platform** — Next.js + FastAPI, akses via browser, DB-persistent
2. **TUI** — Terminal UI (Textual), jalankan langsung di mesin operator, tidak tulis DB

**Stack teknologi:**
- Backend: FastAPI + SQLAlchemy 2.0 + Alembic + uv
- Frontend: Next.js 15 (App Router) + TypeScript + shadcn/ui + Hugeicons + Tailwind CSS
- Database: PostgreSQL 16
- Deploy: Docker Compose (postgres + backend + frontend + nginx)

---

## Struktur Folder Proyek

```
monitoring-ics-apps/
├── backend/                    # Source of truth runtime
│   ├── checks/                 # Semua AWS checker
│   │   ├── common/             # BaseChecker, error helpers
│   │   ├── generic/            # Checker universal (cost, guardduty, cloudwatch, dll)
│   │   ├── aryanoble/          # Checker khusus Aryanoble
│   │   └── huawei/             # Checker Huawei Cloud
│   ├── domain/                 # Orchestration, service layer, report formatting
│   │   ├── engine/             # JobExecutor, JobStore (async job management)
│   │   ├── formatting/         # Report builder functions
│   │   ├── models/             # Job models
│   │   ├── runtime/            # Check registry, customer runner, reports
│   │   └── services/           # check_executor.py — engine utama eksekusi
│   ├── infra/                  # Integrasi eksternal
│   │   ├── database/           # SQLAlchemy models, repositories
│   │   ├── notifications/      # Slack notifier
│   │   └── aws/                # AWS session builder
│   ├── interfaces/
│   │   ├── api/                # FastAPI app, routes, dependencies, middleware
│   │   └── cli/                # TUI (Textual) entry point
│   ├── config/                 # Settings, defaults, schema
│   └── utils/                  # Helpers umum
├── frontend/                   # Next.js 15 app
│   ├── app/
│   │   ├── (auth)/             # Login, auth pages
│   │   ├── (dashboard)/        # Semua halaman dashboard
│   │   └── api/                # Next.js proxy routes ke backend
│   ├── components/             # Shared UI components
│   ├── lib/                    # API client, types, utils
│   └── hooks/                  # Custom React hooks
├── alembic/                    # DB migrations
├── configs/                    # Customer YAML configs (untuk TUI)
├── docs/                       # Dokumentasi
├── infra/                      # Docker Compose, nginx config
├── scripts/                    # Seed scripts, utilities
└── tests/                      # Unit + integration tests
```

---

## Cara Menjalankan (Development)

```bash
# 1. PostgreSQL
docker compose -f infra/docker/docker-compose.yml up -d postgres

# 2. Migrasi DB
DATABASE_URL=postgresql+psycopg://monitor:monitor@localhost:5432/monitoring \
  alembic upgrade head

# 3. Backend API
DATABASE_URL=postgresql+psycopg://monitor:monitor@localhost:5432/monitoring \
  uvicorn backend.interfaces.api.main:app --reload --port 8000

# 4. Frontend
cd frontend && npm install && npm run dev   # http://localhost:3000
```

**TUI:**
```bash
pip install -e .
monitoring-hub
```

**Production (Docker Compose):**
```bash
docker compose -f infra/docker/docker-compose.yml up -d
# Akses: http://localhost:8080
```

---

## CI Gates (Wajib Lulus Sebelum Push)

```bash
# Backend tests (41 unit tests)
uv run --with pytest --with httpx pytest \
  tests/unit/test_api_main.py \
  tests/unit/test_checks_route.py \
  tests/unit/test_check_executor.py \
  tests/unit/test_settings_runtime.py \
  tests/unit/test_src_adapters.py -q

# Backend app import check
uv run python -c "from backend.interfaces.api.main import create_app; create_app()"

# Frontend typecheck
npm run --prefix frontend typecheck
```

---

## Customers (Ringkas)

| Nama | Display | Akun | Keterangan |
|---|---|---|---|
| `aryanoble` | Aryanoble | 17 | Arbel mode, alarm_verification |
| `ksni` | KSNI | 17 | Nabati SSO |
| `frisianflag` | Frisian Flag | 1 | simple report_mode |
| `hungryhub` | HungryHub | 5 | — |
| `diamond` | Diamond | 1 | sadewa-sso |
| `fresnel` | Fresnel | 4 | sadewa-sso |
| `ucoal` | uCoal | 4 | sadewa-sso |
| `token` | Token | 0 | Ticketing khusus, no AWS accounts |
| ... | | | Lihat backend/README.md untuk daftar lengkap |

Detail teknis selengkapnya → lihat [Backend README](./backend/README.md) dan [Frontend README](./frontend/README.md).
