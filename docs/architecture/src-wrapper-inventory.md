# src Wrapper Inventory (Phase 4.5)

Dokumen ini memetakan status `src/*` untuk cleanup foldering bertahap tanpa breaking behavior.

## Ringkasan

- Wrapper terdeteksi: 51 file (`src/*` non-checks, re-export/delegation ke `backend/*`).
- Non-wrapper terdeteksi: 25 file (`__init__`, formatting/check runtime legacy, dan modul transisi lain).
- `src/checks/*` telah dikonversi menjadi compatibility wrapper ke `backend/checks/*`.

## Wrapper yang aman dipertahankan sementara

- `src/app/api/*`
- `src/app/cli/*`
- `src/app/services/*`
- `src/app/tui/*` (kecuali file transisi yang bukan wrapper murni)
- `src/configs/loader.py`, `src/configs/schema/validator.py`
- `src/core/runtime/*`
- `src/db/*`
- `src/integrations/slack/*`
- `src/providers/aws/*`

Alasan: masih menjadi compatibility surface untuk import lama/test legacy.

## Kandidat evaluasi cleanup (batch berikutnya)

1. `src/app/tui/bootstrap.py` (tetap compat delegator atau alias murni)
2. `src/core/*/__init__.py` export policy (compat export vs alias package)
3. `src/integrations/*` dan `src/providers/*` wrapper consolidation

Sudah dimigrasikan di batch ini:
- `src/app/tui/flows/customer.py` -> canonical di `backend/interfaces/cli/flows/customer.py`
- `src/core/engine/*` -> canonical di `backend/domain/engine/*`
- `src/core/models/*` -> canonical di `backend/domain/models/*`
- `src/core/formatting/reports.py` -> canonical di `backend/domain/formatting/reports.py`
- Path legacy di `src/*` sekarang wrapper alias ke canonical path

Kriteria hapus:
- tidak direferensikan runtime/tes,
- ada padanan canonical di `backend/*`,
- full test tetap hijau.

## Guardrail eksekusi

- Jangan hapus `src/checks/*` sebelum seluruh consumer eksternal sudah pindah ke `backend/checks/*`.
- Jangan ubah entrypoint publik `monitoring-hub` sebelum migration gate disetujui.
- Setiap batch removal wajib verifikasi `pytest -q`.
