#!/usr/bin/env python3
"""
run_matrix_round_robin.py — round-robin slot runner for the Square Wind Matrix campaign.

This runner gives each pending combo one attempt per pass, with a fixed mission
timeout budget for that attempt. The default slot is 40 minutes, which keeps the
campaign moving even when higher-wind cases are slow.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

try:
    from . import run_matrix, run_one
except ImportError:  # direct script execution from this directory
    import run_matrix  # type: ignore[no-redef]
    import run_one  # type: ignore[no-redef]


DEFAULT_SLOT_MINUTES = 40.0


def parse_focus_combo(s: str) -> tuple[int, int]:
    """Parse 'wind_x_08_y_12' or 'x_08_y_12' into (x, y) ints."""
    key = s.removeprefix("wind_")
    m = re.fullmatch(r"x_(\d+)_y_(\d+)", key)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Cannot parse {s!r}. Expected form: wind_x_08_y_12 or x_08_y_12"
        )
    return int(m.group(1)), int(m.group(2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--x-values",
        type=run_matrix.parse_wind_values,
        default="0,4,8,12",
        metavar="CSV",
        help="Comma-separated X wind values. Default: 0,4,8,12",
    )
    parser.add_argument(
        "--y-values",
        type=run_matrix.parse_wind_values,
        default="0,4,8,12",
        metavar="CSV",
        help="Comma-separated Y wind values. Default: 0,4,8,12",
    )
    parser.add_argument("--runs-per-combo", type=int, default=4)
    parser.add_argument(
        "--slot-minutes",
        type=float,
        default=DEFAULT_SLOT_MINUTES,
        help="Hard per-attempt mission timeout in minutes. Default: 40.",
    )
    parser.add_argument(
        "--monitor-minutes",
        type=float,
        default=None,
        help=(
            "Mission monitor timeout in minutes. Default is slot minus reserved "
            "infrastructure overhead."
        ),
    )
    parser.add_argument(
        "--max-passes",
        type=int,
        default=0,
        help="Stop after this many round-robin passes. 0 means run until complete.",
    )
    parser.add_argument("--campaign-root", type=Path, default=run_one.DEFAULT_CAMPAIGN_ROOT)
    parser.add_argument("--mission-file", type=Path, default=run_one.MISSION_FILE)
    parser.add_argument(
        "--param-base",
        type=Path,
        default=run_matrix.PLANE_BASE_PARAM_FILE,
        help=f"Base Plane parameter file. Default: {run_matrix.PLANE_BASE_PARAM_FILE}",
    )
    parser.add_argument(
        "--param-airspeed",
        type=Path,
        default=run_matrix.PLANE_AIRSPEED_PARAM_FILE,
        help=f"CTE/airspeed overlay parameter file. Default: {run_matrix.PLANE_AIRSPEED_PARAM_FILE}",
    )
    parser.add_argument(
        "--param-local",
        type=Path,
        default=None,
        help=(
            "Optional local override parameter file. Default: use "
            f"{run_matrix.PLANE_PARAM_LOCAL_OVERRIDE} when present."
        ),
    )
    parser.add_argument(
        "--no-param-local",
        action="store_true",
        help="Do not append the default .private/config/plane_params.local.parm override.",
    )
    parser.add_argument("--mavlink", type=str, default=run_one.DEFAULT_MAVLINK)
    parser.add_argument("--heartbeat-timeout", type=float, default=run_one.DEFAULT_HEARTBEAT_TIMEOUT)
    parser.add_argument("--ready-timeout", type=float, default=run_one.DEFAULT_READY_TIMEOUT)
    parser.add_argument("--upload-timeout", type=float, default=run_one.DEFAULT_UPLOAD_TIMEOUT)
    parser.add_argument("--arm-timeout", type=float, default=run_one.DEFAULT_ARM_TIMEOUT)
    parser.add_argument("--mode-timeout", type=float, default=run_one.DEFAULT_MODE_TIMEOUT)
    parser.add_argument("--stack-settle-s", type=float, default=run_matrix.DEFAULT_STACK_SETTLE)
    parser.add_argument("--retry-delay-s", type=float, default=run_matrix.DEFAULT_RETRY_DELAY)
    parser.add_argument(
        "--auto-wind-phase",
        choices=run_one.AUTO_WIND_PHASES,
        default=run_one.DEFAULT_AUTO_WIND_PHASE,
        help=(
            "When runtime topic wind is used, choose when run_one applies it. "
            "Default: after-takeoff."
        ),
    )
    parser.add_argument(
        "--wind-world-mode",
        choices=("calm-runtime", "preloaded-only", "preloaded-refresh"),
        default="calm-runtime",
        help=(
            "calm-runtime starts Gazebo calm and injects by topic; "
            "preloaded-only bakes requested wind into the SDF with no topic refresh; "
            "preloaded-refresh bakes requested wind and also refreshes by topic."
        ),
    )
    parser.add_argument(
        "--accept-square-only",
        action="store_true",
        help=(
            "Stop after the square and loiter phases are complete and accept "
            "the run even if landing later would fail."
        ),
    )
    parser.add_argument(
        "--require-analysis",
        action="store_true",
        help=(
            "Only count a run as accepted when its analysis completed successfully "
            "(analysis_status == 'done'). Runs with failed analysis are retried. "
            "Default: off (mission success alone is sufficient)."
        ),
    )
    parser.add_argument("--no-force-arm", action="store_true")
    parser.add_argument(
        "--no-wipe-eeprom",
        action="store_true",
        help="Preserve SITL EEPROM between attempts. Default is to wipe each attempt.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Allow sim_vehicle.py to rebuild instead of using --no-rebuild.",
    )
    parser.add_argument(
        "--focus-combo",
        metavar="KEY",
        default=None,
        help=(
            "Restrict the campaign to a single combo key, e.g. wind_x_08_y_12 "
            "(or short form x_08_y_12). Runs until --runs-per-combo successes "
            "are collected for that combo only. The x and y values must be within "
            "--x-values / --y-values (default 0,4,8,12)."
        ),
    )
    args = parser.parse_args()

    if args.runs_per_combo < 1:
        parser.error("--runs-per-combo must be >= 1")
    if args.slot_minutes <= 0:
        parser.error("--slot-minutes must be > 0")
    if args.monitor_minutes is not None and args.monitor_minutes <= 0:
        parser.error("--monitor-minutes must be > 0")
    if args.max_passes < 0:
        parser.error("--max-passes must be >= 0")
    if args.focus_combo is not None:
        try:
            fx, fy = parse_focus_combo(args.focus_combo)
        except argparse.ArgumentTypeError as exc:
            parser.error(str(exc))
        else:
            if fx not in args.x_values:
                parser.error(
                    f"--focus-combo x={fx} is not in --x-values {args.x_values}"
                )
            if fy not in args.y_values:
                parser.error(
                    f"--focus-combo y={fy} is not in --y-values {args.y_values}"
                )
            args.x_values = [fx]
            args.y_values = [fy]
    return args


def pending_combos(args: argparse.Namespace) -> list[tuple[int, int, int]]:
    manifest = run_one.load_manifest(args.campaign_root)
    require_analysis: bool = getattr(args, "require_analysis", False)
    pending: list[tuple[int, int, int]] = []
    for x_wind, y_wind in run_matrix.combo_order(args.x_values, args.y_values):
        key = run_one.combo_key(x_wind, y_wind)
        accepted = len(run_one.combo_successes(
            manifest, key, require_analysis=require_analysis
        ))
        if accepted < args.runs_per_combo:
            # rep stays tied to the logical slot (run_01..run_N). run_one()
            # downgrades analysis-failed successes to failed_analysis when
            # require_analysis is on, which frees the slot for retry without
            # shifting alias numbering.
            pending.append((x_wind, y_wind, accepted + 1))
    return pending


def main() -> None:
    args = parse_args()
    args.campaign_root = args.campaign_root.resolve()
    args.mission_file = args.mission_file.resolve()
    run_one.validate_square_wind_mission_contract(args.mission_file)
    param_files = run_matrix.resolve_param_files(args)
    args.campaign_root.mkdir(parents=True, exist_ok=True)
    slot_log_dir = args.campaign_root / "scripts" / "round_robin_logs"
    slot_log_dir.mkdir(parents=True, exist_ok=True)

    with run_one.campaign_manifest_lock(args.campaign_root):
        manifest = run_one.load_manifest(args.campaign_root)
        manifest["target_run_count"] = args.runs_per_combo
        manifest["require_analysis"] = args.require_analysis
        run_one.save_manifest(args.campaign_root, manifest)
        run_one.save_campaign_summary(args.campaign_root, manifest)

    mission_item_count = run_one.mission_item_count(args.mission_file)
    verify_timeout_s = args.upload_timeout + (
        mission_item_count * run_one.VERIFY_MISSION_ITEM_TIMEOUT_S
    )
    wind_retry_budget_s = (
        0.0
        if args.wind_world_mode == "preloaded-only"
        else run_one.WIND_INJECTION_MAX_ATTEMPTS * run_one.WIND_INJECTION_RETRY_S
    )
    # Budget the monitor phase against the *wall-clock* slot. Account for
    # upload and verify separately, include per-item verification waits, and
    # include cleanup/retry in the slot budget so drift is both reduced and
    # reported honestly.
    infra_overhead_s = (
        args.heartbeat_timeout
        + args.ready_timeout
        + args.upload_timeout
        + verify_timeout_s
        + args.arm_timeout
        + run_one.AUTO_ARM_TO_AUTO_SETTLE_S
        + args.mode_timeout
        + 2 * args.stack_settle_s
        + run_matrix.CLEANUP_TIMEOUT_S
        + args.retry_delay_s
        + wind_retry_budget_s
        + run_one.BIN_FLUSH_DELAY_S
        + run_one.ANALYSIS_HEADROOM_S
    )
    slot_seconds = args.slot_minutes * 60.0
    if args.monitor_minutes is None:
        mission_timeout = max(60.0, slot_seconds - infra_overhead_s)
        monitor_budget_note = f"slot - ~{infra_overhead_s:.0f} s overhead"
    else:
        mission_timeout = args.monitor_minutes * 60.0
        monitor_budget_note = "explicit --monitor-minutes override"
    pass_index = 0

    print()
    run_one.log("=" * 60)
    run_one.log("Square Wind Matrix — run_matrix_round_robin.py")
    run_one.log(f"  Campaign root : {args.campaign_root}")
    run_one.log(f"  Mission       : {args.mission_file}")
    run_one.log(f"  X values      : {args.x_values}")
    run_one.log(f"  Y values      : {args.y_values}")
    run_one.log(f"  Runs/combo    : {args.runs_per_combo}")
    run_one.log("  Param stack   :")
    for param_file in param_files:
        run_one.log(f"    {param_file}")
    run_one.log(f"  Wind world    : {args.wind_world_mode}")
    run_one.log(f"  Auto wind     : {args.auto_wind_phase}")
    run_one.log(f"  Slot minutes  : {args.slot_minutes}")
    run_one.log(
        "  Monitor mins  : "
        f"{mission_timeout/60:.1f} ({monitor_budget_note})"
    )
    run_one.log(f"  Mission items : {mission_item_count}")
    run_one.log("=" * 60)
    print()

    try:
        while True:
            pending = pending_combos(args)
            if not pending:
                run_one.log("All combos reached the target accepted run count.")
                break

            pass_index += 1
            if args.max_passes and pass_index > args.max_passes:
                run_one.log(
                    f"Reached max passes ({args.max_passes}) with {len(pending)} combos still pending."
                )
                break

            run_one.log(
                f"Starting round-robin pass {pass_index} with {len(pending)} pending combos."
            )

            for x_wind, y_wind, rep in pending:
                key = run_one.combo_key(x_wind, y_wind)

                manifest = run_one.load_manifest(args.campaign_root)
                accepted = len(run_one.combo_successes(
                    manifest, key, require_analysis=args.require_analysis
                ))
                if accepted >= args.runs_per_combo:
                    run_one.log(f"{key}: already complete, skipping.")
                    continue
                rep = accepted + 1

                stamp = run_matrix.utc_compact_now()
                prefix = f"{key}__rep_{rep:02d}__pass_{pass_index:03d}__{stamp}"
                sitl_log = slot_log_dir / f"{prefix}_sitl.log"
                gazebo_log = slot_log_dir / f"{prefix}_gazebo.log"
                gazebo_world = slot_log_dir / f"{prefix}_world.sdf"
                sitl_proc = None
                gazebo_proc = None
                sitl_handle = None
                gazebo_handle = None
                record = None

                run_one.log(
                    f"{key}: starting round-robin slot for rep {rep}/{args.runs_per_combo} "
                    f"with timeout={args.slot_minutes:.1f} min."
                )
                run_matrix.cleanup_stack()
                slot_start_wall = time.time()
                slot_deadline_monotonic = time.monotonic() + slot_seconds
                run_one_deadline_monotonic = (
                    slot_deadline_monotonic
                    - run_matrix.CLEANUP_TIMEOUT_S
                    - args.retry_delay_s
                )

                try:
                    sitl_use_dir = slot_log_dir / f"{prefix}_sitl_state"
                    sitl_bin_dir = run_one.sitl_bin_dir(sitl_use_dir)
                    # Snapshot the isolated SITL dir *before* launch so the
                    # new BIN log is identified by name only, not by mtime.
                    pre_launch_bins: set[str] = (
                        {p.name for p in sitl_bin_dir.glob("*.BIN")}
                        if sitl_bin_dir.exists() else set()
                    )

                    sitl_proc, sitl_handle = run_matrix.launch_sitl(
                        sitl_log,
                        no_rebuild=not args.rebuild,
                        wipe_eeprom=not args.no_wipe_eeprom,
                        use_dir=sitl_use_dir,
                        param_files=param_files,
                    )
                    time.sleep(args.stack_settle_s)
                    run_matrix.ensure_process_alive("SITL", sitl_proc, sitl_log)

                    if args.wind_world_mode == "calm-runtime":
                        # Start calm; run_one applies the requested wind by topic.
                        run_matrix.write_static_wind_world(0.0, 0.0, gazebo_world)
                        preloaded_wind_world = None
                        preloaded_wind_refresh = True
                    else:
                        run_matrix.write_static_wind_world(
                            float(x_wind), float(y_wind), gazebo_world
                        )
                        preloaded_wind_world = gazebo_world
                        preloaded_wind_refresh = args.wind_world_mode == "preloaded-refresh"
                    gazebo_proc, gazebo_handle = run_matrix.launch_gazebo(
                        gazebo_log,
                        world_path=gazebo_world,
                    )
                    time.sleep(args.stack_settle_s)
                    run_matrix.ensure_process_alive("Gazebo", gazebo_proc, gazebo_log)

                    record = run_one.run_one(
                        x_wind=x_wind,
                        y_wind=y_wind,
                        rep=rep,
                        campaign_root=args.campaign_root,
                        mavlink_addr=args.mavlink,
                        mission_file=args.mission_file,
                        heartbeat_timeout=args.heartbeat_timeout,
                        mission_timeout=mission_timeout,
                        ready_timeout=args.ready_timeout,
                        upload_timeout=args.upload_timeout,
                        arm_timeout=args.arm_timeout,
                        mode_timeout=args.mode_timeout,
                        accept_square_only=args.accept_square_only,
                        manual_control=False,
                        force_arm=not args.no_force_arm,
                        wipe_eeprom=not args.no_wipe_eeprom,
                        require_analysis=args.require_analysis,
                        before_bin_names=pre_launch_bins,
                        sitl_log_dir=sitl_use_dir,
                        slot_deadline_monotonic=run_one_deadline_monotonic,
                        preloaded_wind_world=preloaded_wind_world,
                        preloaded_wind_refresh=preloaded_wind_refresh,
                        auto_wind_phase=args.auto_wind_phase,
                        param_file_stack=param_files,
                    )
                finally:
                    run_matrix.cleanup_stack()
                    if sitl_handle is not None:
                        sitl_handle.close()
                    if gazebo_handle is not None:
                        gazebo_handle.close()
                    time.sleep(args.retry_delay_s)
                    slot_wall_s = time.time() - slot_start_wall
                    overrun = slot_wall_s - slot_seconds
                    overrun_note = (
                        f"  (overran by {overrun:.0f} s)"
                        if overrun > 0 else ""
                    )
                    slot_status = record.get("status") if isinstance(record, dict) else "error"
                    run_one.log(
                        f"{key}: slot finished with status={slot_status} "
                        f"in {slot_wall_s/60:.1f} min{overrun_note}."
                    )

    finally:
        run_matrix.cleanup_stack()


if __name__ == "__main__":
    main()
