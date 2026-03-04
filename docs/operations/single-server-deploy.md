# Single Server Deployment (API + Worker)

Dokumen ini menjelaskan stack minimum untuk menjalankan platform dual-interface di satu server menggunakan Docker Compose.

## Services

- `postgres`: penyimpanan data job + hasil normalisasi.
- `redis`: queue backend untuk proses asynchronous.
- `api`: FastAPI endpoint (`/health`, `/api/v1/jobs`, `/api/v1/history`).
- `worker`: proses eksekusi job queue.
- `nginx`: reverse proxy ke service API.

## Quick Start

1. Salin file environment:

```bash
cp infra/docker/.env.example infra/docker/.env
```

2. Validasi konfigurasi compose:

```bash
docker compose -f infra/docker/docker-compose.yml config
```

3. Jalankan stack:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

4. Cek health API:

```bash
curl http://localhost:8080/health
```

## Notes

- Untuk production, gunakan secret manager untuk credential.
- Worker command saat ini mengikuti entrypoint Python module (`src.app.worker.main`).
