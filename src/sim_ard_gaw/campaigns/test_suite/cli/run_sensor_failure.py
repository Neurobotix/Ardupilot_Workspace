"""Run the sensor_failure (GPS fault injection) suite — sequential scheduler.

Phase 4 second plugin. GPS-only scope, two case types:
  - gps_disable    (hard GPS denial via SIM_GPS1_ENABLE=0 mid-square)
  - gps_glitch_50m (~50 m position glitch via SIM_GPS1_GLTCH_{X,Y} mid-square)

This CLI is staged-only (the plugin has no legacy delegate) and selects the
plugin through `cli/_registry.py`. The wind_matrix CLIs are unchanged.

Example:
  PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 \\
    -m sim_ard_gaw.campaigns.test_suite.cli.run_sensor_failure \\
    --cases gps_disable,gps_glitch_50m --repeats 3 \\
    --campaign-root var/runs/sensor_failure_gps_live_$(date +%Y%m%dT%H%M%S) \\
    --wipe-eeprom --stack-settle-s 8 --heartbeat-timeout 120 \\
    --ready-timeout 120 --mission-timeout 1800
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ..core.scheduler import SequentialScheduler
from ..core.suite_runner import SuiteRunner, SuiteRunSettings
from ..plugins.sensor_failure import cases as gps_cases
from ..plugins.sensor_failure import defaults


def _parse_cases(text: str) -> tuple[str, ...]:
    out = [c.strip() for c in text.split(",") if c.strip()]
    unknown = [c for c in out if c not in gps_cases.ALL_CASE_IDS]
    if unknown:
        raise argparse.ArgumentTypeError(
            f"Unknown case(s) {unknown}; known: {list(gps_cases.ALL_CASE_IDS)}"
        )
    return tuple(out)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--plugin", default="sensor_failure",
                   help="Plugin name (default and only: sensor_failure)")
    p.add_argument("--attempt-strategy", choices=("staged",), default="staged",
                   help="Attempt implementation path (staged only)")
    p.add_argument("--cases", type=_parse_cases, default=None,
                   help="Comma-separated case ids (default: all GPS cases)")
    p.add_argument("--repeats", type=int, default=defaults.DEFAULT_REPEATS)
    p.add_argument("--max-attempts-per-case", type=int,
                   default=defaults.DEFAULT_MAX_ATTEMPTS_PER_CASE)
    p.add_argument("--campaign-root", type=Path, default=defaults.DEFAULT_CAMPAIGN_ROOT)
    p.add_argument("--mission-file", type=Path, default=defaults.MISSION_FILE)
    p.add_argument("--injection-waypoint", type=int,
                   default=defaults.DEFAULT_INJECTION_WAYPOINT)
    p.add_argument("--post-inject-window-s", type=float,
                   default=defaults.DEFAULT_POST_INJECT_WINDOW_S)
    p.add_argument("--mavlink", type=str, default=defaults.DEFAULT_MAVLINK)
    p.add_argument("--heartbeat-timeout", type=float,
                   default=defaults.DEFAULT_HEARTBEAT_TIMEOUT)
    p.add_argument("--mission-timeout", type=float,
                   default=defaults.DEFAULT_MISSION_TIMEOUT)
    p.add_argument("--ready-timeout", type=float, default=defaults.DEFAULT_READY_TIMEOUT)
    p.add_argument("--upload-timeout", type=float, default=defaults.DEFAULT_UPLOAD_TIMEOUT)
    p.add_argument("--arm-timeout", type=float, default=defaults.DEFAULT_ARM_TIMEOUT)
    p.add_argument("--mode-timeout", type=float, default=defaults.DEFAULT_MODE_TIMEOUT)
    p.add_argument("--stack-settle-s", type=float, default=defaults.DEFAULT_STACK_SETTLE)
    p.add_argument("--retry-delay-s", type=float, default=defaults.DEFAULT_RETRY_DELAY)
    p.add_argument("--param-base", type=Path, default=defaults.PLANE_BASE_PARAM_FILE)
    p.add_argument("--param-airspeed", type=Path,
                   default=defaults.PLANE_AIRSPEED_PARAM_FILE)
    p.add_argument("--param-local", type=Path, default=None)
    p.add_argument("--no-param-local", action="store_true")
    p.add_argument("--no-force-arm", action="store_true")
    p.add_argument("--wipe-eeprom", action="store_true")
    p.add_argument("--rebuild", action="store_true")
    return p


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = build_arg_parser()
    args = p.parse_args(argv)
    if args.plugin != "sensor_failure":
        p.error(
            f"run_sensor_failure only supports --plugin sensor_failure; got {args.plugin}"
        )
    if args.repeats < 1:
        p.error("--repeats must be >= 1")
    if args.max_attempts_per_case < 1:
        p.error("--max-attempts-per-case must be >= 1")
    if args.injection_waypoint < 1:
        p.error("--injection-waypoint must be >= 1")
    return args


def config_kwargs_from_args(args: argparse.Namespace) -> dict:
    """Translate CLI args into SensorFailureConfig kwargs (resolved paths)."""
    param_files = defaults.resolve_param_files(
        param_base=args.param_base,
        param_airspeed=args.param_airspeed,
        param_local=args.param_local,
        no_param_local=args.no_param_local,
    )
    return {
        "case_ids": tuple(args.cases) if args.cases else None,
        "repeats": args.repeats,
        "campaign_root": args.campaign_root.resolve(),
        "mission_file": args.mission_file.resolve(),
        "mavlink_addr": args.mavlink,
        "heartbeat_timeout_s": args.heartbeat_timeout,
        "mission_timeout_s": args.mission_timeout,
        "ready_timeout_s": args.ready_timeout,
        "upload_timeout_s": args.upload_timeout,
        "arm_timeout_s": args.arm_timeout,
        "mode_timeout_s": args.mode_timeout,
        "injection_waypoint": args.injection_waypoint,
        "post_inject_window_s": args.post_inject_window_s,
        "force_arm": not args.no_force_arm,
        "auto_control": True,
        "launch_stack": True,
        "rebuild": args.rebuild,
        "wipe_eeprom": args.wipe_eeprom,
        "stack_settle_s": args.stack_settle_s,
        "retry_delay_s": args.retry_delay_s,
        "param_file_stack": param_files,
        "isolated_sitl_state": True,
        "attempt_strategy": "staged",
    }


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    from sim_ard_gaw.campaigns.mission_contract import (
        validate_square_wind_mission_contract,
    )
    from ._registry import build_plugin

    kwargs = config_kwargs_from_args(args)
    validate_square_wind_mission_contract(kwargs["mission_file"])
    campaign_root: Path = kwargs["campaign_root"]
    campaign_root.mkdir(parents=True, exist_ok=True)

    from sim_ard_gaw.campaigns.manifest_safety import campaign_manifest_lock
    from ..plugins.sensor_failure.manifest import SensorFailureManifest

    with campaign_manifest_lock(campaign_root):
        manifest_adapter = SensorFailureManifest(campaign_root)
        manifest = manifest_adapter.load()
        manifest["target_run_count"] = kwargs["repeats"]
        manifest_adapter.save(manifest)

    selected = list(kwargs["case_ids"] or gps_cases.ALL_CASE_IDS)
    print()
    defaults.log("=" * 60)
    defaults.log("Sensor Failure (GPS) - test_suite.cli.run_sensor_failure")
    defaults.log(f"  Campaign root : {campaign_root}")
    defaults.log(f"  Mission       : {kwargs['mission_file']}")
    defaults.log(f"  Cases         : {selected}")
    defaults.log(f"  Repeats       : {kwargs['repeats']}")
    defaults.log(f"  Inject at WP  : {kwargs['injection_waypoint']}")
    defaults.log(f"  Observe window: {kwargs['post_inject_window_s']:.0f} s")
    defaults.log("  Param stack   :")
    for param_file in kwargs["param_file_stack"]:
        defaults.log(f"    {param_file}")
    defaults.log("=" * 60)
    print()

    plugin = build_plugin("sensor_failure", **kwargs)
    suite = SuiteRunner(
        case_generator=plugin.case_generator,
        scheduler=SequentialScheduler(),
        attempt_runner=plugin.attempt_runner(),
        manifest=plugin.manifest,
        attempt_dir_factory=plugin.attempt_dir_factory(),
        settings=SuiteRunSettings(
            max_attempts_per_case=args.max_attempts_per_case,
            inter_attempt_delay_s=kwargs["retry_delay_s"],
        ),
    )
    suite.run()


if __name__ == "__main__":
    main()
