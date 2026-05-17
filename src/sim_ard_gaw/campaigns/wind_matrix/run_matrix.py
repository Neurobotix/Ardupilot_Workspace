#!/usr/bin/env python3
"""
run_matrix.py — orchestrate the full Square Wind Matrix campaign.

For each wind combination, this script:
  • launches Plane SITL non-interactively
  • launches the Gazebo wind world
  • runs run_one.py with active MAVLink mission control
  • cleans up the stack
  • repeats until the requested number of accepted runs is collected
"""
from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    from . import run_one
except ImportError:  # direct script execution from this directory
    import run_one  # type: ignore[no-redef]
from sim_ard_gaw.campaigns.wind_world import write_world_wind


SCRIPT_DIR = Path(__file__).resolve().parent
LAUNCH_SCRIPT = run_one.LAUNCH_SCRIPT
SIM_VEHICLE = run_one.ARDUPILOT_ROOT / "Tools" / "autotest" / "sim_vehicle.py"
PLANE_BASE_PARAM_FILE = run_one.PLANE_BASE_PARAM_FILE
PLANE_AIRSPEED_PARAM_FILE = run_one.PLANE_AIRSPEED_PARAM_FILE
PLANE_PARAM_LOCAL_OVERRIDE = run_one.WORKSPACE_ROOT / ".private" / "config" / "plane_params.local.parm"
PLANE_WIND_WORLD = run_one.ASSETS_ROOT / "worlds" / "mini_talon_wind_runway.sdf"

DEFAULT_STACK_SETTLE = 3.0
DEFAULT_RETRY_DELAY = 2.0
DEFAULT_MAX_ATTEMPTS_PER_COMBO = 20
CLEANUP_TIMEOUT_S = 30.0


def utc_compact_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_wind_values(text: str) -> list[int]:
    values = [int(part.strip()) for part in text.split(",") if part.strip()]
    invalid = [value for value in values if value not in run_one.WIND_VALUES]
    if invalid:
        raise argparse.ArgumentTypeError(
            f"Invalid wind values {invalid}; expected subset of {run_one.WIND_VALUES}")
    return values


