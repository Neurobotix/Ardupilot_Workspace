"""GPS behavior analysis helpers and Phase-1 classifier."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

from ...core.analysis import Analyzer
from ...core.models import (
    AnalysisResult,
    AttemptContext,
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
        return _result("pre_injection_failure", "failed_readback", False)
    if not _window_met(observation):
        return _result(ANALYSIS_STATE_CLASS, "insufficient_post_injection_window", False)
    if not observation.get("required_artifacts_present", False):
        return _result(ANALYSIS_STATE_CLASS, "missing_required_artifacts", False)
    if not _explicit_evidence_present(
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
    value = observation.get(field)
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
    accepted = bool(
        result.get("accepted_evidence")
        or result.get("mechanism_evidence_accepted")
    )
    normalized.setdefault("mechanism_evidence", accepted)
    state = result.get("mechanism_state") or result.get("mechanism_class")
    if accepted and state == "reset_detected":
        normalized.setdefault("reset_event", True)
    elif accepted and state == "rejected_above_gate":
        normalized.setdefault("pos_test_ratio_rejected", True)
    elif accepted and state == "fused_below_gate":
        normalized.setdefault("fused", True)
    return normalized


def _mechanism_result_dict(observation: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("mechanism_gate_result", "mechanism_result"):
        value = observation.get(key)
        if isinstance(value, MechanismGateResult):
            return value.as_dict()
        if isinstance(value, dict):
            return value
    return None


def _window_met(observation: dict[str, Any]) -> bool:
    return float(observation.get("post_injection_s", 0.0) or 0.0) >= defaults.MIN_POST_INJECTION_S


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
    name: str = "gps_failure_phase1_schema"

    def analyze(self, case: TestCase, ctx: AttemptContext) -> AnalysisResult:
        observation = dict(ctx.extra.get("gps_observation") or {})
        if not observation:
            observation = {
                "injection_triggered": False,
                "required_artifacts_present": False,
            }
        summary = classify_observation(observation)
        return AnalysisResult(
            analyzer_name=self.name,
            ok=bool(summary["accepted_observation"]),
            summary=summary,
        )


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
