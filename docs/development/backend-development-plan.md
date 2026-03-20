# Backend Development Plan (Living)

This is the main living plan for backend evolution.

- Use this file as the single source of truth for phase status.
- Update checklist items before every commit.
- Update user-facing docs and API contract docs only when a phase goal is achieved.

## Scope and constraints

- Backend API is DB-persistent and analytics-oriented.
- TUI remains local and fast, with no DB persistence.
- Backend config source of truth: database.
- TUI config source of truth: customer YAML.
- AWS direct SDK remains primary execution model.
- Migration policy: forward-only (no mandatory backfill).

### Authentication boundary

- App auth and AWS auth are separate layers.
- App auth: users log in to the app with roles `super_user` (admin) and `user` (readonly).
- AWS auth is per customer (not per app user), using `access_key`, `assume_role`, or `sso`.
- Recommendation: new customer onboarding should default to `assume_role` (`MonitoringReadOnlyRole`).
- For expired customer `sso` sessions: send Slack notification and runbook command `aws sso login --profile <profile> --use-device-code --no-browser`.

### Production note (short)

- PostgreSQL: source of truth for persistent backend data (`check_runs`, normalized events/metrics, per-account check config).
- Redis: operational cache/queue/session support where enabled by deployment profile.
- AWS Secrets Manager: store customer AWS connection secrets and integration secrets.

## Current check inventory

- Generic/core: `health`, `cost`, `guardduty`, `cloudwatch`, `notifications`, `backup`, `ec2list`, `aws-utilization-3core`
- Customer-specific: `daily-arbel`, `daily-budget`, `alarm_verification`
- Provider-specific: `huawei-ecs-util`

## Phase overview

| Phase | Goal | Status |
|---|---|---|
| 0 | Enforce execution-mode policy (TUI non-persistent, API persistent) | completed |
| 1 | Normalize security/alert findings | completed |
| 2 | Normalize backup reliability events | completed |
| 3 | Normalize utilization and globalize config-driven checks | completed |
| 4 | Finalize remaining checks + frontend API contract | completed |
| 4.5 | Foldering and docs alignment (pre-Phase 5) | planned |
| 5 | Authentication and AWS connection lifecycle hardening | planned |

## Detailed checklist

### Phase 0 - Execution policy guardrails

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Add execution context fields | Tambahkan field konteks eksekusi `run_source` dan `persist_mode` | Setiap jalur eksekusi punya konteks persistensi eksplisit | Completed (100%) |
| Enforce TUI non-persistent | Terapkan guard agar jalur TUI selalu `persist_mode=none` | TUI tidak menulis data ke repository DB | Completed (100%) |
| Enforce API persistent | Terapkan guard agar jalur API selalu `persist_mode=normalized` | API menulis hasil normalisasi ke DB | Completed (100%) |
| TUI persistence tests | Tambahkan unit test bahwa TUI tidak memanggil repository persistence | Regressions persistence pada TUI terdeteksi otomatis | Completed (100%) |
| API persistence tests | Tambahkan unit test bahwa API menulis data persistence | Regressions persistence pada API terdeteksi otomatis | Completed (100%) |
| Phase closure | Tutup Phase 0 setelah seluruh guardrail tervalidasi | Phase 0 resmi selesai | Completed (100%) |

### Phase 1 - Security/alert normalization

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Add findings schema | Tambahkan skema normalisasi `finding_events` + migrasi DB | Temuan keamanan/alert tersimpan dalam model terstruktur | Completed (100%) |
| Add findings mappers | Implement mapper untuk `guardduty`, `cloudwatch`, `notifications` | Output checker terpetakan konsisten ke event normalisasi | Completed (100%) |
| Persist findings from API | Simpan findings normalisasi pada jalur eksekusi API | Hasil run API menghasilkan data findings queryable | Completed (100%) |
| Findings query endpoint | Tambahkan endpoint query findings (filter + pagination) | Frontend/API consumer dapat query findings stabil | Completed (100%) |
| Findings contract examples | Tambahkan contoh kontrak response findings | Integrasi frontend punya acuan payload yang jelas | Completed (100%) |
| Phase closure | Tutup Phase 1 setelah persistence + query + contract valid | Phase 1 resmi selesai | Completed (100%) |

