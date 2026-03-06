# TUI Customer Mapping and Check Assignment Design

**Date:** 2026-03-05
**Status:** Approved for implementation

## Goal

Make TUI customer operations match web-style workflow for profile mapping and check assignment, while keeping TUI independent from web DB/API.

## Decision

Use `configs/customers/*.yaml` as the TUI source of truth.

- Keep TUI runtime lightweight (no DB dependency).
- Keep compatibility with existing `Customer Report` and CLI commands.
- Add interactive tooling to reduce manual YAML edits.

## Scope

### In Scope

- Add customer management actions for:
  - scanning AWS local profiles
  - assigning profile -> customer account mapping
  - setting default checks per customer
- Update customer-related TUI flow to only use customer mapping lists.
- Remove local-profile source option from customer report path.
- Change multiselect defaults to unselected.
- Add explicit `Select All` / `Clear All` options.
- Add simple search input before selection lists.

### Out of Scope

- Migrating TUI customer flow to DB-backed storage.
- Replacing existing web API behavior.
- Changing Aryanoble-specific checker business logic.

## Current State

- Customer execution flow reads YAML customer configs via `src/configs/loader.py`.
- Customer run flow is in `src/app/tui/flows/customer.py`.
- Generic profile picker is in `src/app/tui/common.py` and includes local profile source.
- CLI customer management supports `init`, `list`, and `validate` only.

## Proposed UX

## 1) Customer report selection behavior

- Customer checks multiselect default: no preselected checks.
- Customer accounts multiselect default: no preselected accounts.
- Before each list selection, user can:
  - filter by keyword (case-insensitive contains)
  - choose `Select All` or `Clear All`

## 2) Profile source behavior

- In customer-related reporting flow, remove local profile source option.
- Only use profile lists from configured customer mappings.

## 3) Customer setup operations

New customer management actions:

- `scan`: list all AWS local profiles and show mapped/unmapped status based on YAML.
- `assign <customer_id>`: add chosen profiles to `accounts` for target customer.
  - attempt `account_id` detection via STS
  - fallback to empty/manual value if STS unavailable
  - prevent accidental duplicate mapping (warn and require explicit overwrite path)
- `checks <customer_id>`: interactive selection of customer default checks from `AVAILABLE_CHECKS`.

## Data and Validation Rules

- YAML remains canonical for TUI.
- Account entry minimum required for runtime mapping:
  - `profile`
  - `display_name` (fallback to profile)
  - `account_id` optional when auto-detect fails
- `checks` must be members of `AVAILABLE_CHECKS`.

## File-Level Impact

- `src/app/cli/customer_commands.py`
  - add scan/assign/checks handlers and YAML update helpers
- `src/app/cli/bootstrap.py`
  - route new customer subcommands in help and parser
- `src/app/tui/flows/customer.py`
  - update account/check pick behavior (search + select all/clear + no default select)
  - enforce customer-mapping-only source for customer report context
- `src/app/tui/common.py`
  - reusable helper for searchable multiselect control patterns
- `README.md`
  - document updated customer setup flow and commands

## Risks and Mitigations

- Risk: duplicate profile assignment across customers.
  - Mitigation: cross-customer lookup and conflict warning before write.
- Risk: STS account detection failure due to expired SSO.
  - Mitigation: allow save without account_id and guide operator to login/patch later.
- Risk: too much prompt complexity in TUI.
  - Mitigation: keep prompts linear and explicit, no hidden auto-actions.

## Verification Plan

- Unit tests for:
  - scan classification mapped/unmapped
  - assign conflict behavior
  - checks update filtering and persistence
- Regression tests for customer report flow behavior with unselected defaults.
- Manual smoke run:
  - create/init customer
  - scan and assign profile
  - set checks
  - run customer report using the new mapping.
