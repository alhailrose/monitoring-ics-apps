# Next Session Handoff Prompt

Continue backend planning from the existing project context.

## Source of Truth

1. `docs/development/backend-development-plan.md` (primary plan, checklist, auth design)
2. `docs/PROJECT.md`
3. `docs/api/frontend-contract-v1.md`
4. `README.md`

---

## Non-Negotiable Architecture

### Authentication Layers

- **App Auth**
  - user login
  - roles: `super_user` (admin), `user` (readonly)

- **AWS Auth (per customer)**
  - `access_key`
  - `assume_role`
  - `sso`

Important:

- AWS auth is per customer, NOT per app user
- App users NEVER own AWS credentials
- System accesses AWS using customer connection

---

### AWS Rules

- New customers -> `assume_role` (`MonitoringReadOnlyRole`)
- Existing customers -> `sso` or `access_key` allowed

### SSO Expiry Handling

- Detect expiration
- Send Slack notification
- Admin executes:

```bash
aws sso login --profile <profile> --use-device-code --no-browser
```

---

## Backend Operating Model

- Canonical implementation: `backend/*`
- `src/*` = compatibility layer only
- API path = DB persistent
- TUI path = local (YAML-based)
- Backend config source of truth = database
- TUI config source of truth = customer YAML

---

## Production Stack

- PostgreSQL
- Redis
- AWS Secrets Manager

---

## Current Status

- Phases 0-4 completed
- API/frontend contract tests exist and were passing at handoff

---

## Task for This Session

- Continue / extend the next feature development plan ONLY
- Maintain consistency with architecture and auth boundaries
- DO NOT redesign existing structure unless explicitly requested

---

If needed, you may ask 1-2 clarifying questions before proceeding.
