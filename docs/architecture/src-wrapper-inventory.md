# src Wrapper Inventory (Archived)

Dokumen ini disimpan sebagai arsip historis migrasi. Full cutover runtime python telah menghapus modul `src/*`.

## Ringkasan

- Full cutover selesai: import runtime/test sudah mengarah ke `backend/*`.
- Modul python `src/*` dihapus dari tracked runtime code.
- Checker implementation canonical tetap di `backend/checks/*`.

## Catatan

Dokumen ini tidak lagi menjadi daftar kerja aktif. Gunakan referensi berikut untuk kondisi terkini:

- `docs/architecture/current-foldering-guide.md`
- `docs/architecture/migration-status.md`
- `docs/development/backend-development-plan.md`

## Guardrail eksekusi

- Jangan hapus `backend/checks/*` sebelum seluruh consumer eksternal sudah pindah ke `backend/checks/*`.
- Jangan ubah entrypoint publik `monitoring-hub` sebelum migration gate disetujui.
- Setiap batch removal wajib verifikasi `pytest -q`.
