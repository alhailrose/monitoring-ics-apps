# Docs Cleanup Inventory

Snapshot untuk merapikan dokumentasi pasca migrasi foldering/backend canonical.

## Primary source-of-truth

- `docs/development/backend-development-plan.md`
- `docs/PROJECT.md`
- `docs/architecture/current-foldering-guide.md`
- `docs/architecture/migration-status.md`
- `docs/architecture/target-structure-contract.md`

## Files reviewed (2026-03-19)

- `docs/AWS-SETUP.md`
- `docs/PROJECT.md`
- `docs/api/frontend-contract-v1.md`
- `docs/architecture/current-foldering-guide.md`
- `docs/architecture/folder-structure.md`
- `docs/architecture/migration-status.md`
- `docs/architecture/src-wrapper-inventory.md`
- `docs/architecture/target-structure-contract.md`
- `docs/development/NEXT-SESSION-HANDOFF.md`
- `docs/development/backend-development-plan.md`
- `docs/design/web-monitoring-platform-design.md`
- `docs/implementation/BACKEND-IMPLEMENTATION.md`
- `docs/implementation/FRONTEND-IMPLEMENTATION.md`
- `docs/implementation/FRONTEND-SESSION-PROMPT.md`
- `docs/operations/deployment-flow.md`
- `docs/operations/release-checklist.md`
- `docs/operations/single-server-deploy.md`
- `docs/setup/setup-guide-id.md`

## Status summary

- Entry-point docs updated: `monitoring-hub -> backend.interfaces.cli.main:main`
- Canonical runtime docs aligned: `backend/*` as source of truth
- Runtime namespace cutover completed: `src/*` python wrappers removed from tracked code

## Remaining docs cleanup candidates

- `docs/design/web-monitoring-platform-design.md` (very long; verify runtime/path sections for current architecture)
- `docs/implementation/*.md` (confirm still needed; merge/archive if obsolete)
- Add archive policy for stale historical docs to reduce noise
