# Deployment Guide — Monitoring ICS Apps

## Daftar Isi

1. [Arsitektur](#arsitektur)
2. [Prasyarat](#prasyarat)
3. [Provisioning EC2 dengan Terraform](#provisioning-ec2-dengan-terraform)
4. [Setup DNS di name.com](#setup-cloudflare-dns)
5. [Setup SSL dengan Certbot di Bastion](#setup-ssl-dengan-certbot-di-bastion)
6. [Setup GitHub Actions Secrets](#setup-github-actions-secrets)
7. [Deployment Pertama (First-time Deploy)](#deployment-pertama-first-time-deploy)
8. [Deployment Selanjutnya (CI/CD)](#deployment-selanjutnya-cicd)
9. [Struktur File](#struktur-file)
10. [Rollback](#rollback)
11. [Troubleshooting](#troubleshooting)

---

## Arsitektur

```
Internet
    │
    ▼
Cloudflare DNS
msmonitoring.bagusganteng.app → 16.78.250.215
    │
    ▼
ics-ms-bastion (EC2 Public, 16.78.250.215)
  └── nginx reverse proxy (Let's Encrypt TLS)
          │
          ▼ proxy_pass http://ics-ms-monitoring-app:80
          │
          ▼
ics-ms-monitoring-app (EC2 Private, 10.0.10.X)
  └── Docker Compose
        ├── nginx container (port 80)       ← entry point
        ├── frontend container (Next.js, port 3000)
        └── backend container (FastAPI, port 8000)
                │
                ▼
        ics-ms-database (EC2 Private, 10.0.10.11)
          └── PostgreSQL (port 5432)
              └── database: ics_ms_monitoringapps
```

**VPC:** `vpc-ics-ms` (10.0.0.0/16), region `ap-southeast-3`

---

## Prasyarat

### Tools yang dibutuhkan

```bash
# Terraform >= 1.6
terraform -version

# AWS CLI v2
aws --version

# AWS SSO login
aws sso login --profile sandbox-ms
```

### Akses yang dibutuhkan

- AWS profile `sandbox-ms` dengan permission: EC2, SSM, IAM (untuk Terraform)
- SSH key pair `ics-ms-ssh-key` tersimpan di `~/.ssh/`
- GitHub repository access (untuk setup secrets)
- Akses ke name.com dashboard (domain `bagusganteng.app`)

---

## Provisioning EC2 dengan Terraform

### 1. Masuk ke direktori Terraform

```bash
cd infra/terraform/monitoring-app
```

### 2. Init Terraform

```bash
terraform init
```

### 3. Review plan — pastikan hanya 2 resource baru yang dibuat

```bash
terraform plan
```

Output yang diharapkan:
```
Plan: 3 to add, 0 to change, 0 to destroy.
  + aws_instance.monitoring_app
  + aws_ssm_document.bastion_setup
  + aws_ssm_association.bastion_setup
```

> **Catatan:** Tidak ada resource existing yang diubah. VPC, subnet, security group,
> dan bastion EC2 hanya dibaca sebagai data source.

### 4. Apply

```bash
terraform apply
```

Ketik `yes` saat diminta konfirmasi.

### 5. Simpan output

```bash
terraform output
# private_ip = "10.0.10.X"
# instance_id = "i-0xxxxxxxxxxxxxxxxx"
```

Catat nilai `private_ip` — dibutuhkan di langkah selanjutnya.

---

## Setup DNS di name.com

1. Login ke name.com dashboard
2. Pilih domain `bagusganteng.app` → **Manage DNS**
3. Tambah record baru:

| Type | Host | Answer | TTL |
|------|------|--------|-----|
| A | `msmonitoring` | `16.78.250.215` | 300 |

---

## Setup SSL dengan Certbot di Bastion

Setelah Terraform apply dan DNS sudah propagate (tunggu ~1-2 menit):

### 1. SSH ke bastion

```bash
ssh -i ~/.ssh/ics-ms-ssh-key ubuntu@16.78.250.215
```

### 2. Verifikasi nginx config sudah terpasang

```bash
ls /etc/nginx/sites-enabled/ics-ms-monitoring-app
cat /etc/nginx/sites-enabled/ics-ms-monitoring-app
```

### 3. Verifikasi /etc/hosts entry sudah ada

```bash
grep ics-ms-monitoring-app /etc/hosts
# Output: 10.0.10.X ics-ms-monitoring-app
```

### 4. Issue SSL certificate

```bash
sudo certbot --nginx -d msmonitoring.bagusganteng.app \
  --non-interactive --agree-tos \
  -m admin@bagusganteng.app
```

Certbot akan otomatis:
- Issue certificate dari Let's Encrypt
- Update nginx config dengan SSL
- Setup auto-renewal via cron/systemd

### 5. Verifikasi

```bash
nginx -t
systemctl status nginx
curl -I https://msmonitoring.bagusganteng.app
```

---

## Setup GitHub Actions Secrets

Buka: **GitHub → Repository → Settings → Secrets and variables → Actions**

### Secrets (nilai sensitif)

| Secret | Nilai | Keterangan |
|--------|-------|------------|
| `EC2_HOST` | `10.0.10.X` | Private IP dari output Terraform |
| `EC2_BASTION_HOST` | `16.78.250.215` | Public IP bastion |
| `EC2_USER` | `ubuntu` | SSH user EC2 |
| `EC2_SSH_KEY` | isi file `~/.ssh/ics-ms-ssh-key` | Private SSH key (seluruh isi file) |
| `DATABASE_URL` | `postgresql+psycopg://superadmin:PASSWORD@10.0.10.11:5432/ics_ms_monitoringapps` | Connection string production DB |
| `JWT_SECRET` | output `openssl rand -hex 32` | Generate sekali, simpan baik-baik |

### Variables (nilai non-sensitif)

| Variable | Nilai default | Keterangan |
|----------|--------------|------------|
| `DEFAULT_REGION` | `ap-southeast-3` | AWS region |
| `MAX_WORKERS` | `5` | Jumlah worker check executor |
| `EXECUTION_TIMEOUT` | `300` | Timeout per check (detik) |
| `CORS_ORIGINS` | `https://msmonitoring.bagusganteng.app` | CORS allowed origin |
| `API_AUTH_ENABLED` | `true` | Aktifkan JWT auth |

### Generate JWT_SECRET

```bash
openssl rand -hex 32
```

---

## Deployment Pertama (First-time Deploy)

### 1. Import data ke production database

Sebelum deploy pertama, schema dan data harus sudah ada di production DB.

**Step A — Buat schema (jalankan di DBGate):**
- Buka `https://dbgate.bagusganteng.app`
- Connect ke database `ics_ms_monitoringapps`
- Execute SQL → paste isi file `monitoring_schema.sql`

**Step B — Import data config (jalankan di DBGate):**
- Execute SQL → paste isi file `monitoring_config_export.sql`

### 2. Trigger deployment pertama

```bash
git push origin main
```

Atau manual trigger via:
**GitHub → Actions → Deploy → Run workflow**

### 3. Pantau progress

GitHub → Actions → pilih run yang sedang berjalan

Urutan job:
```
CI (backend tests + frontend build)
  └── Deploy
        ├── build-and-push (build Docker images → push ke GHCR)
        └── deploy
              ├── Copy compose files ke EC2
              ├── Pull images dari GHCR
              ├── Alembic migration (alembic upgrade head)
              ├── docker compose up -d
              └── Smoke test (curl /health)
```

---

## Deployment Selanjutnya (CI/CD)

Setiap push ke branch `main` akan otomatis:

1. **CI** — jalankan unit tests backend + typecheck + build frontend
2. Jika CI pass → **Deploy** — build images baru, push ke GHCR, deploy ke EC2

```
push to main
    │
    ├── CI job (tests + build check)
    │     └── pass
    │
    └── Deploy job
          ├── Build backend image (Docker layer cache)
          ├── Build frontend image (Docker layer cache)
          ├── Push ke ghcr.io/alhailrose/monitoring-ics-apps/backend:<sha>
          ├── Push ke ghcr.io/alhailrose/monitoring-ics-apps/frontend:<sha>
          ├── SSH via bastion → monitoring-app
          ├── alembic upgrade head
          ├── docker compose pull + up -d
          └── Smoke test: curl /health
```

**Estimasi waktu per deployment:** ~5-8 menit (dengan layer cache)

---

## Struktur File

```
monitoring-ics-apps/
│
├── Dockerfile.backend              # Image FastAPI (multi-stage, Python 3.12)
├── Dockerfile.frontend             # Image Next.js (multi-stage, Node 20, standalone)
│
├── infra/
│   ├── docker/
│   │   ├── docker-compose.prod.yml # Production compose (backend + frontend + nginx)
│   │   ├── nginx.prod.conf         # Nginx config dalam container (proxy ke Next.js + FastAPI)
│   │   └── .env.prod.example       # Template .env production
│   │
│   └── terraform/monitoring-app/
│       ├── main.tf                 # Provider + data sources (VPC, subnet, SG existing)
│       ├── ec2.tf                  # EC2 instance: ics-ms-monitoring-app
│       ├── bastion.tf              # SSM: setup nginx di bastion
│       ├── variables.tf            # Input variables
│       ├── outputs.tf              # Output: private_ip, instance_id
│       ├── user_data.sh.tpl        # Bootstrap script (install Docker)
│       └── bastion-nginx.conf.tpl  # Template nginx config untuk bastion
│
├── .github/workflows/
│   ├── ci.yml                      # CI: unit tests + frontend build (tiap PR/push)
│   └── deploy.yml                  # CD: build images + deploy ke EC2 (push ke main)
│
├── monitoring_schema.sql           # DDL schema untuk production DB (jalankan sekali)
└── monitoring_config_export.sql    # Data config: customers, accounts (jalankan sekali)
```

---

## Rollback

### Rollback ke versi sebelumnya

```bash
# SSH ke monitoring-app via bastion
ssh -i ~/.ssh/ics-ms-ssh-key -J ubuntu@16.78.250.215 ubuntu@10.0.10.X

cd /opt/monitoring-app

# Ganti IMAGE_TAG di .env ke SHA commit sebelumnya
# Cek SHA di: GitHub → Actions → pilih run sebelumnya
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=<previous-sha>/' .env

# Pull dan restart
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Rollback DB migration

```bash
# Rollback 1 versi
docker run --rm \
  --env DATABASE_URL="postgresql+psycopg://..." \
  ghcr.io/alhailrose/monitoring-ics-apps/backend:<sha> \
  alembic downgrade -1
```

---

## Troubleshooting

### Container tidak mau start

```bash
ssh -J ubuntu@16.78.250.215 ubuntu@10.0.10.X
cd /opt/monitoring-app
docker compose -f docker-compose.prod.yml logs --tail=50
```

### Backend tidak bisa konek ke database

```bash
# Test koneksi dari dalam container
docker compose -f docker-compose.prod.yml exec backend \
  python -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    print(conn.execute(text('SELECT 1')).scalar())
"
```

### Nginx bastion error 502 Bad Gateway

Artinya monitoring-app container belum siap atau tidak jalan.

```bash
# Cek status container
docker compose -f docker-compose.prod.yml ps

# Cek /etc/hosts di bastion
grep ics-ms-monitoring-app /etc/hosts

# Test koneksi dari bastion ke monitoring-app
curl -I http://ics-ms-monitoring-app:80/health
```

### GitHub Actions gagal di smoke test

```bash
# Jalankan manual dari bastion
curl -I https://msmonitoring.bagusganteng.app/health
```

### Lihat semua container log sekaligus

```bash
docker compose -f docker-compose.prod.yml logs -f
```
