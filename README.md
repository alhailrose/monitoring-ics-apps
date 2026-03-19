# AWS Monitoring Hub

CLI terpusat untuk memantau kesehatan, keamanan, dan biaya AWS (GuardDuty, CloudWatch, Cost Anomaly, Backup, RDS, EC2 list) dengan menu interaktif.

## Architecture roadmap
- Folder structure roadmap: `docs/architecture/folder-structure.md`
- Migration status: `docs/architecture/migration-status.md`
- Target structure contract: `docs/architecture/target-structure-contract.md`
- Backend living development plan (main checklist): `docs/development/backend-development-plan.md`
- Deployment flow (approval + rollback notes): `docs/operations/deployment-flow.md`
- Single server runbook (web + api): `docs/operations/single-server-deploy.md`
- Release evidence checklist per target: `docs/operations/release-checklist.md`

## Phase 2 scaffold + CI/CD split

- Incremental app scaffold tersedia di `apps/web`, `apps/api`, `apps/tui` (kompatibilitas, non-breaking).
- Frontend tetap Vite di folder `web/` selama masa transisi.
- CI dipisah per target deployment:
  - Web: `.github/workflows/ci-web.yml`
  - API: `.github/workflows/ci-api.yml`
  - TUI: `.github/workflows/ci-tui.yml`
- Kebijakan artifact frontend: `web/node_modules` dan `web/dist` tidak lagi disimpan di git; artifact build web dipublish oleh CI Web.

## Dual Interface Platform (TUI + API/Web)

Platform sekarang mendukung fondasi dual-interface:
- TUI existing tetap dipakai untuk operasional harian.
- API FastAPI tersedia di `backend/interfaces/api/main.py`.
- Execution policy split: TUI runs are non-persistent, API runs are persistent.
- Tidak ada worker terpisah pada runtime compose saat ini (eksekusi lewat API service layer).
- Web runtime tetap di folder `web/` (Vite), scaffold migrasi ada di `apps/web/`.
- Stack single server aktif: `postgres + api + nginx` di `infra/docker/docker-compose.yml`.

Quick check dual-interface:

```bash
# from repository root
bash scripts/ci/api-quality.sh
bash scripts/ci/tui-quality.sh
bash scripts/ci/web-quality.sh
docker compose -f infra/docker/docker-compose.yml config
```

### Local dev hot-reload (web + api)

Untuk development cepat tanpa restart manual:

Terminal 1 (API auto-reload + postgres):

```bash
bash scripts/dev/api-dev.sh
```

Terminal 2 (Web HMR):

```bash
bash scripts/dev/web-dev.sh
```

Port dev:

- Web: `http://localhost:4173`
- API: `http://localhost:8000`

### Industrial Ops Glass Web UI (foundation status)

Web package saat ini berfungsi sebagai fondasi UI yang sudah tervalidasi lewat test, namun belum diposisikan sebagai runtime service produksi siap pakai (build/deploy production belum menjadi default path di repo ini):
- **Home (`/`)**: command-center entrypoint dengan headline operasional, KPI card, dan quick actions.
- **Jobs (`/jobs`)**: form manual run yang aksesibel, action `Run Now`, dan status queue/table dengan badge semantik.
- **History (`/history`)**: state handling lengkap (loading, error banner, empty state `No runs yet`) plus pencarian client-side.
- **Cross-cutting hardening**: responsive layout mobile/desktop, semantic landmarks, focus-visible styling, dan reduced-motion support.

Verifikasi fondasi web + backend lokal:

```bash
# from repository root
bash scripts/ci/web-quality.sh
bash scripts/ci/api-quality.sh
docker compose -f infra/docker/docker-compose.yml config
```

### Backend hardening (Phase 2)

- CORS sekarang lebih aman: wildcard origin (`*`) otomatis mematikan credentials.
- Endpoint checks kritikal (`POST /api/v1/checks/execute`) memiliki validasi kontrak request/response yang konsisten, dengan compatibility layer untuk payload lama `customer_id`.
- Health probes diperjelas: `GET /health`, `GET /health/liveness`, `GET /health/readiness` (DB readiness).
- API menambahkan baseline observability: request ID (`x-request-id`) dan request duration logging.
- API sekarang mendukung guard API key opsional (`API_AUTH_ENABLED`, `API_KEYS`, `API_KEY_HEADER`) untuk seluruh route `/api/v1/*`.

