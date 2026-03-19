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

## Compatibility note

- TUI remains non-persistent and does not write finding history.
- Findings and metrics endpoints return data from API-managed persistent runs only.
- Backup-focused query shortcut:
  - `check_name=backup&severity=ALARM` -> backup failures/expired alerts
  - `check_name=backup&severity=INFO` -> successful backup events
