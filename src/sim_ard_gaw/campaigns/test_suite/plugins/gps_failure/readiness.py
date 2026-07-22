"""No-live integration-readiness report for the gps_failure lane.

The report is deterministic and no-live: it shows what a suite run would
schedule, the manifest/artifact contract, the effective parameter stack, and
the Phase A-G no-live gates that guard the next protected live action.

Nothing here opens a MAVLink connection, starts a stack, or reads a BIN log.
"""
from __future__ import annotations

from typing import Any

from ...core.models import TestCase
from . import analyzers, defaults
from .config import GpsFailureConfig
from .plugin import GpsFailurePlugin, build_plugin


PHASE_H_GATE_ORDER = (
    "vehicle_time_scheduling",
    "bin_stimulus_fidelity",
    "three_verdict_manifest",
    "lifecycle_window_artifact",
    "hard_denial_transient_visibility",
    "source_proof_label",
    "altitude_attitude_authority",
)

PHASE_H_GATE_PROOFS: dict[str, dict[str, Any]] = {
    "vehicle_time_scheduling": {
        "status": "satisfied",
        "label": "vehicle-time scheduling gate",
        "proof_refs": [
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/monitor.py",
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/stimulus.py",
            "tests/unit/test_gps_failure_phase2_path.py",
            "docs/operations/gps_failure_runbook.md",
        ],
        "proof_summary": (
            "Physical slow-drift scheduling uses MAVLink vehicle time_boot_ms "
            "elapsed from the seq-4 trigger and fails closed when vehicle time "
            "is missing or stale."
        ),
    },
    "bin_stimulus_fidelity": {
        "status": "satisfied",
        "label": "BIN stimulus fidelity gate",
        "proof_refs": [
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/bin_analysis.py",
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/analyzers.py",
            "tests/unit/test_gps_failure_phase2_path.py",
        ],
        "proof_summary": (
            "Post-cleanup BIN analysis writes stimulus_fidelity.json and "
            "fails missing, malformed, unanchored, or physically wrong dose "
            "evidence closed."
        ),
    },
    "three_verdict_manifest": {
        "status": "satisfied",
        "label": "three-verdict manifest gate",
        "proof_refs": [
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/manifest.py",
            "src/sim_ard_gaw/campaigns/test_suite/core/manifest.py",
            "tests/unit/test_gps_failure_phase1.py",
            "tests/unit/test_gps_failure_phase2_path.py",
        ],
        "proof_summary": (
            "Terminal rows keep workflow_status, stimulus_fidelity_status, "
            "behavior_status, accepted_observation, and accepted_repetition "
            "separate."
        ),
    },
    "lifecycle_window_artifact": {
        "status": "satisfied",
        "label": "lifecycle-window artifact gate",
        "proof_refs": [
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/bin_analysis.py",
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/analyzers.py",
            "tests/unit/test_gps_failure_phase2_path.py",
        ],
        "proof_summary": (
            "gps_lifecycle_windows.json is required and is the ordered evidence "
            "authority for baseline, trigger, injection, fault-active, EKF "
            "response, recovery/continuation, and terminal windows."
        ),
    },
    "hard_denial_transient_visibility": {
        "status": "satisfied",
        "label": "hard-denial transient visibility gate",
        "proof_refs": [
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/bin_analysis.py",
            "tests/unit/test_gps_failure_phase2_path.py",
            "docs/architecture/gps_failure_lane.md",
        ],
        "proof_summary": (
            "Hard-denial artifacts expose denial/restore timing, GPS quality, "
            "reset offsets, full-window gap, and active post-reset gap summary."
        ),
    },
    "source_proof_label": {
        "status": "satisfied",
        "label": "source-proof label gate",
        "proof_refs": [
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/source_contract.py",
            "tests/unit/test_gps_failure_phase2_path.py",
            "docs/architecture/gps_failure_lane.md",
        ],
        "proof_summary": (
            "source_contract.json labels exact_internal_proof, "
            "bin_observable_proof, and validated_proxy_proof without claiming "
            "direct PV_AidingMode evidence."
        ),
    },
    "altitude_attitude_authority": {
        "status": "satisfied",
        "label": "altitude/attitude authority gate",
        "proof_refs": [
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/bin_analysis.py",
            "src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/monitor.py",
            "tests/unit/test_gps_failure_phase2_path.py",
        ],
        "proof_summary": (
            "attitude_altitude_envelope.json declares live telemetry as runtime "
            "guard and BIN/hybrid source authority after cleanup, failing "
            "closed on missing sources or disagreement."
        ),
    },
}

