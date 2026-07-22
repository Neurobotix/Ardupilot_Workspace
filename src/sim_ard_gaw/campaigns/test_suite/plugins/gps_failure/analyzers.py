"""GPS behavior analysis helpers and observation classifier."""
from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ...core.analysis import Analyzer
from ...core.models import (
    AnalysisResult,
    AttemptContext,
    AttemptStatus,
    MonitorResult,
    TestCase,
    Verdict,
    VerdictClass,
)
from ...core.verdicts import VerdictPolicy
from . import defaults
from .mechanism_gate import MechanismGateResult


BEHAVIOR_CLASSES = defaults.BEHAVIOR_CLASSES
ANALYSIS_STATE_CLASS = defaults.ANALYSIS_STATE_CLASSES[0]


def artifact_schema() -> dict[str, dict[str, Any]]:
    return {
        "run_config.json": {
            "required_fields": [
                "created_at_utc",
                "case_id",
                "attempt_id",
                "mission_file_provenance",
                "gazebo_world_provenance",
                "param_file_provenance",
                "source_tree_snapshot",
                "commands",
                "logs",
                "workspace_gazebo_plugin",
            ],
        },
        "gps_injection.json": {
            "required_fields": [
                "case_id",
                "fault_type",
                "requested_payload",
                "injection_schedule",
                "fault_recipe",
                "payload_resolution",
                "reset_payload",
                "trigger",
                "readback_rules",
                "readback_status_shape",
                "live_plan_contract",
            ],
        },
        "gps_behavior_summary.json": {
            "required_fields": [
                "behavior_class",
                "scientific_behavior_label",
                "scientific_behavior_components",
                "observation_quality_class",
                "accepted_observation",
                "reason",
                "analysis_axes",
                "reset_metrics",
                "truth_terminal_metrics",
                "terminal_state_reached",
                "mission_complete",
                "stop_reason",
                "max_seq_reached",
                "auto_to_rtl_transition_seq",
                "hard_denial_transient",
            ],
        },
        "stimulus_fidelity.json": {
            "required_fields": [
                "case_id",
                "fault_type",
                "status",
                "reason",
                "source",
                "requested",
                "realized",
                "tolerances",
                "evidence_refs",
                "missing_evidence",
            ],
        },
        "gps_lifecycle_windows.json": {
            "required_fields": [
                "case_id",
                "fault_type",
                "status",
                "reason",
                "source",
                "required_order",
                "windows",
                "hard_denial_transient",
                "missing_evidence",
            ],
        },
        "source_contract.json": {
            "required_fields": [
                "ok",
                "exact_internal_proof",
                "bin_observable_proof",
                "validated_proxy_proof",
                "proxy_reason",
                "proof_levels",
                "configuration_proof",
                "reasons",
                "readbacks",
                "estimator_flags",
                "source",
                "readback_results",
            ],
        },
        "ekf_innovation_metrics.json": {
            "required_fields": [
                "pos_test_ratio",
                "reject_flags",
                "reset_events",
                "variance",
            ],
        },
        "truth_vs_belief.json": {
            "required_fields": [
                "horizontal_gap_m",
                "gap_growth_rate_mps",
                "truth_source",
                "belief_source",
            ],
        },
        "mode_timeline.json": {"required_fields": ["mode_timeline"]},
        "attitude_altitude_envelope.json": {
            "required_fields": [
                "status",
                "reason",
                "source",
                "altitude_source",
                "attitude_source",
                "sampling_limits",
                "evidence_quality",
                "final_evidence_quality",
                "runtime_guard_quality",
                "post_injection_min_alt_m",
                "altitude_loss_m",
                "attitude_excursions",
                "threshold_crossings",
                "unexpected_disarm",
                "samples_complete",
                "missing_evidence",
                "limits",
            ],
        },
    }


def required_attempt_artifacts() -> list[str]:
    """The authoritative required attempt-artifact set for this lane."""
    return list(defaults.REQUIRED_ATTEMPT_ARTIFACTS)


def validate_artifact_against_schema(
    artifact_name: str,
    artifact: dict[str, Any],
) -> list[str]:
    """Return the list of required fields missing from ``artifact``.

    An empty list means the artifact satisfies the declared schema. An unknown
    artifact name reports the whole schema as missing so callers fail closed.
    """
    schema = artifact_schema().get(artifact_name)
    if schema is None:
        return [f"<unknown-artifact:{artifact_name}>"]
    missing = [field for field in schema["required_fields"] if field not in artifact]
    if artifact_name == "gps_lifecycle_windows.json":
        missing.extend(_validate_lifecycle_windows_artifact(artifact))
    if artifact_name == "source_contract.json":
        missing.extend(_validate_source_contract_artifact(artifact))
    return missing


