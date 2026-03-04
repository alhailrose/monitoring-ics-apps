# Frontend Session Handoff Prompt

Copy-paste this prompt to start a new session for frontend implementation:

---

## Prompt

Saya sedang mengerjakan project monitoring AWS di `/home/heilrose/Work/Project/monitoring-ics-apps/.worktrees/dual-interface-platform`.

Backend API sudah selesai diimplementasi ulang. Sekarang saya butuh bantuan untuk rebuild frontend (React/TypeScript) agar sesuai dengan backend baru.

### Context

Project ini adalah AWS Monitoring Hub - platform monitoring untuk multi-account AWS. Sebelumnya menggunakan async job queue, sekarang sudah diubah ke synchronous execution.

### Backend API yang sudah ready

Base URL: `http://localhost:8080/api/v1`

**Endpoints:**

1. **Customer Management**
   - `GET /customers` - List semua customer + accounts
   - `GET /customers/{id}` - Detail customer
   - `POST /customers` - Buat customer baru
   - `PATCH /customers/{id}` - Update customer
   - `DELETE /customers/{id}` - Hapus customer
   - `POST /customers/{id}/accounts` - Tambah account ke customer
   - `PATCH /accounts/{id}` - Update account
   - `DELETE /accounts/{id}` - Hapus account

2. **Check Execution (Synchronous)**
   - `POST /checks/execute` - Execute monitoring checks
     - mode: "single" (1 check), "all" (template checks), "arbel" (aryanoble-specific)
     - Bisa pilih specific accounts atau semua
     - Toggle Slack on/off
     - Response langsung berisi results (bukan job ID)
   - `GET /checks/available` - List available check types

3. **History**
   - `GET /history?customer_id=...&start_date=...&end_date=...` - Paginated history
   - `GET /history/{check_run_id}` - Detail hasil check run

4. **Profile Detection**
   - `GET /profiles/detect` - Scan ~/.aws/config, return mapped vs unmapped profiles

### Yang perlu dibangun

Baca dokumen implementasi frontend di `docs/implementation/FRONTEND-IMPLEMENTATION.md` untuk detail lengkap.

**Pages yang dibutuhkan:**
1. Home - Navigation cards
2. Single Check - Pilih customer, check type, accounts, toggle Slack, run
3. All Check - Pilih customer, run template checks (cost, guardduty, notifications, alarm)
4. Arbel Check - Khusus Aryanoble, run full suite
5. Customer Management - CRUD customers + accounts
6. Profile Detection - Scan AWS profiles, d
7. History - Filter by customer/date/check, lihat detail results

**Key Requirements:**
- Output check harus berupa text yang bisa di-copy (bukan formatted cards)
- Status badges: OK=green, WARN=yellow, ERROR=red, ALARM=orange
- Dark theme
- Loading states saat execution (bisa beberapa menit)
- Error handling yang user-friendly
- Responsive layout

**Existing web/ directory** sudah ada di worktree, tapi perlu di-rebuild sesuai backend baru. Cek dulu apa yang ada, lalu sesuaikan.

Mulai dengan membaca `docs/implementation/FRONTEND-IMPLEMENTATION.md` dan existing `web/` directory, lalu implementasi step by step.
