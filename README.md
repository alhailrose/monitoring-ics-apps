# AWS Monitoring Hub

CLI terpusat untuk memantau kesehatan, keamanan, dan biaya AWS (GuardDuty, CloudWatch, Cost Anomaly, Backup, RDS, EC2 list) dengan menu interaktif.

## Jalankan langsung (lokal)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python monitoring_hub.py --interactive
```

## Instalasi untuk tim via repo (tanpa clone manual)
Gunakan pipx supaya isolasi deps per-aplikasi. Ganti `<REPO_URL>` dengan URL Git (SSH/HTTPS) dan `<TAG>` dengan rilis yang ingin dipakai (mis. `v0.1.0`).

```
# sekali: pasang pipx
python3 -m pip install --user pipx && python3 -m pipx ensurepath

# pasang CLI langsung dari repo
pipx install "git+<REPO_URL>@<TAG>"

# jalankan
monitoring-hub --interactive

```

Contoh URL SSH:
```
pipx install "git+ssh://git@your.git.server/monitoring-hub.git@v0.1.0"
```

Contoh URL HTTPS (kalau repo publik atau ada token):
```
pipx install "git+https://your.git.server/monitoring-hub.git@v0.1.0"
```


## Catatan penggunaan
- Pastikan sudah login AWS (SSO atau credentials) sesuai profil yang ada di `PROFILE_GROUPS` atau profil lokal di `~/.aws/config`.
- Esc/Ctrl+C di menu utama langsung keluar; di prompt pemilihan akan kembali/keluar.
- Menu interaktif: pilih check, pilih akun (bisa multi untuk backup/RDS/all), pilih region, lalu output ditampilkan.
