# Backend Development Plan (Living)

This is the main living plan for backend evolution.

- Use this file as the single source of truth for phase status.
- Update checklist items before every commit.
- Update user-facing docs and API contract docs only when a phase goal is achieved.

## Scope and constraints

- Backend API is DB-persistent and analytics-oriented.
- TUI remains local and fast, with no DB persistence.
- Backend config source of truth: database.
- TUI config source of truth: customer YAML.
- AWS direct SDK remains primary execution model.
- Migration policy: forward-only (no mandatory backfill).

### Authentication boundary

- App auth and AWS auth are separate layers.
- App auth: users log in to the app with roles `super_user` (admin) and `user` (readonly).
- AWS auth is per customer (not per app user), using `access_key`, `assume_role`, or `sso`.
- Recommendation: new customer onboarding should default to `assume_role` (`MonitoringReadOnlyRole`).
- For expired customer `sso` sessions: send Slack notification and runbook command `aws sso login --profile <profile> --use-device-code --no-browser`.

### Production note (short)

- PostgreSQL: source of truth for persistent backend data (`check_runs`, normalized events/metrics, per-account check config).
- Redis: operational cache/queue/session support where enabled by deployment profile.
- AWS Secrets Manager: store customer AWS connection secrets and integration secrets.

## Current check inventory

- Generic/core: `health`, `cost`, `guardduty`, `cloudwatch`, `notifications`, `backup`, `ec2list`, `aws-utilization-3core`
- Customer-specific: `daily-arbel`, `daily-budget`, `alarm_verification`
- Provider-specific: `huawei-ecs-util`

## Phase overview

| Phase | Goal | Status |
|---|---|---|
| 0 | Enforce execution-mode policy (TUI non-persistent, API persistent) | completed |
| 1 | Normalize security/alert findings | completed |
| 2 | Normalize backup reliability events | completed |
| 3 | Normalize utilization and globalize config-driven checks | completed |
| 4 | Finalize remaining checks + frontend API contract | completed |
| 4.5 | Foldering and docs alignment (pre-Phase 5) | planned |
| 5 | Authentication and AWS connection lifecycle hardening | planned |

## Detailed checklist

### Phase 0 - Execution policy guardrails

- [x] Add explicit execution context fields (`run_source`, `persist_mode`)
- [x] Enforce `persist_mode=none` for TUI orchestration path
- [x] Enforce `persist_mode=normalized` for API orchestration path
- [x] Add unit tests proving TUI does not call repositories
- [x] Add unit tests proving API does persist
- [x] Mark phase as done in this plan

### Phase 1 - Security/alert normalization

- [x] Add normalized `finding_events` schema and migration
- [x] Add mappers for `guardduty`, `cloudwatch`, `notifications`
- [x] Persist normalized findings from API runs
- [x] Add query endpoint for findings (filter/pagination)
- [x] Add API contract examples for findings
- [x] Mark phase as done in this plan

### Phase 2 - Backup normalization

- [x] Add backup finding mapping dimensions (profile/account/region/plan/vault/status)
- [x] Persist backup reliability events in normalized table
- [x] Add backup-focused findings query filters
- [x] Add tests for failed/expired/completed mapping cases
- [x] Mark phase as done in this plan

### Phase 3 - Utilization and global config-driven rollout

- [x] Add normalized `metric_samples` schema and migration
- [x] Map `daily-arbel` outputs into `metric_samples`
- [x] Add account-level check config model in DB (alarm names, budget names, backup filters, thresholds)
- [x] Implement API management endpoints for per-account check config
- [x] Enable global rollout path for:
  - [x] `alarm_verification`
  - [x] `daily-budget`
  - [x] RDS/utilization checks
  - [x] `backup`
- [x] Keep TUI behavior unchanged (YAML-driven, non-persistent)
- [x] Mark phase as done in this plan

### Phase 4 - API spec and frontend readiness

- [x] Publish stable API spec for frontend (`runs`, `findings`, `metrics`, `dashboard`)
- [x] Add DTO contracts and response examples
- [x] Add integration tests for contract stability
- [x] Update README and interface docs at phase completion
- [x] Mark phase as done in this plan

### Phase 4.5 - Foldering and docs alignment

