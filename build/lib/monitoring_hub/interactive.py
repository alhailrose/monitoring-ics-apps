"""Compatibility wrapper for src.app.tui.interactive."""

from src.app.tui import interactive as _impl

for _name in dir(_impl):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_impl, _name)
