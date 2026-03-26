# Discovery-Driven Checks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use per-account `config_extra["_discovery"]` data to (1) skip live `describe_instances` in `ec2_utilization` and (2) migrate `daily-arbel` config from YAML/hardcoded dict to the `AccountCheckConfig` database table.

**Architecture:** Phase 1 adds an `instance_list` kwarg to `AWSUtilization3CoreChecker` — if provided by the executor from stored discovery data, live EC2 enumeration is skipped. Phase 2 adds a `sections` kwarg to `DailyArbelChecker` that becomes the primary config source (over YAML and `ACCOUNT_CONFIG`), and extends `import_from_yaml` to write those rows automatically during reimport.

**Tech Stack:** Python (FastAPI backend), pytest, SQLAlchemy (via existing repos), boto3 mocking via unittest.mock

---

## File Map

| File | Change |
|------|--------|
| `backend/checks/generic/aws_utilization_3core.py` | Add `instance_list` kwarg; skip discover+list when set |
| `backend/domain/services/check_executor.py` | Inject `instance_list` from `_discovery` for `ec2_utilization` |
| `backend/checks/aryanoble/daily_arbel.py` | Add `sections` kwarg + `_sections_to_cfg` helper; use as primary config source in `_resolve_account_config` |
| `backend/domain/services/customer_service.py` | Extend `import_from_yaml` to also write `AccountCheckConfig` rows for `daily-arbel` |
| `tests/unit/test_check_executor.py` | Add test: discovery data injects instance_list |
| `tests/unit/test_daily_arbel_thresholds.py` | Add test: sections kwarg bypasses YAML/ACCOUNT_CONFIG |

---

## Phase 1 — `ec2_utilization` Region/Instance Optimization

### Task 1: Add `instance_list` kwarg to `AWSUtilization3CoreChecker`

**Files:**
- Modify: `backend/checks/generic/aws_utilization_3core.py:25-41`

- [ ] **Step 1: Write failing test**

In `tests/unit/test_check_executor.py`, add at the bottom:

```python
def test_ec2_utilization_uses_stored_instance_list():
    """instance_list kwarg skips _discover_regions and _list_instances."""
    from backend.checks.generic.aws_utilization_3core import AWSUtilization3CoreChecker
    from unittest.mock import patch, MagicMock

    stored_instances = [
        {
            "instance_id": "i-abc123",
            "name": "my-server",
            "os_type": "linux",
            "instance_type": "t3.small",
            "region": "ap-southeast-3",
        }
    ]

    checker = AWSUtilization3CoreChecker(instance_list=stored_instances)

    with patch.object(checker, "_discover_regions") as mock_discover, \
         patch.object(checker, "_list_instances") as mock_list, \
         patch.object(checker, "_get_session") as mock_session, \
         patch.object(checker, "_collect_instance_metrics") as mock_collect:

        mock_collect.return_value = {**stored_instances[0], "cpu_avg_12h": 10.0,
            "cpu_peak_12h": 15.0, "cpu_peak_at_12h": None, "memory_avg_12h": None,
            "memory_peak_12h": None, "memory_peak_at_12h": None, "memory_metric": None,
            "memory_note": None, "disk_free_min_percent": None, "disk_note": None,
            "status": "NORMAL"}
        mock_session.return_value = MagicMock()

        result = checker.check("test-profile", "123456789012")

    mock_discover.assert_not_called()
    mock_list.assert_not_called()
    assert result["status"] == "success"
    assert len(result["instances"]) == 1
    assert result["instances"][0]["instance_id"] == "i-abc123"
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/heilrose/Work/Project/monitoring-ics-apps
python -m pytest tests/unit/test_check_executor.py::test_ec2_utilization_uses_stored_instance_list -v
```

Expected: `FAILED` — `AWSUtilization3CoreChecker.__init__` does not accept `instance_list`.

- [ ] **Step 3: Implement `instance_list` in `__init__` and `check`**

