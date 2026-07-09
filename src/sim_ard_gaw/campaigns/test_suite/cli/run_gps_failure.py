"""Dry-run and case-list CLI for the gps_failure plugin.

Phase 1 Chunk 1 never starts SITL or Gazebo. This entry point validates the case
schema, constructs the plugin, and prints the requested payload metadata.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from ..plugins.gps_failure import build_plugin
from ..plugins.gps_failure import defaults, glitch
from ..plugins.gps_failure.case_generator import GpsFailureCaseGenerator
from ..plugins.gps_failure.config import GpsFailureConfig
from ..plugins.gps_failure.stimulus import build_injection_artifact


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--probe-schema", action="store_true")
    parser.add_argument("--campaign-root", type=Path, default=None)
    parser.add_argument("--reference-latitude-deg", type=float, default=None)
    parser.add_argument("--preview-elapsed-s", type=float, default=defaults.MIN_POST_INJECTION_S)
    args = parser.parse_args(argv)
    if not args.list_cases and not args.dry_run and not args.probe_schema:
        parser.error("choose --list-cases, --dry-run, or --probe-schema")
    if args.dry_run and not args.case_id:
        parser.error("--dry-run requires --case")
    if args.reference_latitude_deg is not None and not args.dry_run:
        parser.error("--reference-latitude-deg is only valid with --dry-run")
    if args.preview_elapsed_s < 0:
        parser.error("--preview-elapsed-s must be >= 0")
    return args


def _config_from_args(args: argparse.Namespace) -> GpsFailureConfig:
    return GpsFailureConfig(
        campaign_root=(
            args.campaign_root.resolve()
            if args.campaign_root
            else defaults.default_campaign_root()
        ),
        launch_stack=False,
    )


def main(argv: Iterable[str] | None = None) -> None:
    args = _parse_args(argv)
    config = _config_from_args(args)
    plugin = build_plugin(config)
    generator = GpsFailureCaseGenerator(config)

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
            "parameter_schema": defaults.parameter_schema(),
            "launch_performed": False,
        }
        if args.reference_latitude_deg is not None:
            preview = glitch.preview_payload_from_recipe(
                case.parameters.get("fault_recipe"),
                latitude_deg=args.reference_latitude_deg,
                elapsed_s=args.preview_elapsed_s,
            )
            if preview is not None:
                dry_run["resolved_payload_preview"] = preview
        print(json.dumps(dry_run, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