PHASE_H_STOP_RULES: tuple[dict[str, str], ...] = (
    {
        "id": "workflow_failure",
        "stop_on": "workflow failure",
        "action": "stop the validation rerun immediately; preserve the terminal row",
    },
    {
        "id": "stimulus_fidelity_failure",
        "stop_on": "stimulus fidelity failure",
        "action": "stop the validation rerun immediately; do not consume a repetition",
    },
    {
        "id": "lifecycle_window_failure",
        "stop_on": "lifecycle-window failure",
        "action": "stop the validation rerun immediately; mark reviewability blocked",
    },
    {
        "id": "raw_log_archival_failure",
        "stop_on": "raw-log archival failure",
        "action": "stop the validation rerun immediately; raw BIN proof is mandatory",
    },
    {
        "id": "cleanup_failure",
        "stop_on": "cleanup failure",
        "action": "stop the validation rerun immediately; no later case may start",
    },
)


def build_readiness_report(
    plugin: GpsFailurePlugin | None = None,
    config: GpsFailureConfig | None = None,
) -> dict[str, Any]:
    """Assemble the full no-SITL integration-readiness report.

    Passing ``plugin`` reuses an already-built plugin (so the report reflects
    exactly what a caller wired up); otherwise a default plugin is built from
    ``config`` (or plugin defaults).
    """
    if plugin is None:
        plugin = build_plugin(config)
    config = plugin.config

    cases = list(plugin.case_generator.iter_cases())
    phase_h_gates = build_phase_h_gate_report()
    validation_plan = build_phase_h_validation_plan(phase_h_gates=phase_h_gates)
    protected_live_ready = bool(validation_plan.get("live_command_available"))
    return {
        "phase": "no_live_preflight",
        "lane": defaults.LANE_NAME,
        "suite_name": defaults.SUITE_NAME,
        "plugin_constructed": True,
        "launch_stack": bool(config.launch_stack),
        "launch_performed": False,
        "live_readback_performed": False,
        "suite_path": _suite_path_readiness(plugin, cases),
        "case_catalog": _case_catalog(cases),
        "manifest_contract": _manifest_contract(plugin),
        "artifact_contract": _artifact_contract(),
        "parameter_stack": _parameter_stack(config),
        "trigger": dict(defaults.INJECTION_TRIGGER),
        "phase2_protected_smoke": {
            "case_ids": list(defaults.PHASE2_PROTECTED_CASE_IDS),
            "full_phase3_matrix_enabled": False,
            "telemetry_message_types": list(defaults.TELEMETRY_MESSAGE_TYPES),
            "required_live_readbacks": list(defaults.LIVE_READBACK_PARAMS),
            "trigger_heartbeat_max_age_s": defaults.TRIGGER_HEARTBEAT_MAX_AGE_S,
            "trigger_simstate_max_age_s": defaults.TRIGGER_SIMSTATE_MAX_AGE_S,
            "terminal_success_requires_cleanup": True,
            "stop_on_first_non_accepted_repetition": True,
        },
        "phase_h_no_live_gates": phase_h_gates,
        "phase_h_validation_rerun": validation_plan,
        "ready_for_live_run": protected_live_ready,
    }


