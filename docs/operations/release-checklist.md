# Release Checklist (Evidence-Oriented)

Checklist ini dipakai saat rilis bertahap per target (`frontend`, `backend`) supaya bukti deployability tidak bercampur.

## Aturan umum

- Rilis dilakukan per target, bukan satu paket besar.
- Tiap target wajib punya bukti pre-release dan post-release.
- Simpan bukti di tiket rilis (link workflow run, output smoke test, dan rollback note).

## Frontend release evidence

- Pre-release quality gate: `bash scripts/ci/web-quality.sh`
- Build artifact tersedia dari workflow `CI Frontend` (`web-dist` artifact)
- Workflow deploy berjalan: `Deploy Frontend` (trigger otomatis setelah `CI Frontend` sukses di `main`)
- Post-release smoke:
  - otomatis di workflow (`curl /` dari server)
  - atau manual fallback: `WEB_BASE_URL=https://<host> bash scripts/ci/smoke-web.sh`
- Retention image frontend tervalidasi: hanya 8 tag terbaru dipertahankan di server

## Backend release evidence

- Pre-release quality gate: `bash scripts/ci/api-quality.sh`
- Compose valid: `docker compose -f infra/docker/docker-compose.yml config`
- Workflow deploy berjalan: `Deploy Backend` (trigger otomatis setelah `CI Backend` sukses di `main`)
- Post-release smoke:
  - otomatis di workflow (`curl /health/readiness` dari server)
  - atau manual fallback: `API_BASE_URL=https://<host> bash scripts/ci/smoke-api.sh`
- Retention image backend tervalidasi: hanya 8 tag terbaru dipertahankan di server

## Definition of done per release target

- Evidence pre-release + post-release lengkap.
- Workflow run sukses dan terlampir di tiket.
- Rollback command sudah diuji formatnya (tidak placeholder).
- Tidak ada blocker lint/test pada target terkait.
