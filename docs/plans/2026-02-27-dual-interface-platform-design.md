# Dual Interface Platform Design (TUI + Webapp)

Date: 2026-02-27
Owner: Monitoring Hub team
Status: Approved for planning

## 1) Goal

Evolve the current monitoring program into a dual-interface product:
- Keep the existing TUI as a first-class operator workflow
- Add a production-ready Webapp for manual trigger, job visibility, and historical dashboard

The check engine remains shared, with no duplicated business logic between TUI and Webapp.

## 2) Scope Decisions (Locked)

- TUI is not removed
- Webapp is added as second interface
- Single-server deployment first
- PostgreSQL is used for persistent runtime data
- Use Docker for production readiness
- Scheduler is postponed (manual trigger first)
- Database stores normalized structured results only
- Database does not store rendered report text/messages

## 3) Architecture Overview

Recommended architecture: Shared Core + Dual Interface

1. Core Engine (existing)
   - `backend/checks/*`
   - `src/core/runtime/*`
   - Source of truth for check logic and evaluation

2. Application Service Layer (new)
   - Headless use-cases for run/check/report operations
   - Input/Output contracts shared by TUI and API

3. Interface Layer
   - TUI adapter (existing, routed through service layer)
   - Web API + Web UI (new)

4. Runtime Infrastructure
   - API service
   - Worker service
   - PostgreSQL
   - Redis/queue backend
   - Nginx reverse proxy

## 4) Data Policy

### 4.1 Stored in PostgreSQL

- Job metadata: who/what/when/status/duration
- Check execution metadata: customer, account, profile, check type, region
- Normalized check outputs:
  - metric values
  - threshold values
  - evaluation statuses
  - alarm periods/time windows
  - important timestamps

### 4.2 Not Stored in PostgreSQL

- Human-facing rendered text (TUI summary text, greeting text, WhatsApp text)
- Any UI-specific phrasing

Rendering is generated on demand from normalized data.

## 5) Initial Product Flow (Phase 1)

Manual-trigger-first (no scheduler yet):

1. User opens Webapp
2. User selects customer/check/profiles and clicks Run
3. API creates job in DB and enqueues task
4. Worker executes shared check engine
5. Worker writes normalized results to DB
6. Webapp dashboard reads latest status + historical trend
7. TUI can still run directly and should use same service contracts when integrated

## 6) Deployment Model (Single Server)

Docker Compose target on one VM/server:

- `api`
- `worker`
- `postgres`
- `redis`
- `nginx`

Persistent volumes:
- PostgreSQL data
- Application logs (if file logging enabled)

## 7) Repository Structure (Target)

Keep existing engine structure and add clear app/runtime boundaries:

- `src/core/` (engine/shared runtime)
- `backend/checks/` (domain checks)
- `src/app/tui/` (existing interface)
- `src/app/api/` (new API)
- `src/app/worker/` (new worker)
- `src/db/` (models, migrations, repositories)
- `web/` (frontend)
- `infra/docker/` (compose, env, deploy scripts)
- `configs/customers/` (local overrides)
- `src/configs/defaults/customers/` (packaged defaults)

## 8) Master Data Strategy

Current source:
- Customer/account/check mapping from YAML configs

Resolution precedence:
1. Local override: `configs/customers/*.yaml`
2. Packaged defaults: `src/configs/defaults/customers/*.yaml`

Operational requirement:
- AWS profile names used at runtime must match resolved YAML `profile` values
- Non-SSO profiles are valid as long as boto3 can resolve credentials for that profile

## 9) Dashboard Minimum Features

Phase 1 dashboard includes:
- Run Now (manual trigger)
- Job list with status timeline
- Run detail with normalized metrics and alarm intervals
- Historical views per customer/account/check

Scheduler UI (daily / 3-hour / 12-hour presets) is deferred to later phase.

## 10) Risk Notes

- Drift risk between local YAML and packaged defaults
  - Mitigation: precedence order already implemented and tested
- Message rendering consistency across TUI/Web
  - Mitigation: centralize renderer helpers on top of normalized model
- Growth risk for historical data
  - Mitigation: retention policy to be defined during implementation

## 11) Acceptance for This Design

This design is accepted when implementation plan delivers:
- TUI continues to work without behavioral regression
- Webapp can manually trigger checks through shared engine
- PostgreSQL stores normalized historical results
- Single-server Docker deployment is runnable by operations