def build_phase_h_gate_report(
    proofs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Report the Phase H no-live gates and fail closed on missing proof."""
    proof_map = proofs if proofs is not None else PHASE_H_GATE_PROOFS
    gates: list[dict[str, Any]] = []
    for gate_id in PHASE_H_GATE_ORDER:
        proof = proof_map.get(gate_id)
        if not isinstance(proof, dict):
            gates.append(
                {
                    "id": gate_id,
                    "label": gate_id.replace("_", " "),
                    "status": "missing",
                    "satisfied": False,
                    "reason": "no explicit proof entry",
                    "proof_refs": [],
                }
            )
            continue
        proof_refs = proof.get("proof_refs")
        status = proof.get("status")
        satisfied = (
            status == "satisfied"
            and isinstance(proof_refs, list)
            and bool(proof_refs)
            and all(isinstance(item, str) and item for item in proof_refs)
        )
        gates.append(
            {
                "id": gate_id,
                "label": str(proof.get("label") or gate_id.replace("_", " ")),
                "status": status if isinstance(status, str) else "malformed",
                "satisfied": satisfied,
                "reason": (
                    "explicit no-live proof present"
                    if satisfied
                    else "explicit satisfied proof_refs are required"
                ),
                "proof_summary": proof.get("proof_summary"),
                "proof_refs": list(proof_refs) if isinstance(proof_refs, list) else [],
            }
        )
    missing_gate_ids = [gate["id"] for gate in gates if not gate["satisfied"]]
    return {
        "schema_version": "gps_failure.phase_h_no_live_gates.v1",
        "all_gates_satisfied": not missing_gate_ids,
        "status": "satisfied" if not missing_gate_ids else "blocked",
        "missing_gate_ids": missing_gate_ids,
        "gates": gates,
    }


def build_phase_h_validation_plan(
    *,
    phase_h_gates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gates = phase_h_gates if phase_h_gates is not None else build_phase_h_gate_report()
    no_live_gates_satisfied = bool(gates.get("all_gates_satisfied"))
    command = (
        "PYTHONPATH=src ./env/bin/python3 -m "
        "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure "
        "--live-phase2-validation-rerun --confirm-live-phase2 "
        "--confirm-validation-rerun --mission-timeout 1800 "
        '--campaign-root "$(pwd)/var/runs/'
        'gps_failure_behavior_v6_single_run_validation_$(date -u +%Y%m%dT%H%M%SZ)"'
    )
    return {
        "schema_version": "gps_failure.phase_h_validation_rerun_plan.v1",
        "purpose": "validate the v6 shorter final-science mission workflow on the protected case set before the multi-run science campaign",
        "case_ids": list(defaults.PHASE2_PROTECTED_CASE_IDS),
        "runs_per_case": 1,
        "total_physical_attempts": len(defaults.PHASE2_PROTECTED_CASE_IDS),
        "automatic_retries": 0,
        "retry_policy": (
            "zero automatic retries; any rerun after failure requires a separate "
            "explicit operator request"
        ),
        "round_robin": True,
        "operator_authorization_required": True,
        "no_live_gates_satisfied": no_live_gates_satisfied,
        "live_command_available": no_live_gates_satisfied,
        "operator_command": command if no_live_gates_satisfied else None,
        "blocked_reason": None
        if no_live_gates_satisfied
        else "all Phase A-G no-live gate proofs must be explicit first",
        "stop_rules": [dict(rule) for rule in PHASE_H_STOP_RULES],
        "not_authorized_for": [
            "full Phase 3 science campaign",
            "large 5x3 round-robin by default",
            "automatic retries after failures",
        ],
    }


def _suite_path_readiness(
    plugin: GpsFailurePlugin,
    cases: list[TestCase],
) -> dict[str, Any]:
    """Prove the plugin exposes every seam the shared SuiteRunner drives."""
    runner = plugin.attempt_runner()
    attempt_dir_factory = plugin.attempt_dir_factory()
    return {
        "registry_key": defaults.SUITE_NAME,
        "attempt_runner_built": runner is not None,
        "attempt_dir_factory_built": callable(attempt_dir_factory),
        "case_generator": type(plugin.case_generator).__name__,
        "manifest": type(plugin.manifest).__name__,
        "scheduled_case_count": len(cases),
        "scheduled_case_ids": [case.case_id for case in cases],
        "all_cases_share_mission": len(
            {str(case.mission_file) for case in cases}
        )
        == 1,
        "mission_file": str(plugin.config.mission_file),
    }


def _case_catalog(cases: list[TestCase]) -> dict[str, Any]:
    by_fault: dict[str, int] = {fault: 0 for fault in defaults.FAULT_TYPES}
    by_fault["nominal"] = 0
    for case in cases:
        fault = str(case.parameters.get("fault_type", "nominal"))
        by_fault[fault] = by_fault.get(fault, 0) + 1
    return {
        "total": len(cases),
        "by_fault_type": by_fault,
        "fault_types": list(defaults.FAULT_TYPES),
        "behavior_classes": list(defaults.BEHAVIOR_CLASSES),
        "analysis_state_classes": list(defaults.ANALYSIS_STATE_CLASSES),
    }


def _manifest_contract(plugin: GpsFailurePlugin) -> dict[str, Any]:
    """Surface the manifest shape without writing anything to disk."""
    empty = plugin.manifest.load()
    return {
        "adapter": type(plugin.manifest).__name__,
        "top_level_keys": sorted(empty.keys()),
        "attempts_initially_empty": empty.get("attempts") == [],
        "acceptance_rule": (
            "measurement validity only; all terminal/verdict/analysis signals "
            "must agree; contradictory or missing analysis fails closed"
        ),
    }


def _artifact_contract() -> dict[str, Any]:
    required = list(defaults.REQUIRED_ATTEMPT_ARTIFACTS)
    schema = analyzers.artifact_schema()
    # Every required attempt artifact must have a schema entry; report any that
    # do not so a missing schema (e.g. the historical gps_injection.json gap)
    # is visible in the readiness report instead of silently accepted.
    required_without_schema = [name for name in required if name not in schema]
    return {
        "required_attempt_artifacts": required,
        "artifact_schema": schema,
        "artifact_schema_names": sorted(schema.keys()),
        "required_artifacts_without_schema": required_without_schema,
        "schema_covers_required_artifacts": not required_without_schema,
        "min_post_injection_s": defaults.MIN_POST_INJECTION_S,
    }


def _parameter_stack(config: GpsFailureConfig) -> dict[str, Any]:
    return {
        "effective_param_stack": [str(path) for path in config.effective_param_stack],
        "required_sim_gps_params": list(defaults.REQUIRED_SIM_GPS_PARAMS),
        "sitl_target": defaults.SITL_TARGET,
        "gazebo_target": defaults.GAZEBO_TARGET,
        "local_override_excluded": True,
        "airspeed_overlay_excluded": True,
        "launch_target_note": (
            "dedicated GPS identities plane-gps / gazebo-plane-gps; exercised "
            "by governed raw validation runs; no curated Phase-2 evidence yet"
        ),
        "static_probe_mode": (
            "static name-existence validation only; live readback is "
            "re-verified on every live attempt"
        ),
    }
