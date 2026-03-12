# Single Server Deployment (Web + API)

Dokumen ini menjelaskan stack minimum untuk menjalankan web + API di satu server menggunakan Docker Compose.

## Services aktif di `infra/docker/docker-compose.yml`

- `postgres`: database utama.
- `api`: FastAPI (`src.app.api.main:app`) di port internal `8000`.
- `nginx`: reverse proxy + static hosting `web/dist` di `http://localhost:8080`.

Catatan: saat ini **tidak ada service `redis`/`worker`** di compose file.

## Quick Start

1. Salin file environment:

```bash
cp infra/docker/.env.example infra/docker/.env
```

2. Build frontend statis yang akan disajikan Nginx:

```bash
npm ci --prefix web
npm --prefix web run build
```

3. Validasi konfigurasi compose:

```bash
docker compose -f infra/docker/docker-compose.yml config
```

4. Jalankan stack:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

5. Jalankan migrasi database (sekali saat deploy/update skema):

```bash
docker compose -f infra/docker/docker-compose.yml exec api alembic upgrade head
```

6. Cek health dan endpoint penting:

```bash
curl -fsS http://localhost:8080/health
curl -fsS http://localhost:8080/health/liveness
curl -fsS http://localhost:8080/health/readiness
curl -fsS http://localhost:8080/api/v1/checks/available
```

7. Verifikasi web ter-load lewat Nginx:

```bash
curl -I http://localhost:8080/
```

## Environment runtime minimum

Variabel yang dipakai runtime API saat ini:

```env
LOG_LEVEL=INFO
EXECUTION_TIMEOUT=300
MAX_WORKERS=5
DEFAULT_REGION=ap-southeast-3
CORS_ORIGINS=http://localhost:8080
CORS_ALLOW_CREDENTIALS=true
API_AUTH_ENABLED=false
API_KEYS=
API_KEY_HEADER=X-API-Key
```

Catatan CORS: jika `CORS_ORIGINS=*`, backend akan otomatis mematikan credentials agar tidak membuka kombinasi CORS yang unsafe.

Catatan API auth:

- Untuk production disarankan aktifkan `API_AUTH_ENABLED=true`.
- Isi `API_KEYS` dengan token dipisah koma (contoh: `token-a,token-b`).
- Header default adalah `X-API-Key` (bisa diubah lewat `API_KEY_HEADER`).
- Opsi kompatibilitas: token juga bisa dikirim via `Authorization: Bearer <token>`.

Catatan kompatibilitas: `REDIS_URL` dan `EXECUTION_MODE` masih ada di `.env.example`, tetapi belum dipakai oleh runtime compose saat ini.

## AWS SSO — Volume Mount

Container API membutuhkan akses ke kredensial AWS SSO dari host. Konfigurasi volume di `docker-compose.yml`:

```yaml
volumes:
  - ${HOME}/.aws:/root/.aws:ro               # seluruh config AWS, read-only
  - ${HOME}/.aws/sso/cache:/root/.aws/sso/cache:rw  # SSO token cache, read-write
```

**Mengapa dua mount?**

AWS SDK (botocore) perlu **menulis** temp file ke `~/.aws/sso/cache/` saat melakukan token refresh. Jika seluruh `.aws` di-mount sebagai `:ro`, proses refresh gagal dengan error:

```
[Errno 30] Read-only file system: '/root/.aws/sso/cache/tmpXXXXXX.tmp'
```

Solusinya: mount `sso/cache` secara terpisah sebagai `:rw` — direktori lain tetap read-only.

**Catatan untuk EC2 / server:**

- Pastikan user yang menjalankan Docker sudah login SSO: `aws sso login --profile <profile>`
- SSO token tersimpan di `~/.aws/sso/cache/` di host — container akan otomatis menggunakannya
- Token SSO berlaku ~8 jam (tergantung konfigurasi IAM Identity Center). Jika expired, jalankan `aws sso login` ulang di host
- Jika server berjalan sebagai user non-root, sesuaikan path `${HOME}` dan pastikan direktori `~/.aws/sso/cache/` sudah ada sebelum container dijalankan:

```bash
mkdir -p ~/.aws/sso/cache
```

## Operasional harian singkat

- Lihat status service: `docker compose -f infra/docker/docker-compose.yml ps`
- Lihat log API: `docker compose -f infra/docker/docker-compose.yml logs -f api`
- Restart API setelah update kode backend: `docker compose -f infra/docker/docker-compose.yml restart api`
- Rebuild web setelah update frontend: `npm --prefix web run build && docker compose -f infra/docker/docker-compose.yml restart nginx`

## Rollback cepat

1. Checkout commit rilis sebelumnya.
2. Rebuild frontend: `npm --prefix web run build`.
3. Restart service: `docker compose -f infra/docker/docker-compose.yml up -d --force-recreate api nginx`.
4. Validasi ulang `/health` dan `/api/v1/checks/available`.

## Notes

- Untuk production, gunakan secret manager untuk credential database.
- Jangan commit file `.env` atau credential AWS ke repository.
- Untuk approval dan rollback notes deployment per target (`web/api/tui`), gunakan flow di `docs/operations/deployment-flow.md`.
- Untuk checklist bukti rilis per target, gunakan `docs/operations/release-checklist.md`.
