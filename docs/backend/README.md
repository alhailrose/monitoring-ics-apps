# Backend — Dokumentasi Lengkap

FastAPI + SQLAlchemy 2.0 + Alembic. Canonical runtime: `backend/*`.

---

## Daftar Isi

- [Struktur Folder Backend](#struktur-folder-backend)
- [Entry Points](#entry-points)
- [Check Registry — Semua Checker](#check-registry--semua-checker)
- [Detail Setiap Checker](#detail-setiap-checker)
- [Execution Engine](#execution-engine)
- [Check Modes & Report Modes](#check-modes--report-modes)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [Integrasi Slack](#integrasi-slack)
- [Konfigurasi Customer](#konfigurasi-customer)
- [Cara Tambah Checker Baru](#cara-tambah-checker-baru)
- [Cara Tambah API Endpoint Baru](#cara-tambah-api-endpoint-baru)
- [Testing](#testing)
- [Common Pitfalls](#common-pitfalls)

---

## Struktur Folder Backend

```
backend/
├── checks/                         # Semua AWS checker
│   ├── common/
│   │   ├── base.py                 # BaseChecker (abstract base class)
│   │   └── aws_errors.py          # Helper is_credential_error()
│   ├── generic/                    # Checker universal (semua customer bisa pakai)
│   │   ├── cost_anomalies.py       # CostAnomalyChecker
│   │   ├── cloudwatch_alarms.py    # CloudWatchAlarmChecker
│   │   ├── guardduty.py            # GuardDutyChecker
│   │   ├── notifications.py        # NotificationChecker
│   │   ├── health_events.py        # HealthChecker
│   │   ├── backup_status.py        # BackupStatusChecker
│   │   ├── ec2_list.py             # EC2ListChecker
│   │   ├── aws_utilization_3core.py # AWSUtilization3CoreChecker
│   │   └── aws_utilization_status.py
│   ├── aryanoble/                  # Checker khusus customer Aryanoble
│   │   ├── daily_arbel.py          # DailyArbelChecker (RDS/EC2 metrics harian)
│   │   ├── alarm_verification.py   # AlarmVerificationChecker
│   │   └── daily_budget.py         # DailyBudgetChecker
│   └── huawei/
│       └── ecs_utilization.py      # HuaweiECSUtilizationChecker
│
├── domain/
│   ├── engine/
│   │   ├── executor.py             # JobExecutor — async job management
│   │   └── store.py                # JobStore — in-memory job state
│   ├── formatting/                 # Report builder functions (reusable)
│   ├── models/
│   │   └── job.py                  # JobRecord dataclass
│   ├── runtime/
│   │   ├── config.py               # AVAILABLE_CHECKS registry
│   │   ├── config_loader.py        # External YAML config loader
│   │   ├── customer_runner.py      # Jalankan check per customer
│   │   ├── reports.py              # Report generation functions
│   │   ├── runners.py              # Parallel runner utilities
│   │   └── ui.py                   # TUI display helpers
│   ├── services/
│   │   └── check_executor.py       # Engine utama eksekusi check via API
│   ├── finding_events.py           # FINDING_EVENT_CHECKS registry + mappers
│   └── metric_samples.py           # Metric normalization mappers
│
├── infra/
│   ├── database/
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── repositories/           # Data access layer per entity
│   │   └── session.py              # DB session factory
│   ├── notifications/
│   │   └── slack/notifier.py       # Slack webhook sender
│   └── aws/
│       └── session.py              # AWS boto3 session builder
│
├── interfaces/
│   ├── api/
│   │   ├── main.py                 # FastAPI app factory (create_app)
│   │   ├── dependencies.py         # Depends: get_db, get_current_user, dll
│   │   ├── middleware.py           # CORS, auth middleware
│   │   └── routes/
│   │       ├── auth.py             # POST /auth/login, /auth/logout, /auth/me
│   │       ├── users.py            # GET/POST/PATCH /users
│   │       ├── customers.py        # CRUD /customers + /accounts
│   │       ├── checks.py           # POST /checks/execute, GET /checks/available
│   │       ├── history.py          # GET /history, /history/{id}, /history/{id}/report
│   │       ├── findings.py         # GET /findings
│   │       ├── metrics.py          # GET /metrics
│   │       ├── dashboard.py        # GET /dashboard/summary
│   │       ├── alarms.py           # Proxy ke gmail-alert-forwarder service
│   │       ├── mailing.py          # CRUD /mailing/contacts
│   │       ├── profiles.py         # GET /profiles (AWS profiles dari ~/.aws/config)
│   │       ├── sessions.py         # GET /sessions/health
│   │       ├── settings.py         # GET/PATCH /settings/runtime
│   │       ├── terminal.py         # WebSocket /terminal/ws (PTY relay)
│   │       └── tickets.py          # CRUD /tickets
│   └── cli/
│       └── main.py                 # TUI entry point (Textual)
│
├── config/
│   ├── settings.py                 # Settings (env vars, pydantic-settings)
│   └── loader.py                   # Customer YAML loader (untuk TUI)
│
└── utils/                          # Helpers umum
```

---

## Entry Points

| Interface | Entry Point | Persistence |
|---|---|---|
| API (web) | `backend.interfaces.api.main:app` | DB-persistent (menulis ke PostgreSQL) |
| TUI/CLI | `backend.interfaces.cli.main:main` | Non-persistent (tidak menulis DB) |

**Packaging:** `monitoring-hub` → `backend.interfaces.cli.main:main`

---

## Check Registry — Semua Checker

Didefinisikan di `backend/domain/runtime/config.py:AVAILABLE_CHECKS`:

| Check Key | Kelas | Modul |
|---|---|---|
| `health` | `HealthChecker` | `backend/checks/generic/health_events.py` |
| `cost` | `CostAnomalyChecker` | `backend/checks/generic/cost_anomalies.py` |
| `guardduty` | `GuardDutyChecker` | `backend/checks/generic/guardduty.py` |
| `cloudwatch` | `CloudWatchAlarmChecker` | `backend/checks/generic/cloudwatch_alarms.py` |
| `notifications` | `NotificationChecker` | `backend/checks/generic/notifications.py` |
| `backup` | `BackupStatusChecker` | `backend/checks/generic/backup_status.py` |
| `ec2list` | `EC2ListChecker` | `backend/checks/generic/ec2_list.py` |
| `ec2_utilization` | `AWSUtilization3CoreChecker` | `backend/checks/generic/aws_utilization_3core.py` |
| `daily-arbel` | `DailyArbelChecker` | `backend/checks/aryanoble/daily_arbel.py` |
| `daily-arbel-rds` | `DailyArbelChecker(section_scope="rds")` | `backend/checks/aryanoble/daily_arbel.py` |
| `daily-arbel-ec2` | `DailyArbelChecker(section_scope="ec2")` | `backend/checks/aryanoble/daily_arbel.py` |
| `alarm_verification` | `AlarmVerificationChecker` | `backend/checks/aryanoble/alarm_verification.py` |
| `daily-budget` | `DailyBudgetChecker` | `backend/checks/aryanoble/daily_budget.py` |
| `huawei-ecs-util` | `HuaweiECSUtilizationChecker` | `backend/checks/huawei/ecs_utilization.py` |

---

## Detail Setiap Checker

### `cost` — CostAnomalyChecker

**File:** `backend/checks/generic/cost_anomalies.py`
**AWS Service:** Cost Explorer (`ce`)
**Region:** `us-east-1` (global, CE selalu di us-east-1)

**Apa yang dicek:**
- List semua Anomaly Monitors di akun
- Ambil anomali untuk period kemarin s/d hari ini
- Hitung total anomali, anomali hari ini, anomali kemarin
- Fetch biaya aktual per linked account dari Cost Explorer

**Output `check()` result:**
```python
{
    "status": "success",
    "profile": str,
    "account_id": str,
    "monitors": list,           # list AnomalyMonitor objects
    "anomalies": list,          # list Anomaly objects
    "total_monitors": int,
    "total_anomalies": int,
    "today_anomaly_count": int,
    "yesterday_anomaly_count": int,
    "account_costs": dict,      # {account_id: float (USD)}
}
```

**Format output single mode:** Notifikasi WhatsApp dengan greeting (pagi/siang/sore/malam), detail per anomali (period, impact, score, contributors per akun + cost per akun, service breakdown).

**Findings normalization:** Ya — mapped ke `finding_events` table.

---

### `cloudwatch` — CloudWatchAlarmChecker

**File:** `backend/checks/generic/cloudwatch_alarms.py`
**AWS Service:** CloudWatch
**Region:** Default `ap-southeast-3` (bisa dikonfigurasi)

**Apa yang dicek:**
- List semua MetricAlarms dalam state `ALARM`
- Output: nama alarm, reason, waktu update (di-convert ke WIB)

**Output `check()` result:**
```python
{
    "status": "success",
    "profile": str,
    "account_id": str,
    "count": int,               # jumlah alarm aktif
    "details": [
        {
            "name": str,        # AlarmName
            "reason": str,      # StateReason
            "updated": str,     # format: "YYYY-MM-DD HH:MM WIB"
        }
    ]
}
```

**Format output single mode:** List alarm per akun, `CLEAR` jika tidak ada alarm.

**Findings normalization:** Ya — setiap alarm dipersist sebagai `finding_event`.

---

### `guardduty` — GuardDutyChecker

**File:** `backend/checks/generic/guardduty.py`
**AWS Service:** GuardDuty
**Region:** Default `ap-southeast-3`

**Apa yang dicek:**
- Deteksi detector ID
- Ambil findings aktif untuk hari ini (WIB midnight s/d WIB 23:59)
- Filter berdasarkan severity (hanya HIGH + MEDIUM by default)
- Juga query CRITICAL dan LOW findings untuk metadata

**Output `check()` result:**
```python
{
    "status": "success" | "disabled",
    "profile": str,
    "account_id": str,
    "findings": int,            # jumlah HIGH+MEDIUM findings
    "details": list,            # list finding detail
}
```

**Findings normalization:** Ya — severity mapped (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`).

---

### `notifications` — NotificationChecker

**File:** `backend/checks/generic/notifications.py`
**AWS Service:** Health (`health`) + SES notifications

**Apa yang dicek:**
- AWS Health Events aktif untuk region yang dikonfigurasi
- Events dengan status `open` atau `upcoming`

**Findings normalization:** Ya — events dipersist ke `finding_events`.

---

### `health` — HealthChecker

**File:** `backend/checks/generic/health_events.py`
**AWS Service:** AWS Health

**Apa yang dicek:**
- AWS Health events untuk akun (open/upcoming events)
- Berbeda dari `notifications`: query endpoint berbeda, tanpa Slack format khusus

---

### `backup` — BackupStatusChecker

**File:** `backend/checks/generic/backup_status.py`
**AWS Service:** AWS Backup, RDS (opsional)
**Region:** Default `ap-southeast-3`

**Apa yang dicek:**
- AWS Backup jobs status dalam 24 jam terakhir (`COMPLETED`, `FAILED`, `EXPIRED`, `PARTIAL`, `ABORTED`)
- Vault activity (opsional — vault tertentu per profile)
- RDS snapshots native (hanya untuk profile `iris-prod`)

**Constructor params:**
```python
BackupStatusChecker(
    region="ap-southeast-3",
    vault_names=None,           # list vault name atau comma-separated string
    monitor_rds_snapshots=None, # override monitoring RDS snapshots
    max_job_details=50,
)
```

**Output `check()` result:**
```python
{
    "status": "success",
    "profile": str,
    "account_id": str,
    "total_jobs": int,
    "completed": int,
    "failed": int,
    "expired": int,
    "partial": int,
    "aborted": int,
    "details": list,            # detail per job
}
```

**Findings normalization:** Ya — failed/expired/partial jobs dipersist sebagai `finding_event`.

---

### `daily-arbel` — DailyArbelChecker

**File:** `backend/checks/aryanoble/daily_arbel.py`
**AWS Service:** CloudWatch (metric queries)
**Region:** Default `ap-southeast-3`

**Apa yang dicek:**
- Metrik RDS: `ACUUtilization`, `CPUUtilization`, `FreeableMemory`, `DatabaseConnections`, `FreeStorageSpace`, `BufferCacheHitRatio`, `ServerlessDatabaseCapacity`
- Metrik EC2: `CPUUtilization` (3-core model via `AWSUtilization3CoreChecker`)
- Threshold per akun dikonfigurasi di `ACCOUNT_CONFIG` dalam checker
- Period default: 12 jam terakhir (dikonfigurasi via `window_hours`)

**Constructor params:**
```python
DailyArbelChecker(
    region="ap-southeast-3",
    window_hours=12,            # window monitoring (6, 12, atau 24)
    section_scope=None,         # None=semua, "rds"=hanya RDS, "ec2"=hanya EC2
)
```

**Akun yang dikonfigurasi** (hardcoded di checker):
- `connect-prod`, `cis-erha`, `aryanoble`, `iris-prod`, `sfa-prod`, `erha-staging`, dll

**Metrics normalization:** Ya — nilai numerik dipersist ke `metric_samples` table.

---

### `alarm_verification` — AlarmVerificationChecker

**File:** `backend/checks/aryanoble/alarm_verification.py`
**AWS Service:** CloudWatch
**Region:** Default `ap-southeast-3`

**Apa yang dicek:**
- Status saat ini dari daftar alarm yang sudah dikonfigurasi
- History alarm dalam 24 jam terakhir untuk mendeteksi breach
- Alarm dianggap "breach" jika dalam status ALARM selama >= `min_duration_minutes`

**Constructor params:**
```python
AlarmVerificationChecker(
    region="ap-southeast-3",
    min_duration_minutes=10,    # durasi minimum untuk dianggap breach
)
```

**Konfigurasi alarm names:** Disimpan per akun di `config_extra.alarm_verification.alarm_names` di tabel `accounts`. Tidak dikirim via `check_params`. Seed via `python -m scripts.seed_alarms`.

---

### `daily-budget` — DailyBudgetChecker

**File:** `backend/checks/aryanoble/daily_budget.py`
**AWS Service:** Budgets
**Region:** `us-east-1` (Budgets API global)

**Apa yang dicek:**
- List semua AWS Budgets untuk akun
- Deteksi budget yang sudah melebihi threshold (actual > budgeted)
- Output status: `OK` atau `WARN` per budget

---

### `ec2list` — EC2ListChecker

**File:** `backend/checks/generic/ec2_list.py`
**AWS Service:** EC2

**Apa yang dicek:**
- List semua EC2 instances di akun
- Status instance (running, stopped, dll)
- Informasi: instance ID, type, state, name tag, launch time

---

### `ec2_utilization` — AWSUtilization3CoreChecker

**File:** `backend/checks/generic/aws_utilization_3core.py`
**AWS Service:** CloudWatch

**Apa yang dicek:**
- 3 metrik utama EC2: `CPUUtilization`, `NetworkIn`, `NetworkOut`
- Statistik: Average, Max, Min per metrik dalam window tertentu

---

### `huawei-ecs-util` — HuaweiECSUtilizationChecker

**File:** `backend/checks/huawei/ecs_utilization.py`
**Provider:** Huawei Cloud (bukan AWS)

**Apa yang dicek:**
- CPU & memory utilization Huawei ECS instances
- Menggunakan Huawei Cloud SDK (bukan boto3)

**Akun fixed (10 akun Huawei):**
`dh_log-ro`, `dh_prod_nonerp-ro`, `afco_prod_erp-ro`, `afco_dev_erp-ro`, `dh_prod_network-ro`, `dh_prod_erp-ro`, `dh_hris-ro`, `dh_dev_erp-ro`, `dh_master-ro`, `dh_mobileapps-ro`

---

## Execution Engine

### `check_executor.py` — Engine Utama

**File:** `backend/domain/services/check_executor.py`

Bertanggung jawab atas:
1. Resolve checker class dari `AVAILABLE_CHECKS`
2. Build session/credentials per akun
3. Eksekusi parallel (ThreadPoolExecutor)
4. Inject `_account_display_name` dan `_account_aws_id` ke result
5. Normalize status via `_normalize_status()`
6. Persist `CheckRun` + `CheckResult` ke DB
7. Persist `FindingEvent` (untuk check yang terdaftar di `FINDING_EVENT_CHECKS`)
8. Persist `MetricSample` (untuk daily-arbel)
9. Build consolidated output berdasarkan `report_mode`

**Sandbox skip list** (selalu di-skip, tidak dieksekusi):
```python
{"sandbox", "prod-sandbox", "sandbox-ms-lebaran", "sandbox-ics"}
```

**`check_params` merging:**
API `check_params` di-merge dengan `config_extra` dari DB. Nilai dari API menang (override DB).

### JobExecutor — Async Job Management

**File:** `backend/domain/engine/executor.py`

Untuk check mode `all` dengan banyak akun — eksekusi dijalankan sebagai async job dengan `JobStore` untuk tracking status. Frontend bisa polling status job.

---

## Check Modes & Report Modes

### Check Modes

| Mode | Keterangan |
|---|---|
| `single` | Satu check, satu atau beberapa akun. Output detail per akun via `format_report()`. |
| `all` | Semua check yang dikonfigurasi di `customer.checks`, semua akun aktif. Output consolidated report. |
| `arbel` | Preset Aryanoble: `cost`, `guardduty`, `cloudwatch`, `notifications`, `backup`, `daily-arbel`. |

### Report Modes (untuk mode `all`)

| `report_mode` | Builder Function | Keterangan |
|---|---|---|
| `simple` | `_build_simple_report()` | Alarm list only, satu baris per alarm. Untuk customer CloudWatch-only (contoh: Frisian Flag). |
| `summary` | `_build_summary_report()` | Compact, WhatsApp-friendly, utilization metrics + ringkasan per check. Default. |
| `detailed` | `_build_consolidated_report()` | Full report semua check, semua detail per akun dan temuan. |

---

## API Endpoints

**Base URL:** `http://localhost:8000/api/v1`

### Auth

| Method | Path | Keterangan |
|---|---|---|
| POST | `/auth/login` | Login dengan username + password, return JWT |
| POST | `/auth/logout` | Logout (invalidate token) |
| GET | `/auth/me` | Info user yang sedang login |

### Users

| Method | Path | Keterangan |
|---|---|---|
| GET | `/users` | List semua users (admin only) |
| POST | `/users` | Buat user baru (admin only) |
| PATCH | `/users/{id}` | Update user |
| DELETE | `/users/{id}` | Hapus user |

### Customers & Accounts

| Method | Path | Keterangan |
|---|---|---|
| GET | `/customers` | List semua customer |
| POST | `/customers` | Buat customer baru |
| GET | `/customers/{id}` | Detail customer |
| PATCH | `/customers/{id}` | Update customer |
| DELETE | `/customers/{id}` | Hapus customer |
| GET | `/customers/{id}/accounts` | List akun customer |
| POST | `/customers/{id}/accounts` | Tambah akun |
| PATCH | `/customers/{id}/accounts/{account_id}` | Update akun |
| DELETE | `/customers/{id}/accounts/{account_id}` | Hapus akun |

### Checks

| Method | Path | Keterangan |
|---|---|---|
| POST | `/checks/execute` | Jalankan check |
| GET | `/checks/available` | List check yang tersedia |

**Request body `POST /checks/execute`:**
```json
{
  "customer_ids": ["uuid"],
  "mode": "single|all|arbel",
  "check_name": "cost",
  "account_ids": ["uuid"],
  "send_slack": false,
  "check_params": {"window_hours": 12}
}
```

**Validation rules:**
- `customer_ids` tidak boleh kosong atau duplikat
- `mode=single` wajib menyertakan `check_name`
- `account_ids` (jika ada) tidak boleh duplikat
- Backward compat: `customer_id` (single string) masih diterima, dinormalisasi ke `customer_ids`

**Response:**
```json
{
  "check_runs": [{"id": "uuid", "customer_id": "uuid", ...}],
  "execution_time_seconds": 4.2,
  "results": {"profile-name": {"status": "OK", "summary": "...", ...}},
  "consolidated_outputs": ["...text lines..."]
}
```

### History

| Method | Path | Keterangan |
|---|---|---|
| GET | `/history?customer_id=...` | List riwayat check run (paginasi) |
| GET | `/history/{id}` | Detail check run + semua results |
| GET | `/history/{id}/report` | Regenerasi report teks dari data tersimpan |

### Findings, Metrics, Dashboard

| Method | Path | Keterangan |
|---|---|---|
| GET | `/findings?customer_id=...&check_name=...&severity=...` | List findings (filterable, paginasi) |
| GET | `/metrics?customer_id=...&check_name=...` | List metric samples (filterable) |
| GET | `/dashboard/summary?customer_id=...` | Agregasi KPI: total run, result, finding, metric |

### Alarms (Gmail Alert Forwarder Proxy)

| Method | Path | Keterangan |
|---|---|---|
| GET | `/alarms` | List alerts dari gmail-alert-forwarder |
| GET | `/alarms/{id}` | Detail alert |
| POST | `/alarms/{id}/dismiss` | Dismiss alert |
| POST | `/alarms/{id}/acknowledge` | Acknowledge alert |

Endpoint ini adalah proxy ke service `gmail-alert-forwarder` eksternal (URL dikonfigurasi via `ALERT_FORWARDER_URL`). Jika tidak dikonfigurasi, return 503.

### Mailing

| Method | Path | Keterangan |
|---|---|---|
| GET | `/mailing/contacts` | List kontak email |
| POST | `/mailing/contacts` | Tambah kontak |
| PATCH | `/mailing/contacts/{id}` | Update kontak |
| DELETE | `/mailing/contacts/{id}` | Hapus kontak |

### Tickets

| Method | Path | Keterangan |
|---|---|---|
| GET | `/tickets` | List tickets (filterable by customer, status) |
| POST | `/tickets` | Buat ticket baru |
| GET | `/tickets/{id}` | Detail ticket |
| PATCH | `/tickets/{id}` | Update ticket |
| DELETE | `/tickets/{id}` | Hapus ticket |

### Profiles & Sessions

| Method | Path | Keterangan |
|---|---|---|
| GET | `/profiles` | Deteksi AWS profile dari `~/.aws/config` |
| GET | `/sessions/health` | Cek status SSO session aktif |

### Settings

| Method | Path | Keterangan |
|---|---|---|
| GET | `/settings/runtime` | Get runtime settings |
| PATCH | `/settings/runtime` | Update runtime settings |

### Terminal

| Method | Path | Keterangan |
|---|---|---|
| WebSocket | `/terminal/ws` | PTY relay WebSocket untuk web terminal |

### Health

| Method | Path | Keterangan |
|---|---|---|
| GET | `/health` | Legacy health check |
| GET | `/health/liveness` | Liveness probe |
| GET | `/health/readiness` | Readiness probe (test koneksi DB `SELECT 1`) |

---

## Database Schema

### `users`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| username | string | Username unik |
| email | string | Email unik |
| hashed_password | string | bcrypt hash |
| role | string | `super_user` (admin) atau `user` (readonly) |
| is_active | bool | Aktif/nonaktif |
| created_at | timestamp | — |

### `customers`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| name | string | Slug unik, contoh: `aryanoble` |
| display_name | string | Nama tampilan |
| checks | JSON | List check keys untuk mode `all` |
| slack_webhook_url | string | URL webhook Slack |
| slack_channel | string | Channel Slack |
| slack_enabled | bool | Aktifkan notifikasi Slack |
| report_mode | string | `simple`, `summary`, `detailed` |
| label | string | Label opsional (`Enterprise`, `Trial`, dll) |
| sso_session | string | Nama SSO session AWS |

### `accounts`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| customer_id | UUID | FK → customers |
| profile_name | string | Nama AWS profile di `~/.aws/config` |
| account_id | string | AWS Account ID (12 digit) |
| display_name | string | Nama tampilan akun |
| is_active | bool | Aktif/nonaktif |
| auth_method | string | `sso`, `access_key`, `assume_role` |
| aws_access_key_id | string | Access key (untuk auth_method=access_key) |
| aws_secret_access_key_enc | string | Secret key ter-enkripsi (write-only, tidak pernah dikembalikan ke frontend) |
| config_extra | JSON | Konfigurasi tambahan, contoh: `{alarm_verification: {alarm_names: [...]}}` |

### `check_runs`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| customer_id | UUID | FK → customers |
| check_mode | string | `single`, `all`, `arbel` |
| check_name | string | Nama check (hanya mode `single`) |
| requested_by | string | Source request (default: `web`) |
| slack_sent | bool | Apakah notif Slack sudah terkirim |
| execution_time_seconds | float | Durasi eksekusi |
| created_at | timestamp | — |

### `check_results`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| check_run_id | UUID | FK → check_runs |
| account_id | UUID | FK → accounts |
| check_name | string | Nama check |
| status | string | `OK`, `WARN`, `ERROR`, `ALARM`, `NO_DATA` |
| summary | string | Ringkasan singkat |
| output | text | Output teks lengkap |
| details | JSON | Raw hasil check |

### `finding_events`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| check_run_id | UUID | FK → check_runs |
| account_id | UUID | FK → accounts |
| check_name | string | Sumber check: `guardduty`, `cloudwatch`, `notifications`, `backup` |
| finding_key | string | Kunci unik finding per check |
| severity | string | `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `ALARM` |
| title | string | Judul finding |
| description | text | Deskripsi detail |
| raw_payload | JSON | Payload mentah |

### `account_check_configs`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| account_id | UUID | FK → accounts |
| check_name | string | Nama check |
| config | JSON | Konfigurasi per-check per-akun |
| created_at / updated_at | timestamp | — |

### `tickets`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| customer_id | UUID | FK → customers (SET NULL on delete) |
| ticket_no | string | Nomor tiket Zoho (opsional) |
| task | string | Deskripsi task |
| pic | string | Nama PIC |
| status | string | `open`, `in_progress`, `done`, `cancelled` |
| description_solution | text | Deskripsi solusi |
| extra_data | JSON | Data tambahan (contoh Token: `{account_id, for_customer_id}`) |
| created_at / ended_at / updated_at | timestamp | — |

### `mailing_contacts`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| customer_id | UUID | FK → customers (nullable) |
| email | string | Alamat email |
| name | string | Nama penerima |
| created_at | timestamp | — |

### `metric_samples`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| check_run_id | UUID | FK → check_runs |
| account_id | UUID | FK → accounts |
| check_name | string | Sumber check (saat ini `daily-arbel`) |
| metric_name | string | Nama metrik (`CPUUtilization`, `FreeableMemory`, dll) |
| metric_status | string | Status evaluasi (`ok`, `warn`, dll) |
| value_num | float | Nilai numerik ter-normalisasi |
| unit | string | Unit (`Percent`, `Bytes`, `Count`) |
| resource_role | string | Role resource (`writer`, `reader`) |
| resource_id | string | ID resource |
| service_type | string | `rds` atau `ec2` |
| section_name | string | Nama section |
| raw_payload | JSON | Payload mentah |

---

## Authentication

### App Auth (User Login)

- JWT-based authentication
- Dua role: `super_user` (admin, akses penuh) dan `user` (readonly)
- Token dikirim via `Authorization: Bearer <token>` header
- Login via `POST /api/v1/auth/login`

### AWS Auth (per Customer)

- AWS auth terpisah dari app auth — per customer, bukan per user
- Tiga metode: `sso`, `access_key`, `assume_role`
- Rekomendasi customer baru: `assume_role` dengan role `MonitoringReadOnlyRole`
- SSO expired: deteksi via `/sessions/health`, kirim Slack notif, operator login manual:
  ```bash
  aws sso login --profile <profile> --use-device-code --no-browser
  ```

---

## Integrasi Slack

**File:** `backend/infra/notifications/slack/notifier.py`

Konfigurasi per customer: `slack_webhook_url`, `slack_channel`, `slack_enabled`.

Notifikasi dikirim saat:
- Check dijalankan dengan `send_slack: true`
- Session health check mendeteksi SSO expired (`GET /sessions/health?notify=true`)

---

## Konfigurasi Customer

### Default checks (semua customer baru)
```python
["cost", "guardduty", "cloudwatch", "notifications"]
```

### Customer dan konfigurasi khusus

| DB Name | Display | SSO Session | Akun | `report_mode` |
|---|---|---|---|---|
| `aryanoble` | Aryanoble | aryanoble-sso | 17 | `summary` |
| `ksni` | KSNI | Nabati | 17 | `summary` |
| `hungryhub` | HungryHub | HungryHub | 5 | `summary` |
| `fresnel` | Fresnel | sadewa-sso | 4 | `summary` |
| `ucoal` | uCoal | sadewa-sso | 4 | `summary` |
| `frisianflag` | Frisian Flag | non-SSO | 1 | `simple` |
| `diamond` | Diamond | sadewa-sso | 1 | `summary` |
| `techmeister` | Techmeister | sadewa-sso | 1 | `summary` |
| `kki` | KKI | sadewa-sso | 1 | `summary` |
| `bbi` | Bintang Bali Indah | sadewa-sso | 1 | `summary` |
| `edot` | eDot | sadewa-sso | 1 | `summary` |
| `programa` | Programa | sadewa-sso | 1 | `summary` |
| `nikp` | NIKP | non-SSO | 1 | `summary` |
| `rumahmedia` | Rumahmedia | non-SSO | 1 | `summary` |
| `asg` | Agung Sedayu | non-SSO | 1 | `summary` |
| `arista-web` | Arista Web | non-SSO | 1 | `summary` |
| `token` | Token | — | 0 | — |

**Token** adalah customer khusus ticketing. Tiket Token memerlukan field tambahan di `extra_data`: `account_id` (AWS Account ID) dan `for_customer_id` (customer yang dituju).

### Sandbox profiles (selalu di-skip)
```
sandbox, prod-sandbox, sandbox-ms-lebaran, sandbox-ics
```

---

## Cara Tambah Checker Baru

### Step 1 — Buat class checker

```python
# backend/checks/generic/my_check.py
from backend.checks.common.base import BaseChecker

class MyChecker(BaseChecker):
    report_section_title = "MY CHECK"
    issue_label = "my issues"
    recommendation_text = "MY REVIEW: ..."

    def check(self, profile, account_id) -> dict:
        try:
            session = self._get_session(profile)
            client = session.client("some-service", region_name=self.region)
            # ... AWS calls ...
            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "count": len(results),
                "details": results,
            }
        except Exception as e:
            return self._error_result(e, profile, account_id)

    def format_report(self, results: dict) -> str:
        """Output untuk single-check mode."""
        return f"Found {results.get('count', 0)} items"

    def count_issues(self, result: dict) -> int:
        """Untuk Executive Summary — berapa issues di result ini?"""
        return result.get("count", 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Untuk consolidated report — return text lines untuk section ini."""
        lines = [f"*{self.report_section_title}*"]
        for profile, result in all_results.items():
            count = result.get("count", 0)
            lines.append(f"  {profile}: {count} items")
        return lines
```

### Step 2 — Register di AVAILABLE_CHECKS

```python
# backend/domain/runtime/config.py
from backend.checks.generic.my_check import MyChecker

AVAILABLE_CHECKS = {
    # ...existing...
    "my-check": MyChecker,
}
```

### Step 3 — Status normalization (jika result shape non-standard)

Di `check_executor.py` → `_normalize_status()` dan `_build_summary()`, tambah branch untuk check name baru.

### Step 4 — Register untuk finding events (opsional)

```python
# backend/domain/finding_events.py
FINDING_EVENT_CHECKS = {"guardduty", "cloudwatch", "notifications", "backup", "my-check"}
```

Lalu implementasi `map_check_findings()` di `finding_events_mapper.py`.

---

## Cara Tambah API Endpoint Baru

### Backend

```python
# backend/interfaces/api/routes/my_feature.py
from fastapi import APIRouter, Depends
from backend.interfaces.api.dependencies import get_db, get_current_user

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.get("")
def list_my_feature(db=Depends(get_db), user=Depends(get_current_user)):
    ...
```

Register di `backend/interfaces/api/main.py`:
```python
from backend.interfaces.api.routes.my_feature import router as my_feature_router
app.include_router(my_feature_router, prefix="/api/v1")
```

### Frontend Proxy

```typescript
// frontend/app/api/my-feature/route.ts
import { NextRequest } from "next/server"
import { backendFetch } from "@/lib/api/backend-fetch"

export async function GET(req: NextRequest) {
  return backendFetch(req, "/api/v1/my-feature")
}
```

### TypeScript Types

Selalu update `frontend/lib/types/api.ts` dengan response shape baru.

---

## Testing

```bash
# Semua unit tests
uv run --with pytest --with httpx pytest \
  tests/unit/test_api_main.py \
  tests/unit/test_checks_route.py \
  tests/unit/test_check_executor.py \
  tests/unit/test_settings_runtime.py \
  tests/unit/test_src_adapters.py -q

# App import check
uv run python -c "from backend.interfaces.api.main import create_app; create_app()"

# Integration tests
uv run --with pytest --with httpx pytest tests/integration/ -q
```

---

## Common Pitfalls

| Situasi | Aturan |
|---|---|
| Tambah enum/literal ke API | Update Pydantic pattern + TypeScript type + frontend badge |
| Checker result pakai `display_name` | Jangan baca di dalam checker — executor inject `_account_display_name` setelah parallel execution |
| Mock `_run_single_check` di test | Return `{"status": "ok"}` — key `_checker_instance` tidak diperlukan |
| Field baru di checker result | Gunakan `result.get("key", default)` di seluruh downstream untuk backward compat |
| `check_params` dari API | Di-merge dengan `config_extra` dari DB; API values override DB |
| Alarm names untuk `alarm_verification` | Disimpan di `account.config_extra.alarm_verification.alarm_names`, BUKAN via `check_params` |
| Sandbox accounts | `sandbox`, `prod-sandbox`, `sandbox-ms-lebaran`, `sandbox-ics` selalu di-skip |
| Secret key AWS | Tidak pernah dikembalikan ke frontend — write-only field |
