# Setup Guide Monitoring Hub (AWS + Huawei)

Dokumen ini merangkum setup dari nol sampai siap menjalankan check Huawei dengan flow token sinkron.

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
aws sso login --profile <nama_profil>
aws sts get-caller-identity --profile <nama_profil> --region ap-southeast-1
```

Catatan: YAML customer/default hanya menyimpan mapping profile/check, bukan credential.

## 4) Setup Huawei profile (hcloud)

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

## 6) Onboarding user lain (share konfigurasi, login tetap masing-masing)

### Opsi A - step manual

1. Export template aman (token dihapus):

```bash
./scripts/huawei/export_hcloud_template.sh --output ./hcloud-config-template.json
```

2. Install template ke home user target:

```bash
./scripts/huawei/bootstrap_hcloud_user.sh \
  --template ./hcloud-config-template.json \
  --target-home /home/<user> \
  --owner <user>:<user>
```

3. Di user target, login lalu sync token:

```bash
hcloud configure sso --cli-profile=dh_prod_erp-ro
./scripts/huawei/sync_sso_token.sh --source dh_prod_erp-ro
```

### Opsi B - satu perintah wrapper

```bash
./scripts/huawei/onboard_hcloud_user.sh \
  --target-user <user> \
  --source-profile dh_prod_erp-ro
```

Jika ingin wrapper langsung mengeksekusi login + sync sebagai user target:

```bash
./scripts/huawei/onboard_hcloud_user.sh \
  --target-user <user> \
  --source-profile dh_prod_erp-ro \
  --execute-login-sync
```

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
