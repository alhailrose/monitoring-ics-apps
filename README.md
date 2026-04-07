# ICS Monitoring Hub

Centralized AWS monitoring platform for multiple customers — health, security, cost, backup, and utilization checks with a web dashboard and WhatsApp-ready reports.

**Live:** https://msmonitoring.bagusganteng.app

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 (App Router) · TypeScript · shadcn/ui |
| Backend | FastAPI · SQLAlchemy 2 · Alembic · Python 3.11 |
| Database | PostgreSQL 16 |
| Infra | Docker Compose · EC2 (bastion) · GHCR |

---

## Features

- **Multi-customer** monitoring — each customer has their own AWS accounts, checks, Slack, and report mode
- **Check modes** — `all` (daily summary), `single` (specific check), `arbel` (Aryanoble preset)
- **Report modes** — `simple` (alarm list only), `summary` (WhatsApp-friendly), `detailed` (full report)
- **Checks** — GuardDuty, CloudWatch, Cost Anomaly, Backup, RDS/EC2 utilization, Health, Notifications, Budget, Alarm Verification
- **Ticketing** — internal ticket management with Zoho ticket no., PIC, and status tracking
- **Mailing list** — manage notification email contacts per customer
- **Slack integration** — per-customer webhook routing

---

## Local Development

**Prerequisites:** Python 3.11+, Node 20+, Docker

```bash
# 1. Start PostgreSQL
docker compose -f infra/docker/docker-compose.yml up -d postgres

# 2. Install backend dependencies
uv sync

# 3. Run migrations
DATABASE_URL=postgresql+psycopg://monitor:monitor@localhost:5432/monitoring \
  alembic upgrade head

# 4. Start backend
DATABASE_URL=postgresql+psycopg://monitor:monitor@localhost:5432/monitoring \
  uvicorn backend.interfaces.api.main:app --reload --port 8000

# 5. Start frontend
cp frontend/.env.local.example frontend/.env.local   # fill in JWT_SECRET
npm install --prefix frontend
npm run dev --prefix frontend
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:3000`

---

## Environment Variables

### Backend
| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://monitor:monitor@localhost:5432/monitoring` | Required in production |
| `JWT_SECRET` | `change-me-in-production` | Generate: `openssl rand -hex 32` |
| `DEFAULT_REGION` | `ap-southeast-3` | AWS default region |
| `MAX_WORKERS` | `20` | Check executor thread pool |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

### Frontend (`frontend/.env.local`)
| Variable | Notes |
|---|---|
| `JWT_SECRET` | Must match backend |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL |

---

## CI/CD

Push to `main` triggers automatic deployment to production EC2.

| Workflow | Trigger | Steps |
|---|---|---|
| `ci-backend` | `backend/**` changed | pytest (41 tests) + app import check |
| `ci-frontend` | `frontend/**` changed | TypeScript typecheck |
| `deploy-backend` | CI Backend passes | Build image → push GHCR → `alembic upgrade head` → restart |
| `deploy-frontend` | CI Frontend passes | Build image → push GHCR → restart |

**Run CI locally:**
```bash
# Backend
uv run --with pytest --with httpx pytest tests/unit/ -q
uv run python -c "from backend.interfaces.api.main import create_app; create_app()"

# Frontend
npm run --prefix frontend typecheck
```

---

## Project Structure

```
├── backend/
│   ├── checks/          # AWS check implementations
│   ├── domain/          # Business logic & services
│   ├── infra/           # Database models, repositories
│   ├── interfaces/
│   │   ├── api/         # FastAPI routes
│   │   └── cli/         # TUI (Textual)
│   └── config/          # Settings
├── frontend/            # Next.js web app
├── alembic/             # Database migrations
├── tests/unit/          # Unit tests (CI gate)
├── infra/docker/        # Docker Compose configs
└── docs/                # Architecture & operations docs
```

---

## Documentation

| Doc | Description |
|---|---|
| [`docs/PROJECT.md`](docs/PROJECT.md) | Full technical reference — schema, API endpoints, checks |
| [`docs/operations/deployment-flow.md`](docs/operations/deployment-flow.md) | Deploy pipeline details |
| [`docs/operations/single-server-deploy.md`](docs/operations/single-server-deploy.md) | Production server runbook |
| [`docs/setup/setup-guide-id.md`](docs/setup/setup-guide-id.md) | AWS setup guide (ID) |
