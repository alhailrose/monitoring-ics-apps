# Migration Status

This repository is in progressive migration to the target scalable layout under `src/`.

Reference contract: `docs/architecture/target-structure-contract.md`

## Completed in this phase

- Created full target directory skeleton:
  - `src/app/*`, `src/core/*`, `src/providers/aws/*`, `src/checks/*`, `src/configs/*`
- Added non-breaking adapter modules in the new layout.
- Added customer config schema/default placeholders in `src/configs`.
- Added and validated canonical runner/core/config modules under `src/`.
- Moved test suite into `tests/unit` and `tests/integration`.
- Switched checks registry imports to `src.checks.*` paths.
- Moved CLI canonical bootstrap to `src/app/cli/bootstrap.py` with stable legacy wrapper.

## Current runtime source of truth

- Canonical source path is now `src/` for app/core/providers/config/check registry entry imports.
- Legacy modules remain as compatibility wrappers to protect existing command usage.

## Next migration steps

1. Continue replacing remaining adapter files with direct implementations under `src/`.
2. Remove legacy wrappers after zero remaining runtime imports.
3. Add API implementation under `src/app/api` for dashboard phase.

## Checkpoint

Migration checkpoint is **green** for continuing structured development.
