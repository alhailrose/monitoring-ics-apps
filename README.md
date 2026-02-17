# AWS Monitoring Hub

CLI terpusat untuk memantau kesehatan, keamanan, dan biaya AWS (GuardDuty, CloudWatch, Cost Anomaly, Backup, RDS, EC2 list) dengan menu interaktif.

## Architecture roadmap
- Folder structure roadmap: `docs/architecture/folder-structure.md`
- Migration status: `docs/architecture/migration-status.md`
- Target structure contract: `docs/architecture/target-structure-contract.md`

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

## Ringkasan command CLI
- Interaktif (default, UI v2): `monitoring-hub`
- Paksa UI v2 (opsional): `monitoring-hub --ui2`
- Pakai legacy UI: `monitoring-hub --legacy-ui`
- Cek spesifik: `monitoring-hub --check <nama_check> --profile <profil>`
- Semua check: `monitoring-hub --all --group <group>`
- Include backup+rds di mode all: `monitoring-hub --all --group <group> --include-backup-rds`
- Init config sample: `monitoring-hub --init-config`

Daftar check valid untuk `--check`:
`health`, `cost`, `guardduty`, `cloudwatch`, `notifications`, `backup`, `daily-arbel`, `ec2list`.

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
pip install -r requirements.txt
python monitoring_hub.py      # atau: monitoring_hub.py --check health --profile myprof
```

## Catatan penggunaan
- Pastikan sudah login AWS (SSO atau credentials) sesuai profil yang ada di `PROFILE_GROUPS` atau profil lokal di `~/.aws/config`.
- Tanpa argumen, `monitoring-hub` langsung membuka menu interaktif. Esc/Ctrl+C di menu utama langsung keluar.
- Mode interaktif: pilih check → pilih akun (backup/RDS/all bisa multi) → pilih region → output tampil.
- Untuk run non-interaktif: `monitoring-hub --check guardduty --profile myprof` atau `--all --profile a,b`.

## Arbel Daily & Alarm (update terbaru)
- Menu `Arbel Check` berfokus pada `RDS Monitoring`, `Alarm Verification`, dan `Backup`.
- Pemilihan akun Arbel menggunakan checkbox dengan default akun utama tercentang: `dermies-max`, `cis-erha`, `connect-prod`.
- Pemilihan alarm menggunakan checkbox dengan default alarm relevan tercentang.
- Alarm check bersifat spesifik nama alarm (tidak mengambil semua alarm ALARM secara global).
- Rule eskalasi alarm: laporkan hanya jika status `ALARM` masih berlangsung `>= 10 menit`.

## Format output WhatsApp alarm
- Ringkasan alarm menampilkan `REPORT_NOW`, `MONITOR`, dan `OK_NOW`.
- Untuk alarm yang sudah pulih, output tetap menampilkan history dan status terkini OK.
- Format klien (contoh):
  ```text
  Selamat Siang Team 👋
  *Arbel Alarm Verification* | 11:34 WIB

  📊 Summary: REPORT_NOW=0 | MONITOR=0 | OK_NOW=1

  ✅ SAAT INI OK (history):
  - Kami informasikan bahwa pada akun *DERMIES MAX*, metrik *Freeable Memory (Reader), CPU Utilization (Reader), serta ACU Utilization (Reader)* terdeteksi *alert melebihi > 75 Percent* pada rentang waktu *11:03 WIB - 11:13 WIB* (10m). Saat ini status alarm sudah *OK*.
    reason: Threshold Crossed
  ```