## Quick Start (3 langkah)
1) Install aplikasi via pipx:
   ```bash
   pipx install "git+ssh://git@github.com/alhailrose/monitoring-ics-apps.git@main"
   ```
2) Login AWS profile yang dipakai:
   ```bash
   aws sso login --profile ksni-master
   ```
3) Jalankan:
   ```bash
   monitoring-hub
   ```

Panduan setup lengkap (AWS + Huawei):
- `docs/setup/setup-guide-id.md`

### Huawei login flow (hcloud)

Untuk user baru (beda laptop/server) paling mudah:

```bash
./scripts/huawei/setup_hcloud_profiles.sh dh_prod_erp-ro
```

Script ini akan:
- install mapping profile Huawei ke `~/.hcloud/config.json`
- login SSO 1 profile (`dh_prod_erp-ro`)
- sinkron token ke semua profile SSO

Jika ingin manual, jalankan helper berikut:

```bash
hcloud configure sso --cli-profile=dh_prod_erp-ro
./scripts/huawei/sync_sso_token.sh --source dh_prod_erp-ro
```

Setelah token sinkron, jalankan check dari monitoring-hub:

```bash
monitoring-hub --check huawei-ecs-util --profile dh_prod_erp-ro --region ap-southeast-4
```

Catatan: helper Huawei yang dipakai di repo hanya:
- `scripts/huawei/setup_hcloud_profiles.sh`
- `scripts/huawei/sync_sso_token.sh`

Jika update versi terbaru:
```bash
pipx reinstall "git+ssh://git@github.com/alhailrose/monitoring-ics-apps.git@main"
```

## Fitur lengkap
- **Single Check (per akun/profil):**
  - `health`: AWS Health Events
  - `cost`: Cost Anomalies
  - `guardduty`: GuardDuty findings
  - `cloudwatch`: CloudWatch alarms
  - `notifications`: notifikasi AWS/operasional
  - `backup`: status backup job + vault summary
  - `daily-arbel`: RDS utilization report
  - `ec2list`: daftar EC2
- **All Checks (multi akun, parallel):** cost + guardduty + cloudwatch + notifications (opsional include backup/rds via flag CLI).
- **Arbel Check (flow operasional):**
  - `RDS Monitoring` (window 1h/3h/12h, multi akun)
  - `Alarm Verification` by alarm name (spesifik, tidak scan semua alarm global)
  - `Backup`
- **Nabati Analysis:** analisis CPU spike dan cost bulanan untuk akun NABATI-KSNI.
- **CloudWatch Cost Report:** output table/markdown/plain text.
  - Scope saat ini: source profile tetap `ksni-master` (NABATI-KSNI).
- **WhatsApp-ready report:** format siap kirim untuk backup, RDS, dan alarm verification.

### Matriks fitur per mode
| Mode | Cakupan | Keterangan |
|---|---|---|
| `Single Check` | `health`, `cost`, `guardduty`, `cloudwatch`, `notifications`, `backup`, `daily-arbel`, `ec2list`, `alarm_verification` | Verifikasi detail per akun/profil |
| `All Checks` | `cost`, `guardduty`, `cloudwatch`, `notifications` | Eksekusi paralel multi akun (ringkasan eksekutif) |
| `All Checks + include` | tambah `backup` + `daily-arbel` | Aktif via `--include-backup-rds` |
| `Arbel Check` | `RDS Monitoring`, `Alarm Verification`, `Backup` | Flow operasional untuk akun Arbel |
| `Nabati Analysis` | CPU spike + Cost bulanan | Fokus akun NABATI-KSNI |
| `Cost Report` | CloudWatch cost usage | Output table/markdown/plain text |

### Fitur operasional penting
- **Parallel workers** untuk multi-account checks (`--workers`).
- **Region resolver** otomatis berdasarkan profil, bisa override manual (`--region`).
- **Config eksternal** via `~/.monitoring-hub/config.yaml` (profile groups + defaults).
- **Auto-refresh wrapper** untuk profil non-SSO berbasis `aws login`.
- **Output WA siap kirim**:
  - `--backup` -> template backup harian
  - `--check daily-arbel` -> report RDS klien
  - `--check alarm_verification` (via Arbel flow) -> summary report now/monitor/ok-now

