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
| 4.5 | Foldering and docs alignment (pre-Phase 5) | completed |
| 5 | Authentication and AWS connection lifecycle hardening | planned |

## Detailed checklist

### Phase 0 - Execution policy guardrails

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Add execution context fields | Add explicit execution context fields `run_source` and `persist_mode` | Every execution path has explicit persistence context | Completed (100%) |
| Enforce non-persistent TUI mode | Add guardrails so TUI path always uses `persist_mode=none` | TUI does not write data to DB repositories | Completed (100%) |
| Enforce persistent API mode | Add guardrails so API path always uses `persist_mode=normalized` | API writes normalized data to DB | Completed (100%) |
| TUI persistence tests | Add unit tests proving TUI does not call persistence repositories | TUI persistence regressions are automatically detected | Completed (100%) |
| API persistence tests | Add unit tests proving API writes persistence data | API persistence regressions are automatically detected | Completed (100%) |
| Phase closure | Close Phase 0 after all guardrails are validated | Phase 0 is officially complete | Completed (100%) |

### Phase 1 - Security/alert normalization

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Add findings schema | Add normalized `finding_events` schema and DB migration | Security/alert findings are stored in structured form | Completed (100%) |
| Add findings mappers | Implement mappers for `guardduty`, `cloudwatch`, `notifications` | Checker output maps consistently to normalized events | Completed (100%) |
| Persist findings from API | Persist normalized findings on API execution path | API runs produce queryable findings data | Completed (100%) |
| Findings query endpoint | Add findings query endpoint (filter + pagination) | Frontend/API consumers can query stable findings data | Completed (100%) |
| Findings contract examples | Add findings response contract examples | Frontend integration has clear payload references | Completed (100%) |
| Phase closure | Close Phase 1 after persistence + query + contract are validated | Phase 1 is officially complete | Completed (100%) |

### Phase 2 - Backup normalization

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Backup mapping dimensions | Add backup dimensions (profile/account/region/plan/vault/status) | Backup events have consistent detailed structure | Completed (100%) |
| Persist backup events | Persist backup reliability events in normalized table | Backup findings are analyzable across runs | Completed (100%) |
| Backup query filters | Add backup-focused findings filters | Consumers can isolate backup events quickly | Completed (100%) |
| Backup mapping tests | Add tests for failed/expired/completed mapping cases | Backup mapping stays stable across key edge cases | Completed (100%) |
| Phase closure | Close Phase 2 after mapping + persistence are validated | Phase 2 is officially complete | Completed (100%) |

### Phase 3 - Utilization and global config-driven rollout

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Add metrics schema | Add normalized `metric_samples` schema and migration | Numeric metrics data is stored in structured form | Completed (100%) |
| Map daily-arbel metrics | Map `daily-arbel` output into `metric_samples` | Daily-arbel metrics are queryable across runs/accounts | Completed (100%) |
| Add per-account config model | Add per-account check config model (alarm/budget/backup/threshold) | Check configuration is centrally managed in DB | Completed (100%) |
| Config management API | Implement API endpoints to manage per-account config | Frontend/operators can update config without direct YAML edits | Completed (100%) |
| Globalized checks rollout | Enable config-driven rollout for `alarm_verification`, `daily-budget`, RDS/utilization, `backup` | API execution path consistently uses DB configuration | Completed (100%) |
| Preserve TUI behavior | Keep TUI YAML-driven and non-persistent | Existing TUI flow remains stable and unaffected by API persistence | Completed (100%) |
| Phase closure | Close Phase 3 after rollout + tests are stable | Phase 3 is officially complete | Completed (100%) |

### Phase 4 - API spec and frontend readiness

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Publish stable API spec | Finalize API specs for `runs`, `findings`, `metrics`, `dashboard` | Frontend has stable endpoint contracts | Completed (100%) |
| Add DTOs and examples | Add DTOs/response examples for key endpoints | Frontend implementation is faster and less ambiguous | Completed (100%) |
| Contract stability tests | Add integration tests to protect API contract stability | Breaking backend changes are detected quickly | Completed (100%) |
| Documentation refresh | Update README and interface docs based on phase outputs | User/dev docs are synchronized with current runtime | Completed (100%) |
| Phase closure | Close Phase 4 after contract + docs are validated | Phase 4 is officially complete | Completed (100%) |

### Phase 4.5 - Foldering and docs alignment

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Canonical boundary freeze | Set runtime boundary: `backend/*` canonical, `src/*` transition compatibility layer | Runtime boundaries are clear and consistent in code/docs | Completed (100%) |
| Wrapper inventory | Inventory `src/*` wrappers and safe-removal candidates | Wrapper list and cleanup candidates are documented | Completed (100%) |
| Architecture docs alignment | Align architecture docs with current foldering state | Architecture docs reflect latest structure accurately | Completed (100%) |
| Stale docs cleanup | Remove/merge stale pre-migration runtime narratives | No misleading stale runtime narratives remain | Completed (100%) |
| Entrypoint docs alignment | Align `README.md`, `docs/PROJECT.md`, and runbooks with latest entrypoint/delegation model | Entrypoint references are consistent across docs | Completed (100%) |
| Foldering handoff guide | Add/update dedicated foldering explanation for cross-session/model continuity | Dedicated foldering handoff guide exists and is current | Completed (100%) |
| Docs reference validation | Validate docs path/command references via grep sanity pass | Docs references are validated with no major mismatches | Completed (100%) |
| Phase closure | Close Phase 4.5 after all tasks are completed | Phase 4.5 is officially complete | Completed (100%) |

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
- 2026-03-19: Finalized checks cutover by removing `src/checks/*` package and updating imports/tests to `backend/checks/*`.
- 2026-03-19: Updated Phase overview status to completed for Phase 4.5 after cutover verification.
