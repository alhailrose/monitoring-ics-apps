# apps/api scaffold

This folder is an incremental scaffold toward the target app-first layout.

- Canonical runtime implementation remains in `src/app/api/` for now.
- `apps/api/main.py` is a compatibility wrapper that re-exports the current API app.
- Existing commands (for example `uvicorn src.app.api.main:app`) are intentionally unchanged.
