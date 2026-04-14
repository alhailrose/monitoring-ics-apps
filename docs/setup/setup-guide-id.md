# Setup Guide Monitoring Hub (TUI + Huawei)

Dokumen ini khusus untuk setup **TUI/CLI** dan **Huawei** di mesin operator lokal.
Untuk setup web platform (Docker Compose), lihat `docs/operations/single-server-deploy.md`.
Untuk setup development lokal, lihat `docs/PROJECT.md`.

## 1) Prasyarat

- Python + `pipx`
- AWS CLI (`aws`)
- Huawei CLI (`hcloud`)
- `jq` (dipakai helper script Huawei)

## 2) Install aplikasi

```bash
pipx install "git+ssh://git@github.com/alhailrose/monitoring-ics-apps.git@main"
```

Jika sudah pernah install dan ingin update terbaru:

```bash
pipx reinstall "git+ssh://git@github.com/alhailrose/monitoring-ics-apps.git@main"
```

## 3) Setup AWS profile

```bash
aws configure sso --profile <nama_profil>
aws sso login --profile <nama_profil> --use-device-code --no-browser
aws sts get-caller-identity --profile <nama_profil> --region ap-southeast-1
```

Catatan method:
- Untuk profile `sso`, gunakan `aws sso login`.
- Untuk profile non-SSO yang memakai login cache AWS CLI modern, gunakan `aws login` sesuai kebutuhan environment.

Catatan: YAML customer/default hanya menyimpan mapping profile/check, bukan credential.

## 4) Setup Huawei profile (hcloud)

Cara paling mudah untuk user baru (beda laptop/server):

```bash
./scripts/huawei/setup_hcloud_profiles.sh dh_prod_erp-ro
```

Script ini otomatis:
- install mapping profile Huawei ke `~/.hcloud/config.json`
- login SSO 1 profile sumber
- sync token ke semua profile SSO

Login SSO sekali di profile sumber, lalu sinkron token ke profile SSO lain:

```bash
hcloud configure sso --cli-profile=dh_prod_erp-ro
./scripts/huawei/sync_sso_token.sh --source dh_prod_erp-ro
```

Verifikasi cepat:

```bash
hcloud configure show --cli-profile=dh_prod_erp-ro --cli-output=json
hcloud ECS ListServersDetails --cli-profile=dh_prod_erp-ro --cli-region=ap-southeast-4 --limit=1 --cli-output=json
```

## 5) Jalankan check Huawei

```bash
monitoring-hub --check huawei-ecs-util --profile dh_prod_erp-ro --region ap-southeast-4
```

Output Huawei saat ini default:
- hanya **1 output report** (tanpa blok WhatsApp terpisah)
- istilah report dipadatkan: **stabil tinggi terus** dan **spike**

## 6) Helper script yang dipakai

- `scripts/huawei/setup_hcloud_profiles.sh`
- `scripts/huawei/sync_sso_token.sh`

## 7) Catatan data Huawei (akurasi)

- Data diambil live dari API Huawei via `hcloud`:
  - `ECS ListServersDetails`
  - `CES ListMetrics`
  - `CES ShowMetricData`
- Pengambilan ECS dan metrik menggunakan pagination supaya tidak berhenti di satu page limit.
- Jika memory tidak tersedia pada akun tertentu, biasanya metrik `AGT.ECS/mem_usedPercent` tidak terpublikasi untuk instance tersebut.

## 8) Troubleshooting singkat

- `profile config not found`:
  - cek `hcloud configure show --cli-profile=<profile>`
- token expired:
  - login ulang `hcloud configure sso --cli-profile=<source>` lalu jalankan sync lagi
- permission config file:
  - pastikan `~/.hcloud` mode `700`
  - pastikan `~/.hcloud/config.json` mode `600`
