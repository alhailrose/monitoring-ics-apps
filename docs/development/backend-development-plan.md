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
| 4.5 | Foldering/docs alignment and full src cutover (pre-Phase 5) | completed |
| 5 | App auth — user roles, login session, frontend auth flow | planned |
| 6 | AWS connection layer — auth mode model, resolver, SSO expiry in API path | planned |

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
| Canonical boundary freeze | Set runtime boundary: `backend/*` sebagai satu-satunya namespace runtime python | Runtime boundaries are clear and consistent in code/docs | Completed (100%) |
| Wrapper inventory | Inventory wrapper `src/*` dan selesaikan removal untuk full cutover | Wrapper list and removal status are documented | Completed (100%) |
| Architecture docs alignment | Align architecture docs with current foldering state | Architecture docs reflect latest structure accurately | Completed (100%) |
| Stale docs cleanup | Remove/merge stale pre-migration runtime narratives | No misleading stale runtime narratives remain | Completed (100%) |
| Entrypoint docs alignment | Align `README.md`, `docs/PROJECT.md`, and runbooks with latest entrypoint/delegation model | Entrypoint references are consistent across docs | Completed (100%) |
| Foldering handoff guide | Add/update dedicated foldering explanation for cross-session/model continuity | Dedicated foldering handoff guide exists and is current | Completed (100%) |
| Docs reference validation | Validate docs path/command references via grep sanity pass | Docs references are validated with no major mismatches | Completed (100%) |
| Phase closure | Close Phase 4.5 after all tasks are completed | Phase 4.5 is officially complete | Completed (100%) |

### Phase 5 - App authentication and frontend login flow

#### Design overview

This phase introduces user-level authentication to the web application. The current API key auth is flat and has no concept of users or roles — this phase replaces it with a proper JWT-based auth system with two roles. It also lays the backend foundation that the frontend login flow depends on.

**This phase is the prerequisite for any multi-user frontend work.**

**Auth boundary separation (important):**

These are two completely separate auth layers that must not be conflated:

| Layer | What it controls | Implemented in |
|---|---|---|
| **App auth** | Who can access the web application | Phase 5 (this phase) |
| **AWS auth** | How the program connects to customer AWS accounts | Phase 6 |

App auth roles do not affect which AWS accounts a user can access — that is determined by the customer-to-account mapping in the database, not by the user's app role.

**Planned roles:**

| Role | Permissions |
|---|---|
| `super_user` | Full admin: create/update/delete customers, accounts, users; run checks; view all data |
| `user` | Read-only + execute checks: view dashboards, history, findings; trigger check runs; cannot modify customer or account records |

#### 5A — User model and database schema

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Add auth dependencies | Add `passlib[bcrypt]`, `python-jose[cryptography]` (or `PyJWT`), and any other required auth packages to project dependencies | Auth libraries are available for password hashing and JWT operations | Completed (100%) |
| Design `users` table | Add a `users` table with columns: `id` (UUID PK), `username` (unique string, not null), `hashed_password` (string, not null), `role` (string, enum: `super_user` / `user`, not null), `is_active` (bool, default true), `created_at`, `updated_at` | User records can be stored and queried with role information | Completed (100%) |
| Write Alembic migration | Create a forward-only Alembic migration for the `users` table. No changes to any existing table. | Migration runs cleanly on all existing databases without touching existing data | Completed (100%) |
| Add `User` SQLAlchemy model | Add `User` model class to `backend/infra/database/models.py` with correct column definitions and type annotations | ORM model accurately reflects the database schema | Completed (100%) |
| Add `UserRepository` | Implement `UserRepository` in `backend/infra/database/repositories/user_repository.py` with methods: `get_by_id`, `get_by_username`, `create_user`, `update_user`, `list_users` | All user data access is encapsulated in the repository. No raw SQL or direct model queries outside the repository. | Completed (100%) |

