# apps/tui scaffold

This folder is an incremental scaffold toward the target app-first layout.

- Canonical runtime implementation is in `backend/interfaces/cli/`.
- `apps/tui/main.py` is a compatibility wrapper that delegates to the existing CLI entrypoint.
- Existing operational command `monitoring-hub` remains the default execution path.
