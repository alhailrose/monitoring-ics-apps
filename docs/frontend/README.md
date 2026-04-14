# Frontend — Dokumentasi Lengkap

Next.js 15 (App Router) + TypeScript + shadcn/ui + Hugeicons + Tailwind CSS.

---

## Daftar Isi

- [Struktur Folder Frontend](#struktur-folder-frontend)
- [Semua Halaman Dashboard](#semua-halaman-dashboard)
- [Halaman Checks — Detail](#halaman-checks--detail)
- [API Proxy Layer](#api-proxy-layer)
- [Shared Components](#shared-components)
- [TypeScript Types](#typescript-types)
- [API Client Layer](#api-client-layer)
- [Auth Flow](#auth-flow)
- [Cara Tambah Halaman Baru](#cara-tambah-halaman-baru)
- [Cara Tambah Proxy API Baru](#cara-tambah-proxy-api-baru)
- [Konvensi UI](#konvensi-ui)
- [Development](#development)

---

## Struktur Folder Frontend

```
frontend/
├── app/
│   ├── (auth)/                     # Auth pages (login, dll)
│   │   └── login/page.tsx
│   ├── (dashboard)/                # Semua halaman dashboard (butuh auth)
│   │   ├── layout.tsx              # Dashboard layout: sidebar + header
│   │   ├── dashboard/page.tsx      # Halaman overview/KPI
│   │   ├── checks/                 # Halaman Checks (multi-tab)
│   │   │   ├── page.tsx
│   │   │   ├── actions.ts          # Server Actions untuk execute check
│   │   │   ├── specific/page.tsx   # Tab: Specific check (per customer, per check)
│   │   │   ├── bundled/page.tsx    # Tab: Bundled/all mode check
│   │   │   └── dedicated/
│   │   │       ├── arbel/page.tsx  # Halaman Arbel (4 sub-menu accordion)
│   │   │       └── huawei/page.tsx # Halaman Huawei check
│   │   ├── alarms/page.tsx         # Daftar alert dari gmail-alert-forwarder
│   │   ├── findings/page.tsx       # Normalized security/alert findings
│   │   ├── history/                # Riwayat check run
│   │   │   └── page.tsx
│   │   ├── metrics/page.tsx        # Metric samples (RDS/EC2 utilization)
│   │   ├── reports/page.tsx        # Report generation/view
│   │   ├── customers/              # Manajemen customer & akun
│   │   │   └── page.tsx
│   │   ├── ticketing/page.tsx      # Tiket / task tracking
│   │   ├── mailing/page.tsx        # Manajemen kontak email
│   │   ├── tasks/page.tsx          # Task management (internal)
│   │   ├── terminal/               # Web terminal (xterm.js + WebSocket)
│   │   ├── logout/                 # Logout handler
│   │   └── settings/               # Pengaturan
│   │       ├── aws-config/         # Konfigurasi AWS connection per akun
│   │       ├── users/              # Manajemen users (admin only)
│   │       ├── my-config/          # Profil user sendiri
│   │       └── invites/            # Invite management
│   └── api/                        # Next.js proxy routes ke backend FastAPI
│       ├── alarms/                 # → /api/v1/alarms
│       ├── customers/              # → /api/v1/customers
│       ├── discover-alarms/        # → /api/v1/... (alarm discovery)
│       ├── discover-full/          # → /api/v1/... (full discovery)
│       ├── discovery-snapshot/     # → /api/v1/... (snapshot)
│       ├── invites/                # → /api/v1/invites
│       ├── mailing/                # → /api/v1/mailing
│       ├── reports/                # → /api/v1/history/report
│       ├── sessions-health/        # → /api/v1/sessions/health
│       ├── settings/               # → /api/v1/settings/runtime
│       ├── terminal-token/         # → /api/v1/terminal/token
│       ├── test-connection/        # → /api/v1/test-connection
│       ├── tickets/                # → /api/v1/tickets
│       └── users/                  # → /api/v1/users
│
├── components/
│   ├── checks/                     # Komponen halaman Checks
│   │   └── ChecksTabs.tsx          # Tab navigator: Specific / Bundled / Dedicated
│   ├── common/                     # Komponen reusable umum
│   │   ├── PageHeader.tsx          # Header halaman (title + description)
│   │   └── ...
│   ├── customers/                  # Komponen customer management
│   ├── dashboard/                  # Komponen dashboard/KPI cards
│   ├── findings/                   # Tabel dan filter findings
│   ├── history/                    # Tabel riwayat check run
│   ├── metrics/                    # Chart/tabel metric samples
│   ├── tasks/                      # Task list components
│   ├── terminal/                   # xterm.js wrapper
│   ├── auth/                       # Auth-related components
│   ├── layout/                     # Layout components
│   ├── next-app/                   # Next.js specific wrappers
│   ├── onboarding/                 # Onboarding wizard
│   ├── providers/                  # Context providers (auth, theme)
│   ├── AlarmIndicator.tsx          # Alarm status badge
│   ├── app-sidebar.tsx             # Sidebar navigasi utama
│   ├── login-form.tsx              # Form login
│   ├── nav-main.tsx                # Main navigation items
│   ├── nav-projects.tsx            # Customer selector di sidebar
│   ├── nav-user.tsx                # User menu (profile, logout)
│   ├── team-switcher.tsx           # Customer context switcher
│   ├── theme-provider.tsx          # Dark/light mode provider
│   └── ui/                         # shadcn/ui components
│
├── lib/
│   ├── api/                        # API client functions
│   │   ├── client.ts               # Base fetch helper + auth header
│   │   ├── auth.ts                 # Login/logout/me API calls
│   │   ├── checks.ts               # Execute check, get available checks
│   │   ├── customers.ts            # Customer + account CRUD
│   │   ├── dashboard.ts            # Dashboard summary API
│   │   ├── findings.ts             # Findings query API
│   │   ├── history.ts              # History API
│   │   ├── metrics.ts              # Metrics API
│   │   └── sessions.ts             # Sessions health API
│   ├── types/
│   │   └── api.ts                  # Semua TypeScript types (source of truth)
│   ├── auth.ts                     # Auth helpers (token management)
│   ├── server-token.ts             # Server-side token retrieval
│   ├── session.ts                  # Session management
│   ├── schedule-utils.ts           # Jadwal/waktu utilities
│   ├── google-oauth.ts             # Google OAuth helpers
│   ├── mock/                       # Mock data untuk development
│   └── utils.ts                    # General utilities (cn, dll)
│
├── hooks/                          # Custom React hooks
├── public/                         # Static assets
├── next.config.ts                  # Next.js config
├── tailwind.config.ts              # Tailwind config
└── tsconfig.json                   # TypeScript config
```

---

## Semua Halaman Dashboard

### `/dashboard` — Overview

**File:** `frontend/app/(dashboard)/dashboard/page.tsx`

Halaman utama setelah login. Menampilkan:
- KPI summary card: total check runs, total results, total findings, total metrics
- Data diambil dari `GET /api/v1/dashboard/summary?customer_id=...`
- Customer bisa di-filter via context/selector

---

### `/checks` — Checks (Multi-Tab)

**File:** `frontend/app/(dashboard)/checks/page.tsx`
**Component:** `components/checks/ChecksTabs.tsx`

Halaman utama untuk menjalankan check. Menggunakan tabs:

| Tab | Path | Keterangan |
|---|---|---|
| Specific | `/checks/specific` | Jalankan satu check tertentu untuk customer + akun yang dipilih |
| Bundled | `/checks/bundled` | Jalankan semua check (mode `all`) untuk customer tertentu |
| Arbel | `/checks/dedicated/arbel` | Halaman khusus Aryanoble, 4 sub-menu accordion |
| Huawei | `/checks/dedicated/huawei` | Halaman khusus Huawei ECS utilization |

#### Tab: Specific Check (`/checks/specific`)

**File:** `frontend/app/(dashboard)/checks/specific/page.tsx`

Flow penggunaan:
1. Pilih customer dari dropdown
2. Pilih check dari daftar available checks
3. Pilih akun (bisa pilih semua atau subset)
4. Set parameter opsional (misal `window_hours` untuk daily-arbel)
5. Toggle "Send to Slack"
6. Klik Run → POST `/api/v1/checks/execute` dengan `mode: "single"`
7. Hasil ditampilkan: per-akun status badge + consolidated output text

#### Tab: Bundled Check (`/checks/bundled`)

**File:** `frontend/app/(dashboard)/checks/bundled/page.tsx`

Flow penggunaan:
1. Pilih customer
2. Pilih akun (opsional — default semua)
3. Toggle "Send to Slack"
4. Klik Run → POST `/api/v1/checks/execute` dengan `mode: "all"`
5. Hasil: consolidated report sesuai `report_mode` customer

#### Tab: Arbel (`/checks/dedicated/arbel`)

**File:** `frontend/app/(dashboard)/checks/dedicated/arbel/page.tsx`

Halaman eksklusif untuk customer Aryanoble. Menampilkan **4 accordion sub-menu**:

| Menu | Check | Keterangan |
|---|---|---|
| Backup Status | `backup` | Status AWS Backup jobs 24h terakhir |
| RDS / EC2 Metrics | `daily-arbel` | Monitoring metrik harian, opsi `window_hours` (6/12/24) |
| Alarm Verification | `alarm_verification` | Verifikasi alarm CloudWatch. Hanya akun dengan `alarm_names` di config_extra |
| Daily Budget | `daily-budget` | Cek threshold AWS Budgets |

Flow per sub-menu:
1. Klik accordion → expand
2. Account selector muncul (Select All default). Alarm Verification: hanya akun dengan `alarm_names`
3. Set opsi spesifik (misal `window_hours`)
4. Toggle Send to Slack
5. Klik Run → `POST /checks/execute` `mode: "single"`, `check_name: "<check>"`
6. Hasil: consolidated output + per-akun detail + status badge

#### Tab: Huawei (`/checks/dedicated/huawei`)

**File:** `frontend/app/(dashboard)/checks/dedicated/huawei/page.tsx`

Satu tombol run → menjalankan `huawei-ecs-util` untuk 10 akun Huawei fixed. Output: DAILY MONITORING REPORT consolidated.

---

### `/alarms` — Alarms

**File:** `frontend/app/(dashboard)/alarms/page.tsx`

Daftar alert dari **gmail-alert-forwarder** service eksternal. Menampilkan alert email yang sudah di-forward dan di-parse.

- Data diambil dari `GET /api/v1/alarms` (proxy ke alert-forwarder)
- Actions: acknowledge, dismiss per alert
- Jika `ALERT_FORWARDER_URL` tidak dikonfigurasi: tampil error 503

---

### `/findings` — Findings

**File:** `frontend/app/(dashboard)/findings/page.tsx`

Tabel normalized security/alert findings dari semua check run yang sudah disimpan di DB.

- Data dari `GET /api/v1/findings`
- Filter: `customer_id`, `check_name` (`guardduty`, `cloudwatch`, `notifications`, `backup`), `severity`
- Kolom: account, check, severity badge, title, description, tanggal
- Pagination tersedia

---

### `/history` — Riwayat Check Run

**File:** `frontend/app/(dashboard)/history/page.tsx`

Tabel semua check run yang pernah dijalankan via API.

- Data dari `GET /api/v1/history?customer_id=...`
- Kolom: customer, mode, check name, status, execution time, tanggal
- Klik row → detail check run + semua results per akun
- Tombol "View Report" → regenerasi report teks dari `GET /api/v1/history/{id}/report`

---

### `/metrics` — Metric Samples

**File:** `frontend/app/(dashboard)/metrics/page.tsx`

Tabel normalized metric samples dari check `daily-arbel`.

- Data dari `GET /api/v1/metrics?customer_id=...`
- Filter: customer, check name, account
- Kolom: account, metrik, nilai, unit, status, service type, tanggal

---

### `/reports` — Reports

**File:** `frontend/app/(dashboard)/reports/page.tsx`

Halaman untuk generate dan melihat report dari riwayat check run.

- Pilih check run → tampilkan report teks yang sudah di-generate
- Regenerate dari data tersimpan tanpa perlu re-run check

---

### `/customers` — Customer Management

**File:** `frontend/app/(dashboard)/customers/page.tsx`

CRUD lengkap untuk customer dan akun AWS mereka.

**Customer management:**
- List semua customer
- Buat customer baru (nama, display name, SSO session, report mode, Slack config)
- Edit / hapus customer

**Account management (nested di bawah customer):**
- List akun per customer
- Tambah akun (profile name, account ID, display name, auth method)
- Edit akun (termasuk toggle active/inactive)
- Hapus akun

---

### `/ticketing` — Ticketing

**File:** `frontend/app/(dashboard)/ticketing/page.tsx`

Sistem tiket internal untuk tracking pekerjaan operasional.

**Fields tiket:**
- Nomor tiket Zoho (opsional)
- Task / deskripsi pekerjaan
- PIC
- Status: `open`, `in_progress`, `done`, `cancelled`
- Deskripsi solusi
- Customer terkait

**Token special case:** Tiket dengan customer Token memerlukan:
- AWS Account ID
- "Untuk Customer" (customer yang dituju)
Data ini disimpan di field `extra_data`.

---

### `/mailing` — Mailing Contacts

**File:** `frontend/app/(dashboard)/mailing/page.tsx`

Manajemen daftar kontak email untuk keperluan notifikasi/laporan.

- List kontak (nama + email + customer terkait)
- Tambah, edit, hapus kontak

---

### `/tasks` — Tasks

**File:** `frontend/app/(dashboard)/tasks/page.tsx`

Task management internal (bukan customer ticket). Untuk tracking item kerja tim.

---

### `/settings/users` — Manajemen Users (Admin Only)

**File:** `frontend/app/(dashboard)/settings/users/`

- Hanya bisa diakses oleh `super_user`
- List semua users
- Buat user baru
- Edit role (super_user / user)
- Hapus user

---

### `/settings/aws-config` — Konfigurasi AWS

**File:** `frontend/app/(dashboard)/settings/aws-config/`

Konfigurasi AWS connection per akun. Di sinilah auth method per akun dikelola.

> **Catatan:** Backend model sudah siap (`auth_method`, `aws_access_key_id`, `aws_secret_access_key_enc`). Secret key adalah write-only — tidak pernah dikembalikan ke frontend.

---

### `/settings/my-config` — Profil User

**File:** `frontend/app/(dashboard)/settings/my-config/`

User bisa update profil sendiri: nama, email, password.

---

### `/settings/invites` — Invite Management

**File:** `frontend/app/(dashboard)/settings/invites/`

Invite user baru ke platform.

---

### Web Terminal

**File:** `frontend/components/terminal/`

Browser-based terminal menggunakan xterm.js + WebSocket ke `backend/interfaces/api/routes/terminal.py`.

- Relay ke PTY (pseudo-terminal) di server
- Akses via URL yang dikonfigurasi di dashboard
- Token auth diperlukan sebelum membuka koneksi WebSocket

---

## API Proxy Layer

**Semua request frontend ke backend melewati Next.js proxy routes** di `frontend/app/api/`.

Ini memastikan:
- Token auth tidak terekspos di client
- Backend URL tidak perlu diketahui browser
- Request bisa di-intercept untuk logging/transformasi

**Pattern proxy route:**
```typescript
// frontend/app/api/some-endpoint/route.ts
import { NextRequest } from "next/server"
import { backendFetch } from "@/lib/api/backend-fetch"

export async function GET(req: NextRequest) {
  return backendFetch(req, "/api/v1/some-endpoint")
}

export async function POST(req: NextRequest) {
  return backendFetch(req, "/api/v1/some-endpoint")
}
```

**Daftar proxy routes yang ada:**

| Proxy Path | Backend Endpoint | Keterangan |
|---|---|---|
| `/api/alarms` | `/api/v1/alarms` | Alert dari gmail-forwarder |
| `/api/customers` | `/api/v1/customers` | CRUD customers + accounts |
| `/api/discover-alarms` | `/api/v1/...` | Alarm discovery |
| `/api/discover-full` | `/api/v1/...` | Full resource discovery |
| `/api/discovery-snapshot` | `/api/v1/...` | Discovery snapshot |
| `/api/invites` | `/api/v1/invites` | Invite management |
| `/api/mailing` | `/api/v1/mailing` | Mailing contacts |
| `/api/reports` | `/api/v1/history/{id}/report` | Report generation |
| `/api/sessions-health` | `/api/v1/sessions/health` | SSO session health |
| `/api/settings` | `/api/v1/settings/runtime` | Runtime settings |
| `/api/terminal-token` | `/api/v1/terminal/token` | WebSocket auth token |
| `/api/test-connection` | `/api/v1/test-connection` | Test AWS connection |
| `/api/tickets` | `/api/v1/tickets` | Ticket CRUD |
| `/api/users` | `/api/v1/users` | User management |

---

## Shared Components

### `app-sidebar.tsx`

Sidebar navigasi utama. Berisi semua menu items:
- Dashboard
- Checks (dengan sub-items: Specific, Bundled, Arbel, Huawei)
- Alarms
- Findings
- History
- Metrics
- Reports
- Customers
- Ticketing
- Mailing
- Tasks
- Settings

Untuk menambah halaman baru ke sidebar, edit `components/app-sidebar.tsx`.

### `PageHeader.tsx`

Komponen header standar halaman:
```tsx
<PageHeader title="Checks" description="Run specific, bundled, or dedicated checks" />
```

### `ChecksTabs.tsx`

Tab navigator untuk halaman `/checks`. Props: `customers[]`.

### shadcn/ui Components (`components/ui/`)

Semua UI primitif: `Button`, `Table`, `Sheet`, `Badge`, `Dialog`, `Tabs`, `Select`, `Accordion`, `Card`, `Input`, `Label`, `Skeleton`, dll.

---

## TypeScript Types

**File:** `frontend/lib/types/api.ts` — **Single source of truth untuk semua types.**

Selalu update file ini ketika menambah response shape baru dari backend. Jangan mendefinisikan types inline di komponen.

**Types utama yang ada:**
- `Customer`, `Account` — customer + account shape
- `CheckRun`, `CheckResult` — check execution hasil
- `FindingEvent` — normalized finding
- `MetricSample` — normalized metric
- `DashboardSummary` — KPI aggregation
- `CheckMode`, `ReportMode` — literal types untuk enums
- `AvailableCheck` — check registry item
- `Ticket`, `MailingContact` — entitas lain

---

## API Client Layer

**Directory:** `frontend/lib/api/`

Semua call ke backend (via proxy) menggunakan helper di folder ini.

### `client.ts` — Base Fetch

```typescript
// Attach auth token, handle errors
export async function apiGet(path: string, token?: string): Promise<Response>
export async function apiPost(path: string, body: unknown, token?: string): Promise<Response>
```

### `checks.ts`

```typescript
export async function executeCheck(payload: ExecuteCheckRequest, token: string)
export async function getAvailableChecks(token: string): Promise<AvailableCheck[]>
```

### `customers.ts`

```typescript
export async function getCustomers(token: string): Promise<Customer[]>
export async function getCustomer(id: string, token: string): Promise<Customer>
export async function createCustomer(data: CreateCustomerRequest, token: string)
// ... update, delete, accounts CRUD
```

### `findings.ts`

```typescript
export async function getFindings(params: FindingQueryParams, token: string)
```

### `history.ts`

```typescript
export async function getHistory(params: HistoryQueryParams, token: string)
export async function getHistoryDetail(id: string, token: string)
```

### `dashboard.ts`

```typescript
export async function getDashboardSummary(customerId: string, token: string)
```

---

## Auth Flow

1. User akses halaman protected → middleware cek token
2. Tidak ada token → redirect ke `/login`
3. Login form → `POST /api/v1/auth/login` → JWT token
4. Token disimpan (cookie/session)
5. Semua request selanjutnya attach `Authorization: Bearer <token>`
6. `server-token.ts` — helper untuk ambil token di server component
7. Logout → `POST /api/v1/auth/logout` + clear token

---

## Cara Tambah Halaman Baru

### Step 1 — Buat halaman

```
frontend/app/(dashboard)/my-page/
  page.tsx
  loading.tsx       # opsional skeleton
  error.tsx         # opsional error boundary
  components/       # opsional komponen spesifik halaman
```

```typescript
// frontend/app/(dashboard)/my-page/page.tsx
import { getToken } from '@/lib/server-token'
import { PageHeader } from '@/components/common/PageHeader'

export default async function MyPage() {
  const token = await getToken()
  // fetch data...

  return (
    <div className="space-y-6 p-6">
      <PageHeader title="My Page" description="..." />
      {/* content */}
    </div>
  )
}
```

### Step 2 — Tambah ke sidebar

Edit `frontend/components/app-sidebar.tsx`. Tambah item ke navigation array yang sesuai.

### Step 3 — Tambah types (jika ada data shape baru)

Update `frontend/lib/types/api.ts`.

### Step 4 — Tambah API client function (jika perlu)

Tambah function di `frontend/lib/api/` untuk call ke backend.

---

## Cara Tambah Proxy API Baru

```
frontend/app/api/my-feature/
  route.ts
```

```typescript
// frontend/app/api/my-feature/route.ts
import { NextRequest } from "next/server"
import { backendFetch } from "@/lib/api/backend-fetch"

export async function GET(req: NextRequest) {
  return backendFetch(req, "/api/v1/my-feature")
}

export async function POST(req: NextRequest) {
  return backendFetch(req, "/api/v1/my-feature")
}
```

---

## Konvensi UI

| Aspek | Aturan |
|---|---|
| Komponen UI | Gunakan shadcn/ui (`Button`, `Table`, `Sheet`, `Badge`, `Dialog`, `Tabs`, dll) |
| Icons | Hugeicons library |
| Styling | Tailwind CSS utility classes |
| Status badge | `Badge` component dengan variant sesuai: `OK`→success, `WARN`→warning, `ERROR`→destructive |
| Loading state | `Skeleton` component atau `loading.tsx` |
| Error state | `error.tsx` dengan `useErrorBoundary` |
| Data fetch | Server components untuk initial fetch, client components untuk interaktif |
| Auth | `getToken()` dari `lib/server-token.ts` di server components |
| Types | Semua types di `lib/types/api.ts` — tidak mendefinisikan inline |
| Enum literals | Selalu update jika backend menambah nilai baru (misal `report_mode`, `check_mode`) |

---

## Development

```bash
# Install dependencies
cd frontend && npm install

# Run dev server
npm run dev   # http://localhost:3000

# TypeCheck (CI gate — wajib lulus)
npm run typecheck

# Build
npm run build
```

**Environment variables** (`frontend/.env.local`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Di production, API URL diarahkan via nginx proxy.
