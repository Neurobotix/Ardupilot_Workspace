"""Shared plugin resolution and lane-neutral case selection for the CLI.

The generic runners historically hardcoded ``wind_matrix``. Plugin names are
resolved through `cli/_registry.py` so every registered lane is reachable, and
lane differences stay in the registry rather than in `core/`.
"""
from __future__ import annotations

import sys
from typing import Iterable

from ._registry import PLUGINS


def known_plugins() -> list[str]:
    return sorted(PLUGINS)


def resolve_plugin_or_exit(name: str) -> str:
    """Return `name` if it is a registered plugin, else exit non-zero."""
    if name not in PLUGINS:
        sys.exit(
            f"ERROR: unknown plugin {name!r}; "
            f"registered plugins: {', '.join(known_plugins())}"
        )
    return name


# Lanes the wind-shaped generic runners can actually execute.
#
# run_case/run_suite/run_round_robin take wind_matrix case coordinates
# (--x/--y/--x-values/--y-values), validate the square-wind mission contract,
# and build a WindMatrixConfig. Only 12 of ~29 config fields are common across
# lanes, and the airspeed/gps missions are rejected by that contract, so these
# runners cannot drive another lane by swapping --plugin alone.
#
# Other lanes have their own entry points (`sim-test airspeed`, `sim-test gps`)
# and are reachable from the wizard. Unifying the runners themselves needs a
# lane-neutral config/case-selection design and is tracked separately.
_WIND_SHAPED_RUNNER_LANES = frozenset({"wind_matrix"})


def resolve_runner_plugin_or_exit(name: str, runner: str) -> str:
    """Resolve a plugin for the wind-shaped generic runners.

    Unknown names and lanes these runners cannot drive both exit non-zero,
    with a message that points at the entry point which does work.
    """
    resolve_plugin_or_exit(name)
    if name not in _WIND_SHAPED_RUNNER_LANES:
        entry = {"airspeed_failure": "sim-test airspeed",
                 "gps_failure": "sim-test gps"}.get(name)
        hint = f"use `{entry}` instead" if entry else "no generic runner available"
        sys.exit(
            f"ERROR: {runner} drives wind_matrix cases only "
            f"(--x/--y wind coordinates and the square-wind mission "
            f"contract); it cannot run {name}: {hint}."
        )
    return name


def unsupported_operation(plugin: str, operation: str, reason: str) -> None:
    """Exit non-zero with an explicit message for a lane-unsupported operation.

    A lane that cannot support an operation must say so, rather than silently
    lacking the flag.
    """
    sys.exit(f"ERROR: {plugin} does not support {operation}: {reason}")


def add_common_actions(parser) -> None:
    """Add the lane-neutral inspection actions every lane must support.

    `--list-cases` and `--dry-run` never launch a simulator stack, so they are
    safe on any lane and give every lane the same name for the same job.
    """
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="Print the case ids this invocation would run, then exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved settings and cases without launching anything.",
    )


def emit_case_list(cases: Iterable[object]) -> None:
    for case in cases:
        print(getattr(case, "case_id", case))


def emit_dry_run(plugin: str, settings: dict, cases: Iterable[object]) -> None:
    """Print a resolved-settings dump plus the case list.

    Doubles as the parity evidence between the wizard and the flag path:
    the same settings dict is produced by whichever path resolved it.
    """
    import json

    payload = {
        "plugin": plugin,
        "launch_performed": False,
        "settings": {k: str(v) for k, v in sorted(settings.items())},
        "cases": [str(getattr(c, "case_id", c)) for c in cases],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def select_case_or_exit(cases: Iterable[object], case_id: str):
    """Pick one case by its lane-neutral string id."""
    available: list[str] = []
    for case in cases:
        current = getattr(case, "case_id", None)
        if current == case_id:
            return case
        if current is not None:
            available.append(str(current))
    sys.exit(
        f"ERROR: unknown case {case_id!r}; "
        f"available: {', '.join(available) if available else '(none)'}"
    )
