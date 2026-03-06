# Huawei Check Consolidated Daily Report Design

**Date:** 2026-03-06  
**Status:** Approved

## Goal

Implement Huawei check flow in TUI that runs utilization monitoring across all designated Huawei accounts and prints one consolidated `DAILY MONITORING REPORT`.

## Scope

### In Scope
- Rename main menu item from `Huawei Utilization` to `Huawei Check`.
- Add Huawei submenu with one item: `Utilization`.
- Run utilization check directly for all fixed Huawei accounts (no manual profile input).
- Use consolidated report pipeline (`run_all_checks`) so output is a single daily report.
- Include all 10 accounts in coverage, even when some accounts have no utilization data.

### Out of Scope
- Changing external Huawei login flow (`hcloud configure sso`, `sync_sso_token.sh`).
- Adding additional Huawei checks beyond utilization.
- Web/API Huawei feature changes.

## Fixed Account Scope

Run for these 10 Huawei profiles:
- `dh_log-ro`
- `dh_prod_nonerp-ro`
- `afco_prod_erp-ro`
- `afco_dev_erp-ro`
- `dh_prod_network-ro`
- `dh_prod_erp-ro`
- `dh_hris-ro`
- `dh_dev_erp-ro`
- `dh_master-ro`
- `dh_mobileapps-ro`

Expected primary utilization data from these 6 accounts:
- `afco_dev_erp-ro`
- `dh_prod_network-ro`
- `dh_prod_erp-ro`
- `afco_prod_erp-ro`
- `dh_hris-ro`
- `dh_prod_nonerp-ro`

## UX Design

## Main Menu
- Replace current Huawei item label with `Huawei Check`.

## Huawei Submenu
- Show submenu section `Huawei Check`.
- Only one actionable menu item: `Utilization`.
- Selecting `Utilization` immediately executes consolidated run across the fixed account list.

## Execution Design

- Region default: `ap-southeast-4`.
- Runner call uses consolidated pipeline:
  - `run_all_checks(profiles=HUAWEI_FIXED_PROFILES, region="ap-southeast-4", group_name="Huawei", checks_override={"huawei-ecs-util": HuaweiECSUtilizationChecker}, exclude_backup_rds=True)`

This ensures report format follows existing daily consolidated structure.

## Report Behavior

- One output report per run: `DAILY MONITORING REPORT`.
- Huawei section appears as a consolidated section (not per-account print loop).
- Coverage includes all 10 accounts.
- Accounts with missing/no metric data remain visible in report as no-data/empty findings.

## Checker Contract Changes

`HuaweiECSUtilizationChecker` will implement consolidated hooks:
- `report_section_title`
- `issue_label`
- `recommendation_text`
- `count_issues(result)`
- `render_section(all_results, errors)`

The checker keeps existing `check()` and `format_report()` behavior for compatibility.

## Testing Strategy

- Unit tests for Huawei consolidated section rendering:
  - mixed successful/no-data/error account results
  - issue counting for spike/high-stable behavior
- Unit tests for interactive Huawei menu flow:
  - menu label `Huawei Check`
  - submenu `Utilization`
  - execution call includes all 10 fixed accounts
- Regression tests for existing Huawei formatter/check output.

## Risks and Mitigations

- Risk: no-data profiles produce confusing output.
  - Mitigation: explicit no-data line per profile in Huawei consolidated section.
- Risk: fixed account list drifts from operations reality.
  - Mitigation: keep list centralized constant in TUI flow for easy future update.
- Risk: consolidated engine expectations not met by checker.
  - Mitigation: implement and test all consolidated hook methods.
