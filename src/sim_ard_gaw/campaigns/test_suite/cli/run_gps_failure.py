"""No-SITL schema, dry-run, and case-list CLI for the gps_failure plugin.

Phase 1 never starts SITL or Gazebo. This entry point validates the case schema,
constructs the plugin, and prints the requested payload and parameter-stack
metadata.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Iterable

from ..core.models import AttemptRecord, AttemptStatus, VerdictClass
from ..plugins.gps_failure import build_plugin
from ..plugins.gps_failure import defaults, glitch
from ..plugins.gps_failure.case_generator import GpsFailureCaseGenerator
from ..plugins.gps_failure.config import GpsFailureConfig
from ..plugins.gps_failure.readiness import build_readiness_report
from ..plugins.gps_failure.stimulus import build_injection_artifact


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--list-cases", action="store_true")
    actions.add_argument("--dry-run", action="store_true")
    actions.add_argument("--probe-schema", action="store_true")
    actions.add_argument("--preflight", action="store_true")
    actions.add_argument("--phase2-smoke-plan", action="store_true")
    actions.add_argument("--live-phase2-smoke", action="store_true")
    actions.add_argument("--live-case", dest="live_case_id")
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--campaign-root", type=Path, default=None)
    parser.add_argument("--mavlink", default="udpin:0.0.0.0:14551")
    parser.add_argument(
        "--mission-timeout",
        type=float,
        default=defaults.PHASE2_MONITOR_TIMEOUT_S,
    )
    parser.add_argument("--confirm-live-phase2", action="store_true")
    parser.add_argument("--reference-latitude-deg", type=float, default=None)
    parser.add_argument("--preview-elapsed-s", type=float, default=None)
    args = parser.parse_args(argv)
    if args.dry_run and not args.case_id:
        parser.error("--dry-run requires --case")
    if args.case_id and not args.dry_run:
        parser.error("--case is only valid with --dry-run")
    if (args.live_phase2_smoke or args.live_case_id) and not args.confirm_live_phase2:
        parser.error("live Phase 2 GPS runs require --confirm-live-phase2")
    if args.live_case_id and args.live_case_id not in defaults.PHASE2_PROTECTED_CASE_IDS:
        parser.error(
            "--live-case is restricted to protected Phase 2 smoke cases: "
            + ", ".join(defaults.PHASE2_PROTECTED_CASE_IDS)
        )
    if args.reference_latitude_deg is not None and not args.dry_run:
        parser.error("--reference-latitude-deg is only valid with --dry-run")
    if args.preview_elapsed_s is not None and not args.dry_run:
        parser.error("--preview-elapsed-s is only valid with --dry-run")
    if args.reference_latitude_deg is not None and not math.isfinite(
        args.reference_latitude_deg
    ):
        parser.error("--reference-latitude-deg must be finite")
    if args.preview_elapsed_s is None:
        args.preview_elapsed_s = defaults.MIN_POST_INJECTION_S
    if not math.isfinite(args.preview_elapsed_s):
        parser.error("--preview-elapsed-s must be finite")
    if args.preview_elapsed_s < 0:
        parser.error("--preview-elapsed-s must be >= 0")
    if not math.isfinite(args.mission_timeout):
        parser.error("--mission-timeout must be finite")
    if args.mission_timeout <= 0:
        parser.error("--mission-timeout must be > 0")
    return args


def _config_from_args(args: argparse.Namespace) -> GpsFailureConfig:
    return GpsFailureConfig(
        campaign_root=(
            args.campaign_root.resolve()
            if args.campaign_root
            else defaults.default_campaign_root()
        ),
        mavlink_addr=args.mavlink,
        launch_stack=bool(args.live_phase2_smoke or args.live_case_id),
        mission_timeout_s=args.mission_timeout,
    )


def main(argv: Iterable[str] | None = None) -> None:
    args = _parse_args(argv)
    config = _config_from_args(args)
    plugin = build_plugin(config)
    generator = GpsFailureCaseGenerator(config)

    if args.probe_schema:
        print(json.dumps(defaults.parameter_schema(), indent=2, sort_keys=True))
        return

    if args.preflight:
        report = build_readiness_report(plugin)
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return

    if args.list_cases:
        for case in plugin.case_generator.iter_cases():
            print(case.case_id)
        return

    if args.phase2_smoke_plan:
        cases = {
            case.case_id: case
            for case in plugin.case_generator.iter_cases()
            if case.case_id in defaults.PHASE2_PROTECTED_CASE_IDS
        }
        print(
            json.dumps(
                {
                    "phase": "phase2_implementation_no_live_run",
                    "launch_performed": False,
                    "live_readback_performed": False,
                    "live_cli_enabled": True,
                    "live_cli_guard": "--confirm-live-phase2 required",
                    "strict_review_accepted_for_nominal_live_smoke": True,
                    "terminal_success_requires_cleanup": True,
                    "stop_on_first_non_accepted_record": True,
                    "protected_case_ids": list(defaults.PHASE2_PROTECTED_CASE_IDS),
                    "cases": {
                        case_id: {
                            "case_id": case.case_id,
                            "fault_type": case.parameters.get("fault_type"),
                            "mission_file": str(case.mission_file),
                            "injection_schedule": case.parameters.get(
                                "injection_schedule", []
                            ),
                            "fault_recipe": case.parameters.get("fault_recipe"),
                        }
                        for case_id, case in sorted(cases.items())
                    },
                    "required_live_readbacks": list(defaults.LIVE_READBACK_PARAMS),
                    "telemetry_message_types": list(defaults.TELEMETRY_MESSAGE_TYPES),
                    "ready_for_live_run": False,
                    "note": (
                        "Plan-only output for later authorized live smoke; this CLI "
                        "action does not start SITL/Gazebo or open MAVLink."
                    ),
                },
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return

    if args.live_phase2_smoke:
        run_live_cases(
            config,
            list(defaults.PHASE2_PROTECTED_CASE_IDS),
            title="GPS Failure Behavior - Phase 2 protected live smoke",
        )
        return

    if args.live_case_id:
        run_live_cases(
            config,
            [args.live_case_id],
            title="GPS Failure Behavior - Phase 2 single protected live case",
        )
        return

    if args.dry_run:
        try:
            case = generator.get_case(args.case_id)
        except ValueError as exc:
            sys.exit(f"ERROR: {exc}")
        dry_run = {
            "phase": "phase1_no_sitl",
            "plugin_constructed": True,
            "effective_param_stack": [
                str(path) for path in config.effective_param_stack
            ],
            "case": {
                "case_id": case.case_id,
                "suite_name": case.suite_name,
                "mission_file": str(case.mission_file),
                "parameters": case.parameters,
            },
            "injection_artifact": build_injection_artifact(case),
            "parameter_schema": defaults.parameter_schema(),
            "launch_performed": False,
            "live_readback_performed": False,
        }
        if args.reference_latitude_deg is not None:
            try:
                preview = glitch.preview_payload_from_recipe(
                    case.parameters.get("fault_recipe"),
                    latitude_deg=args.reference_latitude_deg,
                    elapsed_s=args.preview_elapsed_s,
                )
            except ValueError as exc:
                sys.exit(f"ERROR: {exc}")
            if preview is not None:
                dry_run["resolved_payload_preview"] = preview
        print(json.dumps(dry_run, indent=2, sort_keys=True, allow_nan=False))
        return


def run_live_cases(
    config: GpsFailureConfig,
    cases: list[str],
    *,
    title: str,
) -> None:
    unsupported = [
        case_id
        for case_id in cases
        if case_id not in defaults.PHASE2_PROTECTED_CASE_IDS
    ]
    if unsupported:
        raise SystemExit(
            "ERROR: live GPS Phase 2 cases are restricted to protected smoke cases: "
            + ", ".join(unsupported)
        )
    plugin = build_plugin(config)
    generator = GpsFailureCaseGenerator(config)
    runner = plugin.attempt_runner()
    defaults.log("=" * 60)
    defaults.log(title)
    defaults.log(f"  Campaign root: {config.campaign_root}")
    defaults.log(f"  MAVLink      : {config.mavlink_addr}")
    defaults.log(f"  Cases        : {', '.join(cases)}")
    defaults.log("  Raw output only; no curated evidence promotion")
    defaults.log("=" * 60)
    config.campaign_root.mkdir(parents=True, exist_ok=True)
    for index, case_id in enumerate(cases, start=1):
        case = generator.get_case(case_id)
        attempt_index = next_available_attempt_index(plugin, case)
        attempt_dir = plugin.attempt_dir_factory()(plugin.manifest, case, attempt_index)
        defaults.log(
            f"Starting {case_id}: attempt={attempt_index} root={attempt_dir}"
        )
        record = runner.run(
            case=case,
            target_run_index=1,
            attempt_index=attempt_index,
            attempt_dir=attempt_dir,
        )
        if not _accepted_live_record(record):
            raise SystemExit(
                "ERROR: GPS live case stopped after non-accepted terminal record: "
                f"case={case_id} status={record.status.value} "
                f"verdict={record.verdict.reason if record.verdict else 'missing'}"
            )
        if index < len(cases):
            time.sleep(2.0)


def _accepted_live_record(record: AttemptRecord) -> bool:
    verdict = record.verdict
    return bool(
        record.status is AttemptStatus.SUCCESS
        and verdict is not None
        and verdict.klass is VerdictClass.SUCCESS
        and verdict.metadata.get("accepted_observation") is True
    )


def next_available_attempt_index(plugin, case) -> int:
    attempt_index = plugin.manifest.next_attempt_index(case)
    while plugin.attempt_dir_factory()(plugin.manifest, case, attempt_index).exists():
        attempt_index += 1
    return attempt_index


if __name__ == "__main__":
    main()
