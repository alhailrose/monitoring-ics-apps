# Frontend API Contract v1

This document defines the stable API contract consumed by the frontend.

## Base

- Prefix: `/api/v1`
- Auth: API key (when `API_AUTH_ENABLED=true`)

## Run checks

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
  "results": [],
  "consolidated_outputs": {"<customer-id>": "..."},
  "backup_overviews": {}
}
```

## History

### `GET /history?customer_id=<id>&limit=50&offset=0`

Returns paginated check run history.

### `GET /history/{check_run_id}`

Returns full run detail and per-account results.

## Findings (normalized)

### `GET /findings`

Query params:

- `customer_id` (required)
- `check_name` (optional): `guardduty|cloudwatch|notifications`
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

## Compatibility note

- TUI remains non-persistent and does not write finding history.
- Findings endpoints return data from API-managed persistent runs only.