#### 5B — Authentication service

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Implement password hashing utilities | Use `bcrypt` via `passlib[bcrypt]` for hashing. Add `hash_password(plain: str) -> str` and `verify_password(plain: str, hashed: str) -> bool` to `backend/domain/services/auth_service.py`. Plaintext passwords must never be stored or logged anywhere. | Passwords are hashed before storage and verified correctly on login. Raw passwords never persist beyond the service boundary. | Completed (100%) |
| Implement JWT token issuance | On successful login, issue a signed JWT with payload: `sub` (user id), `username`, `role`, `exp` (configurable TTL via `settings.py`, default 8 hours). Sign with `JWT_SECRET` loaded from environment. Use `python-jose[cryptography]` or `PyJWT`. | A short-lived, signed JWT is returned on successful login. Token payload includes all fields needed for authorization without a DB lookup on each request. | Completed (100%) |
| Implement JWT token validation | Add `decode_access_token(token: str) -> TokenPayload` that verifies the signature, checks expiry, and returns the decoded payload. Raise a typed exception on invalid or expired tokens. | Token validation is centralized and consistently applied. Expired or tampered tokens are rejected with a clear error. | Completed (100%) |
| Add `AuthService` | Implement `AuthService` in `backend/domain/services/auth_service.py` with `login(username, password) -> TokenResponse` that validates credentials via `UserRepository`, issues a JWT on success, and raises an `InvalidCredentialsError` on failure (do not distinguish between wrong username and wrong password in the error message). | Login logic is encapsulated and independently testable | Completed (100%) |
| Seed initial `super_user` account | Add a startup script or CLI command `monitoring-hub user create --username <name> --role super_user` that creates an initial admin user if none exists. Username and password sourced from environment variables or CLI prompt. | Every new deployment has at least one admin account from the start | Completed (100%) |

#### 5C — API auth middleware and endpoints

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Add `POST /auth/login` endpoint | Accept `{ "username": "...", "password": "..." }`. Delegate to `AuthService.login()`. Return `{ "access_token": "...", "token_type": "bearer", "expires_at": "..." }` on success. Return HTTP 401 with a generic message on failure — never reveal which field was wrong. | Login endpoint is functional and secure. Response shape matches the frontend contract documented in `docs/api/frontend-contract-v1.md`. | Completed (100%) |
| Add `GET /auth/me` endpoint | Return the current authenticated user's profile `{ "id": "...", "username": "...", "role": "..." }` decoded from the JWT. Requires valid Bearer token. | Frontend can fetch the current session identity and role after login | Completed (100%) |
| Add `require_auth` dependency | Implement a FastAPI dependency `require_auth(token: str = Depends(oauth2_scheme)) -> TokenPayload` that validates the JWT and returns the decoded payload. Raise HTTP 401 if the token is missing, invalid, or expired. | All protected routes validate the JWT consistently via a single dependency | Completed (100%) |
| Add `require_role` dependency | Implement `require_role(required_role: str)` as a higher-order FastAPI dependency. Inject `require_auth` and compare the user's role against the required role. Raise HTTP 403 if insufficient. | Role enforcement is declarative at the route level and independently testable | Completed (100%) |
| Apply role guards to write endpoints | Apply `require_role("super_user")` to all mutating endpoints: `POST /customers`, `PATCH /customers/{id}`, `DELETE /customers/{id}`, `POST /customers/{id}/accounts`, `PATCH /customers/{id}/accounts/{account_id}`, `DELETE /customers/{id}/accounts/{account_id}`. Read endpoints and check execution endpoints remain accessible to both roles. | `user`-role sessions are blocked from all data-mutating operations with HTTP 403. `super_user` retains full access. | Completed (100%) |
| Transition period: support API key + JWT in parallel | During transition, `require_auth` should accept either a valid JWT Bearer token OR a valid API key (for backward compatibility with existing integrations). Log a deprecation warning when an API key is used. | Existing API key integrations continue to work after Phase 5 is deployed, giving time for migration | Completed (100%) |

