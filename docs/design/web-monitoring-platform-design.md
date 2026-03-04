# Web Monitoring Platform - Design Document

## Overview

Web-based interface untuk AWS monitoring checks yang menggantikan TUI dengan functionality yang sama, ditambah historical metrics tracking dan customer management.

**Konsep Utama:** Synchronous execution dengan real-time display, bukan async job queue.

---

## Architecture

```
┌─────────────────┐
│   Web Browser   │
│  (React/TS UI)  │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│   FastAPI App   │
│  - Execute API  │
│  - History API  │
│  - Customer API │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│  AWS   │ │PostgreSQL│
│  APIs  │ │ Database │
└────────┘ └──────────┘
```

**Key Changes from Current Implementation:**
- ❌ Remove: Redis queue, Worker process, Job queue system
- ✅ Add: Synchronous execution, Customer management, Profile detection
- ✅ Keep: PostgreSQL for metrics storage

---

## Data Models

### 1. Customer
```python
class Customer(Base):
    __tablename__ = "customers"
    
    id: str (UUID, PK)
    name: str (unique, indexed)  # e.g., "aryanoble", "nabati"
    display_name: str            # e.g., "Aryanoble"
    slack_webhook_url: str | None
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    accounts: list[Account]
    check_runs: list[CheckRun]
```

### 2. Account
```python
class Account(Base):
    __tablename__ = "accounts"
    
    id: str (UUID, PK)
    customer_id: str (FK -> customers.id)
    profile_name: str (indexed)  # AWS CLI profile name
    account_id: str | None       # AWS account ID (auto-detected)
    display_name: str            # e.g., "Production", "Staging"
    is_active: bool (default=True)
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    customer: Customer
    check_results: list[CheckResult]
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('customer_id', 'profile_name'),
    )
```

### 3. CheckRun
```python
class CheckRun(Base):
    __tablename__ = "check_runs"
    
    id: str (UUID, PK)
    customer_id: str (FK -> customers.id)
    check_mode: str  # "single", "all", "arbel"
    check_name: str | None  # For single mode: "guardduty", "cost-anomaly", etc.
    requested_by: str (default="web")
    slack_sent: bool (default=False)
    execution_time_seconds: float | None
    created_at: datetime
    
    # Relationships
    customer: Customer
    results: list[CheckResult]
    
    # Index for history queries
    __table_args__ = (
        Index('idx_check_runs_customer_created', 'customer_id', 'created_at'),
        Index('idx_check_runs_check_mode', 'check_mode'),
    )
```

### 4. CheckResult
```python
class CheckResult(Base):
    __tablename__ = "check_results"
    
    id: str (UUID, PK)
    check_run_id: str (FK -> check_runs.id, CASCADE)
    account_id: str (FK -> accounts.id)
    check_name: str (indexed)  # "guardduty", "cost-anomaly", etc.
    status: str  # "OK", "WARN", "ERROR"
    
    # Check-specific data
    summary: str | None  # Short summary text
    details: dict | None (JSON)  # Full check output for display
    findings: dict | None (JSON)  # For GuardDuty findings
    alarm_state: str | None  # For cost-anomaly: "OK", "ALARM"
    
    created_at: datetime
    
    # Relationships
    check_run: CheckRun
    account: Account
    
    # Indexes
    __table_args__ = (
        Index('idx_check_results_run', 'check_run_id'),
        Index('idx_check_results_account_check', 'account_id', 'check_name', 'created_at'),
    )
```

### 5. cLog
```python
class ProfileSyncLog(Base):
    __tablename__ = "profile_sync_logs"
    
    id: str (UUID, PK)
    detected_profiles: list[str] (JSON)  # All profiles from ~/.aws/config
    new_profiles: list[str] (JSON)       # Profiles not yet mapped
    synced_at: datetime
    synced_by: str (default="web")
```

---

## API Endpoints

### Customer Management

#### `GET /api/v1/customers`
List all customers with their accounts.

**Response:**
```json
{
  "customers": [
    {
      "id": "uuid",
      "name": "aryanoble",
      "display_name": "Aryanoble",
      "accounts": [
        {
          "id": "uuid",
          "profile_name": "aryanoble-prod",
          "display_name": "Production",
          "account_id": "123456789012",
          "is_active": true
        }
      ]
    }
  ]
}
```

#### `POST /api/v1/customers`
Create new customer.

**Request:**
```json
{
  "name": "customer-slug",
  "display_name": "Customer Name",
  "slack_webhook_url": "https://hooks.slack.com/..."
}
```

#### `POST /api/v1/customers/{customer_id}/accounts`
Add account to customer.

**Request:**
```json
{
  "profile_name": "aws-cli-profile-name",
  "display_name": "Production"
}
```

