# Frontend API Contract v1

This document defines the stable API contract consumed by the frontend.

## Base

- Prefix: `/api/v1`
- Auth: API key (when `API_AUTH_ENABLED=true`)

## Runs

### `POST /checks/execute`

Request:

```json
{
  "customer_ids": ["<customer-id>"],
  "mode": "single",
  "check_name": "guardduty",
  "account_ids": ["<account-id>"],
  "send_slack": false
}
```

Response:

```json
{
  "check_runs": [
    {"customer_id": "<customer-id>", "check_run_id": "<run-id>", "slack_sent": false}
  ],
  "execution_time_seconds": 1.23,
  "results": [
    {
      "customer_id": "<customer-id>",
      "account": {
        "id": "<account-id>",
        "profile_name": "connect-prod",
        "display_name": "Connect Prod"
      },
      "check_name": "guardduty",
      "status": "OK",
      "summary": "No findings",
      "output": "No findings"
    }
  ],
  "consolidated_outputs": {"<customer-id>": "..."},
  "backup_overviews": {}
}
```

### `GET /history?customer_id=<id>&limit=50&offset=0`

Returns paginated check run history.

Response:

```json
{
  "total": 1,
  "items": [
    {
      "check_run_id": "run-1",
      "check_mode": "single",
      "check_name": "guardduty",
      "created_at": "2026-03-19T10:00:00+00:00",
      "execution_time_seconds": 1.23,
      "slack_sent": false,
      "results_summary": {
        "total": 1,
        "ok": 1,
        "warn": 0,
        "error": 0
      }
    }
  ]
}
```

### `GET /history/{check_run_id}`

Returns full run detail and per-account results.

### `GET /history/{check_run_id}/report`

Returns regenerated text report for a completed run.

## Findings

### `GET /findings`

Query params:

- `customer_id` (required)
- `check_name` (optional): `guardduty|cloudwatch|notifications|backup`
- `severity` (optional): `INFO|LOW|MEDIUM|HIGH|CRITICAL|ALARM`
- `account_id` (optional)
- `limit` (optional, default `50`, max `200`)
- `offset` (optional, default `0`)

Response:

```json
{
  "total": 1,
  "items": [
    {
      "id": "fe-1",
      "check_run_id": "run-1",
      "account": {
        "id": "acc-1",
        "profile_name": "connect-prod",
        "display_name": "Connect Prod"
      },
      "check_name": "guardduty",
      "finding_key": "gd:1",
      "severity": "HIGH",
      "title": "Privilege escalation",
      "description": "Suspicious iam activity",
      "created_at": "2026-03-19T10:00:00+00:00"
    }
  ]
}
```

## Metrics

### `GET /metrics`

Query params:

- `customer_id` (required)
- `check_name` (optional, currently `daily-arbel`)
- `metric_name` (optional)
- `metric_status` (optional)
- `account_id` (optional)
- `limit` (optional, default `50`, max `200`)
- `offset` (optional, default `0`)

Response:

```json
{
  "total": 1,
  "items": [
    {
      "id": "ms-1",
      "check_run_id": "run-1",
      "account": {
        "id": "acc-1",
        "profile_name": "connect-prod",
        "display_name": "Connect Prod"
      },
      "check_name": "daily-arbel",
      "metric_name": "CPUUtilization",
      "metric_status": "warn",
      "value_num": 88.0,
      "unit": "Percent",
      "resource_role": "writer",
      "resource_id": "db-1",
      "resource_name": "db-1",
      "service_type": "rds",
      "section_name": "Primary",
      "created_at": "2026-03-19T10:03:00+00:00"
    }
  ]
}
```

## Dashboard

### `GET /dashboard/summary?customer_id=<id>&window_hours=24`

Returns aggregated run/result/finding/metric summary for dashboard widgets.

Response:

```json
{
  "customer_id": "cust-1",
  "window_hours": 24,
  "generated_at": "2026-03-19T10:10:00+00:00",
  "since": "2026-03-18T10:10:00+00:00",
  "runs": {
    "total": 3,
    "single": 2,
    "all": 1,
    "arbel": 0,
    "latest_created_at": "2026-03-19T10:05:00+00:00"
  },
  "results": {
    "total": 5,
    "ok": 4,
    "warn": 1,
    "error": 0,
    "alarm": 0,
    "no_data": 0
  },
  "findings": {
    "total": 1,
    "by_severity": {
      "HIGH": 1
    }
  },
  "metrics": {
    "total": 1,
    "by_status": {
      "warn": 1
    }
  },
  "top_checks": [
    {
      "check_name": "guardduty",
      "runs": 2
    }
  ]
}
```

## Customers and Accounts

### `GET /customers`

Returns all customers with their accounts.

Response:

```json
[
  {
    "id": "<customer-id>",
    "name": "aryanoble",
    "display_name": "Aryanoble",
    "checks": ["cost", "guardduty", "cloudwatch", "notifications", "backup", "daily-arbel"],
    "slack_enabled": true,
    "slack_channel": "#aws-alerts",
    "accounts": [
      {
        "id": "<account-id>",
        "profile_name": "aryanoble-prod",
        "account_id": "123456789012",
        "display_name": "Aryanoble Prod",
        "is_active": true,
        "aws_auth_mode": "sso",
        "role_arn": null,
        "external_id": null,
        "config_extra": {}
      }
    ]
  }
]
```

### `PATCH /customers/{customer_id}/accounts/{account_id}`

Update account fields including auth mode configuration.

Request:

```json
{
  "display_name": "Aryanoble Prod",
  "is_active": true,
  "aws_auth_mode": "assume_role",
  "role_arn": "arn:aws:iam::123456789012:role/MonitoringReadOnlyRole",
  "external_id": "<unique-external-id-from-db>"
}
```

Auth mode field rules:

| `aws_auth_mode` | Required fields | Optional fields |
|---|---|---|
| `assume_role` | `role_arn`, `external_id` | — |
| `sso` | `profile_name` (already on account) | — |
| `aws_login` | `profile_name` (already on account) | — |
| `access_key` | `access_key_id`, `secret_access_key` (write-only) | — |

**Security note:** `access_key_id` and `secret_access_key` are write-only fields. They are accepted on `POST`/`PATCH` but never returned in any `GET` response or list endpoint. `role_arn` and `external_id` are readable.

Response: updated `Account` object (same shape as in `GET /customers`, without sensitive credential fields).

Validation errors (HTTP 422):

```json
{
  "detail": [
    {
      "field": "role_arn",
      "message": "role_arn is required when aws_auth_mode is assume_role"
    }
  ]
}
```

---

## Sessions and Profiles

### `GET /profiles`

Detects AWS profiles from the local `~/.aws/config` file. Used by the frontend to populate profile selectors when creating or editing accounts.

Response:

```json
{
  "profiles": [
    {
      "profile_name": "aryanoble-prod",
      "sso_session": "aryanoble-sso",
      "region": "ap-southeast-1"
    },
    {
      "profile_name": "nikp-prod",
      "sso_session": null,
      "region": "ap-southeast-1"
    }
  ]
}
```

### `GET /sessions/health`

Checks credential validity for all active account profiles. Detects expired SSO sessions and groups results by SSO session name.

Query params:
- `customer_id` (optional) — filter to a specific customer's accounts
- `notify` (optional, bool, default `false`) — if `true`, sends a Slack notification for any expired sessions

Response:

