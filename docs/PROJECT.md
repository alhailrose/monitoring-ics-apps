# Monitoring Hub — Dokumentasi Project

## Gambaran Umum

Monitoring Hub adalah platform monitoring AWS terpusat untuk multiple customer. Platform ini memiliki **dua interface**:

1. **TUI (Terminal User Interface)** — interface interaktif berbasis terminal, dijalankan langsung di mesin operator
2. **Web Platform** — REST API (FastAPI) + frontend React, dapat diakses via browser

Keduanya menjalankan check yang sama dari `backend/checks/` sebagai lokasi kanonis.

## Status Operasional (sumber kebenaran harian)

- Runtime API kanonis di `backend/interfaces/api/`; `apps/api/main.py` adalah wrapper tipis app entrypoint.
- Runtime TUI/CLI kanonis di `backend/interfaces/cli/`; `apps/tui/main.py` adalah wrapper tipis app entrypoint.
- Execution policy saat ini: TUI non-persistent (tidak menulis DB), API persistent (menulis DB).
- Endpoint findings normalisasi tersedia: `GET /api/v1/findings` (termasuk `backup` via filter `check_name=backup`).
- Endpoint metrics normalisasi tersedia: `GET /api/v1/metrics`.
- Endpoint dashboard summary tersedia: `GET /api/v1/dashboard/summary`.
- Runtime web aktif tetap di `web/`; `apps/web/` masih scaffold migrasi bertahap.
- Deploy single server saat ini menggunakan `postgres + api + nginx` (tanpa worker/redis terpisah).
- Rilis dipisah per target dengan workflow gate `deploy-manual` + checklist bukti di `docs/operations/release-checklist.md`.

---

## Struktur Folder (ringkas, current-state)

```text
monitoring-ics-apps/
├── backend/                    # Canonical implementation (API/CLI/domain/infra/config)
│   ├── interfaces/
│   ├── domain/
│   ├── infra/
│   └── config/
├── apps/                       # App-level scaffold (api/tui/web)
├── web/                        # Frontend React runtime (aktif)
├── docs/
├── configs/
├── alembic/
├── scripts/
├── tests/
└── infra/docker/
```

Catatan:
- Entrypoint package `monitoring-hub` kini langsung ke `backend.interfaces.cli.main`.
- Namespace runtime python `src/*` sudah dicutover penuh.

---

## Arsitektur

```
Browser
  │
  ▼
nginx :8080
  ├── /api/*  ──► FastAPI :8000  ──► PostgreSQL :5432
  └── /*      ──► React SPA (static dist/)

Terminal
  │
  ▼
TUI (Textual) / CLI
  └── backend/interfaces/cli/main.py
        └── backend/domain/runtime/*
              └── backend/checks/**
```

### Web Platform

- **Frontend**: React 18 + TypeScript + Vite, tanpa router library (client-side routing manual via `History API`)
- **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic, eksekusi sinkron (tanpa job queue)
- **Database**: PostgreSQL 16 (via Docker)
- **Deployment**: Docker Compose (postgres + api + nginx)

### TUI

- Dijalankan langsung: `monitoring-hub` atau `python -m backend.interfaces.cli.main`
- Menggunakan Textual untuk UI terminal interaktif
- Tidak memerlukan database atau Docker

---

## Database Schema

### `customers`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| name | string | Identifier unik (slug), contoh: `aryanoble`, `ksni` |
| display_name | string | Nama tampilan, contoh: `Aryanoble`, `KSNI` |
| checks | JSON | List check yang dijalankan di mode `all` |
| slack_webhook_url | string | URL webhook Slack (opsional) |
| slack_channel | string | Channel Slack (opsional) |
| slack_enabled | bool | Aktifkan notifikasi Slack |

### `accounts`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| customer_id | UUID | FK ke customers |
| profile_name | string | Nama AWS profile di `~/.aws/config` |
| account_id | string | AWS Account ID (12 digit) |
| display_name | string | Nama tampilan akun |
| is_active | bool | Aktif/nonaktif |
| config_extra | JSON | Konfigurasi tambahan (contoh: `daily_arbel` untuk Aryanoble) |

