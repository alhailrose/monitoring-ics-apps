# Improvement Plan — Monitoring ICS Apps
_Dibuat: 2026-03-24_

---

## Ringkasan Item

| # | Item | Fase | Kompleksitas | Status |
|---|------|------|-------------|--------|
| 3 | Nama customer di History | 1 | Rendah | ✅ Done |
| 6a | Select All / Clear All di Checks | 1 | Rendah | ✅ Done |
| 6c | Format report backup (Completed/Failed/Expired) + vault | 1 | Sedang | ✅ Done |
| 6c+ | UI detail vault (resources backed up per vault) | 1 | Rendah | ✅ Done |
| 7 | Verifikasi akurasi check (notifications, guardduty, cost, budget, huawei) | 2 | Sedang | ✅ Done |
| 5 | Peningkatan label & visualisasi Metrics | 2 | Sedang | ✅ Done |
| 6b | Parameter vault check (backup-hris, centralized-s3) | 2 | Sedang | ✅ Done |
| 4 | Findings: grouping per akun + upsert/resolved logic | 3 | Tinggi | ✅ Done |
| 1 | Dashboard: global overview semua customer tanpa perlu pilih dulu | 3 | Tinggi | ✅ Done |
| 2 | Auth method UI — input & simpan credentials (access key, SSO, role) dari app | 3 | Tinggi | ⏳ Belum |

---

## Fase 1 — Quick Wins

### Item 3 · Nama Customer di History
**Masalah:** List history tidak menampilkan nama customer, hanya check mode dan tanggal.
**Solusi:** Tambahkan kolom/label nama customer di tabel history (frontend) dan pastikan API mengembalikan `customer.display_name`.

### Item 6a · Select All / Clear All di Checks
**Masalah:** Saat memilih akun untuk dicheck, tidak ada cara cepat untuk memilih semua atau membatalkan semua pilihan.
**Solusi:** Tambahkan tombol "Pilih Semua" dan "Hapus Pilihan" di form pemilihan akun pada halaman Checks.

### Item 6c · Format Report Backup + Vault Check
**Masalah:** Output backup check sulit dibaca dan tidak mencerminkan status vault (backup-hris, centralized-s3).
**Format baru:**
```
Selamat Pagi Team,
Berikut report untuk [Customer] Backup pada hari ini
DD-MM-YYYY

Completed:
- AccountName - AccountID

Failed:
- AccountName - AccountID
  Detail N:
    Resource: ...
    Time: DD-MM-YYYY HH:MM WIB
    Reason: ...

Expired:
- (tidak ada)
```
**Vault check (backup-hris, centralized-s3):** Akun ini bersifat *vault* — mengecek apakah ada backup yang masuk ke vault pada hari tersebut, bukan mengecek job backup itu sendiri. Perlu parameter `vault_mode: true` + logika tambahan: jika tidak ada backup masuk hari ini → masuk ke bagian **Failed** dengan reason "Tidak ada backup yang diterima vault hari ini".

---

## Fase 2 — Perbaikan Fungsional

### Item 7 · Verifikasi Akurasi Check
Verifikasi dilakukan dengan membaca kode checker + run test manual:

- **Notifications** — Apakah window waktu sudah benar? Apakah hanya mengambil notifikasi baru (bukan semua)?
- **GuardDuty** — Apakah findings yang sudah diarchive ikut terhitung? Filter severity?
- **Cost Anomaly** — Apakah membaca anomaly hari ini atau range tertentu?
- **Budget** — AWS Budget Alert membaca data ~2 hari ke belakang. Verifikasi apakah ini sudah dihandle atau menyesatkan.
- **Huawei** — Sudah berjalan di TUI/CLI. Perlu uji di webapp: pastikan endpoint, region, dan auth-nya berjalan.

### Item 5 · Peningkatan Metrics
**Masalah:** Label metrik kurang jelas, visualisasi bisa lebih informatif.
**Solusi:** Perjelas label (satuan, nama metrik lengkap), tambahkan threshold line jika ada, pertimbangkan warna status pada chart.

### Item 6b · Parameter Vault Check
Lanjutan dari 6c — pastikan parameter `vault_mode` terdeteksi dengan benar dari config akun, dan window waktu yang dicek adalah "hari ini" (bukan rolling 24 jam yang bisa overlap ke hari kemarin).

---

## Fase 3 — Arsitektur Besar

### Item 4 · Findings: Grouping + Upsert Logic
**Masalah:** Setiap check run menambah finding baru meski finding yang sama masih aktif → tabel `finding_events` jadi sangat redundan.

**Solusi:**
- Tambah kolom `status` (`active`/`resolved`) dan `resolved_at` di `finding_events`
- Saat check run: jika finding dengan `finding_key` yang sama sudah ada dan masih `active` → update `last_seen_at`, jangan insert baru
- Jika finding hilang di check berikutnya → set `status = resolved`, `resolved_at = now()`
- **UI:** Tampilkan findings dikelompokkan per akun. Klik akun → expand detail findings. Default hanya tampilkan yang masih `active`.

**Alembic migration diperlukan.**

### Item 1 · Dashboard: Global Overview
**Masalah:** Dashboard mengharuskan memilih customer terlebih dahulu — tidak cocok untuk monitoring engineer yang perlu memantau semua customer sekaligus.

**Solusi — tampilan baru:**
- Grid/list semua customer dengan status terkini (hijau/kuning/merah)
- Per customer: tampilkan ringkasan (berapa alarm aktif, berapa finding, kapan terakhir dicheck)
- Klik customer → masuk ke detail customer tersebut
- Filter by status (ada issue / semua ok)

### Item 2 · Auth Method UI — Simpan Credentials dari App
**Masalah:** Menambahkan akun AWS ke customer mengharuskan konfigurasi manual di server (`~/.aws/config`) lalu daftarkan di app.

**Solusi:**
- Tambah field `auth_method` di tabel `accounts`: `profile` (default, pakai `~/.aws/config`), `access_key`, `assumed_role`, `sso`
- Untuk `access_key`: simpan `aws_access_key_id` (plaintext) dan `aws_secret_access_key` (dienkripsi dengan APP_SECRET sebelum masuk DB)
- Untuk `assumed_role`: simpan `role_arn` dan opsional `external_id`
- Untuk `sso`: simpan `sso_start_url`, `sso_account_id`, `sso_role_name`
- Saat check run: jika `auth_method != profile`, buat boto3 session dengan explicit credentials (bukan `profile_name`)
- **UI form:** Dropdown pilih auth method → field dinamis muncul sesuai pilihan
- **Security:** Secret key di-encrypt sebelum disimpan, tidak pernah dikembalikan ke frontend (write-only atau masked)

**Alembic migration diperlukan.**

---

## Urutan Eksekusi

```
Fase 1:  Item 3 → 6a → 6c (termasuk vault)
Fase 2:  Item 7 → 6b → 5
Fase 3:  Item 4 → 1 → 2
```
