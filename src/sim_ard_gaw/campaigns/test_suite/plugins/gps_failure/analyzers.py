"""GPS behavior analysis helpers and Phase-1 classifier."""
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
                "observation_quality_class",
                "accepted_observation",
                "reason",
                "terminal_state_reached",
                "mission_complete",
                "stop_reason",
                "max_seq_reached",
                "auto_to_rtl_transition_seq",
            ],
        },
        "source_contract.json": {
            "required_fields": [
                "ok",
                "validated_proxy",
                "exact_aiding_proof",
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
                "post_injection_min_alt_m",
                "altitude_loss_m",
                "attitude_excursions",
                "threshold_crossings",
                "unexpected_disarm",
                "samples_complete",
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
    return [field for field in schema["required_fields"] if field not in artifact]


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
    if not _is_nominal_smoke_observation(observation) and not _explicit_evidence_present(
        observation,
        primary="mechanism_evidence",
        legacy="mechanism_fields_present",
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
    if _is_nominal_smoke_observation(observation) and observation.get(
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


def _is_nominal_smoke_observation(observation: dict[str, Any]) -> bool:
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


def _explicit_evidence_present(
    observation: dict[str, Any],
    *,
    primary: str,
    legacy: str,
) -> bool:
    if primary in observation:
        return observation.get(primary) is True
    if legacy in observation:
        return observation.get(legacy) is True
    return False


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
            classify_observation(observation), observation
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

    from .bin_analysis import analyze_attempt_bin
    from .environment import identify_attempt_bin

    metrics_path = ctx.attempt_dir / "ekf_innovation_metrics.json"
    truth_path = ctx.attempt_dir / "truth_vs_belief.json"
    raw_metrics = defaults.read_json(metrics_path)
    raw_truth = defaults.read_json(truth_path)
    metrics = raw_metrics if isinstance(raw_metrics, dict) else {}
    truth = raw_truth if isinstance(raw_truth, dict) else {}
    source_bin_path = identify_attempt_bin(ctx)
    if source_bin_path is None:
        analysis: dict[str, Any] = {
            "ok": False,
            "reason": "single_current_attempt_bin_not_available_after_cleanup",
        }
    else:
        execution = ctx.extra.get("gps_injection_execution")
        plan = execution.get("plan") if isinstance(execution, dict) else None
        injection_payload = (
            plan.get("injection_payload") if isinstance(plan, dict) else None
        )
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
            )
        except Exception as exc:
            analysis = {
                "ok": False,
                "bin_path": str(analysis_bin_path),
                "reason": f"{type(exc).__name__}: {exc}",
            }

    ctx.extra["gps_bin_analysis"] = analysis
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
        "bin_analysis_ok": analysis_ok,
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


def _summary_with_terminal_context(
    summary: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    enriched = dict(summary)
    for field in (
        "terminal_state_reached",
        "mission_complete",
        "stop_reason",
        "max_seq_reached",
        "auto_to_rtl_transition_seq",
    ):
        enriched[field] = observation.get(field)
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
    if workflow_complete:
        ctx.extra["attempt_status"] = AttemptStatus.SUCCESS
    fields.update({
        "behavior_class": summary["behavior_class"],
        "observation_quality_class": summary["observation_quality_class"],
        "accepted_observation": summary["accepted_observation"],
        "workflow_status": "complete" if workflow_complete else "incomplete",
        "analysis_status": "complete",
        "terminal_state_reached": observation.get("terminal_state_reached"),
        "mission_complete": observation.get("mission_complete"),
        "stop_reason": observation.get("stop_reason"),
        "max_seq_reached": observation.get("max_seq_reached"),
        "auto_to_rtl_transition_seq": observation.get(
            "auto_to_rtl_transition_seq"
        ),
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
        "live_fallback_source": {
            "truth_source": fallback.get("truth_source"),
            "belief_source": fallback.get("belief_source"),
        },
        "source": truth_belief.get("source", "SIM/POS"),
    }


class GpsFailureVerdictPolicy(VerdictPolicy):
    def classify(
        self,
        case: TestCase,
        monitor_result: MonitorResult,
        analysis_results: Sequence[AnalysisResult],
    ) -> Verdict:
        accepted = bool(analysis_results) and all(
            result.ok and result.summary.get("accepted_observation") is True
            for result in analysis_results
        )
        behavior = next(
            (
                str(result.summary.get("behavior_class"))
                for result in analysis_results
                if result.summary.get("behavior_class")
            ),
            monitor_result.reason,
        )
        if accepted:
            return Verdict(
                klass=VerdictClass.SUCCESS,
                reason=behavior,
                retryable=False,
                metadata={"accepted_observation": True},
            )
        return Verdict(
            klass=VerdictClass.ANALYSIS_FAILED,
            reason=behavior,
            retryable=True,
            metadata={"accepted_observation": False},
        )
