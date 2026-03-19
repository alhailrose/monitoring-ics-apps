"""Compatibility module alias for legacy src CLI bootstrap."""

import sys

from backend.interfaces.cli import bootstrap as _impl

sys.modules[__name__] = _impl

if __name__ == "__main__":
    _impl.main()