In `backend/checks/generic/aws_utilization_3core.py`, modify `__init__` at line 25:

```python
def __init__(self, region: str = "ap-southeast-3", **kwargs):
    super().__init__(region=region, **kwargs)
    self.util_hours = int(kwargs.get("util_hours", 12))
    self.period_seconds = int(kwargs.get("period_seconds", 300))
    self.thresholds = dict(DEFAULT_THRESHOLDS)
    threshold_overrides = kwargs.get("thresholds")
    if isinstance(threshold_overrides, dict):
        for key, value in threshold_overrides.items():
            if key in self.thresholds and isinstance(value, (int, float)):
                self.thresholds[key] = float(value)

    for key in self.thresholds:
        override = kwargs.get(key)
        if isinstance(override, (int, float)):
            self.thresholds[key] = float(override)

    self.profile_regions = dict(kwargs.get("profile_regions", {}) or {})
    raw_list = kwargs.get("instance_list")
    self.instance_list: list[dict] | None = list(raw_list) if raw_list else None
```

In `check()` at line 528, replace:
```python
    regions = self._discover_regions(session, profile=profile)
    instances = self._list_instances(session, regions)
```
with:
```python
    if self.instance_list:
        instances = self.instance_list
    else:
        regions = self._discover_regions(session, profile=profile)
        instances = self._list_instances(session, regions)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/unit/test_check_executor.py::test_ec2_utilization_uses_stored_instance_list -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/checks/generic/aws_utilization_3core.py tests/unit/test_check_executor.py
git commit -m "feat(ec2): accept instance_list kwarg to skip live describe_instances"
```

---

### Task 2: Inject `instance_list` from discovery in executor

**Files:**
- Modify: `backend/domain/services/check_executor.py` around line 1562

- [ ] **Step 1: Write failing test**

In `tests/unit/test_check_executor.py`, add:

```python
def test_executor_injects_instance_list_from_discovery():
    """_execute_parallel injects instance_list into ec2_utilization kwargs from _discovery."""
    executor = _make_executor()

    discovery_data = {
        "ec2_instances": [
            {
                "instance_id": "i-aaa111",
                "name": "prod-server",
                "instance_type": "t3.medium",
                "region": "ap-southeast-3",
                "platform": "",
            },
            {
                "instance_id": "i-bbb222",
                "name": "win-server",
                "instance_type": "t3.large",
                "region": "ap-southeast-3",
                "platform": "windows",
            },
        ]
    }
    acct = _make_account("prod-profile", config_extra={"_discovery": discovery_data})

    captured_kwargs = {}

    def capture(*args, **kwargs):
        # _run_single_check(check_name, profile, region, check_kwargs, injected_creds)
        captured_kwargs[args[0]] = args[3]
        return {"status": "ok"}

    with patch("backend.domain.services.check_executor._run_single_check", side_effect=capture):
        executor._execute_parallel(
            [acct], {"ec2_utilization": MagicMock()}, "ap-southeast-3"
        )

    assert "ec2_utilization" in captured_kwargs
    injected = captured_kwargs["ec2_utilization"]
    assert injected is not None
    instance_list = injected["instance_list"]
    assert len(instance_list) == 2
    linux = next(i for i in instance_list if i["instance_id"] == "i-aaa111")
    win = next(i for i in instance_list if i["instance_id"] == "i-bbb222")
    assert linux["os_type"] == "linux"
    assert win["os_type"] == "windows"
```

- [ ] **Step 2: Run to verify it fails**

```bash
python -m pytest tests/unit/test_check_executor.py::test_executor_injects_instance_list_from_discovery -v
```

Expected: `FAILED` — executor doesn't inject `instance_list` yet.

- [ ] **Step 3: Add injection in executor**

In `backend/domain/services/check_executor.py`, after the `AccountCheckConfig` merge block (after line 1562, before the `daily-budget` special case at line 1567), add:

```python
                    # Inject stored EC2 instance list from discovery for ec2_utilization
                    if chk_name == "ec2_utilization":
                        discovery = (account.config_extra or {}).get("_discovery", {})
                        ec2_instances = discovery.get("ec2_instances") or []
                        if ec2_instances:
                            if check_kwargs is None:
                                check_kwargs = {}
                            check_kwargs.setdefault(
                                "instance_list",
                                [
                                    {
                                        "instance_id": inst["instance_id"],
                                        "name": inst.get("name", "-"),
                                        "os_type": (
                                            "windows"
                                            if "windows"
                                            in (inst.get("platform") or "").lower()
                                            else "linux"
                                        ),
                                        "instance_type": inst.get("instance_type", ""),
                                        "region": inst["region"],
                                    }
                                    for inst in ec2_instances
                                    if inst.get("instance_id") and inst.get("region")
                                ],
                            )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/unit/test_check_executor.py::test_executor_injects_instance_list_from_discovery -v
```

Expected: `PASSED`

- [ ] **Step 5: Run all executor tests**

```bash
python -m pytest tests/unit/test_check_executor.py -v
```

Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/domain/services/check_executor.py tests/unit/test_check_executor.py
git commit -m "feat(executor): inject instance_list from _discovery for ec2_utilization"
```

---

## Phase 2 — `daily-arbel` DB Migration

### Task 3: Add `sections` kwarg to `DailyArbelChecker`

**Files:**
- Modify: `backend/checks/aryanoble/daily_arbel.py:331-500`

- [ ] **Step 1: Write failing test**

In `tests/unit/test_daily_arbel_thresholds.py`, add at the bottom:

```python
def test_sections_kwarg_bypasses_yaml_and_account_config():
    """When sections kwarg is provided, _resolve_account_config uses it directly."""
    checker = DailyArbelChecker(
        sections=[
            {
                "section_name": "Test RDS",
                "service_type": "rds",
                "cluster_id": "test-cluster",
                "instances": {"primary": "test-rds-instance"},
                "metrics": ["CPUUtilization", "FreeableMemory"],
                "thresholds": {"CPUUtilization": 80, "FreeableMemory": 1073741824},
                "alarm_thresholds": {},
            }
        ]
    )

    cfg = checker._resolve_account_config("unknown-profile", "000000000000")

    assert cfg is not None
    assert cfg["cluster_id"] == "test-cluster"
    assert cfg["instances"] == {"primary": "test-rds-instance"}
    assert cfg["thresholds"]["CPUUtilization"] == 80
    assert cfg["service_type"] == "rds"
    assert cfg["extra_sections"] == []


def test_sections_kwarg_with_extra_sections():
    """Second+ sections become extra_sections."""
    checker = DailyArbelChecker(
        sections=[
            {
                "section_name": "Main RDS",
                "service_type": "rds",
                "instances": {"primary": "rds-instance"},
                "metrics": ["FreeableMemory"],
                "thresholds": {},
            },
            {
                "section_name": "Extra EC2",
                "service_type": "ec2",
                "instances": {"webserver": "i-abc123"},
                "metrics": ["CPUUtilization"],
                "thresholds": {"CPUUtilization": 70},
            },
        ]
    )

    cfg = checker._resolve_account_config("any-profile", "111111111111")

    assert cfg["section_name"] == "Main RDS"
    assert len(cfg["extra_sections"]) == 1
    assert cfg["extra_sections"][0]["section_name"] == "Extra EC2"
```

- [ ] **Step 2: Run to verify tests fail**

```bash
python -m pytest tests/unit/test_daily_arbel_thresholds.py::test_sections_kwarg_bypasses_yaml_and_account_config tests/unit/test_daily_arbel_thresholds.py::test_sections_kwarg_with_extra_sections -v
```

Expected: `FAILED` — `DailyArbelChecker` doesn't accept `sections`.

- [ ] **Step 3: Add `db_sections` to `__init__`**

In `backend/checks/aryanoble/daily_arbel.py`, in `DailyArbelChecker.__init__` at line 331, add after `self.section_scope = normalized_scope`:

```python
        raw_sections = kwargs.get("sections")
        self.db_sections: list[dict] | None = (
            list(raw_sections) if isinstance(raw_sections, list) and raw_sections else None
        )
