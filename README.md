# ICS Monitoring Hub

> Centralized AWS monitoring platform — multi-customer health, security, cost anomaly, backup, and utilization visibility with a modern web dashboard and WhatsApp-ready reports.

**🌐 Live:** https://msmonitoring.bagusganteng.app

---

## What is this?

ICS Monitoring Hub is an internal platform built by the ICS team to monitor AWS infrastructure across multiple customers from a single dashboard. Instead of logging into each AWS account manually, operators run checks from one place and get consolidated reports — sent to Slack or formatted for WhatsApp.

The platform supports three report modes per customer:
- **Simple** — clean alarm list, ready to copy-paste
- **Summary** — compact WhatsApp-friendly daily report with utilization metrics
- **Detailed** — full technical report with all findings and per-account breakdown

---

## Stack

| | |
|---|---|
| **Frontend** | Next.js 15 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · Hugeicons |
| **Backend** | FastAPI · SQLAlchemy 2 · Alembic · Python 3.11 · uv |
| **Database** | PostgreSQL 16 |
| **Auth** | JWT · Google OAuth |
| **Infra** | Docker Compose · AWS EC2 (behind bastion) · GitHub Container Registry |
| **CI/CD** | GitHub Actions — split per target (backend / frontend) |

---

## Features

**Monitoring**
- Multi-customer, multi-account AWS checks running in parallel
- Checks: GuardDuty · CloudWatch Alarms · Cost Anomaly · Backup · Health Events · Notifications · RDS/EC2 Utilization · Budget · Alarm Verification
- Per-customer check configuration, Slack webhook, and report mode
- Findings tracked over time with severity levels and age

**Reports**
- WhatsApp-ready daily reports with greeting, utilization metrics, and alert notes
- Cost anomaly detail: contributing accounts with AWS IDs, services, and impact ($)
- Monthly workload report — metric fluctuations, stuck issues, cost highlights
- Export as HTML preview or CSV download

**Operations**
- Ticketing system with Zoho ticket no., PIC, and status tracking
- Mailing list — manage notification email contacts per customer
- Session health monitoring — detect expired AWS SSO sessions across all accounts
- Role-based access: `super_user` (full admin) and regular users

---

## Project Structure

```
monitoring-ics-apps/
│
├── backend/                        # Python backend (canonical implementation)
│   ├── checks/                     # AWS check implementations
│   │   ├── generic/                #   cost_anomalies, guardduty, cloudwatch, backup...
│   │   └── common/                 #   BaseChecker, error helpers
│   ├── domain/
│   │   └── services/               # CheckExecutor, report builders (simple/summary/detailed)
│   ├── infra/
│   │   ├── database/
│   │   │   ├── models.py           # SQLAlchemy models (Customer, Account, Ticket, MailingContact...)
│   │   │   └── repositories/       # Data access layer
│   │   └── notifications/slack/    # Slack webhook notifier
│   ├── interfaces/
│   │   ├── api/                    # FastAPI app — routes, dependencies, main.py
│   │   └── cli/                    # TUI (Textual) for terminal operators
│   └── config/
│       └── settings.py             # All env-based settings with defaults
│
├── frontend/                       # Next.js web application
│   ├── app/
│   │   ├── (dashboard)/            # Protected dashboard pages
│   │   │   ├── customers/          #   Customer & account management
│   │   │   ├── history/            #   Check run history & report viewer
│   │   │   ├── findings/           #   Finding events tracker
│   │   │   ├── metrics/            #   Metric samples explorer
│   │   │   ├── reports/            #   Monthly workload reports
│   │   │   ├── ticketing/          #   Internal ticketing
│   │   │   ├── mailing/            #   Email contact management
│   │   │   └── alarms/             #   Active alarm monitoring
│   │   └── api/                    # Next.js API routes (proxy to backend)
│   ├── components/
│   │   ├── ui/                     # shadcn/ui base components
│   │   ├── customers/              # Customer list, sheets, account rows
│   │   └── common/                 # PageHeader, EmptyState, ConfirmDialog...
│   └── lib/
│       ├── types/api.ts            # TypeScript types — Customer, Account, ReportMode...
│       └── api/                    # Server-side fetch helpers
│
├── alembic/                        # Database migrations
│   └── versions/                   # Migration files (auto-applied on deploy)
│
├── tests/
│   └── unit/                       # CI-gated unit tests (41 tests)
│       ├── test_check_executor.py  #   Executor behavior, parallel checks, timeouts
│       ├── test_checks_route.py    #   API contract validation
│       ├── test_api_main.py        #   App startup & health endpoints
│       └── test_settings_runtime.py
│
├── infra/
│   └── docker/                     # Docker Compose configs (dev & prod)
│
├── docs/
│   ├── PROJECT.md                  # Full technical reference
│   ├── architecture/               # Folder structure, migration status
│   └── operations/                 # Deploy runbook, release checklist
│
└── .github/workflows/              # CI/CD pipelines
    ├── ci-backend.yml
    ├── ci-frontend.yml
    ├── deploy-backend.yml
    └── deploy-frontend.yml
```