## Guide: menambah account/profil

Tujuan section ini: biar nambah akun baru tidak perlu tebak-tebakan.

### A) Untuk pemakaian lokal (tanpa ubah repo)
1) Pastikan profil AWS ada dan valid:
   ```bash
   aws configure sso --profile <nama_profil>
   aws sso login --profile <nama_profil>
   aws sts get-caller-identity --profile <nama_profil> --region ap-southeast-1
   ```
2) Tambahkan ke config lokal `~/.monitoring-hub/config.yaml`:
   ```yaml
   defaults:
     region: ap-southeast-1
     workers: 5

   profile_groups:
     Aryanoble:
       dwh: "<ACCOUNT_ID_12_DIGITS>"
       genero-empower: "<ACCOUNT_ID_12_DIGITS>"
     FFI:
       ffi: "<ACCOUNT_ID_12_DIGITS>"

   display_names:
     dwh: "DWH"
     genero-empower: "Genero Empower"
     ffi: "FFI"
   ```
3) Verifikasi di CLI:
   ```bash
   monitoring-hub --check backup --profile dwh --region ap-southeast-1
   monitoring-hub --check cloudwatch --profile ffi --region ap-southeast-1
   ```

Catatan:
- `~/.monitoring-hub/config.yaml` di-merge dengan default bawaan aplikasi.
- `account_id` harus 12 digit string.

### B) Untuk update default tim di repository
Jika akun baru harus jadi default untuk semua user tim:
- Edit `backend/domain/runtime/config_loader.py`:
  - `DEFAULT_PROFILE_GROUPS`
  - `DEFAULT_DISPLAY_NAMES`
- Untuk akun customer Aryanoble (supaya report backup/daily konsisten), update juga:
  - `configs/customers/aryanoble.yaml`

Contoh update yang sudah dipakai saat ini:
- Aryanoble: `dwh`, `genero-empower`
- FFI group: `ffi` (single account)

## Ringkasan command CLI
- Interaktif (default, UI v2): `monitoring-hub`
- Paksa UI v2 (opsional): `monitoring-hub --ui2`
- Pakai legacy UI: `monitoring-hub --legacy-ui`
- Cek spesifik: `monitoring-hub --check <nama_check> --profile <profil>`
- Cek spesifik + kirim ke Slack: `monitoring-hub --check <nama_check> --profile <profil> --send-slack`
- Semua check: `monitoring-hub --all --group <group>`
- Include backup+rds di mode all: `monitoring-hub --all --group <group> --include-backup-rds`
- Init config sample: `monitoring-hub --init-config`
- Customer setup scan mapping: `monitoring-hub customer scan`
- Customer setup assign akun: `monitoring-hub customer assign <customer_id>`
- Customer setup set checks: `monitoring-hub customer checks <customer_id>`
- Validasi config customer: `monitoring-hub customer validate <customer_id>`

### Catatan flow Customer Report (TUI)
- Sumber akun menggunakan customer mapping (`configs/customers/*.yaml`), bukan local profile picker.
- Pilihan checks dan akun default tidak auto-terpilih.
- Sebelum pilih item tersedia keyword search + aksi `Select All` / `Clear All`.

### Catatan flow Huawei Check (TUI)
- Menu utama: `Huawei Check`.
- Submenu saat ini: `Utilization`.
- Saat `Utilization` dijalankan, sistem mengeksekusi check `huawei-ecs-util` untuk 10 akun Huawei fixed sekaligus dan menampilkan satu output `DAILY MONITORING REPORT` (consolidated).
- Akun fixed Huawei:
  - `dh_log-ro`, `dh_prod_nonerp-ro`, `afco_prod_erp-ro`, `afco_dev_erp-ro`, `dh_prod_network-ro`,
    `dh_prod_erp-ro`, `dh_hris-ro`, `dh_dev_erp-ro`, `dh_master-ro`, `dh_mobileapps-ro`.

Daftar check valid untuk `--check`:
`health`, `cost`, `guardduty`, `cloudwatch`, `notifications`, `backup`, `daily-arbel`, `daily-budget`, `ec2list`, `alarm_verification`.

