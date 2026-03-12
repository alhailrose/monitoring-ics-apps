# apps/web scaffold

This folder is an incremental scaffold toward the target monorepo layout.

- Runtime web app source remains in `web/` (Vite) to keep existing execution paths stable.
- CI and future deployment workflows can safely target `apps/web/**` without forcing a big-bang move.
- When migration is ready, files from `web/` can be moved here in small batches.
