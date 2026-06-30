"""Airspeed behavior analysis helpers and Phase-1 classifier."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

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
from .mechanism_gate import evaluate as evaluate_mechanism
from .mechanism_gate import extract_schedule_signals_from_bin


BEHAVIOR_CLASSES = (
    "nominal_completion",
    "degraded_completion",
    "autopilot_contained",
    "loss_of_control_or_timeout",
    "pre_injection_failure",
    "analysis_incomplete",
)


def artifact_schema() -> dict[str, dict[str, Any]]:
    return {
        "airspeed_behavior_summary.json": {
            "required_fields": [
                "behavior_class",
                "observation_quality_class",
                "accepted_observation",
                "reason",
            ],
        },
        "airspeed_signal_metrics.json": {
            "required_fields": [
                "pre_injection",
                "post_injection",
                "airspeed_minus_groundspeed",
                "fault_visible_deltas",
                "bias_schedule",
                "ramp",
                "pulse_ladder",
            ],
        },
        "airspeed_bias_ramp.json": {
            "required_fields": [
                "recipe",
                "schedule",
                "events",
                "completion",
                "readback",
                "phase_metrics",
            ],
            "case_specific": True,
        },
        "airspeed_bias_pulse_ladder.json": {
            "required_fields": [
                "recipe",
                "schedule",
                "events",
                "completion",
                "readback",
                "phase_metrics",
            ],
            "case_specific": True,
        },
        "mission_progress.json": {
            "required_fields": [
                "injection_seq",
                "max_seq_reached",
                "mission_complete",
                "auto_to_rtl_transition_seq",
                "planned_rtl",
                "timeout",
                "loss_of_progress",
            ],
        },
        "mode_timeline.json": {"required_fields": ["mode_timeline"]},
        "altitude_speed_envelope.json": {
            "required_fields": [
                "post_injection_min_alt_m",
                "altitude_loss_m",
                "airspeed_excursions",
                "groundspeed_excursions",
                "threshold_crossings",
            ],
        },
        "tecs_response.json": {
            "required_fields": ["available", "throttle", "pitch", "speed_height_response"],
            "optional": True,
        },
        "airspeed_mechanism_gate.json": {
            "required_fields": [
                "interpretable",
                "tier",
                "mechanism_status",
                "checks",
                "signals",
                "schedule_analysis",
                "wind_profile",
                "mission_profile_id",
                "speed_source",
            ],
            "case_specific": True,
        },
    }


def classify_observation(observation: dict[str, Any]) -> dict[str, Any]:
    if observation.get("launch_failed"):
        return _result("pre_injection_failure", "failed_launch", False)
    if not observation.get("injection_triggered", False):
        return _result("pre_injection_failure", "pre_injection", False)
    if not observation.get("injection_readback_ok", False):
        return _result("pre_injection_failure", "failed_readback", False)
    if not observation.get("wind_verified", False):
        return _result("analysis_incomplete", "unverified_wind", False)
    if not _window_met(observation):
        return _result("analysis_incomplete", "insufficient_post_injection_window", False)
    if not observation.get("required_artifacts_present", False):
        return _result("analysis_incomplete", "missing_required_artifacts", False)

    if observation.get("loss_of_control") or observation.get("timeout"):
        return _result("loss_of_control_or_timeout", "valid_bad_behavior", True)

    if observation.get("bias_schedule_required") and not observation.get(
        "bias_schedule_complete"
    ):
        schedule_kind = str(observation.get("bias_schedule_kind") or "bias_schedule")
        return _result("analysis_incomplete", f"{schedule_kind}_incomplete", False)

    auto_to_rtl_seq = observation.get("auto_to_rtl_transition_seq")
    planned_rtl_min_seq = int(
        observation.get("planned_rtl_min_seq", defaults.PLANNED_RTL_MIN_SEQ)
    )
    if auto_to_rtl_seq is not None and int(auto_to_rtl_seq) < planned_rtl_min_seq:
        return _result("autopilot_contained", "fault_triggered_early_rtl", True)

    if not observation.get("mission_complete", False):
        return _result("autopilot_contained", "valid_no_clean_completion", True)

    altitude_loss = float(observation.get("altitude_loss_m", 0.0) or 0.0)
    if altitude_loss > defaults.ALT_LOSS_MAX_M or observation.get("degraded_metrics"):
        return _result(
            "degraded_completion",
            "valid_degraded_completion",
            True,
            reason=_measured_reason("valid_degraded_completion", observation),
        )
    return _result(
        "nominal_completion",
        "valid_nominal_completion",
        True,
        reason=_measured_reason("valid_nominal_completion", observation),
    )


def _window_met(observation: dict[str, Any]) -> bool:
    if observation.get("terminal_state_reached"):
        return True
    return float(observation.get("post_injection_s", 0.0) or 0.0) >= defaults.MIN_POST_INJECTION_S


def _result(
    behavior_class: str,
    observation_quality_class: str,
    accepted_observation: bool,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "behavior_class": behavior_class,
        "observation_quality_class": observation_quality_class,
        "accepted_observation": accepted_observation,
        "reason": reason or observation_quality_class,
    }


def _measured_reason(prefix: str, observation: dict[str, Any]) -> str:
    metrics = observation.get("signal_metrics") if isinstance(observation, dict) else None
    post = metrics.get("post_injection", {}) if isinstance(metrics, dict) else {}
    airspeed = post.get("airspeed_mps", {}) if isinstance(post, dict) else {}
    groundspeed = post.get("groundspeed_mps", {}) if isinstance(post, dict) else {}
    values = {
        "post_arsp_mean_mps": airspeed.get("mean"),
        "post_gps_mean_mps": groundspeed.get("mean"),
        "altitude_loss_m": observation.get("altitude_loss_m"),
        "auto_to_rtl_seq": observation.get("auto_to_rtl_transition_seq"),
        "max_seq": observation.get("max_seq_reached"),
    }
    parts = []
    for key, value in values.items():
        if isinstance(value, float):
            parts.append(f"{key}={value:.2f}")
        elif value is not None:
            parts.append(f"{key}={value}")
    return f"{prefix}: " + ", ".join(parts) if parts else prefix


@dataclass
class AirspeedFailureAnalyzer(Analyzer):
    name: str = "airspeed_failure_phase1_schema"

    def analyze(self, case: TestCase, ctx: AttemptContext) -> AnalysisResult:
        observation = dict(ctx.extra.get("airspeed_observation") or {})
        if not observation:
            observation = {
                "injection_triggered": False,
                "required_artifacts_present": False,
            }
        summary = classify_observation(observation)
        if case.parameters.get("mechanism_gate_required"):
            mechanism = _run_mechanism_gate(case, ctx)
            if not mechanism.get("interpretable"):
                summary = dict(summary)
                summary["accepted_observation"] = False
                summary["observation_quality_class"] = mechanism.get(
                    "mechanism_status", "mechanism_unverified"
                )
                summary["reason"] = str(summary["observation_quality_class"])
            summary["mechanism_status"] = mechanism.get("mechanism_status")
            summary_path = ctx.attempt_dir / "airspeed_behavior_summary.json"
            defaults.write_json(summary_path, summary)
            ctx.artifacts["airspeed_behavior_summary"] = summary_path
            plugin_fields = ctx.extra.get("plugin_manifest_fields")
            if isinstance(plugin_fields, dict):
                plugin_fields.update(
                    {
                        "accepted_observation": summary["accepted_observation"],
                        "observation_quality_class": summary[
                            "observation_quality_class"
                        ],
                        "mechanism_status": mechanism.get("mechanism_status"),
                    }
                )
                plugin_fields.setdefault("artifacts", {})[
                    "airspeed_mechanism_gate"
                ] = str(ctx.artifacts.get("airspeed_mechanism_gate", ""))
        return AnalysisResult(
            analyzer_name=self.name,
            ok=bool(summary["accepted_observation"]),
            summary=summary,
        )


def _run_mechanism_gate(case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
    tier = str(case.parameters.get("mechanism_tier") or "protected")
    expected_wind_max = float(case.parameters.get("expected_ahrs_wind_max") or 0.0)
    vehicle = ctx.extra.get("vehicle_airspeed_params")
    intended_eas = 15.0
    if case.parameters.get("speed_source") == "airspeed_cruise" and isinstance(vehicle, dict):
        intended_eas = float(vehicle.get("AIRSPEED_CRUISE") or intended_eas)
    bin_path = _latest_attempt_bin(ctx)
    if bin_path is None:
        result: dict[str, Any] = {
            "interpretable": False,
            "tier": tier,
            "mechanism_status": "mechanism_unverified",
            "checks": [{"name": "bin_present", "ok": False, "detail": "attempt BIN not found"}],
            "signals": None,
            "schedule_analysis": {
                "schedule_kind": "unknown",
                "window_anchor": "BIN PARM SIM_ARSPD_RATIO transitions",
                "matching_errors": ["attempt BIN not found"],
                "matched_window_count": 0,
                "fault_window_count": 0,
                "first_ahrs_source_rejection_bias_percent": None,
                "first_arsp_parameter_disable_bias_percent": None,
                "windows": [],
            },
        }
    else:
        injection = _injection_artifact(ctx)
        events = injection.get("injection_events")
        schedule_kind = str(injection.get("bias_schedule_kind") or "unknown")
        if not isinstance(events, list):
            events = []
        result = analyze_mechanism_bin(
            str(bin_path),
            injection_events=[event for event in events if isinstance(event, dict)],
            expected_cruise=intended_eas,
            tier=tier,
            expected_wind_max=expected_wind_max,
            schedule_kind=schedule_kind,
        )
        result["bin_path"] = str(bin_path)
    result.update(
        {
            "case_id": case.case_id,
            "wind_profile": case.parameters.get("wind_profile"),
            "mission_profile_id": case.parameters.get("mission_profile_id"),
            "speed_source": case.parameters.get("speed_source"),
            "intended_airspeed_eas_mps": intended_eas,
        }
    )
    path = ctx.attempt_dir / "airspeed_mechanism_gate.json"
    defaults.write_json(path, result)
    ctx.artifacts["airspeed_mechanism_gate"] = path
    return result


def analyze_mechanism_bin(
    bin_path: str,
    *,
    injection_events: Sequence[dict[str, Any]],
    expected_cruise: float,
    tier: str,
    expected_wind_max: float,
    schedule_kind: str,
    reader: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    windows, matching_errors = extract_schedule_signals_from_bin(
        bin_path,
        expected_cruise=expected_cruise,
        injection_events=injection_events,
        reader=reader,
    )
    fault_windows = [window for window in windows if window.phase == "fault_observe"]
    evaluated = [
        (window, evaluate_mechanism(window.signals, tier=tier, expected_wind_max=expected_wind_max))
        for window in fault_windows
    ]
    interpretable = [item for item in evaluated if item[1].interpretable]
    # A verified pre-rejection window must not be erased by a later rejected
    # window.  Ramps accumulate history without resets, so a high-bias window
    # can cross into AHRS source rejection after an earlier window already
    # verified the clamp/tracking.  Prefer the last interpretable window for
    # every schedule kind; only fall back to the last evaluated window when no
    # window was interpretable at all.
    representative = interpretable[-1] if interpretable else None
    if representative is None and evaluated:
        representative = evaluated[-1]

    if representative is None:
        result: dict[str, Any] = {
            "interpretable": False,
            "tier": tier,
            "mechanism_status": "mechanism_unverified",
            "observation_quality_class": "mechanism_unverified",
            "checks": [
                {
                    "name": "schedule_window_present",
                    "ok": False,
                    "detail": "no PARM-anchored fault window was extracted",
                }
            ],
            "signals": None,
        }
    else:
        result = representative[1].as_dict()

    if matching_errors:
        result["interpretable"] = False
        result["mechanism_status"] = "mechanism_unverified"
        result["observation_quality_class"] = "mechanism_unverified"
        result.setdefault("checks", []).append(
            {
                "name": "schedule_window_matching",
                "ok": False,
                "detail": "; ".join(matching_errors),
            }
        )

    source_rejection = next(
        (
            window.bias_percent
            for window, _evaluation in evaluated
            if window.signals.sensor_source_rejection_intervals
        ),
        None,
    )
    parameter_disable = next(
        (
            window.bias_percent
            for window, _evaluation in evaluated
            if window.signals.sensor_disable_intervals
        ),
        None,
    )
    result["schedule_analysis"] = {
        "schedule_kind": schedule_kind,
        "window_anchor": "BIN PARM SIM_ARSPD_RATIO transitions",
        "initial_baseline_omitted": True,
        "matching_errors": matching_errors,
        "matched_window_count": len(windows),
        "fault_window_count": len(fault_windows),
        "first_ahrs_source_rejection_bias_percent": source_rejection,
        "first_arsp_parameter_disable_bias_percent": parameter_disable,
        "windows": [
            {
                **window.as_dict(),
                "evaluation": evaluation.as_dict(),
            }
            for window, evaluation in evaluated
        ],
    }
    return result


def _latest_attempt_bin(ctx: AttemptContext) -> Path | None:
    sitl_dir = ctx.extra.get("sitl_log_dir")
    if not isinstance(sitl_dir, Path):
        return None
    before = set(ctx.extra.get("before_bin_names") or set())
    candidates = [
        path for path in (sitl_dir / "logs").glob("*.BIN") if path.name not in before
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _injection_artifact(ctx: AttemptContext) -> dict[str, Any]:
    path = ctx.artifacts.get("airspeed_injection")
    if path is None or not path.exists():
        return {}
    artifact = defaults.read_json(path)
    return artifact if isinstance(artifact, dict) else {}


class AirspeedFailureVerdictPolicy(VerdictPolicy):
    def classify(
        self,
        case: TestCase,
        monitor_result: MonitorResult,
        analysis_results: Sequence[AnalysisResult],
    ) -> Verdict:
        summary = _first_summary(analysis_results)
        accepted = bool(summary.get("accepted_observation"))
        behavior_class = str(summary.get("behavior_class") or "analysis_incomplete")
        if accepted:
            klass = VerdictClass.SUCCESS
            retryable = False
        elif behavior_class == "analysis_incomplete":
            klass = VerdictClass.ANALYSIS_FAILED
            retryable = True
        else:
            klass = VerdictClass.FAILED_RETRYABLE
            retryable = True
        return Verdict(
            klass=klass,
            reason=behavior_class,
            retryable=retryable,
            requires_analysis=True,
            metadata=summary,
        )


def _first_summary(analysis_results: Sequence[AnalysisResult]) -> dict[str, Any]:
    for result in analysis_results:
        if result.summary:
            return dict(result.summary)
    return {
        "behavior_class": "analysis_incomplete",
        "accepted_observation": False,
        "reason": "missing_analysis",
    }