### `check_runs`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| customer_id | UUID | FK ke customers |
| check_mode | string | `single`, `all`, atau `arbel` |
| check_name | string | Nama check (hanya untuk mode `single`) |
| requested_by | string | Sumber request, default `web` |
| slack_sent | bool | Apakah sudah dikirim ke Slack |
| execution_time_seconds | float | Durasi eksekusi |

### `check_results`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| check_run_id | UUID | FK ke check_runs |
| account_id | UUID | FK ke accounts |
| check_name | string | Nama check |
| status | string | `OK`, `WARN`, `ERROR`, `ALARM`, `NO_DATA` |
| summary | string | Ringkasan singkat |
| output | text | Output teks lengkap |
| details | JSON | Data mentah hasil check |

### `finding_events`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| check_run_id | UUID | FK ke check_runs |
| account_id | UUID | FK ke accounts |
| check_name | string | Sumber check (`guardduty`, `cloudwatch`, `notifications`, `backup`) |
| finding_key | string | Kunci temuan unik per check |
| severity | string | `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `ALARM` |
| title | string | Judul temuan |
| description | text | Deskripsi temuan |
| raw_payload | JSON | Payload mentah untuk analitik |

### `account_check_configs`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| account_id | UUID | FK ke accounts |
| check_name | string | Nama check yang dikonfigurasi |
| config | JSON | Konfigurasi per-check per-account |
| created_at | timestamp | Waktu dibuat |
| updated_at | timestamp | Waktu diubah |

### `metric_samples`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| check_run_id | UUID | FK ke check_runs |
| account_id | UUID | FK ke accounts |
| check_name | string | Sumber check (saat ini `daily-arbel`) |
| metric_name | string | Nama metrik, contoh `CPUUtilization` |
| metric_status | string | Status evaluasi metrik (`ok/warn/...`) |
| value_num | float | Nilai numerik ter-normalisasi |
| unit | string | Unit metrik (`Percent`, `Bytes`, `Count`) |
| resource_role | string | Role resource (contoh `writer`) |
| resource_id | string | ID resource |
| service_type | string | Jenis service (`rds`/`ec2`) |
| section_name | string | Nama section sumber |
| raw_payload | JSON | Payload metrik mentah |

---

## API Endpoints

Base URL: `http://localhost:8000/api/v1`

### Customers
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

Request body `POST /checks/execute`:
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

Compatibility: payload lama dengan field `customer_id` (single string) masih diterima dan dinormalisasi otomatis ke `customer_ids`.

Contract validation untuk endpoint ini:
- `customer_ids` tidak boleh kosong/duplikat
- `mode=single` wajib menyertakan `check_name`
- `account_ids` (jika ada) tidak boleh duplikat
- response tervalidasi konsisten (`check_runs`, `execution_time_seconds`, `results`, `consolidated_outputs`)

Field `check_params` (opsional): parameter tambahan yang dikirim ke checker constructor. Merge dengan `config_extra` dari DB (API override DB). Contoh:
- `{"window_hours": 6}` → `DailyArbelChecker(window_hours=6)`
- `{"min_duration_minutes": 15}` → `AlarmVerificationChecker(min_duration_minutes=15)`

Alarm names tidak perlu dikirim via `check_params` — sudah tersimpan di `config_extra.alarm_verification.alarm_names` per akun.

### History
| Method | Path | Keterangan |
|---|---|---|
| GET | `/history?customer_id=...` | List riwayat check run |
| GET | `/history/{id}` | Detail check run |
| GET | `/history/{id}/report` | Regenerasi report teks dari data tersimpan |

### Findings, Metrics, Dashboard
| Method | Path | Keterangan |
|---|---|---|
| GET | `/findings?customer_id=...` | List findings normalisasi (filterable) |
| GET | `/metrics?customer_id=...` | List metric samples normalisasi (filterable) |
| GET | `/dashboard/summary?customer_id=...` | Agregasi KPI run/result/finding/metric |

