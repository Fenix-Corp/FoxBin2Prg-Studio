"""Entrypoint: python -m fb2p_studio."""

from __future__ import annotations

import sys

from fb2p_studio.app import run


def main() -> int:
    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
