"""Shared CLI handling for retired compatibility flags."""
from __future__ import annotations

import argparse
import sys


def add_deprecated_attempt_strategy(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--attempt-strategy",
        dest="_deprecated_attempt_strategy",
        metavar="staged",
        default=None,
        help=argparse.SUPPRESS,
    )


def consume_deprecated_attempt_strategy(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    value = getattr(args, "_deprecated_attempt_strategy", None)
    if value is None:
        return
    if value != "staged":
        parser.error(
            "--attempt-strategy was retired; omit it. The staged attempt "
            "pipeline is now the only wind_matrix implementation."
        )
    print(
        "warning: --attempt-strategy staged is retired and ignored; the staged "
        "attempt pipeline is now the only wind_matrix implementation.",
        file=sys.stderr,
    )
    delattr(args, "_deprecated_attempt_strategy")
