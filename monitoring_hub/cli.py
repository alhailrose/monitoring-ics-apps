#!/usr/bin/env python3
"""Legacy CLI wrapper delegating to canonical src app bootstrap."""


def main():
    from src.app.cli import bootstrap

    return bootstrap.main()


__all__ = ["main"]


if __name__ == "__main__":
    main()
