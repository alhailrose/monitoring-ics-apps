# Consolidated Report Refactor

Date: 2026-02-26

## Problem

`run_all_checks()` in `runners.py` has hardcoded counters and report sections per check.
Adding a new check to the consolidated report requires editing 3-4 places:
- Counter variables in `run_all_checks()`
- Tracking logic in the result loop
- Section in `_print_simple_report()`
- Section in `_print_detailed_report()`
- `CONSOLIDATED_CHECKS` set in `customer.py`

This is fragile, error-prone, and blocks API readiness.

## Solution

Move consolidated report logic into each checker class via BaseChecker methods.
Runner becomes a generic loop. Output stays identical.

### BaseChecker additions

```python
class BaseChecker(ABC):
    # Existing
    report_section_title: str = ""   # e.g. "COST ANOMALIES"
    issue_label: str = ""            # e.g. "cost anomalies" (for Executive Summary)

    def count_issues(self, result: dict) -> int:
        """Count issues from a single profile result. Return 0 = no issues."""
        return 0

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render this check's section for the consolidated report.
        all_results: {profile: {check_name: result_dict}}
        errors: [(profile, error_msg)] for this check
        Returns list of text lines.
        """
        return []

    @property
    def supports_consolidated(self) -> bool:
        return bool(self.report_section_title)
```

### Per-checker implementation

| Checker | section_title | issue_label | count_issues field |
|---------|--------------|-------------|-------------------|
| CostAnomalyChecker | COST ANOMALIES | cost anomalies | total_anomalies |
| GuardDutyChecker | GUARDDUTY FINDINGS | new security findings | findings |
| CloudWatchAlarmChecker | CLOUDWATCH ALARMS | infrastructure alerts | count |
| NotificationChecker | NOTIFICATION CENTER | new notifications | today_count |
| BackupStatusChecker | BACKUP STATUS | backup issues | failed_jobs |
| DailyArbelChecker | DAILY ARBEL METRICS | RDS warnings | (count warn metrics) |
| HealthChecker | (none) | (none) | (not in consolidated) |
| EC2ListChecker | (none) | (none) | (not in consolidated) |

### Runner changes

`run_all_checks()` tracking loop becomes:
```python
for chk_name, results in profile_results.items():
    checker = checkers[chk_name]
    issue_count = checker.count_issues(results)
    if issue_count > 0:
        totals[chk_name] = totals.get(chk_name, 0) + issue_count
        has_issue = True
```

Report rendering becomes:
```python
for name, checker in checkers.items():
    if checker.supports_consolidated:
        lines.extend(checker.render_section(all_results, errors_by_check.get(name, [])))
```

### customer.py change

Remove hardcoded `CONSOLIDATED_CHECKS` set. Instead:
```python
consolidated = [c for c in selected_checks if AVAILABLE_CHECKS[c](region="").supports_consolidated]
```

## Output

Identical to current. No visible change.

## Files to modify

1. `src/checks/common/base.py` — add default methods/properties
2. `src/checks/generic/cost_anomalies.py` — implement 3 methods
3. `src/checks/generic/guardduty.py` — implement 3 methods
4. `src/checks/generic/cloudwatch_alarms.py` — implement 3 methods
5. `src/checks/generic/notifications.py` — implement 3 methods
6. `src/checks/generic/backup_status.py` — implement 3 methods
7. `src/checks/aryanoble/daily_arbel.py` — implement 3 methods
8. `src/core/runtime/runners.py` — genericize run_all_checks, _print_simple_report, _print_detailed_report
9. `src/app/tui/flowomer.py` — remove CONSOLIDATED_CHECKS, use supports_consolidated
