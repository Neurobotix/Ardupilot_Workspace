"""Dry-run and case-list CLI for the airspeed_failure plugin.

Phase 1 never starts SITL or Gazebo. This entry point validates the case schema,
constructs the plugin, and prints the requested payload metadata.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable

from ..plugins.airspeed_failure import build_plugin
from ..plugins.airspeed_failure.case_generator import AirspeedFailureCaseGenerator
from ..plugins.airspeed_failure.config import AirspeedFailureConfig
from ..plugins.airspeed_failure import defaults
from ..plugins.airspeed_failure.environment import build_reference_wind_artifact
from ..plugins.airspeed_failure.stimulus import build_injection_artifact


def _parse_biases(text: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in text.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("expected at least one bias percent")
    return values


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--full-ratio-sweep", action="store_true")
    parser.add_argument("--bias-percent", type=_parse_biases, default=None)
    parser.add_argument("--vehicle-arspd-ratio", type=float, default=defaults.DEFAULT_VEHICLE_ARSPD_RATIO)
    parser.add_argument("--verified-vehicle-ratio", action="store_true")
    parser.add_argument("--probe-schema", action="store_true")
    args = parser.parse_args(argv)
    if not args.list_cases and not args.dry_run and not args.probe_schema:
        parser.error("choose --list-cases, --dry-run, or --probe-schema")
    if args.dry_run and not args.case_id:
        parser.error("--dry-run requires --case")
    return args


def _config_from_args(args: argparse.Namespace) -> AirspeedFailureConfig:
    if args.bias_percent is not None:
        biases = args.bias_percent
    elif args.full_ratio_sweep:
        biases = defaults.FULL_RATIO_BIAS_PERCENTS
    else:
        biases = defaults.V1_RATIO_BIAS_PERCENTS
    return AirspeedFailureConfig(
        ratio_bias_percents=tuple(biases),
        vehicle_arspd_ratio=args.vehicle_arspd_ratio,
        vehicle_arspd_ratio_verified=args.verified_vehicle_ratio,
        launch_stack=False,
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
            "reference_wind_artifact": build_reference_wind_artifact(verified=False),
            "parameter_schema": defaults.parameter_schema(),
            "launch_performed": False,
        }
        print(json.dumps(dry_run, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
