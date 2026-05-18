"""Run one attempt for a single case.

Mirrors the flag surface of the legacy `run_one.py` so existing scripts
can be migrated by swapping the entry point.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core import _legacy
from ..core.models import TestCase


def _parse_args() -> argparse.Namespace:
    run_one = _legacy.run_one_module()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plugin", default="wind_matrix",
                   help="Plugin name (default: wind_matrix)")
    p.add_argument("--x", type=int, required=True, choices=run_one.WIND_VALUES)
    p.add_argument("--y", type=int, required=True, choices=run_one.WIND_VALUES)
    p.add_argument("--rep", type=int, required=True)
    p.add_argument("--campaign-root", type=Path,
                   default=run_one.DEFAULT_CAMPAIGN_ROOT)
    p.add_argument("--mission-file", type=Path, default=run_one.MISSION_FILE)
    p.add_argument("--mavlink", type=str, default=run_one.DEFAULT_MAVLINK)
    p.add_argument("--heartbeat-timeout", type=float,
                   default=run_one.DEFAULT_HEARTBEAT_TIMEOUT)
    p.add_argument("--mission-timeout", type=float,
                   default=run_one.DEFAULT_MISSION_TIMEOUT)
    p.add_argument("--ready-timeout", type=float,
                   default=run_one.DEFAULT_READY_TIMEOUT)
    p.add_argument("--upload-timeout", type=float,
                   default=run_one.DEFAULT_UPLOAD_TIMEOUT)
    p.add_argument("--arm-timeout", type=float, default=run_one.DEFAULT_ARM_TIMEOUT)
    p.add_argument("--mode-timeout", type=float, default=run_one.DEFAULT_MODE_TIMEOUT)
    p.add_argument("--accept-square-only", action="store_true")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--auto-wind-phase", choices=run_one.AUTO_WIND_PHASES,
                   default=run_one.DEFAULT_AUTO_WIND_PHASE)
    p.add_argument("--preloaded-wind-world", type=Path, default=None)
    p.add_argument("--no-preloaded-wind-refresh", action="store_true")
    p.add_argument("--no-force-arm", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if args.plugin != "wind_matrix":
        sys.exit(f"Phase-1 supports only wind_matrix; got {args.plugin}")
    run_one = _legacy.run_one_module()
    if not (1 <= args.rep <= run_one.RUNS_PER_COMBO):
        sys.exit(f"ERROR: --rep must be 1..{run_one.RUNS_PER_COMBO}")

    from ..plugins.wind_matrix import build_plugin
    from ..plugins.wind_matrix.config import WindMatrixConfig

    print()
    run_one.log("=" * 60)
    run_one.log("Square Wind Matrix — test_suite.cli.run_case")
    run_one.log(f"  Wind : x={args.x} m/s (East)   y={args.y} m/s (North)")
    run_one.log(f"  Rep  : {args.rep}/{run_one.RUNS_PER_COMBO}")
    run_one.log(f"  Listen: {args.mavlink}")
    run_one.log(f"  Control: {'auto' if args.auto else 'manual'}")
    if args.auto:
        run_one.log(f"  Auto wind phase: {args.auto_wind_phase}")
    if args.preloaded_wind_world is not None:
        run_one.log(f"  Preloaded world: {args.preloaded_wind_world}")
    run_one.log("=" * 60)
    print()
    if args.auto:
        run_one.log("This run will upload the mission and launch AUTO over MAVLink.")
    else:
        run_one.log("Make sure these are running:")
        run_one.log(f"  Terminal A:  {run_one.CTE_SITL_COMMAND}")
        run_one.log(f"  Terminal B:  {run_one.CTE_GAZEBO_COMMAND}")
    print()

    config = WindMatrixConfig(
        runs_per_combo=run_one.RUNS_PER_COMBO,
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
        case_id=_legacy.run_one_module().combo_key(args.x, args.y),
        parameters={"wind_x_mps": args.x, "wind_y_mps": args.y},
        scenario_name="square_500m_five_laps_loiter5_land",
        stimulus_name="gazebo_world_wind" if args.auto else "gz_topic_wind",
        mission_file=config.mission_file,
        acceptance_target_runs=1,
    )
    attempt_dir = plugin.attempt_dir_factory()(plugin.manifest, case)
    attempt_index = plugin.manifest.next_attempt_index(case)
    runner.run(
        case=case,
        target_run_index=args.rep,
        attempt_index=attempt_index,
        attempt_dir=attempt_dir,
    )


if __name__ == "__main__":
    main()
