# Discovery-Driven Check Optimization — Design Spec

**Date:** 2026-03-26
**Status:** Approved

---

## Overview

Two improvements that use the per-account `config_extra["_discovery"]` data (stored by the auto-discovery feature) to make existing checks smarter and reduce unnecessary AWS API calls.

1. **`ec2_utilization` region optimization** — use stored discovery data to skip `describe_regions` and `describe_instances`, falling back to live calls if data is absent.
2. **`daily-arbel` DB migration** — replace YAML/hardcoded `ACCOUNT_CONFIG` with `AccountCheckConfig` rows; use AWS Name tag as display label (no manual role mapping).

---

## Part 1: `ec2_utilization` Region Optimization

### Problem

Every run, `AWSUtilization3CoreChecker` calls `describe_regions` to find enabled regions, then `describe_instances` across all of them. For accounts with many regions, this is slow and wasteful when instance topology is stable.

### Solution

Before making any AWS calls, check `account.config_extra["_discovery"]["ec2_instances"]`. If present:

- Extract unique `region` values → pass as `profile_regions` (already supported by checker constructor) to skip `describe_regions`
- Use stored instance list directly (id, name, type, region, platform) → skip `describe_instances` entirely
- `platform` field from discovery maps to `os_type` for the Windows disk metric fix

Fallback: if `_discovery` is absent, empty, or older than a configurable threshold (default: no threshold enforced — always use if present), fall back to existing live behavior.

### Data Flow

```
check_executor reads account.config_extra["_discovery"]
  → if ec2_instances present:
      → inject profile_regions=[unique regions] + instance_list=[stored instances]
      → checker skips describe_regions + describe_instances
      → proceeds to CloudWatch metric fetch per instance
  → else:
      → checker runs existing live describe_instances flow
```

### Checker Changes (`aws_utilization_3core.py`)

- Accept `instance_list: list[dict] | None = None` kwarg in `__init__`
- If `instance_list` is provided, skip `_discover_instances()` and use it directly
- `profile_regions` kwarg already wired; executor passes it from discovery regions

### Executor Changes (`check_executor.py`)

- Before building kwargs for `ec2_utilization` check: inspect `account.config_extra.get("_discovery", {}).get("ec2_instances", [])`
- If non-empty: add `profile_regions` and `instance_list` to kwargs

### Risks

- Stale data: new EC2 instances added after last discovery won't appear until Re-discover is run. Acceptable — user controls discovery timing; fallback guarantees correctness for fresh accounts.

---

## Part 2: `daily-arbel` DB Migration

### Problem

`DailyArbelChecker` reads instance IDs, cluster IDs, metrics, and thresholds from:
- YAML (`aryanoble.yaml`) via `ACCOUNT_CONFIG` hardcoded dict
- Manual role mapping (`writer`/`reader` labels assigned per instance ID)

This means adding a new account requires YAML edits and code changes. It also doesn't scale to non-Aryanoble customers.

### Solution

Store all `daily-arbel` config in `AccountCheckConfig` (table already exists, already merged into check kwargs by executor). Use AWS Name tag (from `config_extra["_discovery"]` or live describe) as the display label — no manual role mapping.

### Config Schema (stored in `AccountCheckConfig.config` JSON)

```json
{
  "sections": [
    {
      "section_name": "My Account RDS",
      "service_type": "rds",
      "cluster_id": "my-prod-rds",
      "instance_ids": ["my-prod-rds-writer", "my-prod-rds-reader"],
      "metrics": ["ServerlessDatabaseCapacity", "FreeableMemory", "DatabaseConnections"],
      "thresholds": {
        "FreeableMemory": 21474836480,
        "ServerlessDatabaseCapacity": 24
      }
    },
    {
      "section_name": "My Account EC2",
      "service_type": "ec2",
      "instance_ids": ["i-0abc123", "i-0def456"],
      "metrics": ["CPUUtilization", "NetworkIn", "NetworkOut"],
      "thresholds": {
        "CPUUtilization": 80
      }
    }
  ]
}
```

Rules:
- `sections` is always a list (even if only one section)
- `service_type`: `"rds"` or `"ec2"`
- `cluster_id`: RDS only, optional (for serverless/provisioned clusters)
- `instance_ids`: list of RDS instance identifiers or EC2 instance IDs
- `thresholds`: metric name → numeric threshold (unified across all instances in section, no per-instance overrides)
- `section_name`: display label in report

### Instance Display Names

- **EC2**: use `instance_names` from `_discovery.ec2_instances` (keyed by instance ID → AWS Name tag). No manual mapping needed.
- **RDS**: use instance identifier directly as display name (already human-readable in most cases).

### Checker Changes (`daily_arbel.py`)

- Remove all `ACCOUNT_CONFIG` / YAML references
- Remove `find_customer_account` import
- `__init__` receives `sections: list[dict]` from kwargs (injected by executor via `AccountCheckConfig`)
- Iterate sections: for each section, run existing metric fetch logic, emit report section
- Instance display name: for EC2, look up Name tag from `_discovery` (passed via executor or fetched via `describe_instances` tag filter)

### Migration

Existing Aryanoble accounts have YAML config. Migration path:
1. Write a migration script (or extend the `/reimport` endpoint) that reads YAML `daily_arbel` + `daily_arbel_extra` blocks and creates corresponding `AccountCheckConfig` rows
2. After migration confirmed working, remove `ACCOUNT_CONFIG` from checker

### Executor Changes (`check_executor.py`)

None needed — executor already merges `AccountCheckConfig.config` into kwargs. `sections` will arrive as a kwarg automatically.

---

## Out of Scope

- `alarm_verification` (`cloudwatch` check) — already reads from DB, no changes needed
- `guardduty`, `cost`, `notifications`, `backup` — work at account level, no instance config needed
- Role-specific thresholds (e.g., different `FreeableMemory` limit for reader vs writer) — removed intentionally; unified thresholds per section simplify the model
- Automatic threshold suggestions from discovery data

---

## Implementation Order

1. `ec2_utilization` optimization (smaller scope, immediate benefit, no migration needed)
2. `daily-arbel` migration (larger, requires migration script for existing data)
