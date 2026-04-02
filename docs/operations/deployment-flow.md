# Deployment Flow (Split Frontend/Backend)

Dokumen ini mendefinisikan alur deployment terpisah untuk target `frontend` dan `backend`.

## Prinsip

- Deployment dilakukan per target deployable (`frontend` atau `backend`), tidak big-bang.
- Deploy hanya berjalan setelah workflow CI target terkait sukses di branch `main`.
- Setiap workflow deploy melakukan build image, push ke GHCR, deploy ke EC2, dan smoke check.
- Environment protection tetap menggunakan GitHub Environment `production`.

## Workflow deploy aktif

- Backend: `.github/workflows/deploy-backend.yml`
- Frontend: `.github/workflows/deploy-frontend.yml`

Kedua workflow juga mendukung trigger manual (`workflow_dispatch`) bila diperlukan.

## Perilaku deploy

- `Deploy Backend`:
  - trigger: `workflow_run` dari `CI Backend` (status `success`, branch `main`)
  - build + push image `backend`
  - update `BACKEND_IMAGE_TAG` di `/opt/monitoring-app/.env`
  - jalankan migrasi `alembic upgrade head`
  - restart service `backend`
  - cleanup image backend lama di server (retention: simpan 8 tag terbaru)
  - smoke check: `GET /health/readiness`

- `Deploy Frontend`:
  - trigger: `workflow_run` dari `CI Frontend` (status `success`, branch `main`)
  - build + push image `frontend`
  - update `FRONTEND_IMAGE_TAG` di `/opt/monitoring-app/.env`
  - restart service `frontend` dan `nginx`
  - cleanup image frontend lama di server (retention: simpan 8 tag terbaru)
  - smoke check: `GET /`

## Implementasi deploy aktual

- Single server deployment tetap mengacu ke `docs/operations/single-server-deploy.md`.
- Compose production memakai tag image terpisah:
  - `BACKEND_IMAGE_TAG`
  - `FRONTEND_IMAGE_TAG`

## Checklist evidence rilis

Gunakan checklist bukti per target di `docs/operations/release-checklist.md`.
