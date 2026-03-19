"""Compatibility wrapper for legacy src TUI common helpers."""

from backend.interfaces.cli import common as _impl

for _name in dir(_impl):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_impl, _name)

__all__ = [name for name in dir(_impl) if not name.startswith("__")]