def cleanup_stack() -> None:
    try:
        subprocess.run(
            [str(LAUNCH_SCRIPT), "cleanup"],
            cwd=str(SCRIPT_DIR),
            env=run_one.runtime_env(),
            check=False,
            timeout=CLEANUP_TIMEOUT_S,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        pass


def tail_text(path: Path, max_chars: int = 800) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def ensure_process_alive(name: str, proc: subprocess.Popen[str], log_path: Path) -> None:
    code = proc.poll()
    if code is None:
        return
    tail = tail_text(log_path)
    detail = f"\nLast log output:\n{tail}" if tail else ""
    raise RuntimeError(f"{name} exited early with code {code}.{detail}")


def launch_process(cmd: list[str], cwd: Path, log_path: Path) -> tuple[subprocess.Popen[str], object]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=run_one.runtime_env(),
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    return proc, handle


def launch_sitl(
    log_path: Path,
    no_rebuild: bool,
    wipe_eeprom: bool,
    *,
    use_dir: Path | None = None,
    param_files: list[Path] | None = None,
) -> tuple[subprocess.Popen[str], object]:
    effective_param_files = param_files if param_files is not None else default_param_files()
    cmd = [
        run_one.preferred_python(),
        str(SIM_VEHICLE),
        "-v", "ArduPlane",
        "-f", "JSON",
        "--out=udp:127.0.0.1:14551",
    ]
    for param_file in effective_param_files:
        cmd.append(f"--add-param-file={param_file}")
    if wipe_eeprom:
        cmd.append("--wipe-eeprom")
    if no_rebuild:
        cmd.append("--no-rebuild")
    if use_dir is not None:
        use_dir.mkdir(parents=True, exist_ok=True)
        cmd.append(f"--use-dir={use_dir}")
    return launch_process(cmd, run_one.ARDUPILOT_ROOT, log_path)


def default_param_files() -> list[Path]:
    files = [PLANE_BASE_PARAM_FILE, PLANE_AIRSPEED_PARAM_FILE]
    if PLANE_PARAM_LOCAL_OVERRIDE.exists():
        files.append(PLANE_PARAM_LOCAL_OVERRIDE)
    return files


def isolated_sitl_use_dir(stack_log_dir: Path, prefix: str) -> Path:
    return stack_log_dir / f"{prefix}_sitl_state"


def resolve_param_files(args: argparse.Namespace) -> list[Path]:
    if args.param_local is not None and args.no_param_local:
        raise ValueError("--param-local and --no-param-local are mutually exclusive")

    files = [
        args.param_base.expanduser().resolve(),
        args.param_airspeed.expanduser().resolve(),
    ]
    if args.param_local is not None:
        files.append(args.param_local.expanduser().resolve())
    elif not args.no_param_local and PLANE_PARAM_LOCAL_OVERRIDE.exists():
        files.append(PLANE_PARAM_LOCAL_OVERRIDE.resolve())

    missing = [path for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Parameter file(s) missing: " + ", ".join(str(path) for path in missing)
        )
    return files


def write_static_wind_world(x_wind: float, y_wind: float, output_path: Path) -> Path:
    """Write a per-attempt Gazebo world with wind baked in at startup."""
    return write_world_wind(
        PLANE_WIND_WORLD,
        output_path,
        x_mps=x_wind,
        y_mps=y_wind,
    )


def launch_gazebo(
    log_path: Path,
    *,
    world_path: Path | None = None,
) -> tuple[subprocess.Popen[str], object]:
    world = world_path if world_path is not None else PLANE_WIND_WORLD
    cmd = ["gz", "sim", "-v4", "-r", str(world)]
    return launch_process(cmd, run_one.WORKSPACE_ROOT, log_path)


def combo_order(x_values: Iterable[int], y_values: Iterable[int]) -> Iterable[tuple[int, int]]:
    for y in y_values:
        for x in x_values:
            yield x, y


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--x-values", type=parse_wind_values,
                        default="0,4,8,12", metavar="CSV",
                        help="Comma-separated X wind values. Default: 0,4,8,12")
    parser.add_argument("--y-values", type=parse_wind_values,
                        default="0,4,8,12", metavar="CSV",
                        help="Comma-separated Y wind values. Default: 0,4,8,12")
    parser.add_argument("--runs-per-combo", type=int, default=run_one.RUNS_PER_COMBO)
    parser.add_argument("--max-attempts-per-combo", type=int, default=DEFAULT_MAX_ATTEMPTS_PER_COMBO)
    parser.add_argument("--campaign-root", type=Path, default=run_one.DEFAULT_CAMPAIGN_ROOT)
    parser.add_argument("--mission-file", type=Path, default=run_one.MISSION_FILE)
    parser.add_argument("--mavlink", type=str, default=run_one.DEFAULT_MAVLINK)
    parser.add_argument("--heartbeat-timeout", type=float, default=run_one.DEFAULT_HEARTBEAT_TIMEOUT)
    parser.add_argument("--mission-timeout", type=float, default=run_one.DEFAULT_MISSION_TIMEOUT)
    parser.add_argument("--ready-timeout", type=float, default=run_one.DEFAULT_READY_TIMEOUT)
    parser.add_argument("--upload-timeout", type=float, default=run_one.DEFAULT_UPLOAD_TIMEOUT)
    parser.add_argument("--arm-timeout", type=float, default=run_one.DEFAULT_ARM_TIMEOUT)
    parser.add_argument("--mode-timeout", type=float, default=run_one.DEFAULT_MODE_TIMEOUT)
    parser.add_argument("--stack-settle-s", type=float, default=DEFAULT_STACK_SETTLE)
    parser.add_argument("--retry-delay-s", type=float, default=DEFAULT_RETRY_DELAY)
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
    parser.add_argument("--no-force-arm", action="store_true")
    parser.add_argument("--wipe-eeprom", action="store_true",
                        help="Wipe SITL EEPROM before each attempt. Off by default to match launch.sh plane-airspeed.")
    parser.add_argument("--rebuild", action="store_true",
                        help="Allow sim_vehicle.py to rebuild instead of using --no-rebuild.")
    parser.add_argument(
        "--param-base",
        type=Path,
        default=PLANE_BASE_PARAM_FILE,
        help=f"Base Plane parameter file. Default: {PLANE_BASE_PARAM_FILE}",
    )
    parser.add_argument(
        "--param-airspeed",
        type=Path,
        default=PLANE_AIRSPEED_PARAM_FILE,
        help=f"CTE/airspeed overlay parameter file. Default: {PLANE_AIRSPEED_PARAM_FILE}",
    )
    parser.add_argument(
        "--param-local",
        type=Path,
        default=None,
        help=(
            "Optional local override parameter file. Default: use "
            f"{PLANE_PARAM_LOCAL_OVERRIDE} when present."
        ),
    )
    parser.add_argument(
        "--no-param-local",
        action="store_true",
        help="Do not append the default .private/config/plane_params.local.parm override.",
    )
    args = parser.parse_args()

    if args.runs_per_combo < 1:
        parser.error("--runs-per-combo must be >= 1")
    if args.max_attempts_per_combo < 1:
        parser.error("--max-attempts-per-combo must be >= 1")
    return args


