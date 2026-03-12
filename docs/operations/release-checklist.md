# Release Checklist (Evidence-Oriented)

Checklist ini dipakai saat rilis bertahap per target (`web`, `api`, `tui`) supaya bukti deployability tidak bercampur.

## Aturan umum

- Rilis dilakukan per target, bukan satu paket besar.
- Tiap target wajib punya bukti pre-release, gate approval, dan post-release.
- Simpan bukti di tiket rilis (link workflow run, output smoke test, dan rollback note).

## Web release evidence

- Pre-release quality gate: `bash scripts/ci/web-quality.sh`
- Build artifact tersedia dari workflow CI Web (`web-dist` artifact)
- Manual gate metadata (GitHub Actions):
  - `target=web`
  - `approval_notes` terisi
  - `rollback_notes` terisi
- Post-release smoke:
  - `curl -I http://<host>/` mengembalikan `200` atau `304`
  - buka halaman `http://<host>/` dan verifikasi dashboard render

## API release evidence

- Pre-release quality gate: `bash scripts/ci/api-quality.sh`
- Compose valid: `docker compose -f infra/docker/docker-compose.yml config`
- Manual gate metadata (GitHub Actions):
  - `target=api`
  - `approval_notes` terisi
  - `rollback_notes` terisi
- Post-release smoke:
  - `curl -fsS http://<host>/health`
  - `curl -fsS http://<host>/health/readiness`
  - `curl -fsS http://<host>/api/v1/checks/available`

## TUI release evidence

- Pre-release quality gate: `bash scripts/ci/tui-quality.sh`
- Paket/entrypoint tervalidasi: `uv run monitoring-hub --help`
- Manual gate metadata (GitHub Actions):
  - `target=tui`
  - `approval_notes` terisi
  - `rollback_notes` terisi
- Post-release smoke (operator machine):
  - `monitoring-hub --help`
  - jalankan satu check aman, misalnya `monitoring-hub --check health --profile <profile>`

## Definition of done per release target

- Evidence pre-release + post-release lengkap.
- `deploy-manual` workflow summary terlampir di tiket.
- Rollback command sudah diuji formatnya (tidak placeholder).
- Tidak ada blocker lint/test pada target terkait.