**Response:**
```json
{
  "id": "uuid",
  "account_id": "123456789012",  // Auto-detected via STS
  "profile_name": "aws-cli-profile-name",
  "display_name": "Production"
}
```

#### `GET /api/v1/profiles/detect`
Scan ~/.aws/config for new profiles.

**Response:**
```json
{
  "all_profiles": ["profile1", "profile2", "profile3"],
  "mapped_profiles": ["profile1"],
  "unmapped_profiles": ["profile2", "profile3"],
  "last_sync": "2026-03-03T10:00:00Z"
}
```

---

### Check Execution

#### `POST /api/v1/checks/execute`
Execute monitoring checks synchronously.

**Request:**
```json
{
  "customer_id": "uuid",
  "mode": "single",  // "single", "all", "arbel"
  "check_name": "guardduty",  // Required for "single" mode
  "account_ids": ["uuid1", "uuid2"],  // Empty = all accounts
  "send_slack": true,
  "region": "ap-southeast-3"
}
```

**Response:**
```json
{
  "check_run_id": "uuid",
  "execution_time_seconds": 12.5,
  "results": [
    {
      "account": {
        "profile_name": "aryanoble-prod",
        "display_name": "Production"
      },
      "check_name": "guardduty",
      "status": "WARN",
      "summary": "Found 3 medium severity findings",
      "output": "=== GuardDuty Findings ===\n...",  // Copyable text
      "findings": {
        "high": 0,
        "medium": 3,
        "low": 1
      }
    }
  ],
  "slack_sent": true
}
```

**Execution Flow:**
1. Validate customer + accounts
2. Execute checks synchronously (parallel per account)
3. Format output (copyable text)
4. Save metrics to database
5. Send to Slack if enabled
6. Return results

**Timeout:** 5 minutes per execution (configurable)

---

### History & Metrics

#### `GET /api/v1/history`
Query historical check runs.

**Query Parameters:**
- `customer_id` (required)
- `start_date` (ISO 8601)
- `end_date` (ISO 8601)
- `check_mode` (optional: "single", "all", "arbel")
- `check_name` (optional: specific check)
- `limit` (default: 50)
- `offset` (default: 0)

**Response:**
```json
{
  "total": 150,
  "items": [
    {
      "check_run_id": "uuid",
      "check_mode": "all",
      "created_at": "2026-03-03T10:00:00Z",
      "execution_time_seconds": 12.5,
      "slack_sent": true,
      "results_summary": {
        "total_checks": 8,
        "ok": 5,
        "warn": 2,
        "error": 1
      }
    }
  ]
}
```

#### `GET /api/v1/history/{check_run_id}`
Get detailed results for a specific run.

**Response:**
```json
{
  "check_run_id": "uuid",
  "customer": {
    "name": "aryanoble",
    "display_name": "Aryanoble"
  },
  "check_mode": "all",
  "created_at": "2026-03-03T10:00:00Z",
  "results": [
    {
      "account": {
        "profile_name": anoble-prod",
        "display_name": "Production"
      },
      "check_name": "guardduty",
      "status": "WARN",
      "summary": "Found 3 medium severity findings",
      "output": "=== GuardDuty Findings ===\n...",
      "findings": {...}
    }
  ]
}
```

#### `GET /api/v1/metrics/summary`
Aggregated metrics for dashboard (future).

**Query Parameters:**
- `customer_id` (required)
- `start_date`, `end_date`
- `check_name` (optional)

**Response:**
```json
{
  "period": {
    "start": "2026-03-01T00:00:00Z",
    "end": "2026-03-03T23:59:59Z"
  },
  "total_runs": 45,
  "by_status": {
    "ok": 120,
    "warn": 15,
    "error": 5
  },
  "by_check": {
    "guardduty": {"ok": 30, "warn": 5, "error": 0},
    "cost-anomaly": {"ok": 25, "warn": 10, "error": 0}
  }
}
```

---

## Frontend Flows

### 1. Single Check Flow
```
1. Select customer (dropdown)
2. Select check type (dropdown: guardduty, cost-anomaly, etc.)
3. Select accounts (multi-select or "All")
4. Toggle Slack (checkbox)
5. Click "Run Check"
6. Show loading spinner
7. Display results (copyable text output)
8. Show execution time
```

### 2. All Check Flow
```
1. Select customer (dropdown)
2. Mode automatically set to "all"
3. Checks: cost-anomaly, guardduty, notifications, alarm
4. Toggle Slack (checkbox)
5. Click "Run All Checks"
6. Show loading spinner
7. Display results grouped by check type
8. Show execution time
```

### 3. Arbel Check Flow (Aryanoble-specific)
```
1. Customer locked to "aryanoble"
2. Mode automatically set to "arbel"
3. Checks: same as TUI arbel mode
4. Toggle Slack (checkbox)
5. Click "Run Arbel Checks"
6. Show loading spinner
7. Display results
8. Show execution time
```