def _validate_source_contract_artifact(artifact: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if "validated_proxy" in artifact:
        missing.append("legacy_field:validated_proxy")
    if "exact_aiding_proof" in artifact:
        missing.append("legacy_field:exact_aiding_proof")
    if artifact.get("exact_internal_proof") is not False:
        missing.append("exact_internal_proof.must_be_false_without_logged_signal")
    if artifact.get("bin_observable_proof") is not False:
        missing.append("bin_observable_proof.must_be_false_in_pre_injection_contract")

    ok = artifact.get("ok")
    proxy = artifact.get("validated_proxy_proof")
    if not isinstance(ok, bool):
        missing.append("ok")
    if isinstance(ok, bool) and proxy is not ok:
        missing.append("validated_proxy_proof.must_match_ok")
    elif not isinstance(proxy, bool):
        missing.append("validated_proxy_proof")

    proof_levels = artifact.get("proof_levels")
    if not isinstance(proof_levels, dict):
        missing.append("proof_levels")
    else:
        exact = proof_levels.get("exact_internal_proof")
        if not isinstance(exact, dict) or exact.get("available") is not False:
            missing.append("proof_levels.exact_internal_proof.available")
        bin_proof = proof_levels.get("bin_observable_proof")
        if not isinstance(bin_proof, dict) or bin_proof.get("available") is not False:
            missing.append("proof_levels.bin_observable_proof.available")
        proxy_proof = proof_levels.get("validated_proxy_proof")
        if not isinstance(proxy_proof, dict) or proxy_proof.get("available") is not proxy:
            missing.append("proof_levels.validated_proxy_proof.available")

    configuration = artifact.get("configuration_proof")
    if not isinstance(configuration, dict):
        missing.append("configuration_proof")
    else:
        if configuration.get("exact_runtime_internal_proof") is not False:
            missing.append("configuration_proof.exact_runtime_internal_proof")
        if not isinstance(configuration.get("readback_names"), list):
            missing.append("configuration_proof.readback_names")
    return missing


def _validate_lifecycle_windows_artifact(artifact: dict[str, Any]) -> list[str]:
    required_order = [
        "pre_trigger_baseline",
        "trigger",
        "injection",
        "fault_active",
        "ekf_response",
        "recovery_or_continuation",
        "terminal",
    ]
    required_window_fields = {
        "name",
        "start_time_us",
        "end_time_us",
        "duration_s",
        "source",
        "status",
        "summary",
        "metrics",
        "evidence_refs",
    }
    missing: list[str] = []
    if artifact.get("required_order") != required_order:
        missing.append("required_order")
    windows = artifact.get("windows")
    if not isinstance(windows, list):
        return [*missing, "windows"]
    names = [
        window.get("name")
        for window in windows
        if isinstance(window, dict)
    ]
    if names != required_order:
        missing.append("windows.order")
    if len(windows) != len(required_order):
        missing.append("windows.count")
    transient = artifact.get("hard_denial_transient")
    if not isinstance(transient, dict):
        missing.append("hard_denial_transient")
    else:
        transient_status = transient.get("status")
        if transient_status not in {"pass", "fail", "not_applicable"}:
            missing.append("hard_denial_transient.status")
        if "sample_scope" not in transient:
            missing.append("hard_denial_transient.sample_scope")
        if not isinstance(transient.get("missing_evidence"), list):
            missing.append("hard_denial_transient.missing_evidence")
    for index, window in enumerate(windows):
        prefix = f"windows[{index}]"
        if not isinstance(window, dict):
            missing.append(prefix)
            continue
        missing.extend(
            f"{prefix}.{field}"
            for field in sorted(required_window_fields - set(window))
        )
        source = window.get("source")
        if source not in {"BIN", "live_telemetry", "hybrid"}:
            missing.append(f"{prefix}.source")
        status = window.get("status")
        if status not in {"pass", "fail", "not_applicable"}:
            missing.append(f"{prefix}.status")
        if not isinstance(window.get("metrics"), dict):
            missing.append(f"{prefix}.metrics")
        if not isinstance(window.get("evidence_refs"), list):
            missing.append(f"{prefix}.evidence_refs")
    return missing


def classify_observation(observation: dict[str, Any]) -> dict[str, Any]:
    observation = _with_mechanism_result(observation)
    if observation.get("launch_failed"):
        return _result("pre_injection_failure", "failed_launch", False)
    if not observation.get("injection_triggered", False):
        return _result("pre_injection_failure", "pre_injection", False)
    if not observation.get("injection_readback_ok", False):
        return _result(ANALYSIS_STATE_CLASS, "failed_readback", False)
    window_s, window_error = _finite_number("post_injection_s", observation.get("post_injection_s"))
    if window_error is not None:
        # A malformed / non-finite observation window fails closed, never raises.
        return _result(ANALYSIS_STATE_CLASS, window_error, False)
    required_window_s, required_window_error = _finite_number(
        "required_post_injection_s",
        observation.get("required_post_injection_s", defaults.MIN_POST_INJECTION_S),
    )
    if required_window_error is not None:
        return _result(ANALYSIS_STATE_CLASS, required_window_error, False)
    if (
        window_s < required_window_s
        and observation.get("terminal_state_reached") is not True
    ):
        return _result(ANALYSIS_STATE_CLASS, "insufficient_post_injection_window", False)
    if not observation.get("required_artifacts_present", False):
        return _result(ANALYSIS_STATE_CLASS, "missing_required_artifacts", False)
    if observation.get("behavior_measurements_complete") is False:
        return _result(ANALYSIS_STATE_CLASS, "missing_behavior_samples", False)
    if (
        not _is_nominal_observation(observation)
        and observation.get("mechanism_evidence") is not True
    ):
        return _result(ANALYSIS_STATE_CLASS, "missing_mechanism_fields", False)

    # The behavior tier must be validated from substantive, finite metrics, not
    # from a caller-supplied "behavior_evidence=True" marker. Each accepted
    # behavior class is selected by its own positive evidence; nominal requires
    # explicit nominal evidence, never merely "no adverse flag was supplied".
    evidence, error = _behavior_evidence(observation)
    if evidence is None:
        return _result(ANALYSIS_STATE_CLASS, error or "missing_behavior_fields", False)
    if observation.get("terminal_state_reached") is not True:
        return _result(ANALYSIS_STATE_CLASS, "terminal_state_not_reached", False)
    if _is_nominal_observation(observation) and observation.get(
        "mission_complete"
    ) is not True:
        return _result(ANALYSIS_STATE_CLASS, "nominal_mission_incomplete", False)
    return _classify_behavior(evidence)


def _classify_behavior(evidence: "_BehaviorEvidence") -> dict[str, Any]:
    if evidence.loss_of_control:
        return _result("loss_of_control", "valid_bad_behavior", True)
    if evidence.mode_change or evidence.failsafe:
        return _result("autopilot_contained", "valid_contained_behavior", True)
    if evidence.reset_event:
        return _result("reset_captured", "valid_reset_behavior", True)
    if evidence.rejected:
        return _result("detected_rejected", "valid_detected_rejection", True)
    if evidence.fused and evidence.gap_growing and not evidence.failsafe:
        return _result("silent_drift", "valid_silent_drift", True)
    if (
        evidence.fused
        and not evidence.gap_growing
        and evidence.gap_within_nominal_band
        and not evidence.failsafe
        and not evidence.mode_change
        and evidence.attitude_in_band
    ):
        return _result("nominal", "valid_nominal", True)
    # Fields present and finite but no class positively established (e.g. a fix
    # that was neither fused nor rejected, or a contradictory nominal claim with
    # a growing gap). This is an incomplete analysis, not a silent nominal.
    return _result(ANALYSIS_STATE_CLASS, "behavior_evidence_inconclusive", False)


def _is_nominal_observation(observation: dict[str, Any]) -> bool:
    return (
        observation.get("case_id") == "nominal"
        or observation.get("fault_type") == "nominal"
    )


@dataclass(frozen=True)
class _BehaviorEvidence:
    fused: bool
    rejected: bool
    reset_event: bool
    failsafe: bool
    mode_change: bool
    loss_of_control: bool
    gap_growing: bool
    gap_within_nominal_band: bool
    attitude_in_band: bool


# The substantive behavior-tier fields the classifier requires. Each must be
# present (directly, or derivable from the mechanism gate) before any accepted
# behavior class is chosen. A bare "behavior_evidence" marker is not sufficient.
_REQUIRED_BEHAVIOR_FIELDS = (
    "horizontal_gap_m",
    "gap_growing",
    "attitude_in_band",
)
_SUPPORTED_BEHAVIOR_FIELDS = frozenset(
    {
        "horizontal_gap_m",
        "gap_growing",
        "gap_within_nominal_band",
        "attitude_in_band",
        "fused",
        "rejected",
        "pos_test_ratio_rejected",
        "reject_flags",
        "reset_event",
        "failsafe",
        "mode_change",
        "loss_of_control",
        "timeout",
    }
)
# Gap magnitude (metres) at or below which the truth-vs-belief gap is treated as
# within the nominal control band when an explicit band flag is not supplied.
_DEFAULT_NOMINAL_GAP_BAND_M = 5.0


def _behavior_evidence(
    observation: dict[str, Any],
) -> tuple["_BehaviorEvidence | None", str | None]:
    # Behavior evidence may be supplied either as flat observation keys (the
    # mechanism-gate-derived path) or under an explicit ``behavior_fields``
    # namespace (the artifact/analysis contract). When the namespace is present,
    # any key inside it that is not part of the contract is rejected outright.
    namespace = observation.get("behavior_fields")
    if namespace is not None:
        if not isinstance(namespace, dict):
            return None, "unsupported_behavior_fields"
        unsupported_ns = set(namespace) - _SUPPORTED_BEHAVIOR_FIELDS
        if unsupported_ns:
            return None, "unsupported_behavior_fields"
        observation = {**observation, **namespace}

    supplied = _behavior_fields_supplied(observation)
    if not supplied:
        return None, "missing_behavior_fields"

    missing = [name for name in _REQUIRED_BEHAVIOR_FIELDS if name not in observation]
    if missing:
        return None, "missing_behavior_fields"

    gap_m, gap_error = _finite_metric(observation, "horizontal_gap_m")
    if gap_error is not None:
        return None, gap_error

    try:
        fused = _strict_bool(observation, "fused")
        rejected = _strict_bool(observation, "pos_test_ratio_rejected") or _strict_bool(
            observation, "reject_flags"
        ) or _strict_bool(observation, "rejected")
        reset_event = _strict_bool(observation, "reset_event")
        failsafe = _strict_bool(observation, "failsafe")
        mode_change = _strict_bool(observation, "mode_change")
        loss_of_control = _strict_bool(observation, "loss_of_control") or _strict_bool(
            observation, "timeout"
        )
        gap_growing = _strict_bool(observation, "gap_growing")
        attitude_in_band = _strict_bool(observation, "attitude_in_band")
    except _NonBoolField as exc:
        return None, f"invalid_behavior_field_{exc.field}"

    if "gap_within_nominal_band" in observation:
        try:
            gap_within_nominal_band = _strict_bool(observation, "gap_within_nominal_band")
        except _NonBoolField as exc:
            return None, f"invalid_behavior_field_{exc.field}"
    else:
        gap_within_nominal_band = abs(gap_m) <= _DEFAULT_NOMINAL_GAP_BAND_M

    # Contradiction guard: a fix cannot be both fused and rejected in the same
    # observation window summary.
    if fused and rejected:
        return None, "contradictory_fused_and_rejected"

    return (
        _BehaviorEvidence(
            fused=fused,
            rejected=rejected,
            reset_event=reset_event,
            failsafe=failsafe,
            mode_change=mode_change,
            loss_of_control=loss_of_control,
            gap_growing=gap_growing,
            gap_within_nominal_band=gap_within_nominal_band,
            attitude_in_band=attitude_in_band,
        ),
        None,
    )


def _behavior_fields_supplied(observation: dict[str, Any]) -> set[str]:
    return {
        name
        for name in observation
        if name in _SUPPORTED_BEHAVIOR_FIELDS
    }


class _NonBoolField(Exception):
    def __init__(self, field: str) -> None:
        super().__init__(field)
        self.field = field


def _strict_bool(observation: dict[str, Any], field: str) -> bool:
    if field not in observation:
        return False
    value = observation[field]
    if isinstance(value, bool):
        return value
    raise _NonBoolField(field)


def _finite_metric(
    observation: dict[str, Any],
    field: str,
) -> tuple[float, str | None]:
    return _finite_number(field, observation.get(field))


def _finite_number(field: str, value: Any) -> tuple[float, str | None]:
    """Coerce a numeric field, failing closed (never raising) on bad input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0, f"invalid_behavior_field_{field}"
    numeric = float(value)
    if not math.isfinite(numeric):
        return 0.0, f"non_finite_behavior_field_{field}"
    return numeric, None


def _with_mechanism_result(observation: dict[str, Any]) -> dict[str, Any]:
    result = _mechanism_result_dict(observation)
    if result is None:
        return observation
    normalized = dict(observation)
    # When a mechanism result is supplied it is authoritative and OVERRIDES any
    # caller-supplied marker: a failed result must not be overridden by a stale
    # mechanism_evidence=True. The mechanism-accepted markers must also be a
    # strict boolean True; a truthy non-bool (e.g. "true", 1) is malformed
    # evidence and must not become an accepted mechanism.
    accepted = (
        result.get("accepted_evidence") is True
        or result.get("mechanism_evidence_accepted") is True
    )
    normalized["mechanism_evidence"] = accepted
    state = result.get("mechanism_state") or result.get("mechanism_class")
    # The mechanism result is the sole source of truth for the derived
    # mechanism-tier flags, so a caller cannot pre-seed them either. Clear any
    # stale caller values, then set from the (accepted) result.
    for stale in ("reset_event", "pos_test_ratio_rejected", "fused"):
        normalized.pop(stale, None)
    if accepted and state == "reset_detected":
        normalized["reset_event"] = True
    elif accepted and state == "rejected_above_gate":
        normalized["pos_test_ratio_rejected"] = True
    elif accepted and state == "fused_below_gate":
        normalized["fused"] = True
    return normalized


def _mechanism_result_dict(observation: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("mechanism_gate_result", "mechanism_result"):
        value = observation.get(key)
        if isinstance(value, MechanismGateResult):
            return value.as_dict()
        if isinstance(value, dict):
            return value
    return None


def _result(
    behavior_class: str,
    observation_quality_class: str,
    accepted_observation: bool,
) -> dict[str, Any]:
    return {
        "behavior_class": behavior_class,
        "observation_quality_class": observation_quality_class,
        "accepted_observation": accepted_observation,
        "reason": observation_quality_class,
    }


@dataclass
class GpsFailureAnalyzer(Analyzer):
    name: str = "gps_failure_post_cleanup_analysis"

    def analyze(self, case: TestCase, ctx: AttemptContext) -> AnalysisResult:
        observation = dict(ctx.extra.get("gps_observation") or {})
        if not observation:
            observation = {
                "injection_triggered": False,
                "required_artifacts_present": False,
            }
        if isinstance(ctx.extra.get("gps_launch_plan"), dict):
            observation = _finalize_live_bin_analysis(case, ctx, observation)
        summary = _summary_with_terminal_context(
            classify_observation(observation), observation, case=case
        )
        if isinstance(ctx.extra.get("gps_launch_plan"), dict):
            _persist_final_live_summary(ctx, observation, summary)
        return AnalysisResult(
            analyzer_name=self.name,
            ok=bool(summary["accepted_observation"]),
            summary=summary,
        )


def _finalize_live_bin_analysis(
    case: TestCase,
    ctx: AttemptContext,
    observation: dict[str, Any],
) -> dict[str, Any]:
    """Decode the cleanup-finalized BIN and replace live fallback metrics."""

    from .bin_analysis import (
        analyze_attempt_bin,
        attitude_altitude_envelope_from_decoded_records,
        lifecycle_windows_missing_bin_artifact,
        stimulus_fidelity_missing_bin_artifact,
    )
    from .environment import identify_attempt_bin

    metrics_path = ctx.attempt_dir / "ekf_innovation_metrics.json"
    truth_path = ctx.attempt_dir / "truth_vs_belief.json"
    fidelity_path = ctx.attempt_dir / "stimulus_fidelity.json"
    lifecycle_path = ctx.attempt_dir / "gps_lifecycle_windows.json"
    raw_metrics = defaults.read_json(metrics_path)
    raw_truth = defaults.read_json(truth_path)
    envelope_path = ctx.attempt_dir / "attitude_altitude_envelope.json"
    raw_envelope = defaults.read_json(envelope_path)
    metrics = raw_metrics if isinstance(raw_metrics, dict) else {}
    truth = raw_truth if isinstance(raw_truth, dict) else {}
    live_envelope = raw_envelope if isinstance(raw_envelope, dict) else {}
    fault_recipe = case.parameters.get("fault_recipe")
    recipe = fault_recipe if isinstance(fault_recipe, dict) else None
    source_bin_path = identify_attempt_bin(ctx)
    if source_bin_path is None:
        analysis: dict[str, Any] = {
            "ok": False,
            "reason": "single_current_attempt_bin_not_available_after_cleanup",
        }
        stimulus_fidelity = stimulus_fidelity_missing_bin_artifact(
            case_id=case.case_id,
            fault_type=str(case.parameters.get("fault_type", "")),
            fault_recipe=recipe,
            reason="single_current_attempt_bin_not_available_after_cleanup",
        )
        lifecycle_windows = lifecycle_windows_missing_bin_artifact(
            case_id=case.case_id,
            fault_type=str(case.parameters.get("fault_type", "")),
            reason="single_current_attempt_bin_not_available_after_cleanup",
        )
    else:
        execution = ctx.extra.get("gps_injection_execution")
        plan = execution.get("plan") if isinstance(execution, dict) else None
        injection_payload = (
            plan.get("injection_payload") if isinstance(plan, dict) else None
        )
        trigger_event = plan.get("trigger_event") if isinstance(plan, dict) else None
        analysis_bin_path = source_bin_path
        try:
            analysis_bin_path = _archive_attempt_bin(source_bin_path, ctx)
            analysis = analyze_attempt_bin(
                analysis_bin_path,
                decoder=ctx.extra.get("gps_bin_decoder"),
                window_start_time_us=_trigger_window_time_us(ctx),
                trigger_seq=int(defaults.INJECTION_TRIGGER["seq"]),
                injection_payload=(
                    injection_payload
                    if isinstance(injection_payload, dict)
                    else None
                ),
                case_id=case.case_id,
                fault_type=str(case.parameters.get("fault_type", "")),
                fault_recipe=recipe,
                trigger_event=(
                    trigger_event if isinstance(trigger_event, dict) else None
                ),
                injection_execution=(
                    execution if isinstance(execution, dict) else None
                ),
                source_contract=(
                    metrics_source_contract
                    if isinstance((metrics_source_contract := _source_contract(ctx)), dict)
                    else None
                ),
                terminal_context=_terminal_lifecycle_context(ctx, observation),
                wall_elapsed_s=_finite_observation_number(
                    observation.get("post_injection_wall_elapsed_s")
                ),
                clock_ratio=_finite_observation_number(
                    observation.get("post_injection_clock_ratio")
                    or observation.get("clock_ratio")
                ),
                live_attitude_altitude_envelope=live_envelope,
            )
            stimulus_fidelity = analysis.get("stimulus_fidelity")
            if not isinstance(stimulus_fidelity, dict):
                stimulus_fidelity = stimulus_fidelity_missing_bin_artifact(
                    case_id=case.case_id,
                    fault_type=str(case.parameters.get("fault_type", "")),
                    fault_recipe=recipe,
                    reason="stimulus_fidelity_not_emitted",
                )
            lifecycle_windows = analysis.get("lifecycle_windows")
            if not isinstance(lifecycle_windows, dict):
                lifecycle_windows = lifecycle_windows_missing_bin_artifact(
                    case_id=case.case_id,
                    fault_type=str(case.parameters.get("fault_type", "")),
                    reason="lifecycle_windows_not_emitted",
                )
        except Exception as exc:
            analysis = {
                "ok": False,
                "bin_path": str(analysis_bin_path),
                "reason": f"{type(exc).__name__}: {exc}",
            }
            stimulus_fidelity = stimulus_fidelity_missing_bin_artifact(
                case_id=case.case_id,
                fault_type=str(case.parameters.get("fault_type", "")),
                fault_recipe=recipe,
                reason=f"{type(exc).__name__}: {exc}",
            )
            lifecycle_windows = lifecycle_windows_missing_bin_artifact(
                case_id=case.case_id,
                fault_type=str(case.parameters.get("fault_type", "")),
                reason=f"{type(exc).__name__}: {exc}",
            )
    envelope = analysis.get("attitude_altitude_envelope")
    if not isinstance(envelope, dict):
        envelope = attitude_altitude_envelope_from_decoded_records(
            [],
            window_start_time_us=None,
            live_artifact=live_envelope,
            reason="attitude_altitude_envelope_not_emitted",
        )

    ctx.extra["gps_bin_analysis"] = analysis
    ctx.extra["gps_stimulus_fidelity"] = stimulus_fidelity
    ctx.extra["gps_lifecycle_windows"] = lifecycle_windows
    ctx.extra["gps_attitude_altitude_envelope"] = envelope
    defaults.write_json(fidelity_path, stimulus_fidelity)
    defaults.write_json(lifecycle_path, lifecycle_windows)
    defaults.write_json(envelope_path, envelope)
    ctx.artifacts["stimulus_fidelity.json"] = fidelity_path
    ctx.artifacts["gps_lifecycle_windows.json"] = lifecycle_path
    ctx.artifacts["attitude_altitude_envelope.json"] = envelope_path
    mechanism = analysis.get("mechanism")
    if isinstance(mechanism, dict) and mechanism.get("ok") is True:
        metrics = _ekf_metrics_from_bin(mechanism, fallback=metrics)
    truth_belief = analysis.get("truth_vs_belief")
    if isinstance(truth_belief, dict) and truth_belief.get("ok") is True:
        truth = _truth_belief_from_bin(truth_belief, fallback=truth)
    metrics["bin_analysis"] = analysis
    truth["bin_analysis"] = analysis
    defaults.write_json(metrics_path, metrics)
    defaults.write_json(truth_path, truth)
    ctx.artifacts["ekf_innovation_metrics.json"] = metrics_path
    ctx.artifacts["truth_vs_belief.json"] = truth_path

    ratios = [
        float(value)
        for value in metrics.get("pos_test_ratio", [])
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    gaps = [
        float(value)
        for value in truth.get("horizontal_gap_m", [])
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    finalized = dict(observation)
    analysis_ok = analysis.get("ok") is True
    mechanism_ok = isinstance(mechanism, dict) and mechanism.get("ok") is True
    lifecycle_ok = lifecycle_windows.get("status") == "pass"
    envelope_ok = envelope.get("status") == "pass"
    hard_denial_transient = lifecycle_windows.get("hard_denial_transient")
    finalized.update({
        "required_artifacts_present": all(
            (ctx.attempt_dir / name).exists()
            for name in defaults.REQUIRED_ATTEMPT_ARTIFACTS
            if name != "gps_behavior_summary.json"
        ),
        "mechanism_evidence": bool(
            mechanism_ok and finalized.get("source_contract_ok") is True
        ),
        "behavior_measurements_complete": bool(
            finalized.get("behavior_measurements_complete") is True
            and analysis_ok
            and lifecycle_ok
            and envelope_ok
            and ratios
            and len(gaps) >= 2
        ),
        "horizontal_gap_m": gaps[-1] if gaps else 0.0,
        "gap_growing": bool(
            len(gaps) >= 2
            and gaps[-1] > 5.0
            and gaps[-1] - gaps[0] > 1.0
            and float(truth.get("gap_growth_rate_mps", 0.0)) > 0.0
        ),
        "gap_within_nominal_band": bool((gaps[-1] if gaps else 0.0) <= 5.0),
        "fused": bool(ratios and max(ratios) < 1.0),
        "pos_test_ratio_rejected": bool(ratios and max(ratios) >= 1.0),
        "reset_event": bool(metrics.get("reset_events")),
        "attitude_in_band": bool(
            envelope_ok and not envelope.get("threshold_crossings")
        ),
        "attitude_altitude_envelope_status": envelope.get("status"),
        "attitude_altitude_envelope_reason": envelope.get("reason"),
        "bin_analysis_ok": analysis_ok,
        "stimulus_fidelity_status": stimulus_fidelity.get("status"),
        "stimulus_fidelity_reason": stimulus_fidelity.get("reason"),
        "lifecycle_windows_status": lifecycle_windows.get("status"),
        "lifecycle_windows_reason": lifecycle_windows.get("reason"),
        "hard_denial_transient": (
            hard_denial_transient
            if isinstance(hard_denial_transient, dict)
            else None
        ),
    })
    reset_metrics = _reset_metrics_from_observation(metrics)
    truth_terminal_metrics = _truth_terminal_metrics_from_observation(case, truth)
    finalized.update({
        "reset_metrics": reset_metrics,
        "truth_gap_summary": _truth_gap_summary_from_observation(truth),
        "truth_terminal_metrics": truth_terminal_metrics,
        "analysis_axes": _analysis_axes_from_observation(
            case=case,
            observation=finalized,
            ratios=ratios,
            reset_metrics=reset_metrics,
            truth_terminal_metrics=truth_terminal_metrics,
            truth=truth,
        ),
    })
    ctx.extra["gps_observation"] = finalized
    return finalized


def _archive_attempt_bin(source_bin_path: Path, ctx: AttemptContext) -> Path:
    copied_name = "{}.BIN".format(
        defaults.case_attempt_id(
            ctx.case.case_id,
            ctx.target_run_index,
            ctx.attempt_index,
        )
    )
    dest_bin_path = ctx.attempt_dir / copied_name
    if source_bin_path.resolve(strict=False) != dest_bin_path.resolve(strict=False):
        shutil.copy2(source_bin_path, dest_bin_path)
    ctx.artifacts["raw_log"] = dest_bin_path
    return dest_bin_path


def _trigger_window_time_us(ctx: AttemptContext) -> float | None:
    candidates: list[Any] = [ctx.extra.get("gps_trigger_event")]
    execution = ctx.extra.get("gps_injection_execution")
    plan = execution.get("plan") if isinstance(execution, dict) else None
    if isinstance(plan, dict):
        candidates.insert(0, plan.get("trigger_event"))
    trace = ctx.extra.get("gps_trigger_trace")
    if isinstance(trace, list):
        trigger_seq = int(defaults.INJECTION_TRIGGER["seq"])
        candidates.extend(
            event
            for event in trace
            if isinstance(event, dict) and event.get("seq") == trigger_seq
        )
    for event in candidates:
        if not isinstance(event, dict):
            continue
        value = event.get("trigger_time_us")
        if (
            event.get("trigger_boot_time_fresh") is True
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            and float(value) >= 0.0
        ):
            return float(value)
    return None


def _source_contract(ctx: AttemptContext) -> dict[str, Any] | None:
    raw = ctx.extra.get("gps_source_contract")
    if isinstance(raw, dict):
        return raw
    path = ctx.attempt_dir / "source_contract.json"
    if not path.exists():
        return None
    loaded = defaults.read_json(path)
    return loaded if isinstance(loaded, dict) else None


def _terminal_lifecycle_context(
    ctx: AttemptContext,
    observation: dict[str, Any],
) -> dict[str, Any]:
    required_json = [
        name
        for name in defaults.REQUIRED_ATTEMPT_ARTIFACTS
        if name != "gps_lifecycle_windows.json"
    ]
    raw_log_path = ctx.artifacts.get("raw_log")
    return {
        "terminal_state_reached": observation.get("terminal_state_reached"),
        "mission_complete": observation.get("mission_complete"),
        "stop_reason": observation.get("stop_reason"),
        "max_seq_reached": observation.get("max_seq_reached"),
        "auto_to_rtl_transition_seq": observation.get("auto_to_rtl_transition_seq"),
        "cleanup_result": ctx.extra.get("cleanup_result"),
        "raw_log_path": str(raw_log_path) if raw_log_path is not None else None,
        "raw_bin_archived": bool(raw_log_path is not None and Path(raw_log_path).is_file()),
        "required_json_artifacts": required_json,
        "required_json_artifacts_present": all(
            (ctx.attempt_dir / name).exists()
            for name in required_json
        ),
    }


def _summary_with_terminal_context(
    summary: dict[str, Any],
    observation: dict[str, Any],
    *,
    case: TestCase,
) -> dict[str, Any]:
    enriched = dict(summary)
    for field in (
        "analysis_axes",
        "reset_metrics",
        "truth_gap_summary",
        "truth_terminal_metrics",
        "terminal_state_reached",
        "mission_complete",
        "stop_reason",
        "max_seq_reached",
        "auto_to_rtl_transition_seq",
        "stimulus_fidelity_status",
        "stimulus_fidelity_reason",
        "lifecycle_windows_status",
        "lifecycle_windows_reason",
        "hard_denial_transient",
    ):
        enriched[field] = observation.get(field)
    label, components = _scientific_behavior_label_and_components(
        case=case,
        summary=enriched,
        observation=observation,
    )
    enriched["scientific_behavior_label"] = label
    enriched["scientific_behavior_components"] = components
    return enriched


def _persist_final_live_summary(
    ctx: AttemptContext,
    observation: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    summary_path = ctx.attempt_dir / "gps_behavior_summary.json"
    defaults.write_json(summary_path, summary)
    ctx.artifacts["gps_behavior_summary.json"] = summary_path
    ctx.extra["gps_observation"] = observation
    fields = dict(ctx.extra.get("plugin_manifest_fields") or {})
    workflow_complete = _workflow_complete_after_cleanup(ctx, observation)
    behavior_accepted = summary["accepted_observation"] is True
    stimulus_passed = observation.get("stimulus_fidelity_status") == "pass"
    accepted_observation = bool(workflow_complete and behavior_accepted)
    accepted_repetition = bool(accepted_observation and stimulus_passed)
    if workflow_complete:
        ctx.extra["attempt_status"] = AttemptStatus.SUCCESS
    fields.update({
        "behavior_class": summary["behavior_class"],
        "scientific_behavior_label": summary.get("scientific_behavior_label"),
        "scientific_behavior_components": summary.get(
            "scientific_behavior_components"
        ),
        "observation_quality_class": summary["observation_quality_class"],
        "accepted_observation": accepted_observation,
        "accepted_repetition": accepted_repetition,
        "stimulus_fidelity_status": observation.get("stimulus_fidelity_status"),
        "stimulus_fidelity_reason": observation.get("stimulus_fidelity_reason"),
        "lifecycle_windows_status": observation.get("lifecycle_windows_status"),
        "lifecycle_windows_reason": observation.get("lifecycle_windows_reason"),
        "workflow_status": "complete" if workflow_complete else "incomplete",
        "behavior_status": "accepted" if behavior_accepted else "incomplete",
        "analysis_status": "complete",
        "terminal_state_reached": observation.get("terminal_state_reached"),
        "mission_complete": observation.get("mission_complete"),
        "stop_reason": observation.get("stop_reason"),
        "max_seq_reached": observation.get("max_seq_reached"),
        "auto_to_rtl_transition_seq": observation.get(
            "auto_to_rtl_transition_seq"
        ),
        "analysis_axes": observation.get("analysis_axes"),
        "reset_metrics": observation.get("reset_metrics"),
        "truth_terminal_metrics": observation.get("truth_terminal_metrics"),
        "artifacts": {name: str(path) for name, path in ctx.artifacts.items()},
    })
    raw_log_path = ctx.artifacts.get("raw_log")
    if raw_log_path is not None:
        fields["raw_log_path"] = str(raw_log_path)
    notes = list(fields.get("notes") or [])
    if summary["reason"] not in notes:
        notes.append(summary["reason"])
    fields["notes"] = notes
    ctx.extra["plugin_manifest_fields"] = fields


def _scientific_behavior_label_and_components(
    *,
    case: TestCase,
    summary: dict[str, Any],
    observation: dict[str, Any],
) -> tuple[str, dict[str, str]]:
    axes_obj = summary.get("analysis_axes")
    axes = axes_obj if isinstance(axes_obj, dict) else {}
    terminal = _scientific_terminal_component(
        str(axes.get("truth_terminal_severity") or "")
    )
    response = _scientific_response_component(
        fault_type=str(case.parameters.get("fault_type") or ""),
        estimator_response=str(axes.get("estimator_response") or ""),
        recovery_outcome=str(axes.get("recovery_outcome") or ""),
        reset_count=int(axes.get("reset_count") or 0),
    )
    stimulus = _scientific_stimulus_component(case)
    acceptance = _scientific_acceptance_component(
        summary=summary,
        observation=observation,
    )
    components = {
        "terminal_truth": terminal,
        "estimator_fault_response": response,
        "stimulus_profile": stimulus,
        "acceptance": acceptance,
    }
    return (
        " + ".join(
            [
                components["terminal_truth"],
                components["estimator_fault_response"],
                components["stimulus_profile"],
                components["acceptance"],
            ]
        ),
        components,
    )


def _scientific_terminal_component(severity: str) -> str:
    mapping = {
        "nominal_terminal_band": "true_terminal",
        "mild_false_terminal": "false_terminal_mild",
        "material_false_terminal": "false_terminal_material",
        "severe_false_terminal": "false_terminal_severe",
    }
    return mapping.get(severity, "terminal_truth_unknown")


def _scientific_response_component(
    *,
    fault_type: str,
    estimator_response: str,
    recovery_outcome: str,
    reset_count: int,
) -> str:
    if fault_type == "hard_denial":
        if recovery_outcome == "transient_denial_recovered_no_reset":
            return "transient_denial_recovered_no_reset"
        if recovery_outcome == "transient_denial_recovered_with_reset":
            return "transient_denial_reset_recovered"
        return "transient_denial_unresolved"
    if fault_type == "slow_drift":
        if estimator_response == "fused_below_gate":
            return "gps_fused_silent"
        if estimator_response == "repeated_resets":
            return "reset_loop"
        if reset_count == 1:
            return "reset_capture_drift"
        if estimator_response == "detected_rejection_without_reset":
            return "gps_rejected_drift"
        return "drift_response_unknown"
    if fault_type == "step_glitch":
        if reset_count > 0:
            return "reset_capture_fixed_offset"
        if estimator_response == "detected_rejection_without_reset":
            return "gps_rejected_fixed_offset"
        if estimator_response == "fused_below_gate":
            return "gps_fused_fixed_offset"
        return "fixed_offset_response_unknown"
    if fault_type == "nominal":
        return "gps_nominal"
    return "estimator_response_unknown"


def _scientific_stimulus_component(case: TestCase) -> str:
    fault_type = str(case.parameters.get("fault_type") or "")
    if fault_type == "slow_drift":
        if case.case_id == "slow_drift_accumulation_ramp":
            return "accumulation_ramp"
        return "stepped_ramp"
    if fault_type == "step_glitch":
        return "fixed_step"
    if fault_type == "hard_denial":
        return "denial_window"
    if fault_type == "nominal":
        return "no_fault"
    return "stimulus_unknown"


def _scientific_acceptance_component(
    *,
    summary: dict[str, Any],
    observation: dict[str, Any],
) -> str:
    if (
        summary.get("accepted_observation") is True
        and observation.get("stimulus_fidelity_status") == "pass"
    ):
        return "accepted"
    if summary.get("accepted_observation") is True:
        return "accepted_observation_bad_stimulus"
    return "analyzer_rejected"


def _workflow_complete_after_cleanup(
    ctx: AttemptContext,
    observation: dict[str, Any],
) -> bool:
    cleanup = ctx.extra.get("cleanup_result")
    raw_log = ctx.artifacts.get("raw_log")
    return bool(
        observation.get("injection_triggered") is True
        and observation.get("injection_readback_ok") is True
        and observation.get("terminal_state_reached") is True
        and observation.get("telemetry_delivery_ok") is True
        and isinstance(cleanup, dict)
        and cleanup.get("ok") is True
        and raw_log is not None
        and Path(raw_log).is_file()
    )


def _finite_observation_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def _ekf_metrics_from_bin(
    mechanism: dict[str, Any],
    *,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    samples = [
        sample for sample in mechanism.get("samples", [])
        if isinstance(sample, dict)
    ]
    ratios = [
        sample.get("pos_test_ratio")
        for sample in samples
        if isinstance(sample.get("pos_test_ratio"), (int, float))
    ]
    return {
        "pos_test_ratio": ratios,
        "reject_flags": [
            bool(sample.get("gps_position_rejected")) for sample in samples
        ],
        "reset_events": list(mechanism.get("reset_events") or []),
        "variance": list(fallback.get("variance") or []),
        "samples": samples,
        "source": mechanism.get("source", "XKF4"),
    }


def _truth_belief_from_bin(
    truth_belief: dict[str, Any],
    *,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    samples = [
        sample for sample in truth_belief.get("samples", [])
        if isinstance(sample, dict)
    ]
    gaps = [
        float(sample["horizontal_gap_m"])
        for sample in samples
        if isinstance(sample.get("horizontal_gap_m"), (int, float))
    ]
    growth = 0.0
    if len(samples) >= 2 and len(gaps) >= 2:
        first_time = samples[0].get("time_us")
        last_time = samples[-1].get("time_us")
        if isinstance(first_time, (int, float)) and isinstance(last_time, (int, float)):
            dt = (last_time - first_time) / 1_000_000.0
            if dt > 0:
                growth = (gaps[-1] - gaps[0]) / dt
    return {
        "horizontal_gap_m": gaps,
        "gap_growth_rate_mps": growth,
        "truth_source": "SIM",
        "belief_source": "POS",
        "samples": samples,
        "sample_scope": truth_belief.get("sample_scope"),
        "all_sample_count": truth_belief.get("all_sample_count"),
        "active_segment_index": truth_belief.get("active_segment_index"),
        "reset_event_times_us": list(truth_belief.get("reset_event_times_us") or []),
        "full_window_gap_summary": truth_belief.get("full_window_gap_summary"),
        "active_segment_gap_summary": truth_belief.get(
            "active_segment_gap_summary"
        ),
        "mission_terminal_event": truth_belief.get("mission_terminal_event"),
        "mission_terminal_sample": truth_belief.get("mission_terminal_sample"),
        "full_window_terminal_sample": truth_belief.get(
            "full_window_terminal_sample"
        ),
        "active_segment_terminal_sample": truth_belief.get(
            "active_segment_terminal_sample"
        ),
        "full_window_max_gap_sample": truth_belief.get("full_window_max_gap_sample"),
        "sample_scope_labels": truth_belief.get("sample_scope_labels"),
        "live_fallback_source": {
            "truth_source": fallback.get("truth_source"),
            "belief_source": fallback.get("belief_source"),
        },
        "source": truth_belief.get("source", "SIM/POS"),
    }


def _reset_metrics_from_observation(metrics: dict[str, Any]) -> dict[str, Any]:
    events = [
        event for event in metrics.get("reset_events", [])
        if isinstance(event, dict)
    ]
    times = [
        _finite_observation_number(event.get("time_us"))
        for event in events
    ]
    times = [value for value in times if value is not None]
    return {
        "reset_count": len(events),
        "first_reset_time_us": min(times) if times else None,
        "last_reset_time_us": max(times) if times else None,
        "reset_events": events,
    }


def _truth_gap_summary_from_observation(truth: dict[str, Any]) -> dict[str, Any]:
    return {
        "classifier_sample_scope": truth.get("sample_scope"),
        "classifier_gap_count": len(truth.get("horizontal_gap_m") or []),
        "classifier_gap_growth_rate_mps": truth.get("gap_growth_rate_mps"),
        "full_window_gap_summary": truth.get("full_window_gap_summary"),
        "active_segment_gap_summary": truth.get("active_segment_gap_summary"),
        "sample_scope_labels": truth.get("sample_scope_labels"),
    }


def _truth_terminal_metrics_from_observation(
    case: TestCase,
    truth: dict[str, Any],
) -> dict[str, Any]:
    terminal_sample = truth.get("mission_terminal_sample")
    terminal_sample_scope = "sample_nearest_mission_terminal_event"
    terminal_event = truth.get("mission_terminal_event")
    if not isinstance(terminal_sample, dict):
        terminal_sample = truth.get("full_window_terminal_sample")
        terminal_sample_scope = "full_post_trigger_window"
        terminal_event = None
    if not isinstance(terminal_sample, dict):
        return {
            "status": "unavailable",
            "reason": "missing_mission_or_full_window_terminal_sample",
        }
    waypoint = _mission_waypoint_lat_lon(case.mission_file or defaults.MISSION_FILE, 8)
    if waypoint is None:
        return {
            "status": "unavailable",
            "reason": "missing_wp8_mission_waypoint",
            "terminal_sample": terminal_sample,
        }
    truth_lat = _finite_observation_number(terminal_sample.get("truth_lat_deg"))
    truth_lon = _finite_observation_number(terminal_sample.get("truth_lon_deg"))
    belief_lat = _finite_observation_number(terminal_sample.get("belief_lat_deg"))
    belief_lon = _finite_observation_number(terminal_sample.get("belief_lon_deg"))
    if (
        truth_lat is None
        or truth_lon is None
        or belief_lat is None
        or belief_lon is None
    ):
        return {
            "status": "unavailable",
            "reason": "malformed_full_window_terminal_sample",
            "terminal_sample": terminal_sample,
            "waypoint": waypoint,
        }
    sim_to_wp8 = _lat_lon_gap_m(
        truth_lat,
        truth_lon,
        waypoint["lat_deg"],
        waypoint["lon_deg"],
    )
    pos_to_wp8 = _lat_lon_gap_m(
        belief_lat,
        belief_lon,
        waypoint["lat_deg"],
        waypoint["lon_deg"],
    )
    pos_sim_gap = _finite_observation_number(
        terminal_sample.get("horizontal_gap_m")
    )
    severity = _false_terminal_severity(sim_to_wp8)
    return {
        "status": "available",
        "sample_scope": terminal_sample_scope,
        "mission_terminal_event": terminal_event if isinstance(terminal_event, dict) else None,
        "terminal_time_us": terminal_sample.get("time_us"),
        "terminal_sample": terminal_sample,
        "target_waypoint": {"seq": 8, **waypoint},
        "sim_to_wp8_m": sim_to_wp8,
        "pos_to_wp8_m": pos_to_wp8,
        "pos_sim_horizontal_gap_m": pos_sim_gap,
        "truth_position_outcome": (
            "true_terminal_band"
            if severity == "nominal_terminal_band"
            else "false_terminal_progress"
        ),
        "truth_terminal_severity": severity,
        "terminal_band_m": 50.0,
    }


def _analysis_axes_from_observation(
    *,
    case: TestCase,
    observation: dict[str, Any],
    ratios: list[float],
    reset_metrics: dict[str, Any],
    truth_terminal_metrics: dict[str, Any],
    truth: dict[str, Any],
) -> dict[str, Any]:
    fault_type = str(case.parameters.get("fault_type") or observation.get("fault_type") or "")
    reset_count = int(reset_metrics.get("reset_count") or 0)
    max_ratio = max(ratios) if ratios else None
    if reset_count > 1:
        estimator_response = "repeated_resets"
    elif reset_count == 1:
        estimator_response = "single_reset"
    elif max_ratio is not None and max_ratio >= 1.0:
        estimator_response = "detected_rejection_without_reset"
    elif max_ratio is not None and max_ratio < 1.0:
        estimator_response = "fused_below_gate"
    else:
        estimator_response = "estimator_response_unavailable"

    if observation.get("terminal_state_reached") is not True:
        mission_progress = "terminal_not_reached"
    elif observation.get("mission_complete") is True:
        mission_progress = "planned_rtl_terminal_reached_by_belief"
    else:
        mission_progress = "terminal_state_reached_without_nominal_completion"

    truth_position = truth_terminal_metrics.get("truth_position_outcome")
    if not isinstance(truth_position, str):
        truth_position = "truth_terminal_unavailable"

    if fault_type == "hard_denial" and observation.get("stimulus_fidelity_status") == "pass":
        if truth_position == "true_terminal_band" and reset_count == 0:
            recovery = "transient_denial_recovered_no_reset"
        elif truth_position == "true_terminal_band" and reset_count > 0:
            recovery = "transient_denial_recovered_with_reset"
        else:
            recovery = "hard_denial_terminal_truth_unresolved"
    elif reset_count > 0:
        recovery = "reset_after_fault"
    elif observation.get("terminal_state_reached") is True:
        recovery = "terminal_reached_without_reset"
    else:
        recovery = "recovery_unavailable"

    full_gap = truth.get("full_window_gap_summary")
    full_max_gap = (
        full_gap.get("max_horizontal_gap_m")
        if isinstance(full_gap, dict)
        else None
    )
    return {
        "stimulus_fidelity": observation.get("stimulus_fidelity_status"),
        "estimator_response": estimator_response,
        "mission_progress_outcome": mission_progress,
        "truth_position_outcome": truth_position,
        "truth_terminal_severity": truth_terminal_metrics.get(
            "truth_terminal_severity"
        ),
        "recovery_outcome": recovery,
        "reset_count": reset_count,
        "max_pos_test_ratio": max_ratio,
        "max_full_window_truth_belief_gap_m": full_max_gap,
        "classifier_sample_scope": truth.get("sample_scope"),
    }


def _false_terminal_severity(distance_m: float) -> str:
    if distance_m <= 50.0:
        return "nominal_terminal_band"
    if distance_m <= 150.0:
        return "mild_false_terminal"
    if distance_m <= 500.0:
        return "material_false_terminal"
    return "severe_false_terminal"


def _mission_waypoint_lat_lon(path: Path, seq: int) -> dict[str, float] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("QGC "):
            continue
        fields = stripped.split()
        if len(fields) < 11:
            continue
        try:
            row_seq = int(fields[0])
        except ValueError:
            continue
        if row_seq != seq:
            continue
        lat = _finite_observation_number(_parse_float(fields[8]))
        lon = _finite_observation_number(_parse_float(fields[9]))
        if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
            return None
        return {"lat_deg": lat, "lon_deg": lon}
    return None


def _parse_float(value: str) -> float | None:
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _lat_lon_gap_m(
    a_lat_deg: float,
    a_lon_deg: float,
    b_lat_deg: float,
    b_lon_deg: float,
) -> float:
    ref_lat_rad = math.radians((a_lat_deg + b_lat_deg) / 2.0)
    dn = (b_lat_deg - a_lat_deg) * 111_320.0
    de = (b_lon_deg - a_lon_deg) * 111_320.0 * math.cos(ref_lat_rad)
    return math.hypot(dn, de)


class GpsFailureVerdictPolicy(VerdictPolicy):
    def classify(
        self,
        case: TestCase,
        monitor_result: MonitorResult,
        analysis_results: Sequence[AnalysisResult],
    ) -> Verdict:
        accepted_observation = bool(analysis_results) and all(
            result.ok and result.summary.get("accepted_observation") is True
            for result in analysis_results
        )
        stimulus_passed = bool(analysis_results) and all(
            result.summary.get("stimulus_fidelity_status") == "pass"
            for result in analysis_results
        )
        accepted_repetition = bool(accepted_observation and stimulus_passed)
        behavior = next(
            (
                str(result.summary.get("behavior_class"))
                for result in analysis_results
                if result.summary.get("behavior_class")
            ),
            monitor_result.reason,
        )
        if accepted_observation:
            return Verdict(
                klass=VerdictClass.SUCCESS,
                reason=behavior,
                retryable=False,
                metadata={
                    "accepted_observation": True,
                    "accepted_repetition": accepted_repetition,
                    "stimulus_fidelity_status": (
                        "pass" if stimulus_passed else "fail"
                    ),
                    "behavior_status": "accepted",
                },
            )
        return Verdict(
            klass=VerdictClass.ANALYSIS_FAILED,
            reason=behavior,
            retryable=True,
            metadata={
                "accepted_observation": False,
                "accepted_repetition": False,
                "behavior_status": "incomplete",
            },
        )