```

- [ ] **Step 4: Add `_sections_to_cfg` method**

Add this method to `DailyArbelChecker` (before `_resolve_account_config`):

```python
    def _sections_to_cfg(self, sections: list[dict], profile: str) -> dict | None:
        """Convert DB sections list to internal cfg format expected by _collect_section_report."""
        if not sections:
            return None
        first = sections[0]
        extra_sections = list(sections[1:])
        cfg: dict = {
            "account_name": first.get("section_name", profile),
            "section_name": first.get("section_name", profile),
            "cluster_id": first.get("cluster_id"),
            "service_type": first.get("service_type", "rds"),
            "alarm_regions": list(first.get("alarm_regions") or []),
            "instances": dict(first.get("instances") or {}),
            "instance_names": dict(first.get("instance_names") or {}),
            "metrics": list(first.get("metrics") or []),
            "thresholds": dict(first.get("thresholds") or {}),
            "role_thresholds": dict(first.get("role_thresholds") or {}),
            "alarm_thresholds": dict(first.get("alarm_thresholds") or {}),
            "extra_sections": extra_sections,
        }
        return self._apply_account_config_override(cfg, profile)
```

- [ ] **Step 5: Modify `_resolve_account_config` to check `db_sections` first**

In `_resolve_account_config` at line 465, add as the very first block before the YAML lookup:

```python
    def _resolve_account_config(self, profile, account_id):
        # DB path — highest priority (from AccountCheckConfig table via executor)
        if self.db_sections:
            return self._sections_to_cfg(self.db_sections, profile)

        customer_account = None
        try:
            customer_account = find_customer_account("aryanoble", account_id)
        # ... rest of existing method unchanged
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_daily_arbel_thresholds.py::test_sections_kwarg_bypasses_yaml_and_account_config tests/unit/test_daily_arbel_thresholds.py::test_sections_kwarg_with_extra_sections -v
```

Expected: `PASSED`

- [ ] **Step 7: Run all daily-arbel tests**

```bash
python -m pytest tests/unit/test_daily_arbel_thresholds.py -v
```

Expected: all PASSED

- [ ] **Step 8: Commit**

```bash
git add backend/checks/aryanoble/daily_arbel.py tests/unit/test_daily_arbel_thresholds.py
git commit -m "feat(daily-arbel): add sections kwarg for DB-driven config, bypass YAML/ACCOUNT_CONFIG"
```

---

### Task 4: Extend `import_from_yaml` to write `AccountCheckConfig` for daily-arbel

**Files:**
- Modify: `backend/domain/services/customer_service.py:411-503`

When `import_from_yaml` (called by `POST /customers/{id}/reimport`) processes an account with `daily_arbel` config, it should also upsert an `AccountCheckConfig` row with `check_name="daily-arbel"` and a `sections` list.

- [ ] **Step 1: Add `_yaml_daily_arbel_to_sections` helper to `CustomerService`**

Add this static method before `import_from_yaml`:

```python
    @staticmethod
    def _yaml_daily_arbel_to_sections(acct: dict) -> list[dict] | None:
        """Build sections list from YAML account config for daily-arbel check."""
        daily = acct.get("daily_arbel")
        if not daily:
            return None

        main_section: dict = {
            "section_name": acct.get("display_name", acct.get("profile", "")),
            "service_type": daily.get("service_type", "rds"),
            "cluster_id": daily.get("cluster_id"),
            "alarm_regions": daily.get("alarm_regions") or [],
            "instances": dict(daily.get("instances") or {}),
            "instance_names": dict(daily.get("instance_names") or {}),
            "metrics": list(daily.get("metrics") or []),
            "thresholds": dict(daily.get("thresholds") or {}),
            "role_thresholds": dict(daily.get("role_thresholds") or {}),
            "alarm_thresholds": dict(daily.get("alarm_thresholds") or {}),
        }
        # Remove None cluster_id to keep config clean
        if main_section["cluster_id"] is None:
            main_section.pop("cluster_id", None)

        sections = [main_section]

        for extra in acct.get("daily_arbel_extra") or []:
            if isinstance(extra, dict):
                sections.append(dict(extra))

        return sections
