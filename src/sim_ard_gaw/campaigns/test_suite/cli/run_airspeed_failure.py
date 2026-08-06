"""Dry-run and case-list CLI for the airspeed_failure plugin.

Phase 1 never starts SITL or Gazebo. This entry point validates the case schema,
constructs the plugin, and prints the requested payload metadata.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path
from typing import Iterable

from ..plugins.airspeed_failure import build_plugin
from ..plugins.airspeed_failure.case_generator import AirspeedFailureCaseGenerator
from ..plugins.airspeed_failure.config import AirspeedFailureConfig
from ..plugins.airspeed_failure import defaults
from ..plugins.airspeed_failure.environment import build_reference_wind_artifact
from ..plugins.airspeed_failure.wind_profiles import WIND_PROFILES
from ..plugins.airspeed_failure.stimulus import build_injection_artifact
from ._plugin_select import unsupported_operation


def _parse_biases(text: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in text.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("expected at least one bias percent")
    return values


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--round-robin",
        action="store_true",
        help=(
            "Not supported on this lane; airspeed cases are ordered by the "
            "sequential scheduler. Present so the flag reports its own "
            "absence rather than failing as an unknown argument."
        ),
    )
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--full-ratio-sweep", action="store_true")
    parser.add_argument("--bias-percent", type=_parse_biases, default=None)
    parser.add_argument("--vehicle-arspd-ratio", type=float, default=defaults.DEFAULT_VEHICLE_ARSPD_RATIO)
    parser.add_argument("--verified-vehicle-ratio", action="store_true")
    parser.add_argument("--probe-schema", action="store_true")
    parser.add_argument(
        "--wind-profile",
        choices=sorted(WIND_PROFILES),
        default=defaults.DEFAULT_WIND_PROFILE_ID,
    )
    parser.add_argument(
        "--speed-source",
        choices=("do_change_speed_15", "airspeed_cruise"),
        default="do_change_speed_15",
    )
    parser.add_argument(
        "--mechanism-tier",
        choices=("protected", "diagnostic"),
        default="protected",
    )
    parser.add_argument("--expected-ahrs-wind-max", type=float, default=15.0)
    parser.add_argument("--live-smoke", action="store_true")
    parser.add_argument("--live-measurement-probes", action="store_true")
    parser.add_argument("--live-case", dest="live_case_id")
    parser.add_argument("--confirm-live-phase2", action="store_true")
    parser.add_argument("--confirm-live-tailwind-phase3", action="store_true")
    parser.add_argument("--campaign-root", type=Path, default=None)
    parser.add_argument(
        "--param-airspeed",
        type=Path,
        default=None,
        help=(
            "Airspeed overlay applied on top of plane_base.parm. Selects the "
            "envelope cell for the ADR-0012 sensitivity matrix. Defaults to the "
            "baseline config/overlays/plane_airspeed.parm (14/22)."
        ),
    )
    parser.add_argument(
        "--mission",
        type=Path,
        default=None,
        help=(
            "Override the mission file for the live case(s). Used to fly the "
            "ADR-0016 cruise-follow ramp mission (no DO_CHANGE_SPEED) so the "
            "overlay's AIRSPEED_CRUISE is actually flown. Defaults to the case's "
            "built-in mission."
        ),
    )
    parser.add_argument("--mavlink", default="udpin:0.0.0.0:14551")
    parser.add_argument("--mission-timeout", type=float, default=900.0)
    parser.add_argument("--ready-timeout", type=float, default=60.0)
    parser.add_argument("--heartbeat-timeout", type=float, default=defaults.HEARTBEAT_TIMEOUT_S)
    parser.add_argument("--upload-timeout", type=float, default=60.0)
    parser.add_argument("--arm-timeout", type=float, default=60.0)
    parser.add_argument("--mode-timeout", type=float, default=30.0)
    parser.add_argument("--stack-settle-s", type=float, default=defaults.STACK_SETTLE_S)
    parser.add_argument("--no-force-arm", action="store_true")
    parser.add_argument("--no-wipe-eeprom", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args(argv)
    if args.round_robin:
        unsupported_operation(
            "airspeed_failure",
            "--round-robin",
            "cases run under the sequential scheduler; use --live-case or the "
            "sim-test wizard suite path",
        )
    if (
        not args.list_cases
        and not args.dry_run
        and not args.probe_schema
        and not args.live_smoke
        and not args.live_measurement_probes
        and not args.live_case_id
    ):
        parser.error(
            "choose --list-cases, --dry-run, --probe-schema, "
            "--live-smoke, --live-measurement-probes, or --live-case"
        )
    if args.dry_run and not args.case_id:
        parser.error("--dry-run requires --case")
    if (
        args.live_smoke
        or args.live_measurement_probes
        or args.live_case_id
    ) and not args.confirm_live_phase2:
        parser.error("live Phase 2 runs require --confirm-live-phase2")
    if (
        (args.live_smoke or args.live_measurement_probes or args.live_case_id)
        and args.wind_profile == "tailwind_eastbound"
        and not args.confirm_live_tailwind_phase3
    ):
        parser.error(
            "live tailwind runs require separate Phase 3 approval and "
            "--confirm-live-tailwind-phase3"
        )
    return args


def _config_from_args(args: argparse.Namespace) -> AirspeedFailureConfig:
    if args.bias_percent is not None:
        biases = args.bias_percent
    elif args.full_ratio_sweep:
        biases = defaults.FULL_RATIO_BIAS_PERCENTS
    else:
        biases = defaults.V1_RATIO_BIAS_PERCENTS
    if args.param_airspeed is not None:
        param_airspeed = args.param_airspeed.expanduser().resolve()
        if not param_airspeed.exists():
            raise SystemExit(f"ERROR: --param-airspeed file not found: {param_airspeed}")
        param_file_stack: tuple[Path, ...] | None = (
            defaults.PLANE_BASE_PARAM_FILE,
            param_airspeed,
        )
    else:
        param_file_stack = None
    return AirspeedFailureConfig(
        ratio_bias_percents=tuple(biases),
        param_file_stack=param_file_stack,
        campaign_root=args.campaign_root.resolve() if args.campaign_root else defaults.default_campaign_root(),
        vehicle_arspd_ratio=args.vehicle_arspd_ratio,
        vehicle_arspd_ratio_verified=args.verified_vehicle_ratio,
        mavlink_addr=args.mavlink,
        launch_stack=bool(args.live_smoke or args.live_measurement_probes or args.live_case_id),
        force_arm=not args.no_force_arm,
        rebuild=args.rebuild,
        wipe_eeprom=not args.no_wipe_eeprom,
        stack_settle_s=args.stack_settle_s,
        heartbeat_timeout_s=args.heartbeat_timeout,
        ready_timeout_s=args.ready_timeout,
        upload_timeout_s=args.upload_timeout,
        arm_timeout_s=args.arm_timeout,
        mode_timeout_s=args.mode_timeout,
        mission_timeout_s=args.mission_timeout,
        wind_profile_id=args.wind_profile,
        continuous_speed_source=args.speed_source,
        mechanism_tier=args.mechanism_tier,
        expected_ahrs_wind_max=args.expected_ahrs_wind_max,
    )


def main(argv: Iterable[str] | None = None) -> None:
    args = _parse_args(argv)
    config = _config_from_args(args)
    plugin = build_plugin(config)
    generator = AirspeedFailureCaseGenerator(config)

    if args.probe_schema:
        print(json.dumps(defaults.parameter_schema(), indent=2, sort_keys=True))

    if args.list_cases:
        for case in plugin.case_generator.iter_cases():
            print(case.case_id)

    if args.dry_run:
        try:
            case = generator.get_case(args.case_id)
        except ValueError as exc:
            sys.exit(f"ERROR: {exc}")
        dry_run = {
            "phase": "phase1_no_sitl",
            "plugin_constructed": True,
            "case": {
                "case_id": case.case_id,
                "suite_name": case.suite_name,
                "mission_file": str(case.mission_file),
                "parameters": case.parameters,
            },
            "injection_artifact": build_injection_artifact(case),
            "reference_wind_artifact": build_reference_wind_artifact(
                verified=False,
                profile=config.wind_profile,
            ),
            "parameter_schema": defaults.parameter_schema(),
            "launch_performed": False,
        }
        print(json.dumps(dry_run, indent=2, sort_keys=True))

    if args.live_smoke:
        run_live_cases(
            config,
            ["healthy_reference", "fail_primary"],
            title="Airspeed Failure Behavior - Phase 2 live smoke",
        )

    if args.live_measurement_probes:
        run_live_cases(
            config,
            ["healthy_reference", "ofs_noop_probe", "pitot_500pa", "fail_primary"],
            title="Airspeed Failure Behavior - Phase 2 measurement probes",
        )

    if args.live_case_id:
        run_live_cases(
            config,
            [args.live_case_id],
            mission_override=args.mission,
            title="Airspeed Failure Behavior - Phase 2 single live case",
        )


def run_live_cases(
    config: AirspeedFailureConfig,
    cases: list[str],
    *,
    title: str,
    mission_override: Path | None = None,
) -> None:
    plugin = build_plugin(config)
    generator = AirspeedFailureCaseGenerator(config)
    runner = plugin.attempt_runner()
    if mission_override is not None:
        mission_override = mission_override.expanduser().resolve()
        if not mission_override.exists():
            raise SystemExit(f"ERROR: --mission file not found: {mission_override}")
    defaults.log("=" * 60)
    defaults.log(title)
    defaults.log(f"  Campaign root: {config.campaign_root}")
    defaults.log(f"  Mission      : {mission_override or config.mission_file}")
    defaults.log(f"  Cases        : {', '.join(cases)}")
    defaults.log("  Raw output only; no curated evidence promotion")
    defaults.log("=" * 60)
    config.campaign_root.mkdir(parents=True, exist_ok=True)
    for index, case_id in enumerate(cases, start=1):
        case = generator.get_case(case_id)
        if mission_override is not None:
            case = dataclasses.replace(case, mission_file=mission_override)
        attempt_index = next_available_attempt_index(plugin, case)
        attempt_dir = plugin.attempt_dir_factory()(plugin.manifest, case, attempt_index)
        defaults.log(
            f"Starting {case_id}: attempt={attempt_index} root={attempt_dir}"
        )
        runner.run(
            case=case,
            target_run_index=1,
            attempt_index=attempt_index,
            attempt_dir=attempt_dir,
        )
        if index < len(cases):
            time.sleep(2.0)


def run_suite_from_args(args: argparse.Namespace) -> None:
    """Execute an airspeed suite through the framework SuiteRunner.

    The flag path above drives individual cases directly; this is the
    campaign path used by the interactive wizard. Both build their config
    from an argparse namespace so settings resolution stays in one module.
    """
    from ..core.scheduler import SequentialScheduler
    from ..core.suite_runner import SuiteRunner, SuiteRunSettings

    campaign_root = (
        defaults.default_campaign_root()
        if not str(args.campaign_root).strip()
        else args.campaign_root.resolve()
    )

    # Fixed cases keep FIXED_CASE_ORDER ordering; ratio-bias cases follow.
    selected_fixed = set(args.af_fixed_cases)
    ordered_fixed = [c for c in defaults.FIXED_CASE_ORDER if c in selected_fixed]
    bias_percents = tuple(args.af_bias_percents)

    config = AirspeedFailureConfig(
        ratio_bias_percents=bias_percents,
        runs_per_case=args.af_runs_per_case,
        campaign_root=campaign_root,
        mission_file=args.mission_file.resolve(),
        vehicle_arspd_ratio=args.af_vehicle_arspd_ratio,
        vehicle_arspd_ratio_verified=args.af_verified_vehicle_ratio,
        mavlink_addr=args.mavlink,
        launch_stack=False,
        mission_timeout_s=args.mission_timeout,
        ready_timeout_s=args.ready_timeout,
        upload_timeout_s=args.upload_timeout,
        arm_timeout_s=args.arm_timeout,
        mode_timeout_s=args.mode_timeout,
        wind_profile_id=args.af_wind_profile,
        continuous_speed_source=args.af_speed_source,
        mechanism_tier=args.af_mechanism_tier,
        expected_ahrs_wind_max=args.af_expected_ahrs_wind_max,
    )

    print()
    print("=" * 60)
    print("Airspeed Failure Behavior - suite")
    print(f"  Campaign root : {campaign_root}")
    print(f"  Mission       : {config.mission_file}")
    print(f"  Fixed cases   : {ordered_fixed}")
    print(f"  Ratio biases  : {bias_percents}")
    print(f"  Runs/case     : {config.runs_per_case}")
    print(f"  Max attempts  : {args.af_max_attempts_per_case}")
    print(f"  Wind profile  : {config.wind_profile_id}")
    print(f"  Speed source  : {config.continuous_speed_source}")
    print(f"  MAVLink       : {config.mavlink_addr}")
    print("=" * 60)
    print()

    plugin = build_plugin(config)

    class _FilteredGenerator(AirspeedFailureCaseGenerator):
        """Keep only wizard-selected fixed cases; all bias cases stay."""

        def iter_cases(self):
            for case in super().iter_cases():
                if (
                    case.case_id in defaults.FIXED_CASE_ORDER
                    and case.case_id not in selected_fixed
                ):
                    continue
                yield case

    SuiteRunner(
        case_generator=_FilteredGenerator(config),
        scheduler=SequentialScheduler(),
        attempt_runner=plugin.attempt_runner(),
        manifest=plugin.manifest,
        attempt_dir_factory=plugin.attempt_dir_factory(),
        settings=SuiteRunSettings(
            max_attempts_per_case=args.af_max_attempts_per_case,
            inter_attempt_delay_s=0.0,
        ),
    ).run()


def next_available_attempt_index(plugin, case) -> int:
    attempt_index = plugin.manifest.next_attempt_index(case)
    while plugin.attempt_dir_factory()(plugin.manifest, case, attempt_index).exists():
        attempt_index += 1
    return attempt_index


if __name__ == "__main__":
    main()