### Profiles & Sessions
| Method | Path | Keterangan |
|---|---|---|
| GET | `/profiles` | Deteksi AWS profile dari `~/.aws/config` |
| GET | `/sessions/health` | Cek status SSO session |

### Platform Health
| Method | Path | Keterangan |
|---|---|---|
| GET | `/health` | Legacy health endpoint (kompatibilitas) |
| GET | `/health/liveness` | Liveness probe untuk container/orchestrator |
| GET | `/health/readiness` | Readiness probe (validasi koneksi DB `SELECT 1`) |

---

## Check Modes

| Mode | Keterangan |
|---|---|
| `single` | Satu check, satu atau beberapa akun. Output detail per akun. |
| `all` | Semua check yang dikonfigurasi di `customer.checks`, semua akun. Output consolidated report. |
| `arbel` | Preset khusus Aryanoble: check `cost`, `guardduty`, `cloudwatch`, `notifications`, `backup`, `daily-arbel`. |

---

## Available Checks

| Nama | Kelas | Keterangan |
|---|---|---|
| `cost` | `CostAnomaliesChecker` | Deteksi anomali biaya AWS |
| `guardduty` | `GuardDutyChecker` | Temuan GuardDuty aktif |
| `cloudwatch` | `CloudWatchAlarmsChecker` | Alarm CloudWatch dalam status ALARM |
| `notifications` | `NotificationsChecker` | Notifikasi AWS Health Events |
| `backup` | `BackupStatusChecker` | Status AWS Backup jobs |
| `daily-arbel` | `DailyArbelChecker` | Monitoring metrik RDS & EC2 harian. Param: `window_hours` (default 12) |
| `alarm_verification` | `AlarmVerificationChecker` | Verifikasi status CloudWatch alarm & riwayat breach. Param: `alarm_names` (dari DB), `min_duration_minutes` (default 10) |
| `daily-budget` | `DailyBudgetChecker` | Cek threshold AWS Budgets & alert over-budget |

---

## Arbel Page — 4 Sub-Menu

Halaman Arbel (`/checks/arbel`) menampilkan 4 menu accordion (collapsible card). User memilih satu menu → sub-menu expand dengan account selector + opsi spesifik → tombol Run per menu.

| Menu | Check Name | Keterangan |
|---|---|---|
| Backup Status | `backup` | Cek status AWS Backup job. Semua akun aktif. |
| RDS / EC2 Metrics | `daily-arbel` | Monitoring metrik harian. Opsi: `window_hours` (6/12/24 jam). |
| Alarm Verification | `alarm_verification` | Verifikasi alarm CloudWatch. Hanya akun yang punya `alarm_names` di `config_extra`. |
| Daily Budget | `daily-budget` | Cek threshold AWS Budgets. Semua akun aktif. |

### Alur Eksekusi Arbel

1. Halaman load → fetch customer Aryanoble dari API
2. User klik salah satu menu → accordion expand
3. Account selector muncul (Select All default on). Untuk Alarm Verification, hanya akun dengan `alarm_names` yang tampil.
4. User set opsi (misal `window_hours` untuk RDS) dan toggle Send to Slack
5. Klik "Run [Menu Name]" → `POST /checks/execute` dengan `mode: "single"`, `check_name: "[check]"`, `check_params: {...}`
6. Hasil ditampilkan: consolidated output + per-akun detail dengan status badge

### config_extra untuk Alarm Verification

Alarm names disimpan di DB per akun:
```json
{
  "alarm_verification": {
    "alarm_names": ["alarm-1", "alarm-2", "..."]
  }
}
```

Seed via `python -m scripts.seed_alarms` (query AWS CloudWatch per akun Aryanoble).

---

## Konfigurasi Customer

### Default checks (semua customer baru)
```python
["cost", "guardduty", "cloudwatch", "notifications"]
```

### Aryanoble
```python
["cost", "guardduty", "cloudwatch", "notifications", "backup", "daily-arbel"]
```

### Sandbox profiles yang selalu di-skip
```
sandbox, prod-sandbox, sandbox-ms-lebaran, sandbox-ics
```