#### 5D — Frontend login flow

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Build `/login` page | Create a login page in the frontend at route `/login` with a username + password form. On submit, `POST /auth/login`. On success, store the JWT and redirect to the dashboard. On failure, display a generic error message. | Users can log in through the browser and receive a session token | Planned |
| Auth-aware API client | Update the frontend API client (`src/api/client.ts` or equivalent) to read the stored JWT and attach it as `Authorization: Bearer <token>` on every request. | All frontend API calls include the auth token automatically | Planned |
| Handle 401 responses globally | If any API response returns HTTP 401, clear the stored token and redirect the user to `/login`. | Expired or invalid sessions are handled gracefully without confusing error states | Planned |
| Role-aware UI | After login, fetch `GET /auth/me` and store the role in app state. Hide or disable write actions (create/update/delete customer, account) for `user`-role sessions. Show them only for `super_user`. | The UI accurately reflects the user's permission level. Unauthorized actions are not exposed, not just blocked server-side. | Planned |
| Token storage decision | Decide between `localStorage` (simpler, XSS risk) and `httpOnly` cookie (more secure, requires CSRF handling). Document the decision and its trade-offs. Default recommendation: `httpOnly` cookie set by the server on `/auth/login` response. | Token storage mechanism is documented and consistently applied | Planned |

#### 5E — API key deprecation

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Define deprecation timeline | Decide and document when API key auth will be fully removed (suggested: after Phase 5 is stable in production for 2+ weeks). Add a deprecation notice to the `X-API-Key` auth path in the code. | Deprecation timeline is explicit and tracked | Planned |
| Remove API key auth | Once the timeline is reached: remove `require_api_key`, `API_AUTH_ENABLED`, and `API_KEYS` from `settings.py` and all route dependencies. Update `docs/api/frontend-contract-v1.md` to reflect JWT-only auth. | Codebase has a single auth mechanism. No legacy API key paths remain. | Planned |
| Phase closure | Close Phase 5 after login flow, role enforcement, frontend auth, and API key deprecation are end-to-end validated. Update phase overview table and change log. | Phase 5 is officially complete | Planned |

#### 5F — Tests

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Unit test `AuthService.login` | Test successful login, wrong password, and unknown username. Verify that the error message is the same for both failure cases (no username/password enumeration). | Login logic is secure and correctly handles all credential scenarios | Completed (100%) |
| Unit test JWT issuance and validation | Test that issued JWTs decode to the correct payload, that expired tokens raise the correct error, and that tampered signatures are rejected. | JWT lifecycle is correctly handled end-to-end | Completed (100%) |
| Unit test `require_role` dependency | Test that `super_user` passes all role checks, that `user` is blocked from `super_user`-only routes with HTTP 403, and that missing tokens return HTTP 401. | Role enforcement logic is independently validated | Completed (100%) |
| Integration test login endpoint | Test `POST /auth/login` with valid and invalid credentials. Verify response shape, token presence, and error message consistency. | Login endpoint behaves correctly in a full request/response cycle | Completed (100%) |
| Integration test protected routes | Test that write endpoints (e.g., `POST /customers`) return 403 for `user`-role tokens and 200 for `super_user`-role tokens. | Route-level role enforcement is validated end-to-end | Completed (100%) |
| Integration test token expiry | Test that an expired JWT returns HTTP 401 on any protected endpoint. | Expired session handling is validated | Completed (100%) |

---

### Phase 6 - AWS connection layer

#### Design overview

This phase hardens the AWS connection layer by introducing an explicit per-account auth mode model, replacing the implicit profile-based session creation that currently exists. It also extends SSO expiry detection — currently only present in the TUI — into the API execution path with automatic Slack alerts.

**Auth boundary separation:**
- **App auth** — who can access the web application (implemented in Phase 5)
- **AWS auth** — how the program connects to each customer's AWS account (this phase)

These two layers are independent. AWS auth mode is a per-account property, not a per-user property.

**4 supported AWS auth modes:**