```json
{
  "total_profiles": 5,
  "ok": 4,
  "expired": 1,
  "error": 0,
  "profiles": [
    {
      "profile_name": "sadewa-prod",
      "account_id": "123456789012",
      "display_name": "Sadewa Prod",
      "status": "ok",
      "error": "",
      "sso_session": "sadewa-sso",
      "login_command": "aws sso login --sso-session sadewa-sso"
    },
    {
      "profile_name": "aryanoble-prod",
      "account_id": "987654321098",
      "display_name": "Aryanoble Prod",
      "status": "expired",
      "error": "SSO session expired. Run: aws sso login --sso-session aryanoble-sso",
      "sso_session": "aryanoble-sso",
      "login_command": "aws sso login --sso-session aryanoble-sso"
    }
  ],
  "sso_sessions": {
    "aryanoble-sso": {
      "session_name": "aryanoble-sso",
      "login_command": "aws sso login --sso-session aryanoble-sso",
      "status": "expired",
      "profiles_ok": [],
      "profiles_expired": ["aryanoble-prod"],
      "profiles_error": []
    }
  }
}
```

**Profile status values:**

| Status | Meaning | Action required |
|---|---|---|
| `ok` | Credentials valid | None |
| `expired` | SSO token expired | Run `login_command` |
| `no_config` | Profile not found in `~/.aws/config` | Check AWS config |
| `error` | Unexpected AWS error | Check logs |

---

## Auth errors in check results (Phase 5+)

When a check result fails due to an AWS authentication error, the result includes an `error_class` field to enable targeted UI rendering.

Example — SSO expired result:

```json
{
  "account": {
    "id": "<account-id>",
    "profile_name": "aryanoble-prod",
    "display_name": "Aryanoble Prod"
  },
  "check_name": "guardduty",
  "status": "ERROR",
  "summary": "SSO session expired. Run: aws sso login --sso-session aryanoble-sso",
  "output": "SSO session expired. Run: aws sso login --sso-session aryanoble-sso",
  "error_class": "sso_expired"
}
```

**`error_class` values:**

| Value | Meaning | Suggested frontend treatment |
|---|---|---|
| `sso_expired` | SSO token expired during check | Show "Login required" badge + `login_command` |
| `assume_role_failed` | `sts:AssumeRole` was rejected | Show "Access denied" badge + contact admin |
| `invalid_credentials` | `access_key` credentials rejected | Show "Invalid credentials" badge |
| `no_config` | Required auth fields missing on account | Show "Not configured" badge + link to account settings |
| `null` / absent | Non-auth error (check logic failure) | Show standard error state |

---

## App auth endpoints (Phase 5 — planned)

> These endpoints do not exist yet. They will be added in Phase 5. This section documents the planned contract for frontend preparation.

### `POST /auth/login`

Request:

```json
{
  "username": "admin",
  "password": "your-password"
}
```

Response:

```json
{
  "access_token": "<jwt-token>",
  "token_type": "bearer",
  "expires_at": "2026-04-01T00:00:00+00:00"
}
```

Error (HTTP 401):

```json
{
  "detail": "Invalid username or password"
}
```

### `GET /auth/me`

Returns the current authenticated user's profile. Requires `Authorization: Bearer <token>` header.

Response:

```json
{
  "id": "<user-id>",
  "username": "admin",
  "role": "super_user"
}
```

**Roles:**

| Role | Permissions |
|---|---|
| `super_user` | Full access: read, write, delete, execute checks |
| `user` | Read-only + execute checks. Cannot create/update/delete customers or accounts. |

---

## Compatibility note

- TUI remains non-persistent and does not write finding history.
- Findings and metrics endpoints return data from API-managed persistent runs only.
- Backup-focused query shortcut:
  - `check_name=backup&severity=ALARM` -> backup failures/expired alerts
  - `check_name=backup&severity=INFO` -> successful backup events
- App auth (`/auth/login`, `/auth/me`, JWT Bearer tokens) is a Phase 5 addition. Before Phase 5, API key auth via `X-API-Key` header remains the only authentication method.
- `aws_auth_mode` and auth-related account fields are Phase 6 additions. Before Phase 6, all accounts implicitly use `profile_name`-based sessions.