def main() -> None:
    args = parse_args()
    args.campaign_root = args.campaign_root.resolve()
    args.mission_file = args.mission_file.resolve()
    run_one.validate_square_wind_mission_contract(args.mission_file)
    param_files = resolve_param_files(args)
    args.campaign_root.mkdir(parents=True, exist_ok=True)
    stack_log_dir = args.campaign_root / "scripts" / "orchestrator_logs"
    stack_log_dir.mkdir(parents=True, exist_ok=True)
    with run_one.campaign_manifest_lock(args.campaign_root):
        manifest = run_one.load_manifest(args.campaign_root)
        manifest["target_run_count"] = args.runs_per_combo
        run_one.save_manifest(args.campaign_root, manifest)
        run_one.save_campaign_summary(args.campaign_root, manifest)

    print()
    run_one.log("=" * 60)
    run_one.log("Square Wind Matrix — run_matrix.py")
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
    run_one.log("=" * 60)
    print()

    try:
        for x_wind, y_wind in combo_order(args.x_values, args.y_values):
            key = run_one.combo_key(x_wind, y_wind)
            combo_attempts = 0

            while True:
                manifest = run_one.load_manifest(args.campaign_root)
                accepted = len(run_one.combo_successes(manifest, key))
                if accepted >= args.runs_per_combo:
                    run_one.log(
                        f"{key}: skipping launch because manifest already has "
                        f"{accepted}/{args.runs_per_combo} accepted runs "
                        f"in {args.campaign_root}."
                    )
                    break

                combo_attempts += 1
                if combo_attempts > args.max_attempts_per_combo:
                    raise RuntimeError(
                        f"{key}: exceeded max attempts per combo ({args.max_attempts_per_combo})")

                rep = accepted + 1
                stamp = utc_compact_now()
                prefix = f"{key}__rep_{rep:02d}__{stamp}"
                sitl_log = stack_log_dir / f"{prefix}_sitl.log"
                gazebo_log = stack_log_dir / f"{prefix}_gazebo.log"
                gazebo_world = stack_log_dir / f"{prefix}_world.sdf"
                sitl_use_dir = isolated_sitl_use_dir(stack_log_dir, prefix)
                sitl_bin_dir = run_one.sitl_bin_dir(sitl_use_dir)
                pre_launch_bins: set[str] = (
                    {p.name for p in sitl_bin_dir.glob("*.BIN")}
                    if sitl_bin_dir.exists() else set()
                )
                sitl_proc = None
                gazebo_proc = None
                sitl_handle = None
                gazebo_handle = None

                run_one.log(f"{key}: starting attempt for rep {rep}/{args.runs_per_combo}.")
                cleanup_stack()

                try:
                    sitl_proc, sitl_handle = launch_sitl(
                        sitl_log,
                        no_rebuild=not args.rebuild,
                        wipe_eeprom=args.wipe_eeprom,
                        use_dir=sitl_use_dir,
                        param_files=param_files,
                    )
                    time.sleep(args.stack_settle_s)
                    ensure_process_alive("SITL", sitl_proc, sitl_log)

                    if args.wind_world_mode == "calm-runtime":
                        # Start calm; run_one applies the requested wind by topic.
                        write_static_wind_world(0.0, 0.0, gazebo_world)
                        preloaded_wind_world = None
                        preloaded_wind_refresh = True
                    else:
                        write_static_wind_world(float(x_wind), float(y_wind), gazebo_world)
                        preloaded_wind_world = gazebo_world
                        preloaded_wind_refresh = args.wind_world_mode == "preloaded-refresh"
                    gazebo_proc, gazebo_handle = launch_gazebo(
                        gazebo_log,
                        world_path=gazebo_world,
                    )
                    time.sleep(args.stack_settle_s)
                    ensure_process_alive("Gazebo", gazebo_proc, gazebo_log)

                    record = run_one.run_one(
                        x_wind=x_wind,
                        y_wind=y_wind,
                        rep=rep,
                        campaign_root=args.campaign_root,
                        mavlink_addr=args.mavlink,
                        mission_file=args.mission_file,
                        heartbeat_timeout=args.heartbeat_timeout,
                        mission_timeout=args.mission_timeout,
                        ready_timeout=args.ready_timeout,
                        upload_timeout=args.upload_timeout,
                        arm_timeout=args.arm_timeout,
                        mode_timeout=args.mode_timeout,
                        accept_square_only=args.accept_square_only,
                        manual_control=False,
                        force_arm=not args.no_force_arm,
                        before_bin_names=pre_launch_bins,
                        sitl_log_dir=sitl_use_dir,
                        preloaded_wind_world=preloaded_wind_world,
                        preloaded_wind_refresh=preloaded_wind_refresh,
                        auto_wind_phase=args.auto_wind_phase,
                        param_file_stack=param_files,
                    )
                    run_one.log(f"{key}: attempt finished with status={record.get('status')}.")
                finally:
                    cleanup_stack()
                    if sitl_handle is not None:
                        sitl_handle.close()
                    if gazebo_handle is not None:
                        gazebo_handle.close()
                    time.sleep(args.retry_delay_s)

    finally:
        cleanup_stack()


if __name__ == "__main__":
    main()