---

## Cara Menjalankan

### Development (lokal)

**1. Jalankan PostgreSQL:**
```bash
docker compose -f infra/docker/docker-compose.yml up -d postgres
```

**2. Jalankan migrasi database:**
```bash
DATABASE_URL=postgresql+psycopg://monitor:monitor@localhost:5432/monitoring \
  alembic upgrade head
```

**3. Seed database dari `~/.aws/config`:**
```bash
python -m scripts.seed_database
```

**4. Jalankan backend API:**
```bash
DATABASE_URL=postgresql+psycopg://monitor:monitor@localhost:5432/monitoring \
  uvicorn backend.interfaces.api.main:app --reload --port 8000
```

**5. Jalankan frontend:**
```bash
cd web
npm install
 npm run dev   # http://localhost:4173
```

### Production (Docker Compose)

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

Akses di `http://localhost:8080`

### TUI

```bash
pip install -e .
monitoring-hub
```

Command setup customer di TUI/CLI:

```bash
monitoring-hub customer scan
monitoring-hub customer assign <customer_id>
monitoring-hub customer checks <customer_id>
monitoring-hub customer validate <customer_id>
```

Perilaku selection terbaru pada Customer Report:
- sumber akun dari customer mapping YAML
- checks dan akun default tidak auto selected
- tersedia search keyword + aksi pilih massal (`select all` / `clear all`)

Perilaku menu Huawei Check (TUI):
- main menu: `Huawei Check`
- submenu: `Utilization`
- `Utilization` menjalankan check `huawei-ecs-util` untuk 10 akun Huawei fixed dan output ditampilkan sebagai satu `DAILY MONITORING REPORT` consolidated
- akun fixed: `dh_log-ro`, `dh_prod_nonerp-ro`, `afco_prod_erp-ro`, `afco_dev_erp-ro`, `dh_prod_network-ro`, `dh_prod_erp-ro`, `dh_hris-ro`, `dh_dev_erp-ro`, `dh_master-ro`, `dh_mobileapps-ro`

---

## Integrasi Slack

Setiap customer dapat dikonfigurasi dengan `slack_webhook_url` dan `slack_channel`. Notifikasi dikirim via `send_to_webhook(url, text, channel)` di `backend/infra/notifications/slack/notifier.py`.

Notifikasi dikirim:
- Saat check dijalankan dengan `send_slack: true`
- Saat session health check mendeteksi SSO expired (via `GET /sessions/health?notify=true`)

---

## Testing

```bash
# Jalankan semua tests
pytest tests/

# E2E API tests
pytest tests/integration/test_e2e_api.py

# Endpoint integration tests
pytest tests/integration/test_new_endpoints.py

# Frontend tests
cd web && npm test

# Frontend quality gates
cd web && npm run typecheck
cd web && npm run lint
cd web && npm run format:check
```

---

## Daftar Customer

| DB Name | Display Name | SSO Session | Jumlah Akun |
|---|---|---|---|
| `diamond` | Diamond | sadewa-sso | 1 |
| `techmeister` | Techmeister | sadewa-sso | 1 |
| `fresnel` | Fresnel | sadewa-sso | 4 |
| `kki` | KKI | sadewa-sso | 1 |
| `bbi` | Bintang Bali Indah | sadewa-sso | 1 |
| `edot` | eDot | sadewa-sso | 1 |
| `ucoal` | uCoal | sadewa-sso | 4 |
| `programa` | Programa | sadewa-sso | 1 |
| `aryanoble` | Aryanoble | aryanoble-sso | 17 |
| `ksni` | KSNI | Nabati | 17 |
| `hungryhub` | HungryHub | HungryHub | 5 |
| `nikp` | NIKP | non-SSO | 1 |
| `rumahmedia` | Rumahmedia | non-SSO | 1 |
| `asg` | Agung Sedayu | non-SSO | 1 |
| `arista-web` | Arista Web | non-SSO | 1 |
| `frisianflag` | Frisian Flag Indonesia | non-SSO | 1 |
