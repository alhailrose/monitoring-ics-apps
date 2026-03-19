# Current Foldering Guide (Canonical + Compatibility)

Dokumen ini menjelaskan struktur folder yang berlaku saat ini agar sesi lanjutan tidak salah interpretasi.

## Prinsip utama

- `backend/*` adalah implementasi kanonis (source of truth runtime).
- `src/*` dipertahankan sebagai compatibility layer bertahap.
- `src/checks/*` masih aktif sebagai lokasi checker saat ini.
- Wrapper di `src/*` hanya boleh mendelegasikan ke `backend/*` (tanpa logika baru).

## Struktur operasional saat ini

```text
backend/
  interfaces/   # API + CLI/TUI canonical entry/runtime
  domain/       # runtime orchestration + service layer
    engine/     # runner job engine (JobExecutor/JobStore)
    models/     # runner job models (JobRecord)
    formatting/ # reusable report formatting builders
  infra/        # AWS/DB/Slack integrations
  config/       # settings + defaults + schema

src/
  app/          # compatibility wrappers ke backend/interfaces + backend/domain
  checks/       # active check implementations
  core|db|integrations|providers  # legacy paths (wrapper/compat bertahap)
```

## Entry point model

- Packaging script: `monitoring-hub -> backend.interfaces.cli.main:main`.
- Wrapper `src.app.cli.main` tetap tersedia hanya untuk kompatibilitas import legacy.
- API canonical berada di `backend.interfaces.api.main:app`.

## Cleanup policy (bertahap)

1. Pindahkan konsumsi import runtime ke `backend/*`.
2. Pertahankan wrapper tipis di `src/*` selama masih ada pemakai.
3. Hapus wrapper hanya jika tidak ada referensi runtime/test yang tersisa.
4. Setiap batch cleanup wajib green test.

## Referensi wajib

- `docs/architecture/target-structure-contract.md`
- `docs/architecture/migration-status.md`
- `docs/development/backend-development-plan.md`
