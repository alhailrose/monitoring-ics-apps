# Deployment Flow (Separable Web/API/TUI)

Dokumen ini mendefinisikan mekanisme gate approval + rollback untuk deployment terpisah `web`, `api`, dan `tui`.

## Prinsip

- Deployment dilakukan per target (`web` atau `api` atau `tui`), tidak big-bang.
- Setiap deployment wajib menyertakan catatan approval dan rollback.
- Approval level dijalankan melalui GitHub Environment protection rules.
- Workflow ini menjalankan gate metadata dan smoke verification post-deploy (bukan eksekutor deploy aplikasi).

## Workflow gate (`deploy-manual`)

- Workflow: `.github/workflows/deploy-manual.yml`
- Trigger: manual (`workflow_dispatch`)
- Input wajib:
  - `target`: `web|api|tui`
  - `environment`: nama environment GitHub
  - `approval_notes`: referensi tiket/approver/risk
  - `rollback_notes`: command/runbook rollback
  - `run_smoke`: jalankan smoke check (`true|false`)
- Input smoke (wajib saat target terkait):
  - `web_base_url` untuk target `web`
  - `api_base_url` untuk target `api`

Output input dan hasil smoke dicatat di `GITHUB_STEP_SUMMARY` sebagai jejak audit minimum.

## Smoke checks yang dijalankan workflow

- `web`: `bash scripts/ci/smoke-web.sh` (cek HTTP status root URL)
- `api`: `bash scripts/ci/smoke-api.sh` (cek liveness, readiness, dan checks endpoint)
- `tui`: `bash scripts/ci/smoke-tui.sh` (cek entrypoint CLI `monitoring-hub --help`)

## Implementasi deploy aktual

- `web` + `api` single server: ikuti `docs/operations/single-server-deploy.md`.
- `tui`: rilis package/command `monitoring-hub` sesuai alur distribusi tim.

## Checklist evidence rilis

Gunakan checklist bukti per target di `docs/operations/release-checklist.md`.

## Template catatan approval dan rollback

Gunakan format ringkas berikut saat trigger workflow:

- `approval_notes`: `Approved by <name> | ticket <id> | risk <low|med|high>`
- `rollback_notes`: `Rollback via <command/runbook-link> | owner <name> | ETA <minutes>`

## Contoh

- `approval_notes`: `Approved by oncall-ops | ticket OPS-2419 | risk medium`
- `rollback_notes`: `Rollback via docs/operations/single-server-deploy.md step 3 | owner platform-team | ETA 10`
