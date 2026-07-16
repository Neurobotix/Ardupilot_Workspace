"""Case generator for the gps_failure plugin."""
from __future__ import annotations

import copy
import math
from typing import Any, Iterable

from ...core.case_generator import CaseGenerator
from ...core.models import TestCase
from . import defaults, glitch
from .config import (
    GpsFailureConfig,
    denial_duration_token,
    drift_rate_token,
    glitch_magnitude_token,
)


class GpsFailureCaseGenerator(CaseGenerator):
    def __init__(self, config: GpsFailureConfig) -> None:
        self._config = config

    def iter_cases(self) -> Iterable[TestCase]:
        yield self._nominal_case()
        for rate_mps in self._config.drift_rates_mps:
            yield self._slow_drift_case(rate_mps)
        yield self._slow_drift_accumulation_case()
        for magnitude_m in self._config.glitch_magnitudes_m:
            yield self._step_glitch_case(magnitude_m)
        for duration_s in self._config.denial_durations_s:
            yield self._hard_denial_case(duration_s)
        for repeat_index in range(1, self._config.jamming_repeats + 1):
            yield self._jamming_case(repeat_index)

    def get_case(self, case_id: str) -> TestCase:
        for case in self.iter_cases():
            if case.case_id == case_id:
                return case
        raise ValueError(f"Unknown gps_failure case id: {case_id}")

    def _nominal_case(self) -> TestCase:
        return self._case(
            case_id="nominal",
            fault_type="nominal",
            stimulus_name="gps_nominal_control",
            injection_payload={},
            tags=("gps", "nominal", "no_sitl_phase1"),
        )

    def _slow_drift_case(self, rate_mps: float) -> TestCase:
        example_elapsed_s = defaults.MIN_POST_INJECTION_S
        return self._case(
            case_id=f"slow_drift_{rate_token(rate_mps)}_mps",
            fault_type="slow_drift",
            stimulus_name="sim_gps_glitch_slow_drift",
            injection_payload={},
            fault_recipe={
                **glitch.glitch_recipe_metadata(requires_live_resolution=True),
                "fault_type": "slow_drift",
                "independent_variable": "drift_rate_mps",
                "drift_rate_mps": float(rate_mps),
                "axis": "east",
                "glitch_params": ["SIM_GPS1_GLTCH_X", "SIM_GPS1_GLTCH_Y"],
                "formula": "offset_m = drift_rate_mps * elapsed_since_trigger_s",
                "example_elapsed_since_trigger_s": float(example_elapsed_s),
                "example_offset_m": float(rate_mps) * float(example_elapsed_s),
                "example_resolved_payload": glitch.slow_drift_payload(
                    float(rate_mps),
                    example_elapsed_s,
                    glitch.EXAMPLE_REFERENCE_LATITUDE_DEG,
                    axis="east",
                ),
                "reset_policy": "fresh flight per rate; no in-flight reset schedule",
            },
            tags=("gps", "slow_drift", "no_sitl_phase1"),
        )

    def _slow_drift_accumulation_case(self) -> TestCase:
        return self._case(
            case_id="slow_drift_accumulation_ramp",
            fault_type="slow_drift",
            stimulus_name="sim_gps_glitch_slow_drift_accumulation",
            injection_payload={},
            fault_recipe={
                **glitch.glitch_recipe_metadata(requires_live_resolution=True),
                "fault_type": "slow_drift",
                "independent_variable": "continuous_accumulation",
                "axis": "east",
                "glitch_params": ["SIM_GPS1_GLTCH_X", "SIM_GPS1_GLTCH_Y"],
                "drift_rates_mps": [float(rate) for rate in self._config.drift_rates_mps],
                "formula": "offset_m = selected_drift_rate_mps * elapsed_since_trigger_s",
                "schedule_status": "live schedule deferred; no-SITL recipe only",
                "continuous_ramp": True,
                "in_flight_reset": False,
                "fresh_flight_required": True,
                "measurement_role": "accumulation/endurance, not independent knee points",
                "reset_policy": "continuous ramp, no reset inside the flight",
            },
            tags=("gps", "slow_drift", "accumulation", "no_sitl_phase1"),
        )

    def _step_glitch_case(self, magnitude_m: float) -> TestCase:
        return self._case(
            case_id=f"step_glitch_{glitch_magnitude_token(float(magnitude_m))}m",
            fault_type="step_glitch",
            stimulus_name="sim_gps_glitch_step",
            injection_payload={},
            fault_recipe={
                **glitch.glitch_recipe_metadata(requires_live_resolution=True),
                "fault_type": "step_glitch",
                "independent_variable": "offset_magnitude_m",
                "offset_magnitude_m": float(magnitude_m),
                "axis": "east",
                "glitch_params": ["SIM_GPS1_GLTCH_X", "SIM_GPS1_GLTCH_Y"],
                "example_resolved_payload": glitch.step_glitch_payload(
                    float(magnitude_m),
                    glitch.EXAMPLE_REFERENCE_LATITUDE_DEG,
                    axis="east",
                ),
                "reset_policy": "fresh flight per magnitude; reset params only during cleanup",
            },
            tags=("gps", "step_glitch", "no_sitl_phase1"),
        )

    def _hard_denial_case(self, duration_s: float) -> TestCase:
        schedule = [
            {
                "event_index": 1,
                "phase": "fault_observe",
                "elapsed_since_trigger_s": 0.0,
                "observe_s": float(duration_s),
                "payload": {"SIM_GPS1_ENABLE": 0.0},
            },
            {
                "event_index": 2,
                "phase": "restore",
                "elapsed_since_trigger_s": float(duration_s),
                "observe_s": 0.0,
                "payload": {"SIM_GPS1_ENABLE": 1.0},
            },
        ]
        return self._case(
            case_id=f"hard_denial_{denial_duration_token(float(duration_s))}s",
            fault_type="hard_denial",
            stimulus_name="sim_gps_hard_denial",
            injection_payload={"SIM_GPS1_ENABLE": 0.0},
            injection_schedule=schedule,
            fault_recipe={
                "fault_type": "hard_denial",
                "independent_variable": "denial_duration_s",
                "denial_duration_s": float(duration_s),
                "restore_payload": {"SIM_GPS1_ENABLE": 1.0},
            },
            tags=("gps", "hard_denial", "no_sitl_phase1"),
        )

    def _jamming_case(self, repeat_index: int) -> TestCase:
        return self._case(
            case_id=f"jamming_repeat_{repeat_index:02d}",
            fault_type="jamming",
            stimulus_name="sim_gps_jamming",
            injection_payload={"SIM_GPS1_JAM": 1.0},
            fault_recipe={
                "fault_type": "jamming",
                "independent_variable": "repeat_index",
                "repeat_index": int(repeat_index),
                "jam_duration_s": float(self._config.jamming_duration_s),
                "binary_fault": True,
                "stochastic": True,
            },
            tags=("gps", "jamming", "repeat", "no_sitl_phase1"),
        )

    def _case(
        self,
        *,
        case_id: str,
        fault_type: str,
        stimulus_name: str,
        injection_payload: dict[str, float],
        tags: tuple[str, ...],
        fault_recipe: dict[str, Any] | None = None,
        injection_schedule: list[dict[str, Any]] | None = None,
    ) -> TestCase:
        return TestCase(
            suite_name=defaults.SUITE_NAME,
            case_id=case_id,
            parameters=case_metadata(
                case_id=case_id,
                fault_type=fault_type,
                injection_payload=injection_payload,
                fault_recipe=fault_recipe,
                injection_schedule=injection_schedule,
                min_post_injection_s=(
                    self._config.nominal_smoke_observation_s
                    if fault_type == "nominal"
                    else defaults.MIN_POST_INJECTION_S
                ),
            ),
            scenario_name=defaults.SCENARIO_NAME,
            stimulus_name=stimulus_name,
            mission_file=self._config.mission_file,
            acceptance_target_runs=self._config.runs_per_case,
            tags=tags,
        )


