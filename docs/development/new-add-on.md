# Dashboard Add-ons — Frontend Changes

Dokumen ini mencatat penambahan fitur pada halaman Dashboard yang membutuhkan data dari backend.

---

## 1. Recent History

**Komponen:** `frontend/components/dashboard/RecentHistory.tsx`

Menampilkan 5 run terakhir untuk customer yang dipilih.

**Endpoint yang digunakan:**
```
GET /api/v1/history?customer_id={id}&limit=5
```

**Data yang ditampilkan:**
- `check_name` — nama check yang dijalankan
- `check_mode` — mode run (specific / all / arbel)
- `created_at` — waktu run
- `results_summary.ok`, `results_summary.warn`, `results_summary.error` — jumlah hasil per status

---

## 2. Account Overview (gabungan Findings + Results)

**Komponen:** `frontend/components/dashboard/AccountOverview.tsx`

Menampilkan daftar akun yang memiliki findings atau hasil check non-OK. Akun clean (semua OK, tidak ada findings) tidak ditampilkan. Tiap akun punya tombol "Detail" untuk expand panel yang menampilkan findings dan check results sekaligus.

**Endpoint yang digunakan:**
```
GET /api/v1/findings?customer_id={id}&limit=100
GET /api/v1/history?customer_id={id}&limit=1        ← ambil run terakhir
GET /api/v1/history/{run_id}                         ← ambil detail results per akun
```

**Data yang ditampilkan per akun:**
- `account.display_name` — nama akun AWS
- Findings: `check_name`, `severity`, `title`, `description`
- Results: `check_name`, `status`, `summary`

**Highlight logic:**
- CRITICAL findings → border merah
- HIGH findings → border oranye
- ERROR/ALARM results → border merah
- WARN results → border kuning
- Akun clean → tidak muncul di list

**Catatan untuk backend:**
- Field `summary` pada `CheckResult` sangat penting untuk UX — pastikan semua check mengisi field ini.
- Jika findings bisa sangat banyak (>100), pertimbangkan endpoint summary per account.

---

## 5. Report Schedule / Task System (Backend Belum Ada — UI Mock)

**Komponen:** `frontend/components/dashboard/ReportReminder.tsx`

Card ke-4 di stat cards menampilkan jadwal pengiriman report per customer. Saat ini menggunakan mock data. Ketika backend siap, ganti fungsi `getMockSchedules` di `dashboard/page.tsx` dengan API call nyata.

### Endpoint yang dibutuhkan (BELUM ADA — perlu dibuat di backend)

#### GET `/api/v1/tasks/schedules`
Ambil semua jadwal report.

Query params:
- `customer_id` (optional) — filter per customer

Response:
```json
[
  {
    "id": "uuid",
    "customer_id": "uuid",
    "customer_name": "Acme Corp",
    "interval_hours": 12,
    "last_report_sent_at": "2024-01-15T10:00:00Z",
    "last_check_run_at": "2024-01-15T09:00:00Z",
    "report_sent_with_last_run": true
  }
]
```

#### POST `/api/v1/tasks/schedules`
Buat jadwal baru (super_user only).

Body:
```json
{
  "customer_id": "uuid",
  "interval_hours": 12
}
```

#### PATCH `/api/v1/tasks/schedules/{id}`
Update interval jadwal (super_user only).

Body:
```json
{
  "interval_hours": 3
}
```

#### DELETE `/api/v1/tasks/schedules/{id}`
Hapus jadwal (super_user only).

### Auto-checklist logic

Ketika check dijalankan (`POST /checks/execute`), backend harus:
1. Cek apakah customer punya jadwal aktif
2. Jika ya, set `report_sent_with_last_run = true` dan update `last_report_sent_at` ke waktu sekarang
3. Frontend akan otomatis menampilkan status "sent" di ReportReminder card

### Database schema yang dibutuhkan