### Phase 2 - Backup normalization

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Backup mapping dimensions | Tambahkan dimensi backup (profile/account/region/plan/vault/status) | Event backup punya struktur detail yang konsisten | Completed (100%) |
| Persist backup events | Simpan event reliability backup ke tabel normalisasi | Temuan backup bisa dianalisis lintas run | Completed (100%) |
| Backup query filters | Tambahkan filter query findings khusus backup | Consumer bisa isolasi event backup dengan cepat | Completed (100%) |
| Backup mapping tests | Tambahkan test untuk kasus failed/expired/completed | Mapping backup stabil terhadap edge case utama | Completed (100%) |
| Phase closure | Tutup Phase 2 setelah mapping + persistence tervalidasi | Phase 2 resmi selesai | Completed (100%) |

### Phase 3 - Utilization and global config-driven rollout

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Add metrics schema | Tambahkan skema normalisasi `metric_samples` + migrasi | Data metrik numerik tersimpan terstruktur | Completed (100%) |
| Map daily-arbel metrics | Petakan output `daily-arbel` ke `metric_samples` | Metrik daily-arbel dapat diquery lintas run/account | Completed (100%) |
| Add per-account config model | Tambahkan model config check per account (alarm/budget/backup/threshold) | Konfigurasi check dapat dikelola terpusat di DB | Completed (100%) |
| Config management API | Implement endpoint API untuk kelola config per account | Frontend/operator dapat ubah config tanpa edit YAML langsung | Completed (100%) |
| Globalized check rollout | Aktifkan rollout config-driven untuk `alarm_verification`, `daily-budget`, RDS/utilization, `backup` | Jalur eksekusi API menggunakan konfigurasi DB secara konsisten | Completed (100%) |
| Preserve TUI behavior | Pertahankan TUI tetap YAML-driven non-persistent | TUI existing flow tetap stabil dan tidak terdampak persistence API | Completed (100%) |
| Phase closure | Tutup Phase 3 setelah rollout + test stabil | Phase 3 resmi selesai | Completed (100%) |

### Phase 4 - API spec and frontend readiness

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Publish stable API spec | Finalisasi spec API untuk `runs`, `findings`, `metrics`, `dashboard` | Frontend punya kontrak endpoint stabil | Completed (100%) |
| Add DTO and examples | Tambahkan DTO/response examples untuk endpoint utama | Implementasi frontend lebih cepat dan minim ambiguity | Completed (100%) |
| Contract stability tests | Tambahkan integration test untuk menjaga stabilitas kontrak | Perubahan backend yang breaking cepat terdeteksi | Completed (100%) |
| Docs refresh | Update README dan docs interface sesuai hasil phase | Dokumentasi user/dev sinkron dengan runtime aktual | Completed (100%) |
| Phase closure | Tutup Phase 4 setelah kontrak + docs tervalidasi | Phase 4 resmi selesai | Completed (100%) |

### Phase 4.5 - Foldering and docs alignment

| Task | Description | Expected Outcome | Status Progress |
|---|---|---|---|
| Canonical boundary freeze | Tetapkan boundary runtime: `backend/*` sebagai canonical, `src/*` sebagai compatibility layer transisi | Boundary runtime jelas dan konsisten di code/docs | Completed (100%) |
| Wrapper inventory | Inventaris modul wrapper `src/*` dan kandidat safe-removal | Daftar wrapper + kandidat cleanup terdokumentasi | Completed (100%) |
| Architecture docs alignment | Sinkronkan dokumen arsitektur ke struktur foldering current-state | Dokumen arsitektur merefleksikan struktur terbaru | Completed (100%) |
| Stale docs cleanup | Rapikan/hapus narasi pre-migration yang masih dianggap runtime aktif | Tidak ada narasi stale yang menyesatkan | Completed (100%) |
| Entrypoint docs alignment | Selaraskan `README.md`, `docs/PROJECT.md`, runbook terhadap model entrypoint/delegation terbaru | Referensi entrypoint konsisten lintas dokumen | Completed (100%) |
| Foldering guide handoff | Tambah/update dokumen penjelasan foldering untuk continuity antarsesi/model | Ada panduan foldering khusus untuk handoff | Completed (100%) |
| References sanity check | Validasi path/command docs dengan grep sanity pass | Referensi docs tervalidasi tanpa mismatch utama | Completed (100%) |
| Phase closure | Tutup Phase 4.5 setelah semua task selesai | Phase 4.5 resmi selesai | Completed (100%) |

