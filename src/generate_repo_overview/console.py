from __future__ import annotations

import sys


def print_status(message: str, *, prefix: str = "repo-overview") -> None:
    print(f"[{prefix}] {message}", file=sys.stderr)