---

## Local Development

**Requirements:** Python 3.11+, Node 20+, Docker, [uv](https://github.com/astral-sh/uv)

```bash
# 1. Start PostgreSQL
docker compose -f infra/docker/docker-compose.yml up -d postgres

# 2. Install backend deps & run migrations
uv sync
DATABASE_URL=postgresql+psycopg://monitor:monitor@localhost:5432/monitoring \
  alembic upgrade head

# 3. Start backend (auto-reload)
DATABASE_URL=postgresql+psycopg://monitor:monitor@localhost:5432/monitoring \
  uvicorn backend.interfaces.api.main:app --reload --port 8000

# 4. Start frontend
cp frontend/.env.local.example frontend/.env.local
npm install --prefix frontend
npm run dev --prefix frontend
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Environment Variables

### Backend
| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://monitor:monitor@localhost:5432/monitoring` | PostgreSQL connection string |
| `JWT_SECRET` | `change-me-in-production` | Sign with `openssl rand -hex 32` |
| `DEFAULT_REGION` | `ap-southeast-3` | AWS default region |
| `MAX_WORKERS` | `20` | Parallel check thread pool size |
| `EXECUTION_TIMEOUT` | `300` | Max seconds per check batch |
| `CORS_ORIGINS` | `*` | Allowed origins (comma-separated) |
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID |
| `SMTP_USER` / `SMTP_PASSWORD` | — | Gmail App Password for invite emails |

### Frontend (`frontend/.env.local`)
| Variable | Description |
|---|---|
| `JWT_SECRET` | Must match backend exactly |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL |

---

## CI/CD

Every push to `main` triggers CI and, if it passes, auto-deploys to production.

```
Push → CI (tests + typecheck) → Build Docker image → Push to GHCR
     → SSH to EC2 → alembic upgrade head → docker compose up → smoke test
```

| Workflow | Trigger path | Quality gate |
|---|---|---|
| `ci-backend` | `backend/**` | 41 pytest unit tests + app import |
| `ci-frontend` | `frontend/**` | TypeScript strict typecheck |
| `deploy-backend` | CI Backend ✅ on `main` | Build → migrate → restart backend |
| `deploy-frontend` | CI Frontend ✅ on `main` | Build → restart frontend + nginx |

**Run CI locally:**
```bash
# Backend — must pass before pushing
uv run --with pytest --with httpx pytest tests/unit/ -q
uv run python -c "from backend.interfaces.api.main import create_app; create_app()"

# Frontend — must pass before pushing
npm run --prefix frontend typecheck
```

---

## Documentation

| | |
|---|---|
| [`docs/PROJECT.md`](docs/PROJECT.md) | Full technical reference: DB schema, API endpoints, all checks |
| [`docs/operations/deployment-flow.md`](docs/operations/deployment-flow.md) | Deploy pipeline in detail |
| [`docs/operations/single-server-deploy.md`](docs/operations/single-server-deploy.md) | Production server runbook |
| [`docs/setup/setup-guide-id.md`](docs/setup/setup-guide-id.md) | AWS & environment setup guide |

---

<div align="center">
  <sub>Built with ☕ by the ICS team · Powered by FastAPI, Next.js & PostgreSQL</sub>
</div>