### Phase 5 - Authentication and AWS connection layer

- [ ] Enforce auth boundary in backend services (App Auth roles vs per-customer AWS Auth ownership)
- [ ] Add/verify per-customer AWS auth mode model and API contract (`access_key`, `assume_role`, `sso`)
- [ ] Implement AWS login method selection/validation per customer (`assume_role` default, `sso`, `access_key`)
- [ ] Add explicit backend login-method resolver rules (priority, required fields, and invalid-combination errors)
- [ ] Set onboarding default for new customers to `assume_role` (`MonitoringReadOnlyRole`)
- [ ] Add runtime handling for expired `sso` sessions (detect expiry, classify error state)
- [ ] Send Slack notification on `sso` expiry with actionable profile context
- [ ] Document and expose admin runbook action: `aws sso login --profile <profile> --use-device-code --no-browser`
- [ ] Add AWS CLI login method guidance in ops runbook (`aws login` vs `aws sso login`) and enforce supported command per auth mode
- [ ] Add unit/integration tests for auth boundary, mode selection, and `sso` expiry notification path
- [ ] Mark phase as done in this plan

## Commit and docs workflow

### Before every commit

- [ ] Update relevant checklist items in this file
- [ ] Ensure item statuses match actual implementation

### At phase completion only

- [ ] Update `README.md` current architecture and usage notes
- [ ] Update API contract docs for changed endpoints/payloads
- [ ] Update interface docs (TUI/API/Web) only where phase impact exists

## Change log

- 2026-03-19: Initial living plan created from backend readiness assessment.
- 2026-03-19: Phase 0 completed (execution policy split + persistence policy tests).
- 2026-03-19: Phase 1 started (finding_events schema + security mapper + API persistence write path).
- 2026-03-19: Phase 1 completed (`/api/v1/findings` + frontend contract examples).
- 2026-03-19: Phase 2 completed (backup normalized finding mapping + persistence and tests).
- 2026-03-19: Phase 3 started (account check-config DB model + API CRUD + executor merge path).
- 2026-03-19: Phase 3 progress (added metric_samples schema + daily-arbel metric normalization persistence path).
- 2026-03-19: Phase 3 progress (globalized DB-config rollout for alarm verification, budget, backup, and utilization checks).
- 2026-03-19: Phase 3 completed.
- 2026-03-19: Phase 4 completed (stable contract for runs/findings/metrics/dashboard + integration contract test).
- 2026-03-19: Clarified app-vs-AWS auth boundary, customer auth modes, SSO-expiry Slack+runbook handling, and production infra note.
- 2026-03-19: Added Phase 5 checklist for authentication boundary and AWS connection lifecycle implementation tracking.
- 2026-03-19: Added Phase 4.5 checklist for foldering/docs alignment before Phase 5 implementation.
- 2026-03-19: Added `src/*` wrapper inventory doc and initial safe-removal candidate list for foldering cleanup.
- 2026-03-19: Migrated customer TUI flow to canonical backend path and converted legacy src flow to compatibility alias.
- 2026-03-19: Migrated runner engine/models (`src/core/engine`, `src/core/models`) to canonical backend paths with src compatibility aliases.
- 2026-03-19: Migrated report formatting (`src/core/formatting/reports.py`) to canonical backend path with src compatibility alias.
- 2026-03-19: Phase 4.5 completed (foldering/docs alignment, wrapper inventory, and canonical migration checkpoints).
- 2026-03-19: Added `backend/checks/*` bridge namespace and switched backend runtime imports away from direct `src.checks.*` dependencies.
- 2026-03-19: Migrated checker implementations to `backend/checks/*` and converted `src/checks/*` to compatibility aliases.
- 2026-03-19: Finalized checks cutover by removing `src/checks/*` package and updating imports/tests to `backend/checks/*`.
