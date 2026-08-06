"""Unified test-suite entry point.

With no arguments: launches the interactive wizard, then dispatches to the
appropriate runner.

With arguments: passes straight through to the correct sub-command, so all
existing flag-based invocations keep working:

    sim-test case      --x 0 --y 4 --rep 1 ...
    sim-test suite     --x-values 0,4 ...
    sim-test rr        --x-values 0,4 ...
    sim-test airspeed  --list-cases ...
    sim-test gps       --list-cases ...

Run ``sim-test <subcommand> --help`` for the full flag surface of each mode.

The wizard does not reimplement any runner. It builds an argparse namespace
and hands it to the same ``run_from_args`` function the flag path calls, so
the two paths cannot drift apart in their settings.
"""
from __future__ import annotations

import sys

_SUBCOMMANDS = {
    "case": ("run_case", "main"),
    "suite": ("run_suite", "main"),
    "rr": ("run_round_robin", "main"),
    "round-robin": ("run_round_robin", "main"),
    "airspeed": ("run_airspeed_failure", "main"),
    "gps": ("run_gps_failure", "main"),
}


def main() -> None:
    # No arguments at all → interactive wizard
    if len(sys.argv) == 1:
        from .interactive import run_wizard
        mode, args = run_wizard()
        _dispatch(mode, args)
        return

    # First positional argument selects sub-command
    sub = sys.argv[1]

    if sub in _SUBCOMMANDS:
        module_name, func_name = _SUBCOMMANDS[sub]
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        module = __import__(
            f"{__package__}.{module_name}", fromlist=[func_name]
        )
        getattr(module, func_name)()
        return

    # No recognised sub-command — could be a bare flag like --help.
    print(__doc__)
    print(f"Subcommands: {', '.join(dict.fromkeys(_SUBCOMMANDS))}")
    sys.exit(1 if sub not in ("-h", "--help") else 0)


def _dispatch(mode: str, args) -> None:
    """Route a wizard namespace to the runner that owns that lane and mode.

    Each branch calls the same entry function as the corresponding flag-based
    invocation; there is no wizard-only execution path.
    """
    if args.plugin == "airspeed_failure":
        from .run_airspeed_failure import run_suite_from_args
        run_suite_from_args(args)
    elif args.plugin == "gps_failure":
        from .run_gps_failure import run_suite_from_args as run_gps_suite
        run_gps_suite(args)
    elif mode == "case":
        from .run_case import run_from_args
        run_from_args(args, title="test_suite.cli.run  [interactive]")
    elif mode == "suite":
        from .run_suite import run_from_args
        run_from_args(args, title="test_suite.cli.run  [interactive]")
    else:
        from .run_round_robin import run_from_args
        run_from_args(args, title="test_suite.cli.run  [interactive]")


if __name__ == "__main__":
    main()
