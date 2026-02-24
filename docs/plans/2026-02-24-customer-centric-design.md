# Customer-Centric Slack Reporting & Config Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make "customer" the first-class entity for check execution and Slack delivery, replacing profile-centric routing.

**Architecture:** Customer YAML configs define accounts, checks, Slack channel. CLI `--customer` flag runs configured checks per customer, displays results, then prompts operator to send to Slack. Generic checks (`--check`, `--all`) stay unchanged.

**Tech Stack:** Python, boto3, questionary (prompts), pyyaml, existing rich CLI output

---

## Problem

Current model routes by SSO profile group, not by customer. One SSO group can serve multiple customers, and Slack routing is per-report-type, not per-customer. This makes it impossible to send customer-specific reports to customer-specific Slack channels.

## Design

### 1. Customer Config Schema

Each customer gets `configs/customers/<customer_id>.yaml`:

```yaml
customer_id: aryanoble
display_name: Aryanoble

slack:
  webhook_url: "https://hooks.slack.com/services/XXX/YYY/ZZZ"
  channel: "#aryanoble-monitoring"
  enabled: true

checks:
  - daily-arbel
  - daily-budget
  - backup

accounts:
  - profile: cis-erha
    account_id: "451916275465"
    display_name: "CIS ERHA"
    daily_arbel:
      cluster_id: cis-prod-rds
      # ... per-account check config
```

Key fields:
- `slack`: one webhook/channel per customer, `enabled` flag to toggle
- `checks`: which checks to run when using `--customer` (customer-specific only)
- `accounts`: existing shape, backward compatible

### 2. CLI Changes

New flags:
```bash
# Run configured checks for a customer, prompt to send Slack
monitoring-hub --customer aryanoble

# Scaffold new customer config
monitoring-hub customer init <customer_id>

# List configured customers
monitoring-hub customer list

# Validate customer config
monitoring-hub customer validate <customer_id>
```

Existing flags unchanged: `--check`, `--all`, `--group`, `--profile`, `--send-slack`

### 3. Customer Runner Flow

`run_customer_checks(customer_id, region, workers)`:
1. Load customer config from `configs/customers/<customer_id>.yaml`
2. For each check in `config.checks`:
   - For each account in `config.accounts`:
     - Run `checker.check(profile, account_id)` in parallel
3. Format + display results (same `format_report()` as today)
4. Interactive prompt: `Kirim report ke Slack {display_name} ({channel})? [y/n]`
5. If yes: send aggregated report to customer's webhook

### 4. Customer Config Management

`monitoring-hub customer init <name>` creates scaffold:
```yaml
customer_id: <name>
display_name: <NAME>

slack:
  webhook_url: ""
  channel: ""
  enabled: false

checks: []

accounts: []
```

Operator edits YAML to add accounts, checks, Slack config.

### 5. Slack Delivery per Customer

New function `send_customer_report_to_slack(customer_config, reports)`:
- Reads webhook_url from customer config (not global config)
- Sends aggregated report text to customer's channel
- Returns (sent: bool, reason: str)

### 6. What Stays the Same

- All output formats (WA text, console, report structure) — untouched
- `--check`, `--all`, `--group`, `--profile` flags — unchanged
- `format_report()` methods — unchanged
- TUI interactive mode — unchanged (can add customer menu later)
- Generic checks work with profiles/groups as before

### 7. CIS ERHA Metrics Update (done)

Updated `aryanoble.yaml` to match actual CloudWatch dashboard alarms:
- Added `ServerlessDatabaseCapacity` (> 24 ACU)
- Added `BufferCacheHitRatio` (< 90%)
- Reader FreeableMemory threshold: 18 GB (via `role_thresholds`)
- Checker updated to evaluate both new metrics

### 8. Files to Create/Modify

Create:
- `src/core/runtime/customer_runner.py` — customer check orchestration + Slack prompt
- `src/app/cli/customer_comm— `init`, `list`, `validate` subcommands

Modify:
- `src/app/cli/bootstrap.py` — add `--customer` flag + `customer` subcommand routing
- `src/configs/loader.py` — add `load_customer_config(customer_id)`, `list_customers()`
- `src/configs/schema/validator.py` — add customer config validation (slack, checks, accounts)
- `src/integrations/slack/notifier.py` — add `send_to_customer_webhook(webhook_url, report)`
- `configs/customers/aryanoble.yaml` — add `slack` and `checks` sections

Tests:
- `tests/unit/test_customer_runner.py` — customer check flow
- `tests/unit/test_customer_commands.py` — init/list/validate
- `tests/unit/test_customer_config_validation.py` — schema validation