## Slack report routing (opsional)

Anda bisa mengirim hasil report tertentu ke Slack berdasarkan channel route di config.

1) Tambahkan konfigurasi di `~/.monitoring-hub/config.yaml`:
```yaml
slack:
  enabled: true
  reports:
    backup:
      webhook_url: "https://hooks.slack.com/services/XXX/YYY/ZZZ"
      channel: "#aryanoble-backup"
      username: "Monitoring Bot"
      clients:
        cis-erha:
          channel: "#cis-backup"
        connect-prod:
          channel: "#connect-backup"
    daily-arbel:
      webhook_url: "https://hooks.slack.com/services/XXX/YYY/ZZZ"
      channel: "#aryanoble-rds"
      clients:
        dermies-max:
          channel: "#dermies-rds"
    daily-budget:
      webhook_url: "https://hooks.slack.com/services/XXX/YYY/ZZZ"
      channel: "#aryanoble-budget"
      clients:
        cis-erha:
          channel: "#cis-budget"
        erha-buddy:
          channel: "#buddy-budget"
```

2) Jalankan check dengan flag `--send-slack`:
```bash
monitoring-hub --check daily-budget --profile cis-erha --region ap-southeast-1 --send-slack
```

Catatan:
- Jika route untuk check tersebut tidak ada, report tetap jalan lokal dan Slack akan di-skip.
- Route key mengikuti nama check (`backup`, `daily-arbel`, `alarm_verification`, `daily-budget`, dll).
- `clients.<profile>` bersifat override per client; jika tidak ada maka pakai route default report.

## Test layout
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Run all tests:
  ```bash
  uv run --with pytest pytest
  ```

Catatan UI migration:
- UI v2 sekarang menjadi default untuk pengalaman split dashboard.
- UI lama tetap tersedia via `--legacy-ui` untuk fallback operasional.

## Prasyarat
- Python 3.9+
- Akses AWS (SSO atau kredensial) sesuai profil di `~/.aws/config`
- Git + akses ke repo (SSH atau HTTPS)
- pipx (disarankan untuk instalasi tim) atau venv lokal
- AWS CLI terpasang dan terkonfigurasi

## Install & konfigurasi AWS CLI
1) Pasang AWS CLI v2 (Linux/WSL): ikuti panduan resmi https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html (curl installer, unzip, sudo install).
2) Konfigurasi profil (manual):
   ```
   aws configure --profile <nama_profil>
   aws configure set region ap-southeast-3 --profile <nama_profil>
   ```
3) Untuk SSO (CLI v2):
   ```
   aws configure sso --profile <nama_profil_sso>
   aws sso login --profile <nama_profil_sso>
   ```
4) Pastikan profil yang Anda pakai ada di `~/.aws/config` dan sesuai daftar `PROFILE_GROUPS` di kode. Jika butuh acuan config milik tim (mis. laptop pc Bagus Syafiq), salin/seragamkan entri profilnya.
5) Uji kredensial:
   ```
   aws sts get-caller-identity --profile <nama_profil>
   ```

## Konfigurasi GitHub SSH (WSL/Linux)
1) Pastikan paket SSH:
   ```
   sudo apt-get update && sudo apt-get install git openssh-client
   ```
2) Buat key (jika belum ada):
   ```
   ssh-keygen -t ed25519 -C "email@domain"
   ```
3) Jalankan agent dan tambah key (set otomatis di shell rc bila perlu):
   ```
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```
4) Tambahkan ke GitHub (copy isi `~/.ssh/id_ed25519.pub` ke Settings > SSH keys).
5) Opsional `~/.ssh/config` agar pasti pakai key ini:
   ```
   Host github.com
     HostName github.com
     User git
     IdentityFile ~/.ssh/id_ed25519
     IdentitiesOnly yes
   ```
6) Tes akses:
   ```
   ssh -T git@github.com
   ```

## Setup pipx (tanpa clone)
1) Pasang pipx (Debian/Ubuntu/WSL):
   ```
   sudo apt-get update && sudo apt-get install pipx
   pipx ensurepath
   ```
   Jika tidak bisa apt, gunakan:
   ```
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```
   Tambahkan PATH bila perlu (WSL/bash/zsh): `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc` lalu buka terminal baru.

