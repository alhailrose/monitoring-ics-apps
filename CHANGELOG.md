# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Alarm verification sekarang menyertakan konteks status saat ini (`ALARM`/`OK`) dan history breach terbaru.
- Tambah pengujian:
  - `tests/test_alarm_verification.py` untuk batas durasi 10 menit dan status terkini.
  - `tests/test_whatsapp_alarm_report.py` untuk validasi format WhatsApp klien.
- Struktur target aplikasi `src/` untuk layer `app`, `core`, `providers`, `checks`, dan `configs`.
- Modul runner core kanonik di `src/core/engine` + model di `src/core/models`.
- Loader konfigurasi customer kanonik di `src/configs/loader.py`.
- Integrasi Slack command runner di `monitoring_hub/integrations/slack`.
- Penataan test suite ke `tests/unit` dan `tests/integration`.

### Changed
- Arbel flow di menu interaktif disederhanakan menjadi 3 mode utama: `RDS Monitoring`, `Alarm Verification`, `Backup`.
- Pemilihan akun dan nama alarm sekarang langsung via checkbox (default tercentang) agar lebih cepat untuk operasional.
- Format `build_whatsapp_rds` dikembalikan ke format klien yang lebih detail; format ringkas dipindah ke `build_whatsapp_rds_compact`.
- Pesan WhatsApp alarm format klien diperjelas dengan penggabungan metrik yang naik dalam satu kalimat agar tidak membingungkan penerima.
- Dokumentasi README diperbarui untuk mencakup semua fitur (single/all/arbel/nabati/cost report) beserta ringkasan command CLI.
- Registry checks sekarang mengarah ke namespace `src.checks.*` sebagai jalur migrasi kanonik.
- Entrypoint CLI legacy sekarang bertindak sebagai wrapper ke `src/app/cli/bootstrap.py`.

### Fixed
- Kasus alarm yang sudah kembali `OK` sekarang tetap ditampilkan dengan history rentang waktu dan durasi breach.
- Ringkasan alarm tidak lagi menampilkan hasil seolah "normal" tanpa konteks history.

## [1.4.0] - 2026-02-09

### Added
- **Hourly monitoring mode** untuk profil `connect-prod` dan `cis-erha`
  - Monitoring window 1 jam terakhir (vs 12 jam untuk profil lain)
  - Period 60 detik untuk detail lebih tinggi
  - Timestamp data di output report
- **Multiple breach periods detection**
  - Menampilkan semua periode breach dalam 1 jam
  - Format: `85% pukul 13:25-13:29 WIB, 92% pukul 13:40-13:44 WIB`
  - Grouping otomatis dengan gap 5 menit
- **Menu interaktif terpisah**
  - Daily Arbel Hourly: connect-prod & cis-erha (1 jam)
  - Daily Arbel: akun lainnya (12 jam)

### Changed
- Greeting lebih akurat: Pagi (5-11), Siang (11-15), Sore (15-18), Malam (18-5)
- Format breach lebih jelas tanpa kata "min/max"
- Konstanta `HOURLY_PROFILES` untuk konfigurasi profil hourly

### Fixed
- Duplikasi kode di `daily_arbel.py`
- Import error `BaseCheck` → `BaseChecker` di `nabati_analysis.py`

## [1.3.2] - Previous version
- (changelog sebelumnya)
