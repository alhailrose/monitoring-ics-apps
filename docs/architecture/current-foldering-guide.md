# Current Foldering Guide (Canonical Runtime)

Dokumen ini menjelaskan struktur folder yang berlaku saat ini agar sesi lanjutan tidak salah interpretasi.

## Prinsip utama

- `backend/*` adalah implementasi kanonis (source of truth runtime).
- `backend/checks/*` adalah lokasi checker kanonis.
- Namespace `src/*` sudah dicutover dari runtime python.

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
```

## Entry point model

- Packaging script: `monitoring-hub -> backend.interfaces.cli.main:main`.
- API canonical berada di `backend.interfaces.api.main:app`.

## Cutover policy

1. Semua import runtime/test mengarah ke `backend/*`.
2. Jangan menambahkan kembali namespace python `src/*`.
3. Setiap perubahan struktur wajib diikuti verifikasi test.

## Referensi wajib

- `docs/architecture/target-structure-contract.md`
- `docs/architecture/migration-status.md`
- `docs/development/backend-development-plan.md`