```sql
CREATE TABLE task_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    interval_hours INTEGER NOT NULL DEFAULT 12,
    last_report_sent_at TIMESTAMPTZ,
    last_check_run_at TIMESTAMPTZ,
    report_sent_with_last_run BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

---

## 7. Check Execution — Revisi Phase 4 (Frontend)

### Perubahan dari versi sebelumnya

#### 7.1 Multi-Customer Support

Semua form check sekarang mendukung **multi-customer** — user bisa memilih lebih dari satu customer sekaligus. Backend sudah mendukung ini via `customer_ids: string[]` di `POST /checks/execute`.

#### 7.2 Specific Check (revisi)

**Komponen:** `frontend/components/checks/SpecificCheckForm.tsx`

- User memilih **satu check name** (guardduty, cloudwatch_alarms, dll)
- User memilih **satu atau lebih customer** (toggle button)
- Per customer, user bisa memilih **akun spesifik** atau biarkan kosong (semua akun)
- Hasil ditampilkan sebagai tabel detail per akun dengan status badge

**Endpoint:** `POST /api/v1/checks/execute` dengan `mode: "single"`

#### 7.3 Bundled Check (revisi — fokus daily reporting)

**Komponen:** `frontend/components/checks/BundledCheckForm.tsx`

- User memilih **mode** (`all` atau `arbel`) dan **satu atau lebih customer**
- Hasil ditampilkan sebagai **per-customer report card** yang bisa di-expand/collapse
- Setiap card punya tombol **Copy** untuk copy report ke clipboard tanpa harus expand
- Report format adalah plain-text yang bisa langsung dikirim/disimpan
- Jika banyak customer, semua muncul sebagai card terpisah

**Endpoint:** `POST /api/v1/checks/execute` dengan `mode: "all"` atau `mode: "arbel"`

**Catatan backend:** Field `consolidated_outputs` di response sangat berguna untuk report — pastikan diisi dengan output yang sudah diformat per customer.

#### 7.4 Dedicated Checks (BARU)

**Komponen:** `frontend/components/checks/DedicatedCheckForm.tsx`

Menu baru **Dedicated Checks** di sidebar untuk check yang spesifik per customer/platform:

##### Arbel Check (`/checks/dedicated/arbel`)
Check khusus untuk customer Arya Noble:
- `daily_arbel` — full daily utilization analysis
- `daily_budget` — budget monitoring
- `alarm_verification` — CloudWatch alarm verification

**Endpoint:** `POST /api/v1/checks/execute` dengan `mode: "arbel"` dan `check_name` sesuai pilihan

##### Huawei Check (`/checks/dedicated/huawei`)
Check khusus untuk Huawei Cloud:
- `huawei_ecs_utilization` — ECS instance utilization

**Endpoint:** `POST /api/v1/checks/execute` dengan `mode: "huawei"` dan `check_name: "huawei_ecs_utilization"`

**Catatan backend — mode baru yang dibutuhkan:**

Backend perlu mendukung mode tambahan di `POST /checks/execute`:

| `mode` | `check_name` | Keterangan |
|---|---|---|
| `arbel` | `daily_arbel` | Full Arbel daily check (sudah ada) |
| `arbel` | `daily_budget` | Budget check saja |
| `arbel` | `alarm_verification` | Alarm verification saja |
| `huawei` | `huawei_ecs_utilization` | Huawei ECS utilization |

Jika backend belum mendukung `mode: "huawei"`, tambahkan handler di `backend/checks/huawei/ecs_utilization.py`.

#### 7.5 Sidebar Navigation (revisi)

Struktur menu Checks sekarang:
```
Checks (collapsible)
├── Specific Checks    → /checks/specific
├── Bundled Checks     → /checks/bundled
└── Dedicated Checks   (collapsible)
    ├── Arbel Check    → /checks/dedicated/arbel
    └── Huawei Check   → /checks/dedicated/huawei
```

---

## 6. Perubahan Layout Dashboard

Dashboard page (`frontend/app/(dashboard)/dashboard/page.tsx`) sekarang melakukan fetch paralel:

```
Promise.all([
  getDashboardSummary(customerId, 24, token),   // stat cards
  getHistory({ customer_id, limit: 5 }, token), // recent history + latest run id
  getFindings({ customer_id, limit: 100 }, token), // account findings
])
+ getRunDetail(latestRunId, token)               // account results (sequential, butuh run_id dulu)
```

**Potensi optimasi backend:**
- Endpoint `/dashboard/summary` bisa diperluas untuk menyertakan `top_findings_by_account` agar tidak perlu fetch `/findings` terpisah.
- Atau tambah endpoint `/dashboard/account-status` yang mengembalikan status per akun secara agregat.
