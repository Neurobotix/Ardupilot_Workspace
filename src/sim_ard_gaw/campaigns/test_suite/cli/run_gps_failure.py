"""CLI for the gps_failure plugin.

The default actions (`--list-cases`, `--dry-run`, `--probe-schema`,
`--preflight`, `--phase2-validation-rerun-plan`) are no-SITL: they validate the
case schema, construct the plugin, and print plan/readiness JSON without
starting SITL/Gazebo or opening MAVLink. Live actions are explicit and
confirmation-guarded (`--live-case`, `--live-phase2-validation-rerun`,
`--live-phase2-round-robin-campaign`).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, cast

from ...provenance import file_provenance, parameter_file_provenance, source_tree_snapshot
from ..core.manifest import attempt_record_to_generic_fields
from ..core.models import AttemptRecord
from ..plugins.gps_failure import build_plugin
from ..plugins.gps_failure import defaults, glitch
from ..plugins.gps_failure.case_generator import GpsFailureCaseGenerator
from ..plugins.gps_failure.config import GpsFailureConfig
from ..plugins.gps_failure.manifest import (
    accepted_observation_from_attempt,
    accepted_repetition_from_attempt,
    workflow_complete_from_attempt,
)
from ..plugins.gps_failure.readiness import build_readiness_report
from ..plugins.gps_failure.readiness import build_phase_h_gate_report
from ..plugins.gps_failure.readiness import build_phase_h_validation_plan
from ..plugins.gps_failure.stimulus import build_injection_artifact


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--list-cases", action="store_true")
    actions.add_argument("--dry-run", action="store_true")
    actions.add_argument("--probe-schema", action="store_true")
    actions.add_argument("--preflight", action="store_true")
    actions.add_argument("--phase2-validation-rerun-plan", action="store_true")
    actions.add_argument("--live-phase2-validation-rerun", action="store_true")
    actions.add_argument("--live-phase2-round-robin-campaign", action="store_true")
    actions.add_argument("--live-case", dest="live_case_id")
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--campaign-root", type=Path, default=None)
    parser.add_argument(
        "--envelope",
        choices=defaults.ENVELOPE_NAMES,
        default=defaults.BASELINE_ENVELOPE_NAME,
        help="Named GPS envelope variant for mission, param stack, and source-contract expectations.",
    )
    parser.add_argument(
        "--mission-file",
        type=Path,
        default=None,
        help="Explicit mission override. Defaults to the selected envelope mission.",
    )
    parser.add_argument(
        "--extra-param-file",
        type=Path,
        action="append",
        default=[],
        help="Extra parameter file appended after the selected envelope stack.",
    )
    parser.add_argument("--mavlink", default="udpin:0.0.0.0:14551")
    parser.add_argument(
        "--mission-timeout",
        type=float,
        default=defaults.PHASE2_MONITOR_TIMEOUT_S,
    )
    parser.add_argument("--confirm-live-phase2", action="store_true")
    parser.add_argument("--confirm-validation-rerun", action="store_true")
    parser.add_argument("--confirm-live-campaign", action="store_true")
    parser.add_argument(
        "--campaign-cases",
        default=",".join(defaults.PHASE2_PROTECTED_CASE_IDS),
        help=(
            "Comma-separated non-jamming GPS case IDs for the live round-robin "
            "campaign. Defaults to the protected Phase-2 qualification set."
        ),
    )
    parser.add_argument("--runs-per-case", type=int, default=1)
    parser.add_argument("--inter-attempt-delay", type=float, default=2.0)
    parser.add_argument(
        "--no-force-arm",
        action="store_true",
        help="Run live GPS readiness and arming without MAV_CMD force-arm semantics.",
    )
    parser.add_argument("--reference-latitude-deg", type=float, default=None)
    parser.add_argument("--preview-elapsed-s", type=float, default=None)
    args = parser.parse_args(argv)
    if args.dry_run and not args.case_id:
        parser.error("--dry-run requires --case")
    if args.case_id and not args.dry_run:
        parser.error("--case is only valid with --dry-run")
    live_requested = (
        args.live_phase2_validation_rerun
        or args.live_phase2_round_robin_campaign
        or args.live_case_id
    )
    if live_requested and not args.confirm_live_phase2:
        parser.error("live Phase 2 GPS runs require --confirm-live-phase2")
    if args.live_phase2_validation_rerun and not args.confirm_validation_rerun:
        parser.error(
            "Phase H validation rerun requires --confirm-validation-rerun in "
            "addition to --confirm-live-phase2"
        )
    if args.live_phase2_round_robin_campaign and not args.confirm_live_campaign:
        parser.error(
            "live GPS campaigns require --confirm-live-campaign in addition to "
            "--confirm-live-phase2"
        )
    if args.live_case_id and args.live_case_id not in defaults.PHASE2_PROTECTED_CASE_IDS:
        parser.error(
            "--live-case is restricted to the protected Phase 2 case set: "
            + ", ".join(defaults.PHASE2_PROTECTED_CASE_IDS)
        )
    args.campaign_cases = _parse_campaign_cases(parser, args.campaign_cases)
    if not args.live_phase2_round_robin_campaign:
        if args.runs_per_case != 1:
            parser.error("--runs-per-case is only valid with --live-phase2-round-robin-campaign")
        if args.inter_attempt_delay != 2.0:
            parser.error(
                "--inter-attempt-delay is only valid with "
                "--live-phase2-round-robin-campaign"
            )
    if args.runs_per_case < 1:
        parser.error("--runs-per-case must be >= 1")
    if not math.isfinite(args.inter_attempt_delay) or args.inter_attempt_delay < 0:
        parser.error("--inter-attempt-delay must be finite and >= 0")
    unsupported_campaign_cases = [
        case_id
        for case_id in args.campaign_cases
        if case_id not in defaults.PHASE2_NON_JAMMING_CAMPAIGN_CASE_IDS
    ]
    if unsupported_campaign_cases:
        parser.error(
            "--campaign-cases is restricted to non-jamming GPS campaign cases: "
            + ", ".join(unsupported_campaign_cases)
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


def _parse_campaign_cases(
    parser: argparse.ArgumentParser,
    raw: str,
) -> list[str]:
    cases = [item.strip() for item in raw.split(",") if item.strip()]
    if not cases:
        parser.error("--campaign-cases must include at least one case")
    seen: set[str] = set()
    duplicates: list[str] = []
    for case_id in cases:
        if case_id in seen:
            duplicates.append(case_id)
        seen.add(case_id)
    if duplicates:
        parser.error("--campaign-cases contains duplicates: " + ", ".join(duplicates))
    return cases


def _config_from_args(args: argparse.Namespace) -> GpsFailureConfig:
    return GpsFailureConfig(
        campaign_root=(
            args.campaign_root.resolve()
            if args.campaign_root
            else defaults.default_campaign_root()
        ),
        envelope_name=args.envelope,
        mission_file=(
            args.mission_file.resolve()
            if args.mission_file
            else defaults.mission_file_for_envelope(args.envelope)
        ),
        extra_param_files=tuple(path.resolve() for path in args.extra_param_file),
        mavlink_addr=args.mavlink,
        launch_stack=bool(
            args.live_phase2_validation_rerun
            or args.live_phase2_round_robin_campaign
            or args.live_case_id
        ),
        mission_timeout_s=args.mission_timeout,
        force_arm=not args.no_force_arm,
        runs_per_case=args.runs_per_case,
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

    if args.phase2_validation_rerun_plan:
        print(
            json.dumps(
                build_phase_h_validation_plan(),
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return

    if args.live_phase2_validation_rerun:
        gates = build_phase_h_gate_report()
        if not gates["all_gates_satisfied"]:
            raise SystemExit(
                "ERROR: Phase H validation rerun blocked by missing no-live gates: "
                + ", ".join(gates["missing_gate_ids"])
            )
        run_live_round_robin_campaign(
            config,
            list(defaults.PHASE2_PROTECTED_CASE_IDS),
            runs_per_case=1,
            inter_attempt_delay_s=args.inter_attempt_delay,
            title="GPS Failure Behavior - Phase H protected validation rerun",
            campaign_mode="phase_h_validation_rerun",
        )
        return

    if args.live_phase2_round_robin_campaign:
        run_live_round_robin_campaign(
            config,
            args.campaign_cases,
            runs_per_case=args.runs_per_case,
            inter_attempt_delay_s=args.inter_attempt_delay,
            title="GPS Failure Behavior - Phase 2 protected round-robin campaign",
            campaign_mode="round_robin",
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
            "phase": "no_sitl_dry_run",
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
            "ERROR: live GPS Phase 2 cases are restricted to the protected case set: "
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
                "ERROR: GPS live case stopped after non-accepted repetition: "
                f"case={case_id} status={record.status.value} "
                f"verdict={record.verdict.reason if record.verdict else 'missing'}"
            )
        if index < len(cases):
            time.sleep(2.0)


def _accepted_live_record(record: AttemptRecord) -> bool:
    return accepted_repetition_from_attempt(_record_manifest_fields(record))


def run_live_round_robin_campaign(
    config: GpsFailureConfig,
    case_ids: list[str],
    *,
    runs_per_case: int,
    inter_attempt_delay_s: float,
    title: str,
    campaign_mode: str = "round_robin",
) -> None:
    unsupported = [
        case_id
        for case_id in case_ids
        if case_id not in defaults.PHASE2_NON_JAMMING_CAMPAIGN_CASE_IDS
    ]
    if unsupported:
        raise SystemExit(
            "ERROR: live GPS campaigns are restricted to non-jamming GPS campaign cases: "
            + ", ".join(unsupported)
        )
    plugin = build_plugin(config)
    generator = GpsFailureCaseGenerator(config)
    cases = [generator.get_case(case_id) for case_id in case_ids]
    runner = plugin.attempt_runner()

    defaults.log("=" * 60)
    defaults.log(title)
    defaults.log(f"  Campaign root     : {config.campaign_root}")
    defaults.log(f"  MAVLink           : {config.mavlink_addr}")
    defaults.log(f"  Cases             : {', '.join(case_ids)}")
    defaults.log(f"  Workflow runs/case: {runs_per_case}")
    defaults.log("  Ordering          : true round robin")
    defaults.log("  Retry policy      : zero automatic retries")
    defaults.log(
        "  Stop rule         : stop on workflow/stimulus/lifecycle/raw-log/cleanup failure"
    )
    defaults.log("  Raw output only; no curated evidence promotion")
    defaults.log("=" * 60)

    config.campaign_root.mkdir(parents=True, exist_ok=True)
    _write_campaign_contract(
        config=config,
        case_ids=case_ids,
        runs_per_case=runs_per_case,
        inter_attempt_delay_s=inter_attempt_delay_s,
        campaign_mode=campaign_mode,
    )

    round_index = 0
    while True:
        active = [
            case
            for case in cases
            if _workflow_complete_count(plugin, case) < runs_per_case
        ]
        if not active:
            defaults.log("[gps_campaign] done: all workflow-complete targets met")
            return
        round_index += 1
        defaults.log(f"[gps_campaign] round {round_index} active={len(active)}")
        for case in active:
            target_run_index = _workflow_complete_count(plugin, case) + 1
            attempt_index = next_available_attempt_index(plugin, case)
            attempt_dir = plugin.attempt_dir_factory()(
                plugin.manifest,
                case,
                attempt_index,
            )
            defaults.log(
                f"[gps_campaign] {case.case_id}: workflow_run={target_run_index} "
                f"attempt={attempt_index} root={attempt_dir}"
            )
            record = runner.run(
                case=case,
                target_run_index=target_run_index,
                attempt_index=attempt_index,
                attempt_dir=attempt_dir,
                attempt_metadata={
                    "campaign_mode": campaign_mode,
                    "campaign_round_index": round_index,
                    "workflow_target_runs": runs_per_case,
                },
            )
            if not _workflow_complete_live_record(record):
                raise SystemExit(
                    "ERROR: GPS round-robin campaign stopped after workflow "
                    "failure: "
                    f"case={case.case_id} status={record.status.value} "
                    f"workflow_status="
                    f"{record.plugin_manifest_fields.get('workflow_status')}"
                )
            if not _accepted_live_record(record):
                defaults.log(
                    "[gps_campaign] accepted repetition not recorded; workflow "
                    "run is preserved and campaign continues: "
                    f"case={case.case_id} verdict="
                    f"{record.verdict.reason if record.verdict else 'missing'} "
                    f"accepted_observation="
                    f"{accepted_observation_from_attempt(_record_manifest_fields(record))} "
                    f"stimulus_fidelity_status="
                    f"{record.plugin_manifest_fields.get('stimulus_fidelity_status')}"
                )
            if inter_attempt_delay_s > 0:
                time.sleep(inter_attempt_delay_s)


def _workflow_complete_live_record(record: AttemptRecord) -> bool:
    return workflow_complete_from_attempt(_record_manifest_fields(record))


def _record_manifest_fields(record: AttemptRecord) -> dict[str, Any]:
    fields = attempt_record_to_generic_fields(record)
    fields.update(record.plugin_manifest_fields)
    fields.setdefault("case_id", record.case_id)
    fields.setdefault("status", record.status.value)
    fields.setdefault("artifacts", dict(record.artifacts))
    return fields


def _workflow_complete_count(plugin: Any, case: Any) -> int:
    counter = getattr(plugin.manifest, "workflow_complete_count", None)
    if callable(counter):
        typed_counter = cast(Callable[[Any], int], counter)
        return int(typed_counter(case))
    return 0


def _write_campaign_contract(
    *,
    config: GpsFailureConfig,
    case_ids: list[str],
    runs_per_case: int,
    inter_attempt_delay_s: float,
    campaign_mode: str = "round_robin",
) -> None:
    contract_path = config.campaign_root / "campaign_contract.json"
    payload = _campaign_contract_payload(
        config=config,
        case_ids=case_ids,
        runs_per_case=runs_per_case,
        inter_attempt_delay_s=inter_attempt_delay_s,
        campaign_mode=campaign_mode,
    )
    if contract_path.exists():
        existing = defaults.read_json(contract_path)
        comparable = dict(payload)
        if isinstance(existing, dict):
            comparable["created_at_utc"] = existing.get("created_at_utc")
        if existing != comparable:
            raise SystemExit(
                "ERROR: campaign contract drift for existing campaign root: "
                f"{contract_path}"
            )
        return
    defaults.write_json(contract_path, payload)


def _campaign_contract_payload(
    *,
    config: GpsFailureConfig,
    case_ids: list[str],
    runs_per_case: int,
    inter_attempt_delay_s: float,
    campaign_mode: str = "round_robin",
) -> dict[str, Any]:
    plugin_file = defaults.WORKSPACE_GAZEBO_PLUGIN_FILE
    return {
        "schema_version": "gps_failure.live_campaign_contract.v1",
        "created_at_utc": defaults.utc_now(),
        "campaign_root": str(config.campaign_root),
        "suite_name": defaults.SUITE_NAME,
        "campaign_mode": campaign_mode,
        "envelope": config.envelope_metadata,
        "case_ids": list(case_ids),
        "runs_per_case": runs_per_case,
        "phase_h_validation_rerun": campaign_mode == "phase_h_validation_rerun",
        "inter_attempt_delay_s": inter_attempt_delay_s,
        "retry_policy": {
            "automatic_retries": 0,
            "failed_attempts_preserved": True,
            "operator_must_request_retry_after_failure": True,
        },
        "counting_rule": (
            "protected campaign scheduler counts workflow-complete physical "
            "attempts; accepted_observation records behavior usefulness, and "
            "accepted_repetition records workflow + stimulus fidelity + "
            "behavior acceptance for the requested recipe"
        ),
        "stop_rules": [
            "workflow failure",
            "stimulus fidelity failure",
            "lifecycle-window failure",
            "readiness/source/mission/trigger/injection failure",
            "restore/readback failure",
            "dirty cleanup or surviving simulator process",
            "missing or ambiguous attempt-local raw BIN",
            "campaign contract drift",
            "operator interrupt",
        ],
        "launch_targets": {
            "sitl": defaults.SITL_TARGET,
            "gazebo": defaults.GAZEBO_TARGET,
        },
        "inputs": {
            "mission": file_provenance(config.mission_file),
            "world": file_provenance(defaults.GAZEBO_WORLD_FILE),
            "param_stack": parameter_file_provenance(config.effective_param_stack),
            "workspace_gazebo_plugin": (
                file_provenance(plugin_file) if plugin_file.is_file() else None
            ),
        },
        "source_tree": source_tree_snapshot(defaults.WORKSPACE_ROOT),
    }


def next_available_attempt_index(plugin, case) -> int:
    attempt_index = plugin.manifest.next_attempt_index(case)
    while plugin.attempt_dir_factory()(plugin.manifest, case, attempt_index).exists():
        attempt_index += 1
    return attempt_index


if __name__ == "__main__":
    main()