| Mode | How it works | Required fields | When to use |
|---|---|---|---|
| `assume_role` | Cross-account AssumeRole. Customer creates `MonitoringReadOnlyRole` in their account with a trust policy pointing to our base identity. Program calls `sts:AssumeRole` to obtain temporary credentials. | `role_arn`, `external_id` | **Default for all new customers.** Most secure — no long-lived credentials stored. |
| `sso` | Uses an SSO session configured in `~/.aws/config` via `sso_session` block. Credentials are obtained via AWS IAM Identity Center. | `profile_name` | Existing SSO customers (e.g., sadewa-sso, aryanoble-sso). |
| `aws_login` | Standard AWS profile configured via `aws configure`. Uses long-lived credentials stored in `~/.aws/credentials`. No SSO involved. | `profile_name` | Non-SSO customers with static profile config (e.g., NIKP). |
| `access_key` | Direct `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` stored in the database (encrypted at rest). Use only when profile-based methods are not feasible. | `access_key_id`, `secret_access_key` | Legacy or last-resort configurations only. |

**Base identity (program's own AWS identity):**
- Local development: a named profile in `~/.aws/config` (e.g., `ics-monitor`)
- Production (future): EC2/ECS Instance Profile — zero credential storage

**External ID requirement for `assume_role`:**
Every `assume_role` account must have a unique `external_id` stored in the database. It is included in the `sts:AssumeRole` call and must match the trust policy condition in the customer's account. This prevents the [confused deputy problem](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html).

**`access_key` security note:**
`access_key_id` and `secret_access_key` are stored encrypted in the database using an application-level encryption key (`ENCRYPT_KEY` from environment). They must never be logged or returned in any API response. Migration to AWS Secrets Manager is deferred to a future phase.

#### 6A — Database schema

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Add auth mode fields to accounts table | Add columns `aws_auth_mode` (string, not null, default `aws_login`), `role_arn` (nullable string), `external_id` (nullable string), `access_key_id` (nullable encrypted string), `secret_access_key` (nullable encrypted string) to the `accounts` table | Database schema supports all 4 auth modes with correct nullability constraints | Planned |
| Write Alembic migration | Create a forward-only Alembic migration that adds the new columns with safe defaults. Must not alter or drop any existing column. | Migration runs cleanly on existing databases without breaking any existing account records | Planned |
| Backfill existing accounts | Set `aws_auth_mode` on all existing accounts based on their current connection type. SSO-based profiles → `sso`; standard profiles → `aws_login`. Do not set `assume_role` on existing accounts unless manually verified. | All existing accounts have a valid, non-null `aws_auth_mode` value after migration | Planned |
| Update SQLAlchemy `Account` model | Add the new columns to `backend/infra/database/models.py` `Account` class with correct types and nullability | ORM model reflects the new schema accurately | Planned |

#### 6B — Auth resolver

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Implement `resolve_boto3_session(account)` | Replace the placeholder stub in `backend/infra/cloud/aws/auth.py` with a full resolver function. Accepts an `Account` model instance, returns a valid `boto3.Session` based on `aws_auth_mode`. | `resolve_boto3_session(account) -> boto3.Session` works correctly for all 4 modes and raises a descriptive error for misconfigured accounts | Planned |
| Implement `assume_role` session flow | For `assume_role` mode: obtain base session → call `sts.assume_role(RoleArn=role_arn, RoleSessionName="MonitoringHub", ExternalId=external_id)` → construct `boto3.Session` from returned temporary credentials. | `assume_role` mode produces a valid cross-account session with scoped temporary credentials | Planned |
| Implement `access_key` session flow | For `access_key` mode: decrypt `access_key_id` and `secret_access_key` from the account record using the application encryption key, then construct `boto3.Session(aws_access_key_id=..., aws_secret_access_key=...)`. Decrypted values must not be logged. | `access_key` mode produces a valid session without exposing credentials in logs or responses | Planned |
| Add per-mode field validation | Before creating any session, validate that all required fields for the selected mode are present and non-empty. Raise `ValueError` with a descriptive message identifying the missing field and mode. | Invalid auth configurations are caught before any boto3 call, with a clear actionable error message | Planned |
| Add base identity resolver | Implement `get_base_session()` used by `assume_role` mode. For local dev: reads from a configurable profile name in `settings.py`. For production: falls back to the default boto3 credentials chain (Instance Profile). | Base session resolves correctly in both local and production environments | Planned |

#### 6C — Wire auth resolver into CheckExecutor

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Replace profile-based boto3 session creation | In `backend/domain/services/check_executor.py`, replace all `boto3.Session(profile_name=account.profile_name)` calls with `resolve_boto3_session(account)`. | All check executions go through the auth resolver. No hardcoded profile-based session creation remains in the executor. | Planned |
| Add auth mode error classification | In `backend/checks/common/aws_errors.py`, extend classification to handle: `sso_expired` (SSO token expired), `assume_role_failed` (AssumeRole rejected), `invalid_credentials` (access_key rejected), `no_config` (missing required fields). Each class includes an actionable message. | Auth errors from any mode are classified consistently and surfaced with actionable context | Planned |
| Propagate auth error to check result | When `resolve_boto3_session` raises or an auth-related boto3 error is caught, mark the check result `status=ERROR` with the classified error message as `summary` and `login_command` (where applicable) in `output`. | Operators can identify auth problems directly from the check result without inspecting backend logs | Planned |

#### 6D — SSO expiry handling in the API execution path

Currently SSO expiry detection only exists in the TUI. This sub-area extends it to the API execution path.

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Detect SSO expiry during API check execution | Extend `aws_errors.py` to recognize SSO expiry signals in the boto3 exception hierarchy (`ExpiredTokenException`, `Unable to load SSO token`, `Token has expired`). Tag classified errors with `error_class = "sso_expired"`. | SSO expiry during API-triggered check execution is detected with the same accuracy as in the TUI path | Planned |
| Auto-send Slack notification on SSO expiry | In `CheckExecutor`, after processing results, check if any result has `error_class = "sso_expired"`. If so, retrieve the customer's Slack config and send an alert via `send_to_webhook` including: expired profile name, SSO session name, and `login_command`. | Operators receive an automatic Slack alert with actionable login command on SSO expiry — no manual `/sessions/health` trigger required | Planned |
| Include `login_command` in API error response | When a check result has `error_class = "sso_expired"`, include the `login_command` string in the result's `output` field. | Frontend can display the exact command the operator needs to restore the session | Planned |
| Add `error_class` field to check result response | Extend `CheckResult` response schema with an optional `error_class` field (`sso_expired`, `assume_role_failed`, `invalid_credentials`, `no_config`). | Frontend can programmatically distinguish auth errors from check logic errors and render targeted error UI | Planned |

#### 6E — Onboarding defaults and API contract

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Set `assume_role` as default `aws_auth_mode` for new accounts | When creating a new account via `POST /customers/{id}/accounts`, default `aws_auth_mode` to `assume_role` if not explicitly provided. | All new accounts have an explicit auth mode from creation. Operators are nudged toward the most secure option. | Planned |
| Add server-side validation for auth mode fields | On account create and update, validate that required fields for the selected mode are present. `assume_role` requires `role_arn` and `external_id`; `access_key` requires `access_key_id` and `secret_access_key`. Return HTTP 422 with a field-level error on failure. | Misconfigured accounts cannot be saved. The error response clearly identifies which field is missing and why. | Planned |
| Update account API request/response schema | Add `aws_auth_mode`, `role_arn`, `external_id` to the `Account` response schema and `PATCH` request body. `access_key_id` and `secret_access_key` are write-only — never returned in any response. | Frontend can read and update auth mode for any account. Sensitive credentials are never exposed through the API. | Planned |
| Update `docs/api/frontend-contract-v1.md` | Document the updated `Account` object shape, `error_class` on check results, and `PATCH` account request body with auth mode fields. | Frontend integration has accurate and complete contract reference for Phase 6 changes. | Planned |

#### 6F — Ops runbook

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Document `MonitoringReadOnlyRole` setup guide | Write a step-by-step guide for setting up `MonitoringReadOnlyRole` in a customer's AWS account. Include: trust policy JSON with `external_id` condition, required IAM permissions (ReadOnly + specific service actions: GuardDuty, CostExplorer, CloudWatch, Backup, Health, Budgets), and how to obtain the `external_id` from the database. | Operators have a clear, self-contained guide for onboarding new `assume_role` customers | Planned |
| Document auth mode selection guide | Write a decision table explaining when to use each auth mode and what fields to configure. | Operators can determine the correct auth mode for any new customer without guessing | Planned |
| Document SSO login commands per mode | `sso` mode: `aws sso login --sso-session <session>`. `aws_login` mode: `aws configure --profile <profile>`. Commands must match what is surfaced in `login_command` in API responses and Slack alerts. | Runbook commands are consistent with what the system surfaces automatically | Planned |

#### 6G — Tests

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Unit test resolver — all 4 modes | Test `resolve_boto3_session` for each auth mode with valid input. Mock `boto3.Session` and `sts.assume_role`. | Resolver produces the correct session type for each mode. All 4 paths are independently tested. | Planned |
| Unit test resolver — validation errors | Test that `resolve_boto3_session` raises `ValueError` with a descriptive message for each invalid configuration (e.g., `assume_role` with missing `role_arn`). | Misconfiguration is caught at the resolver level before any network call | Planned |
| Unit test SSO expiry classification | Test that `aws_errors.py` correctly classifies all known SSO expiry exception patterns as `sso_expired`, including edge cases and mixed-case error messages. | Error classification is robust against boto3 exception format variations | Planned |
| Unit test Slack auto-notification on expiry | Test that `CheckExecutor` triggers a Slack notification when any result has `error_class = "sso_expired"` and Slack is enabled. Test that no notification fires when Slack is disabled. | Auto-notification behavior is deterministic | Planned |
| Integration test — account auth mode CRUD | Test `POST` and `PATCH` account endpoints for all 4 modes. Verify HTTP 422 on missing required fields. Verify sensitive fields are absent from all GET/PATCH responses. | Auth mode CRUD is correct end-to-end. Credential fields are never leaked. | Planned |
| Integration test — check execution with `assume_role` | Test a full check execution cycle with an `assume_role` account. Mock `sts.assume_role` to return temporary credentials. Verify those credentials are used. | `assume_role` flow is exercised end-to-end in a controlled environment | Planned |
| Phase closure | Close Phase 6 after all sub-areas are implemented and tests pass. Update phase overview table and change log. | Phase 6 is officially complete | Planned |

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
- 2026-03-21: Completed full runtime/test cutover from `src/*` to `backend/*`, removed tracked `src/*` python modules, and updated architecture docs/tests accordingly.
- 2026-03-21: Rewrote Phase 5 as app auth (user model, JWT, roles, frontend login flow) and Phase 6 as AWS connection layer (auth mode model, resolver, SSO expiry in API path). Both phases now use detailed sub-area tables. Updated frontend-contract-v1.md with accounts/auth-mode schema, sessions/health contract, error_class field, and Phase 5 app auth endpoints.
- 2026-03-21: Phase 5 implementation complete through 5C — User model, Alembic migration (c7f8a9b2d3e4), AuthService (bcrypt + JWT), UserRepository, /auth/login, /auth/me, require_auth, require_role, role guards on customer write endpoints. All 295 existing tests pass.
- 2026-03-21: Phase 5F complete — 27 auth tests added (test_auth_service.py, test_auth_routes.py) covering password hashing, JWT lifecycle, login endpoint, require_role enforcement, customer write guards, and token expiry. Fixed passlib+bcrypt 5.0 incompatibility by switching to direct bcrypt API. Updated e2e tests with JWT auth headers. 337 tests pass.