```

- [ ] **Step 2: Call it inside `import_from_yaml` after account is saved**

In `import_from_yaml`, after the `self.repo.commit()` at line 497 (but before it — we need the account id), modify the account processing block to also upsert `AccountCheckConfig`. Replace the account loop body:

```python
        for acct in customer_config.get("accounts", []):
            profile = acct.get("profile")
            if not profile:
                continue

            existing_accounts = self.repo.get_accounts_by_customer(
                customer.id, active_only=False
            )
            existing_acct = next(
                (a for a in existing_accounts if a.profile_name == profile), None
            )

            # Extract check-specific config as config_extra
            config_extra = {}
            for key in ("daily_arbel", "daily_budget"):
                if key in acct:
                    config_extra[key] = acct[key]
            if "sso" in acct:
                config_extra["sso"] = acct["sso"]

            alarm_names = acct.get("alarm_names") or None
            region = acct.get("region") or None

            if existing_acct:
                self.repo.update_account(
                    existing_acct.id,
                    display_name=acct.get("display_name", profile),
                    account_id=acct.get("account_id", existing_acct.account_id),
                    config_extra=config_extra
                    if config_extra
                    else existing_acct.config_extra,
                    alarm_names=alarm_names,
                    region=region,
                )
                account_db_id = existing_acct.id
                updated += 1
            else:
                new_acct = self.repo.add_account(
                    customer_id=customer.id,
                    profile_name=profile,
                    display_name=acct.get("display_name", profile),
                    account_id=acct.get("account_id"),
                    config_extra=config_extra if config_extra else None,
                    alarm_names=alarm_names,
                    region=region,
                )
                account_db_id = new_acct.id
                added += 1

            # Migrate daily-arbel config to AccountCheckConfig table
            sections = self._yaml_daily_arbel_to_sections(acct)
            if sections:
                self.repo.upsert_account_check_config(
                    account_id=account_db_id,
                    check_name="daily-arbel",
                    config={"sections": sections},
                )
```

Note: `self.repo.add_account` needs to return the created object. Verify `add_account` in the repo returns the model instance (if not, use `get_accounts_by_customer` again after commit, or restructure — see existing pattern in `add_account` for `discover_account_full`).

- [ ] **Step 3: Verify `repo.add_account` returns the new account**

Check `backend/infra/database/repositories/customer_repository.py`:

```bash
grep -n "def add_account" /home/heilrose/Work/Project/monitoring-ics-apps/backend/infra/database/repositories/customer_repository.py
```

If it returns the model instance, the plan above works. If it returns `None`, replace `account_db_id = new_acct.id` with:

```python
                self.repo.add_account(...)
                # Fetch the newly added account
                existing_accounts_after = self.repo.get_accounts_by_customer(customer.id, active_only=False)
                new_acct = next((a for a in existing_accounts_after if a.profile_name == profile), None)
                account_db_id = new_acct.id if new_acct else None
```

- [ ] **Step 4: Run the reimport for aryanoble to trigger migration**

```bash
curl -X POST http://localhost:8000/api/v1/customers/aryanoble/reimport \
  -H "Authorization: Bearer <token>"
```

Or test via the frontend customers page → Re-import button.

Expected: HTTP 200, accounts_added=0 (already exist), accounts_updated=N, and `AccountCheckConfig` rows created for each account that has `daily_arbel` in YAML (connect-prod, cis-erha, dermies-max, erha-buddy, public-web, HRIS, sfa).

- [ ] **Step 5: Verify rows in DB**

```bash
cd /home/heilrose/Work/Project/monitoring-ics-apps
python -c "
from backend.infra.database.database import get_db
from backend.infra.database.models import AccountCheckConfig
db = next(get_db())
rows = db.query(AccountCheckConfig).filter_by(check_name='daily-arbel').all()
for r in rows:
    print(r.account_id, list(r.config.get('sections', [{}])[0].get('instances', {}).keys()))
