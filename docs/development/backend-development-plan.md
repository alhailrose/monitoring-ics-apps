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

## Current check inventory

- Generic/core: `health`, `cost`, `guardduty`, `cloudwatch`, `notifications`, `backup`, `ec2list`, `aws-utilization-3core`
- Customer-specific: `daily-arbel`, `daily-budget`, `alarm_verification`
- Provider-specific: `huawei-ecs-util`

## Phase overview

| Phase | Goal | Status |
|---|---|---|
| 0 | Enforce execution-mode policy (TUI non-persistent, API persistent) | completed |
| 1 | Normalize security/alert findings | completed |
| 2 | Normalize backup reliability events | planned |
| 3 | Normalize utilization and globalize config-driven checks | planned |
| 4 | Finalize remaining checks + frontend API contract | planned |

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

- [ ] Add backup finding mapping dimensions (profile/account/region/plan/vault/status)
- [ ] Persist backup reliability events in normalized table
- [ ] Add backup-focused findings query filters
- [ ] Add tests for failed/expired/completed mapping cases
- [ ] Mark phase as done in this plan

### Phase 3 - Utilization and global config-driven rollout

- [ ] Add normalized `metric_samples` schema and migration
- [ ] Map `daily-arbel` outputs into `metric_samples`
- [ ] Add account-level check config model in DB (alarm names, budget names, backup filters, thresholds)
- [ ] Implement API management endpoints for per-account check config
- [ ] Enable global rollout path for:
  - [ ] `alarm_verification`
  - [ ] `daily-budget`
  - [ ] RDS/utilization checks
  - [ ] `backup`
- [ ] Keep TUI behavior unchanged (YAML-driven, non-persistent)
- [ ] Mark phase as done in this plan

### Phase 4 - API spec and frontend readiness

- [ ] Publish stable API spec for frontend (`runs`, `findings`, `metrics`, `dashboard`)
- [ ] Add DTO contracts and response examples
- [ ] Add integration tests for contract stability
- [ ] Update README and interface docs at phase completion
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