def rate_token(rate_mps: float) -> str:
    return drift_rate_token(_finite_float("rate_mps", rate_mps))


def case_metadata(
    *,
    case_id: str,
    fault_type: str,
    injection_payload: dict[str, float],
    fault_recipe: dict[str, Any] | None,
    injection_schedule: list[dict[str, Any]] | None,
    min_post_injection_s: float = defaults.MIN_POST_INJECTION_S,
) -> dict[str, Any]:
    validate_payload(injection_payload)
    schedule = copy.deepcopy(injection_schedule or [])
    for step in schedule:
        payload = step.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("injection_schedule step missing payload")
        validate_payload(payload)
    return {
        "case_id": case_id,
        "fault_type": fault_type,
        "injection_payload": copy.deepcopy(injection_payload),
        "injection_schedule": schedule,
        "fault_recipe": copy.deepcopy(fault_recipe),
        "reset_payload": copy.deepcopy(defaults.SOURCE_DEFAULTS),
        "parameter_metadata": copy.deepcopy(defaults.PARAMETER_METADATA),
        "readback_rules": readback_rules(injection_payload),
        "trigger": copy.deepcopy(defaults.INJECTION_TRIGGER),
        "acceptance_requirements": {
            "injection_readback_required": fault_type != "nominal",
            "measurement_validity_only": True,
            "min_post_injection_s": _finite_float(
                "min_post_injection_s",
                min_post_injection_s,
            ),
            "required_artifacts": list(defaults.REQUIRED_ATTEMPT_ARTIFACTS),
            "bad_flight_counts_if_observation_valid": True,
        },
        "classification_model": {
            "accepted_observation": "measurement_validity_only",
            "behavior_class": "characterize_not_gate",
            "mechanism_tier": "posTestRatio crossing 1.0",
            "behavior_tier": "truth_vs_belief_gap plus mode/failsafe/control envelope",
        },
        "schema_validation": schema_validation_payload(),
    }


def validate_payload(payload: dict[str, float]) -> None:
    unknown = [name for name in payload if name not in defaults.REQUIRED_SIM_GPS_PARAMS]
    if unknown:
        raise ValueError(f"Unknown SIM_GPS payload names: {unknown}")
    for name, value in payload.items():
        _finite_float(name, value)


def schema_validation_payload() -> dict[str, Any]:
    defaults.validate_required_param_names(defaults.REQUIRED_SIM_GPS_PARAMS)
    return defaults.parameter_schema()


def readback_rules(payload: dict[str, float]) -> dict[str, dict[str, float]]:
    names = set(payload) | set(defaults.SOURCE_DEFAULTS)
    rules: dict[str, dict[str, float]] = {}
    for name in sorted(names):
        expected = _finite_float(name, payload.get(name, defaults.SOURCE_DEFAULTS[name]))
        tolerance = _finite_float(
            f"{name} readback_tolerance",
            defaults.PARAMETER_METADATA[name]["readback_tolerance"],
        )
        if tolerance < 0:
            raise ValueError(f"{name} readback_tolerance must be >= 0")
        rules[name] = {"expected": expected, "tolerance": tolerance}
    return rules


def _finite_float(name: str, value: object) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be finite") from None
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed
