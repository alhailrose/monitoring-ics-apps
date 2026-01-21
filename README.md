# AWS Monitoring Hub

CLI terpusat untuk memantau kesehatan, keamanan, dan biaya AWS (GuardDuty, CloudWatch, Cost Anomaly, Backup, RDS, EC2 list) dengan menu interaktif.

## Prasyarat
- Python 3.9+
- Akses AWS (SSO atau kredensial) sesuai profil di `~/.aws/config`
- Git + akses ke repo (SSH atau HTTPS)
- pipx (disarankan untuk instalasi tim) atau venv lokal

## Konfigurasi GitHub SSH (WSL/Linux)
1) Pastikan paket SSH:
   ```
   sudo apt-get update && sudo apt-get install git openssh-client
   ```
2) Buat key (jika belum ada):
   ```
   ssh-keygen -t ed25519 -C "email@domain"
   ```
3) Jalankan agent dan tambah key (set otomatis di shell rc bila perlu):
   ```
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```
4) Tambahkan ke GitHub (copy isi `~/.ssh/id_ed25519.pub` ke Settings > SSH keys).
5) Opsional `~/.ssh/config` agar pasti pakai key ini:
   ```
   Host github.com
     HostName github.com
     User git
     IdentityFile ~/.ssh/id_ed25519
     IdentitiesOnly yes
   ```
6) Tes akses:
   ```
   ssh -T git@github.com
   ```

## Setup pipx (tanpa clone)
1) Pasang pipx (Debian/Ubuntu/WSL):
   ```
   sudo apt-get update && sudo apt-get install pipx
   pipx ensurepath
   ```
   Jika tidak bisa apt, gunakan:
   ```
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```
   Tambahkan PATH bila perlu (WSL/bash/zsh): `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc` lalu buka terminal baru.

2) Install dari repo (ganti `<REPO_URL>` dan `<TAG>`/`main`):
   ```
   pipx install "git+<REPO_URL>@<TAG>"
   ```
   Contoh SSH: `pipx install "git+ssh://git@github.com/alhailrose/monitoring-ics-apps.git@main"`
   Contoh HTTPS (publik/bertok): `pipx install "git+https://github.com/alhailrose/monitoring-ics-apps.git@main"`
3) Jalankan di folder mana saja:
   ```
   monitoring-hub
   ```
   (tanpa argumen langsung masuk mode interaktif)
4) Upgrade ke versi terbaru:
   ```
   pipx reinstall "git+<REPO_URL>@<TAG>"   # atau pipx upgrade monitoring-hub jika URL sama
   ```

## Jalankan langsung (lokal, venv)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python monitoring_hub.py      # atau: monitoring_hub.py --check health --profile myprof
```

## Catatan penggunaan
- Pastikan sudah login AWS (SSO atau credentials) sesuai profil yang ada di `PROFILE_GROUPS` atau profil lokal di `~/.aws/config`.
- Tanpa argumen, `monitoring-hub` langsung membuka menu interaktif. Esc/Ctrl+C di menu utama langsung keluar.
- Mode interaktif: pilih check → pilih akun (backup/RDS/all bisa multi) → pilih region → output tampil.
- Untuk run non-interaktif: `monitoring-hub --check guardduty --profile myprof` atau `--all --profile a,b`.

## Catatan penggunaan
- Pastikan sudah login AWS (SSO atau credentials) sesuai profil yang ada di `PROFILE_GROUPS` atau profil lokal di `~/.aws/config`.
- Esc/Ctrl+C di menu utama langsung keluar; di prompt pemilihan akan kembali/keluar.
- Menu interaktif: pilih check, pilih akun (bisa multi untuk backup/RDS/all), pilih region, lalu output ditampilkan.