- [x] Freeze canonical boundary: `backend/*` canonical, `src/*` compatibility + active checks only
- [x] Inventory `src/*` wrappers and mark safe-removal candidates (no runtime references)
- [x] Update architecture docs to current-state foldering and wrapper lifecycle
- [x] Remove/merge stale docs that still describe pre-migration layout as active runtime
- [x] Align `README.md`, `docs/PROJECT.md`, and runbooks with current entrypoint/delegation model
- [x] Add/update dedicated foldering explanation doc for handoff continuity
- [x] Verify docs references (paths/commands) via grep sanity pass
- [x] Mark phase as done in this plan

### Phase 5 - Authentication and AWS connection layer

- [ ] Enforce auth boundary in backend services (App Auth roles vs per-customer AWS Auth ownership)
- [ ] Add/verify per-customer AWS auth mode model and API contract (`access_key`, `assume_role`, `sso`)
- [ ] Implement AWS login method selection/validation per customer (`assume_role` default, `sso`, `access_key`)
- [ ] Add explicit backend login-method resolver rules (priority, required fields, and invalid-combination errors)
- [ ] Set onboarding default for new customers to `assume_role` (`MonitoringReadOnlyRole`)
- [ ] Add runtime handling for expired `sso` sessions (detect expiry, classify error state)
- [ ] Send Slack notification on `sso` expiry with actionable profile context
- [ ] Document and expose admin runbook action: `aws sso login --profile <profile> --use-device-code --no-browser`
- [ ] Add AWS CLI login method guidance in ops runbook (`aws login` vs `aws sso login`) and enforce supported command per auth mode
- [ ] Add unit/integration tests for auth boundary, mode selection, and `sso` expiry notification path
- [ ] Mark phase as done in this plan

## Commit and docs workflow

### Before every commit

- [ ] Update relevant checklist items in this file
- [ ] Ensure item statuses match actual implementation

### At phase completion only

- [ ] Update `README.md` current architecture and usage notes
- [ ] Update API contract docs for changed endpoints/payloads
- [ ] Update interface docs (TUI/API/Web) only where phase impact exists

## Change log

- 2026-03-19: Initial living plan created from backend readiness assessment.
- 2026-03-19: Phase 0 completed (execution policy split + persistence policy tests).
- 2026-03-19: Phase 1 started (finding_events schema + security mapper + API persistence write path).
- 2026-03-19: Phase 1 completed (`/api/v1/findings` + frontend contract examples).
- 2026-03-19: Phase 2 completed (backup normalized finding mapping + persistence and tests).
- 2026-03-19: Phase 3 started (account check-config DB model + API CRUD + executor merge path).
- 2026-03-19: Phase 3 progress (added metric_samples schema + daily-arbel metric normalization persistence path).
- 2026-03-19: Phase 3 progress (globalized DB-config rollout for alarm verification, budget, backup, and utilization checks).
- 2026-03-19: Phase 3 completed.
- 2026-03-19: Phase 4 completed (stable contract for runs/findings/metrics/dashboard + integration contract test).
- 2026-03-19: Clarified app-vs-AWS auth boundary, customer auth modes, SSO-expiry Slack+runbook handling, and production infra note.
- 2026-03-19: Added Phase 5 checklist for authentication boundary and AWS connection lifecycle implementation tracking.
- 2026-03-19: Added Phase 4.5 checklist for foldering/docs alignment before Phase 5 implementation.
- 2026-03-19: Added `src/*` wrapper inventory doc and initial safe-removal candidate list for foldering cleanup.
- 2026-03-19: Migrated customer TUI flow to canonical backend path and converted legacy src flow to compatibility alias.
- 2026-03-19: Migrated runner engine/models (`src/core/engine`, `src/core/models`) to canonical backend paths with src compatibility aliases.
- 2026-03-19: Migrated report formatting (`src/core/formatting/reports.py`) to canonical backend path with src compatibility alias.
- 2026-03-19: Phase 4.5 completed (foldering/docs alignment, wrapper inventory, and canonical migration checkpoints).
- 2026-03-19: Added `backend/checks/*` bridge namespace and switched backend runtime imports away from direct `src.checks.*` dependencies.
- 2026-03-19: Migrated checker implementations to `backend/checks/*` and converted `src/checks/*` to compatibility aliases.
