# apps/api scaffold

This folder is an incremental scaffold toward the target app-first layout.

- Canonical runtime implementation is `backend/interfaces/api/`.
- `apps/api/main.py` is a compatibility wrapper that re-exports the current API app.
- Recommended startup command: `uvicorn backend.interfaces.api.main:app`.