### 4. Customer Management Flow
```
1. Navigate to "Customers" page
2. View list of customers + accounts
3. Click "Add Customer"
   - Enter name, display name, Slack webhook
4. Click "Add Account" for customer
   - Select from detected profiles
   - Enter display name
   - Auto-detect AWS account ID
5. Click "Detect New Profiles"
   - Show unmapped profiles
   - Quick-add to customer
```

### 5. History Flow
```
1. Navigate to "History" page
2. Select customer (dropdown)
3. Select date range (date picker)
ional: filter by check mode/name
5. View list of past runs
6. Click run to see detailed results
7. Copy output text
```

---

## Migration Strategy

### Phase 1: Database Schema Migration
1. Create new tables: `customers`, `accounts`, `check_runs`, `check_results`, `profile_sync_logs`
2. Drop old tables: `jobs`, `job_results`
3. Migration script to convert YAML configs to database:
   - Parse `configs/customers/*.yaml`
   - Create customer records
   - Create account records from profile lists

### Phase 2: Backend Refactoring
1. Remove: `RedisJobQueue`, `start_worker()`, `run_job()`
2. Create: `CheckExecutor` service for synchronous execution
3. Create: `CustomerService`, `ProfileDetector`
4. Refactor: API endpoints to new design
5. Update: `WorkerRunner` → `CheckExecutor` (no queue, direct execution)

### Phase 3: Frontend Rebuild
1. Remove: Job queue polling UI
2. Create: Customer management pages
3. Create: Check execution forms (3 modes)
4. Create: History viewer with filters
5. Update: Output display (copyable text)

### Phase 4: Testing & Deployment
1. Test all check modes with real AWS accounts
2. Test Slack integration
3. Test profile detection
4. Load testing (multiple concurrent executions)
5. Deploy to production

---

## Configuration Strategy

### Database vs YAML

**Database (Production):**
- Customer configs
- Account mappings
- Historical metrics
- Used by Web UI

**YAML (Optional - TUI only):**
- Keep for backward compatibility with TUI
- Or deprecate TUI entirely in favor of Web UI

**Recommendation:** Deprecate TUI, use Web UI only. Simpler maintenance.

---

## Technical Considerations

### 1. Execution Timeout
- Default: 5 minutes per execution
- Configurable via environment variable
- Frontend shows timeout warning at 4:30

### 2. Concurrent Executions
- Use FastAPI background tasks or ad pool
- Limit concurrent executions per customer (e.g., max 3)
- Queue if limit reached (simple in-memory queue, not Redis)

### 3. AWS Credentials
- Use existing AWS CLI profiles
- Support AWS SSO (existing wrapper)
- Auto-refresh tokens

### 4. Slack Integration
- Use existing Slack client
- Format output same as TUI
- Store webhook URL per customer

### 5. Profile Detection
- Parse `~/.aws/config` file
- Extract profile names
- Compare with database
- Manual trigger (not automatic)

### 6. Output Format
- Plain text (copyable)
- Same format as TUI output
- Store in `details` JSON field for history

---

## Security Considerations

1. **Authentication:** Add basic auth or OAuth (future)
2. **Authorization:** Customer-level access control (future)
3. **AWS Credentials:** Never expose in API responses
4. **Slack Webhooks:** Encrypt in database
5. **Input Validation:** Validate all user inputs
6. **SQL Injection:** Use SQLAlchemy ORM (parameterized queries)

---

## Performance Optimization

1. **Parallel Execution:** Run checks across accounts in parallel (existing `max_workers`)
2. **Database Indexes:** On customer_id, created_at, check_name
3. **Connection Pooling:** stgreSQL connection pool
4. **Caching:** Cache customer/account lists (5 min TTL)
5. **Pagination:** History API with limit/offset

---

## Future Enhancements

1. **Dashboard:** Metrics visualization (charts, trends)
2. **Scheduled Checks:** Cron-like scheduling (add back queue for this)
3. **Alerting:** Email/Slack alerts for specific conditions
4. **Multi-region:** Support multiple AWS regions per check
5. **Export:** CSV/JSON export of historical data
6. **API Keys:** For programmatic access
7. **Webhooks:** Notify external systems on check completion

---

## Summary

**Key Changes:**
- ❌ Remove async job queue (Redis, Worker)
- ✅ Synchronous execution with real-time results
- ✅ Customer/account management in database
- ✅ Historical metrics tracking
- ✅ Profile detection from AWS CLI config
- ✅ Three check modes (single, all, arbel)
- ✅ Slack toggle per execution

**Benefits:**
- Simpler architecture (no queue complexity)
- Immediate feedback (no waiting for worker)
- Better UX (like TUI but web-based)
- Production-ready (database-backed)
- Historical analytics capability
