"""Run an automated suite — sequential scheduler.

Mirrors the flag surface of `run_matrix.py`. With `--plugin
wind_matrix`, the default `--attempt-strategy legacy` body delegates
through the legacy `run_one.run_one(...)` call path. The opt-in
`--attempt-strategy staged` path uses extracted stage adapters but is
not campaign-runtime parity evidence yet; a live SITL/Gazebo
single-attempt diff against the legacy `run_matrix.py` runtime is still
required before treating it as runtime-equivalent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core import _legacy
from ..core.scheduler import SequentialScheduler
from ..core.suite_runner import SuiteRunner, SuiteRunSettings


def _parse_wind_values(text: str) -> list[int]:
    out: list[int] = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        out.append(int(chunk))
    if not out:
        raise argparse.ArgumentTypeError("expected at least one integer")
    run_one = _legacy.run_one_module()
    invalid = [value for value in out if value not in run_one.WIND_VALUES]
    if invalid:
        raise argparse.ArgumentTypeError(
            f"Invalid wind values {invalid}; expected subset of {run_one.WIND_VALUES}"
        )
    return out


def _parse_args() -> argparse.Namespace:
    run_one = _legacy.run_one_module()
    run_matrix = _legacy.run_matrix_module()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plugin", default="wind_matrix")
    p.add_argument("--attempt-strategy", choices=("legacy", "staged"),
                   default="legacy")
    p.add_argument("--x-values", type=_parse_wind_values, default=[0, 4, 8, 12])
    p.add_argument("--y-values", type=_parse_wind_values, default=[0, 4, 8, 12])
    p.add_argument("--runs-per-combo", type=int, default=run_one.RUNS_PER_COMBO)
    p.add_argument("--max-attempts-per-combo", type=int,
                   default=run_matrix.DEFAULT_MAX_ATTEMPTS_PER_COMBO)
    p.add_argument("--campaign-root", type=Path, default=run_one.DEFAULT_CAMPAIGN_ROOT)
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
    p.add_argument("--stack-settle-s", type=float,
                   default=run_matrix.DEFAULT_STACK_SETTLE)
    p.add_argument("--retry-delay-s", type=float,
                   default=run_matrix.DEFAULT_RETRY_DELAY)
    p.add_argument("--auto-wind-phase", choices=run_one.AUTO_WIND_PHASES,
                   default=run_one.DEFAULT_AUTO_WIND_PHASE)
    p.add_argument("--wind-world-mode",
                   choices=("calm-runtime", "preloaded-only", "preloaded-refresh"),
                   default="calm-runtime")
    p.add_argument("--accept-square-only", action="store_true")
    p.add_argument("--no-force-arm", action="store_true")
    p.add_argument("--wipe-eeprom", action="store_true")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--param-base", type=Path,
                   default=run_matrix.PLANE_BASE_PARAM_FILE)
    p.add_argument("--param-airspeed", type=Path,
                   default=run_matrix.PLANE_AIRSPEED_PARAM_FILE)
    p.add_argument("--param-local", type=Path, default=None)
    p.add_argument("--no-param-local", action="store_true")
    args = p.parse_args()
    if args.runs_per_combo < 1:
        p.error("--runs-per-combo must be >= 1")
    if args.max_attempts_per_combo < 1:
        p.error("--max-attempts-per-combo must be >= 1")
    return args


def main() -> None:
    args = _parse_args()
    if args.plugin != "wind_matrix":
        sys.exit(f"Phase-1 supports only wind_matrix; got {args.plugin}")

    from ..plugins.wind_matrix import build_plugin
    from ..plugins.wind_matrix.config import WindMatrixConfig
    run_one = _legacy.run_one_module()
    run_matrix = _legacy.run_matrix_module()

    args.campaign_root = args.campaign_root.resolve()
    args.mission_file = args.mission_file.resolve()
    run_one.validate_square_wind_mission_contract(args.mission_file)
    param_files = run_matrix.resolve_param_files(args)
    args.campaign_root.mkdir(parents=True, exist_ok=True)
    with run_one.campaign_manifest_lock(args.campaign_root):
        manifest = run_one.load_manifest(args.campaign_root)
        manifest["target_run_count"] = args.runs_per_combo
        run_one.save_manifest(args.campaign_root, manifest)
        run_one.save_campaign_summary(args.campaign_root, manifest)

    print()
    run_one.log("=" * 60)
    run_one.log("Square Wind Matrix — test_suite.cli.run_suite")
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

    config = WindMatrixConfig(
        x_values=tuple(args.x_values),
        y_values=tuple(args.y_values),
        runs_per_combo=args.runs_per_combo,
        campaign_root=args.campaign_root,
        mission_file=args.mission_file,
        mavlink_addr=args.mavlink,
        heartbeat_timeout_s=args.heartbeat_timeout,
        mission_timeout_s=args.mission_timeout,
        ready_timeout_s=args.ready_timeout,
        upload_timeout_s=args.upload_timeout,
        arm_timeout_s=args.arm_timeout,
        mode_timeout_s=args.mode_timeout,
        accept_square_only=args.accept_square_only,
        force_arm=not args.no_force_arm,
        auto_control=True,
        launch_stack=True,
        rebuild=args.rebuild,
        wipe_eeprom=args.wipe_eeprom,
        stack_settle_s=args.stack_settle_s,
        retry_delay_s=args.retry_delay_s,
        auto_wind_phase=args.auto_wind_phase,
        wind_world_mode=args.wind_world_mode,
        param_file_stack=param_files,
        isolated_sitl_state=True,
        attempt_strategy=args.attempt_strategy,
    )

    plugin = build_plugin(config)
    suite = SuiteRunner(
        case_generator=plugin.case_generator,
        scheduler=SequentialScheduler(),
        attempt_runner=plugin.attempt_runner(),
        manifest=plugin.manifest,
        attempt_dir_factory=plugin.attempt_dir_factory(),
        settings=SuiteRunSettings(
            max_attempts_per_case=args.max_attempts_per_combo,
            inter_attempt_delay_s=config.retry_delay_s,
        ),
    )
    suite.run()


if __name__ == "__main__":
    main()
