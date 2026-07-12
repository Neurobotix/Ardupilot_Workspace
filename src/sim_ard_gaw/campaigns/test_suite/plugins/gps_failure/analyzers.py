"""GPS behavior analysis helpers and Phase-1 classifier."""
from __future__ import annotations

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


BEHAVIOR_CLASSES = defaults.BEHAVIOR_CLASSES
ANALYSIS_STATE_CLASS = defaults.ANALYSIS_STATE_CLASSES[0]


def artifact_schema() -> dict[str, dict[str, Any]]:
    return {
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


def classify_observation(observation: dict[str, Any]) -> dict[str, Any]:
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
    if not _explicit_evidence_present(
        observation,
        primary="behavior_evidence",
        legacy="behavior_fields_present",
    ):
        return _result(ANALYSIS_STATE_CLASS, "missing_behavior_fields", False)

    if observation.get("loss_of_control") or observation.get("timeout"):
        return _result("loss_of_control", "valid_bad_behavior", True)
    if observation.get("mode_change") or observation.get("failsafe"):
        return _result("autopilot_contained", "valid_contained_behavior", True)
    if observation.get("reset_event"):
        return _result("reset_captured", "valid_reset_behavior", True)
    if observation.get("pos_test_ratio_rejected") or observation.get("reject_flags"):
        return _result("detected_rejected", "valid_detected_rejection", True)
    if (
        observation.get("fused", False)
        and observation.get("truth_belief_gap_growing", False)
        and not observation.get("failsafe", False)
    ):
        return _result("silent_drift", "valid_silent_drift", True)
    return _result("nominal", "valid_nominal", True)


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
