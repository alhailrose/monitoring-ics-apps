# Changelog

All notable changes to this project will be documented in this file.

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