"
```

Expected: rows for each aryanoble account that has `daily_arbel` config, showing instance keys.

- [ ] **Step 6: Commit**

```bash
git add backend/domain/services/customer_service.py
git commit -m "feat(import): migrate daily-arbel sections to AccountCheckConfig on reimport"
```

---

### Task 5: End-to-end verification that daily-arbel uses DB config

- [ ] **Step 1: Confirm `sections` kwarg reaches checker**

Add a temporary debug log or use the test endpoint. Verify by running a check manually via the API:

```bash
curl -X POST "http://localhost:8000/api/v1/runs/single" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"check_name": "daily-arbel", "account_ids": ["<cis-erha-account-uuid>"]}'
```

Expected: check runs without errors and returns metric data for `cis-prod-rds`.

- [ ] **Step 2: Temporarily break YAML to confirm fallthrough doesn't happen**

In `DailyArbelChecker._resolve_account_config`, add a temporary `logger.info` to log which path was taken:

```python
    def _resolve_account_config(self, profile, account_id):
        if self.db_sections:
            logger.info("[daily-arbel] Using DB sections for profile=%s", profile)
            return self._sections_to_cfg(self.db_sections, profile)
        logger.info("[daily-arbel] Falling through to YAML/ACCOUNT_CONFIG for profile=%s", profile)
        ...
```

Check logs after running the check — should see "Using DB sections" for aryanoble accounts.

- [ ] **Step 3: Remove the debug log**

```bash
# Remove the logger.info lines added in step 2
git add backend/checks/aryanoble/daily_arbel.py
git commit -m "feat(daily-arbel): remove debug log after DB migration verified"
```

---

### Task 6: Clean up (optional, after verification)

Once DB migration is confirmed working for all accounts, `ACCOUNT_CONFIG` and the YAML fallback in `_resolve_account_config` can be removed. This is a separate commit — only do it once you've confirmed all accounts have `AccountCheckConfig` rows.

- [ ] **Step 1: Remove `ACCOUNT_CONFIG` dict and YAML fallback**

In `backend/checks/aryanoble/daily_arbel.py`:
- Delete the `ACCOUNT_CONFIG` dict (lines 36–254)
- Remove the `find_customer_account` import
- Simplify `_resolve_account_config` to just: check `db_sections` → if not set, return `self._apply_account_config_override(None, profile)` (which uses kwargs override or returns an empty cfg)

- [ ] **Step 2: Run all tests**

```bash
python -m pytest tests/unit/ -v
```

Expected: all PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/checks/aryanoble/daily_arbel.py
git commit -m "refactor(daily-arbel): remove ACCOUNT_CONFIG and YAML fallback — fully DB-driven"
```

---

## Self-Review Notes

**Spec coverage:**
- ✅ `ec2_utilization` skips `describe_instances` when discovery data present — Tasks 1–2
- ✅ `ec2_utilization` falls back to live calls if `_discovery` absent — implicit (instance_list is None → existing path)
- ✅ `daily-arbel` reads from `AccountCheckConfig` — Task 3
- ✅ Migration via `import_from_yaml` / reimport endpoint — Task 4
- ✅ AWS Name tag as display label (via `instance_names` in section) — baked into sections format
- ✅ Multiple sections per account (main + extra) — `_sections_to_cfg` maps sections[1:] to `extra_sections`
- ✅ Clean-up path once verified — Task 6

**Type consistency:** `sections: list[dict]` flows through `DailyArbelChecker.db_sections` → `_sections_to_cfg` → returns same `dict` format as `_apply_account_config_override` already produces.

**No placeholders:** All code is complete.