2) Install dari repo (ganti `<REPO_URL>` dan `<TAG>`/`main`):
   ```
   pipx install "git+<REPO_URL>@<TAG>"
   ```
   Contoh SSH: `pipx install "git+ssh://git@github.com/alhailrose/monitoring-ics-apps.git@main"`
   Contoh HTTPS (publik/bertok): `pipx install "git+https://github.com/alhailrose/monitoring-ics-apps.git@main"`

3) **Untuk profil non-SSO (aws login):** Install wrapper auto-refresh credentials
   ```bash
   # Download wrapper
   curl -o /tmp/monitoring-hub-wrapper https://raw.githubusercontent.com/alhailrose/monitoring-ics-apps/main/scripts/monitoring-hub-wrapper
   
   # Install globally
   sudo cp /tmp/monitoring-hub-wrapper /usr/local/bin/monitoring-hub-wrapper
   sudo chmod +x /usr/local/bin/monitoring-hub-wrapper
   
   # Tambah alias (pilih sesuai shell)
   echo "alias monitoring-hub='monitoring-hub-wrapper'" >> ~/.zshrc   # untuk zsh
   echo "alias monitoring-hub='monitoring-hub-wrapper'" >> ~/.bashrc  # untuk bash
   
   # Reload shell
   source ~/.zshrc  # atau source ~/.bashrc
   ```
   
   Wrapper ini otomatis refresh credentials dari `aws login` sebelum jalankan monitoring-hub.
   Edit `/usr/local/bin/monitoring-hub-wrapper` untuk menambah profil non-SSO di array `AWS_LOGIN_PROFILES`.

4) Jalankan di folder mana saja:
   ```
   monitoring-hub --check health --profile myprof
   ```
   (tanpa argumen langsung masuk mode interaktif)

5) Upgrade ke versi terbaru:
   ```
   pipx reinstall "git+<REPO_URL>@<TAG>"   # atau pipx upgrade monitoring-hub jika URL sama
   ```

## Jalankan langsung (lokal, venv)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
monitoring-hub                # atau: monitoring-hub --check health --profile myprof
```

## Catatan penggunaan
- Pastikan sudah login AWS (SSO atau credentials) sesuai profil yang ada di `PROFILE_GROUPS` atau profil lokal di `~/.aws/config`.
- Tanpa argumen, `monitoring-hub` langsung membuka menu interaktif. Esc/Ctrl+C di menu utama langsung keluar.
- Mode interaktif: pilih check → pilih akun (backup/RDS/all bisa multi) → pilih region → output tampil.
- Untuk run non-interaktif: `monitoring-hub --check guardduty --profile myprof` atau `--all --profile a,b`.

## Arbel Daily & Alarm (update terbaru)
- Menu `Arbel Check` berfokus pada `RDS Monitoring`, `Alarm Verification`, dan `Backup`.
- Di dalam menu `Alarm Verification`, tersedia submenu metode input alarm:
  - pilih dari account (catalog YAML), atau
  - paste nama alarm (multi baris / koma, bisa lebih dari 1).
- Pemilihan akun Arbel menggunakan checkbox dengan default akun utama tercentang: `dermies-max`, `cis-erha`, `connect-prod`.
- Pemilihan alarm menggunakan checkbox dengan default alarm relevan tercentang.
- Alarm check bersifat spesifik nama alarm (tidak mengambil semua alarm ALARM secara global).
- Rule eskalasi alarm: laporkan hanya jika status `ALARM` masih berlangsung `>= 10 menit`.

## Format output WhatsApp alarm
- Output detail status alarm ada di hasil checker/TUI dengan format tabel `Alarm Verification Data`.
- WhatsApp hanya menampilkan narasi `Pelaporan` untuk alarm `Report Now` (masih ALARM dan >= 10 menit).
- Tidak memakai ringkasan `Summary` dan istilah `OK_NOW`.
- Format klien (contoh):
  ```text
  Selamat Siang, kami informasikan pada *dc-dwh-olap-memory-above-70* sedang melewati threshold >= 70 sejak 11:03 WIB (status: ongoing 26 menit).
  ```
