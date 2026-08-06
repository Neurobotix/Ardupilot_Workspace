"""Run one attempt for a single case.

Mirrors the flag surface of the historical `run_one.py` where that surface is
still live. The attempt pipeline uses the extracted stage adapters (stimulus,
MAVLink control, monitor, analysis, verdict).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core.models import TestCase
from ..plugins.wind_matrix import defaults
from ._plugin_select import (
    add_common_actions,
    emit_case_list,
    emit_dry_run,
    resolve_runner_plugin_or_exit,
)
from .deprecated_flags import (
    add_deprecated_attempt_strategy,
    consume_deprecated_attempt_strategy,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plugin", default="wind_matrix",
                   help="Plugin name (default: wind_matrix)")
    add_common_actions(p)
    add_deprecated_attempt_strategy(p)
    p.add_argument("--x", type=int, choices=defaults.WIND_VALUES)
    p.add_argument("--y", type=int, choices=defaults.WIND_VALUES)
    p.add_argument("--rep", type=int)
    p.add_argument("--campaign-root", type=Path,
                   default=defaults.DEFAULT_CAMPAIGN_ROOT)
    p.add_argument("--mission-file", type=Path, default=defaults.MISSION_FILE)
    p.add_argument("--mavlink", type=str, default=defaults.DEFAULT_MAVLINK)
    p.add_argument("--heartbeat-timeout", type=float,
                   default=defaults.DEFAULT_HEARTBEAT_TIMEOUT)
    p.add_argument("--mission-timeout", type=float,
                   default=defaults.DEFAULT_MISSION_TIMEOUT)
    p.add_argument("--ready-timeout", type=float,
                   default=defaults.DEFAULT_READY_TIMEOUT)
    p.add_argument("--upload-timeout", type=float,
                   default=defaults.DEFAULT_UPLOAD_TIMEOUT)
    p.add_argument("--arm-timeout", type=float, default=defaults.DEFAULT_ARM_TIMEOUT)
    p.add_argument("--mode-timeout", type=float, default=defaults.DEFAULT_MODE_TIMEOUT)
    p.add_argument("--accept-square-only", action="store_true")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--auto-wind-phase", choices=defaults.AUTO_WIND_PHASES,
                   default=None)
    p.add_argument("--preloaded-wind-world", type=Path, default=None)
    p.add_argument("--no-preloaded-wind-refresh", action="store_true")
    p.add_argument("--no-force-arm", action="store_true")
    args = p.parse_args()
    consume_deprecated_attempt_strategy(args, p)
    # --x/--y/--rep stay mandatory for an actual run; the inspection actions
    # are the only invocations that may omit them.
    if not (args.list_cases or args.dry_run):
        missing = [
            flag for flag, value in
            (("--x", args.x), ("--y", args.y), ("--rep", args.rep))
            if value is None
        ]
        if missing:
            p.error(
                "the following arguments are required: " + ", ".join(missing)
            )
    if args.auto_wind_phase is None:
        args.auto_wind_phase = defaults.default_auto_wind_phase(
            auto_control=args.auto,
        )
    return args


def run_from_args(args: argparse.Namespace, *, title: str = "test_suite.cli.run_case") -> None:
    """Execute one attempt from parsed args.

    Shared by the flag path (`main`) and the interactive wizard, so both
    resolve settings through exactly one code path.
    """
    from ..plugins.wind_matrix import build_plugin
    from ..plugins.wind_matrix.config import WindMatrixConfig

    # Inspection actions never launch a stack. run_case targets one combo, so
    # it lists the combos --x/--y can select from.
    if getattr(args, "list_cases", False) or getattr(args, "dry_run", False):
        preview = WindMatrixConfig(
            campaign_root=args.campaign_root.resolve(),
            mission_file=args.mission_file.resolve(),
        )
        cases = list(build_plugin(preview).case_generator.iter_cases())
        if args.x is not None and args.y is not None:
            selected = defaults.combo_key(args.x, args.y)
            cases = [c for c in cases if c.case_id == selected]
        if args.list_cases:
            emit_case_list(cases)
        else:
            emit_dry_run(
                "wind_matrix",
                {
                    "x": args.x,
                    "y": args.y,
                    "rep": args.rep,
                    "campaign_root": args.campaign_root.resolve(),
                    "mission_file": args.mission_file.resolve(),
                    "mavlink": args.mavlink,
                    "auto_control": args.auto,
                    "auto_wind_phase": args.auto_wind_phase,
                    "accept_square_only": args.accept_square_only,
                    "mission_timeout_s": args.mission_timeout,
                    "launch_stack": False,
                },
                cases,
            )
        return

    if not (1 <= args.rep <= defaults.RUNS_PER_COMBO):
        sys.exit(f"ERROR: --rep must be 1..{defaults.RUNS_PER_COMBO}")

    print()
    defaults.log("=" * 60)
    defaults.log(f"Square Wind Matrix - {title}")
    defaults.log(f"  Wind : x={args.x} m/s (East)   y={args.y} m/s (North)")
    defaults.log(f"  Rep  : {args.rep}/{defaults.RUNS_PER_COMBO}")
    defaults.log(f"  Listen: {args.mavlink}")
    defaults.log(f"  Control: {'auto' if args.auto else 'manual'}")
    if args.auto:
        defaults.log(f"  Auto wind phase: {args.auto_wind_phase}")
    if args.preloaded_wind_world is not None:
        defaults.log(f"  Preloaded world: {args.preloaded_wind_world}")
    defaults.log("=" * 60)
    print()
    if args.auto:
        defaults.log("This run will upload the mission and launch AUTO over MAVLink.")
    else:
        defaults.log("Make sure these are running:")
        defaults.log(f"  Terminal A:  {defaults.CTE_SITL_COMMAND}")
        defaults.log(f"  Terminal B:  {defaults.CTE_GAZEBO_COMMAND}")
    print()

    config = WindMatrixConfig(
        runs_per_combo=defaults.RUNS_PER_COMBO,
        campaign_root=args.campaign_root.resolve(),
        mission_file=args.mission_file.resolve(),
        mavlink_addr=args.mavlink,
        heartbeat_timeout_s=args.heartbeat_timeout,
        mission_timeout_s=args.mission_timeout,
        ready_timeout_s=args.ready_timeout,
        upload_timeout_s=args.upload_timeout,
        arm_timeout_s=args.arm_timeout,
        mode_timeout_s=args.mode_timeout,
        accept_square_only=args.accept_square_only,
        auto_control=args.auto,
        launch_stack=False,
        force_arm=not args.no_force_arm,
        auto_wind_phase=args.auto_wind_phase,
        preloaded_wind_world=(
            args.preloaded_wind_world.resolve()
            if args.preloaded_wind_world is not None else None
        ),
        preloaded_wind_refresh=not args.no_preloaded_wind_refresh,
    )

    plugin = build_plugin(config)
    runner = plugin.attempt_runner()
    case = TestCase(
        suite_name="wind_matrix",
        case_id=defaults.combo_key(args.x, args.y),
        parameters={"wind_x_mps": args.x, "wind_y_mps": args.y},
        scenario_name="square_500m_five_laps_loiter5_land",
        stimulus_name="gazebo_world_wind" if args.auto else "gz_topic_wind",
        mission_file=config.mission_file,
        acceptance_target_runs=1,
    )
    attempt_index = plugin.manifest.next_attempt_index(case)
    attempt_dir = plugin.attempt_dir_factory()(
        plugin.manifest,
        case,
        attempt_index,
    )
    runner.run(
        case=case,
        target_run_index=args.rep,
        attempt_index=attempt_index,
        attempt_dir=attempt_dir,
    )


def main() -> None:
    args = _parse_args()
    resolve_runner_plugin_or_exit(args.plugin, "run_case")
    run_from_args(args)


if __name__ == "__main__":
    main()
