"""Console logging for campaign lanes.

One `log()` for every lane, so console evidence carries a consistent
timestamp and can be correlated against a BIN log timeline or wall-clock
during an incident review.

This module is sensor-agnostic: it takes no lane parameter and contains
no lane-specific behaviour. Machine-readable CLI output (`--list-cases`,
`--dry-run`, `--probe-schema`) must keep using bare `print()`, because a
timestamp prefix would corrupt output that callers parse.
"""
from __future__ import annotations

from datetime import datetime


def log(msg: str) -> None:
    """Print `msg` to stdout prefixed with a local `[HH:MM:SS]` timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
