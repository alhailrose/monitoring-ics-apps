# Konfigurasi AWS Profiles untuk monitoring-hub

Panduan setup AWS CLI profiles agar monitoring-hub bisa mengakses semua customer account.

---

## Prasyarat

- **AWS CLI v2** — [Panduan install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Akses ke SSO portal masing-masing customer (butuh undangan/permission dari admin customer)

Cek versi AWS CLI:
```bash
aws --version
# aws-cli/2.x.x ...
```

---

## Cara Cepat: Script Otomatis

Script `setup-aws-profiles.sh` di root repo ini akan menambahkan semua profiles ke `~/.aws/config` secara otomatis.

```bash
bash setup-aws-profiles.sh
```

Script ini:
- Menambahkan SSO sessions dan semua profile SSO tanpa input manual
- Untuk profile yang menggunakan assumed role atau IAM user, akan meminta input ARN / credentials
- **Tidak menimpa** profile yang sudah ada

Setelah script selesai, lanjut ke bagian [Login SSO](#login-sso) di bawah.

---

## Cara Manual

Jika ingin menambahkan profile satu per satu, edit file `~/.aws/config`.

### Struktur Umum

Ada dua tipe profile yang digunakan:

**1. SSO (mayoritas customer)**
```ini
[profile <nama-profile>]
sso_session = <nama-sso-session>
sso_account_id = <account-id-aws>
sso_role_name = <nama-role>
region = ap-southeast-3
```

**2. Assumed Role / IAM User (beberapa customer)**
```ini
[profile <nama-profile>]
login_session = <arn-assumed-role-atau-iam-user>
region = <region>
```

> Profile dengan `login_session` **tidak di-refresh otomatis**. Credentials perlu diupdate manual jika expired.

---

## SSO Sessions

Tambahkan semua blok SSO session berikut ke `~/.aws/config`:

```ini
[sso-session sadewa-sso]
sso_start_url = https://d-96670a95bf.awsapps.com/start/#/
sso_region = ap-southeast-1
sso_registration_scopes = sso:account:access

[sso-session aryanoble-sso]
sso_start_url = https://aryanoble-sso.awsapps.com/start/#
sso_region = ap-southeast-3
sso_registration_scopes = sso:account:access

[sso-session Nabati]
sso_start_url = https://ksni.awsapps.com/start/
sso_region = ap-southeast-3
sso_registration_scopes = sso:account:access

[sso-session HungryHub]
sso_start_url = https://d-9667bb79ef.awsapps.com/start/#
sso_region = ap-southeast-1
sso_registration_scopes = sso:account:access
```

---

## Profiles per Customer

### sadewa-sso

| Profile | Account ID | Role |
|---------|-----------|------|
| Diamond | 464587839665 | aws_ms |
| Techmeister | 763944546283 | aws_ms |
| fresnel-ykai | 339712722804 | aws_ms |
| fresnel-pialang | 510940807875 | aws_ms |
| fresnel-phoenix | 197353582440 | aws_ms |
| KKI | 471112835466 | aws_ms |
| bbi | 940404076348 | aws_ctc |
| edot | 261622543538 | aws_ctc |
| ucoal-appfuel | 593793048887 | aws_ctc |
| ucoal-legal | 622022425112 | aws_ctc |
| ucoal-minescape | 595985021323 | aws_ctc |
| ucoal-prod | 637423564327 | aws_ctc |
| programa | 779060063462 | aws_ctc |

Contoh blok config:
```ini
[profile Diamond]
sso_session = sadewa-sso
sso_account_id = 464587839665
sso_role_name = aws_ms
region = ap-southeast-3
```

### aryanoble-sso

| Profile | Account ID | Role |
|---------|-----------|------|
| HRIS | 493314732063 | ics-ms-rw |
| fee-doctor | 084828597777 | ics-ms-rw |
| iris-dev | 522814711071 | ics-ms-rw |
| backup-hris | 390403877301 | ics-ms-rw |
| cis-erha | 451916275465 | AWSReadOnlyAccess |
| connect-prod | 620463044477 | AWSReadOnlyAccess |
| public-web | 211125667194 | AWSReadOnlyAccess |
| dermies-max | 637423567244 | AWSReadOnlyAccess |
| tgw | 654654394944 | AWSReadOnlyAccess |
| iris-prod | 522814722913 | AWSReadOnlyAccess |
| sfa | 546158667544 | AWSReadOnlyAccess |
| erha-buddy | 486250145105 | AWSReadOnlyAccess |
| centralized-s3 | 533267291161 | AWSReadOnlyAccess |
| dwh | 084056488725 | AWSReadOnlyAccess |
| genero-empower | 941377160792 | AWSReadOnlyAccess |
| genero-manufacture | 798344624633 | AWSReadOnlyAccess |
| arbel-master | 477153214925 | AWSReadOnlyAccess |

Contoh blok config:
```ini
[profile connect-prod]
sso_session = aryanoble-sso
sso_account_id = 620463044477
sso_role_name = AWSReadOnlyAccess
region = ap-southeast-3
```

### Nabati (KSNI)

| Profile | Account ID | Role |
|---------|-----------|------|
| ksni-master | 317949653982 | ReadOnlyAccess |
| core-network-ksni | 207567759835 | ReadOnlyAccess |
| data-ksni | 563983755611 | ReadOnlyAccess |
| dc-trans-ksni | 982538789545 | ReadOnlyAccess |
| edin-ksni | 288232812256 | ReadOnlyAccess |
| eds-ksni | 701824263187 | ReadOnlyAccess |
| epc-ksni | 783764594649 | ReadOnlyAccess |
| erp-ksni | 992382445286 | ReadOnlyAccess |
| etl-ksni | 654654389300 | ReadOnlyAccess |
| hc-assessment-ksni | 909927813600 | ReadOnlyAccess |
| hc-portal-ksni | 954030863852 | ReadOnlyAccess |
| ngs-ksni | 296062577084 | ReadOnlyAccess |
| outdig-ksni | 465455994566 | ReadOnlyAccess |
| outlet-ksni | 112555930839 | ReadOnlyAccess |
| q-devpro | 528160043048 | ReadOnlyAccess |
| sales-support-pma | 734881641265 | ReadOnlyAccess |
| website-ksni | 637423330091 | ReadOnlyAccess |

### HungryHub

| Profile | Account ID | Role |
|---------|-----------|------|
| prod-hungryhub | 202255947274 | AWSReadOnlyAccess |
| prod-audit | 454538763126 | AWSReadOnlyAccess |
| prod-log | 993490993790 | AWSReadOnlyAccess |
| prod-security | 380983552701 | AWSReadOnlyAccess |
| prod-root | 891572013503 | AWSPowerUserAccess |
| prod-sandbox | 079994049689 | AWSReadOnlyAccess |

### Profiles dengan login_session

Profile berikut tidak menggunakan SSO — sudah di-hardcode ARN-nya di script (sama dengan konfigurasi pemilik repo).

| Profile | ARN | Region |
|---------|-----|--------|
| fresnel-master | `arn:aws:sts::466650104955:assumed-role/ics-awsc-msw/bagus` | ap-southeast-3 |
| nikp | `arn:aws:sts::038361715485:assumed-role/ics-awsc-msw/bagus` | ap-southeast-1 |
| sandbox | `arn:aws:sts::339712808680:assumed-role/ics-awsc-msa/bagus.faqihuddin@icscompute.com` | us-east-1 |
| rumahmedia | `arn:aws:sts::975050309328:assumed-role/ics-awsc-msw/bagus.faqihuddin@icscompute.com` | ap-southeast-2 |
| asg | `arn:aws:iam::264887202956:user/bagusfaqihuddin.ics` | ap-southeast-3 |
| arista-web | `arn:aws:iam::717271747993:user/arista-webmarketing-admin` | ap-southeast-1 |

> **Catatan:** `login_session` adalah field custom untuk monitoring-hub. Profile ini tidak di-refresh otomatis oleh AWS CLI — jika credentials expired, perlu update manual di `~/.aws/config`.

---

## Login SSO

Setelah semua profile dikonfigurasi, login ke setiap SSO session:

```bash
aws sso login --sso-session sadewa-sso
aws sso login --sso-session aryanoble-sso
aws sso login --sso-session Nabati
aws sso login --sso-session HungryHub
```

Browser akan terbuka untuk autentikasi. Token berlaku **±8 jam**.

Jika token expired, cukup jalankan ulang perintah `aws sso login` yang sesuai.

---

## Verifikasi

Cek apakah profile bisa diakses:

```bash
# Cek satu profile
aws sts get-caller-identity --profile connect-prod

# Cek beberapa profile sekaligus
for p in connect-prod HRIS prod-hungryhub; do
  echo -n "$p: "
  aws sts get-caller-identity --profile "$p" --query 'Account' --output text 2>/dev/null || echo "GAGAL"
done
```

---

## Troubleshooting

**`Error loading SSO Token: Token for ...`**
: Token expired. Jalankan `aws sso login --sso-session <nama-session>`.

**`Profile "xxx" not found`**
: Profile belum ada di `~/.aws/config`. Tambahkan manual atau jalankan ulang script.

**`An error occurred (AccessDenied)`**
: Profile ada tapi tidak punya permission. Pastikan role name sesuai dengan yang diberikan customer.

**`login_session` tidak bisa digunakan**
: Profile jenis ini memerlukan credentials yang masih valid (tidak expired). Hubungi PIC untuk mendapatkan credentials baru.
