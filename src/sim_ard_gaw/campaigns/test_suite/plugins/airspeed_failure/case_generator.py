"""Case generator for the airspeed_failure plugin."""
from __future__ import annotations

from typing import Any, Iterable

from ...core.case_generator import CaseGenerator
from ...core.models import TestCase
from . import defaults
from .config import AirspeedFailureConfig, validate_bias_percent


class AirspeedFailureCaseGenerator(CaseGenerator):
    def __init__(self, config: AirspeedFailureConfig) -> None:
        self._config = config

    def iter_cases(self) -> Iterable[TestCase]:
        for case_id in defaults.FIXED_CASE_ORDER:
            yield self._case_from_payload(case_id, defaults.FIXED_CASE_PAYLOADS[case_id])
        for bias_percent in self._config.ratio_bias_percents:
            yield self._ratio_case(bias_percent)

    def get_case(self, case_id: str) -> TestCase:
        for case in self.iter_cases():
            if case.case_id == case_id:
                return case
        raise ValueError(f"Unknown airspeed_failure case id: {case_id}")

    def _case_from_payload(self, case_id: str, payload: dict[str, float]) -> TestCase:
        return TestCase(
            suite_name=defaults.SUITE_NAME,
            case_id=case_id,
            parameters=case_metadata(
                case_id=case_id,
                injection_payload=payload,
                ratio_recipe=None,
                calibration_required=False,
            ),
            scenario_name=defaults.SCENARIO_NAME,
            stimulus_name="sim_arspd_param_fault",
            mission_file=self._config.mission_file,
            acceptance_target_runs=self._config.runs_per_case,
            tags=("airspeed", "fault", "no_sitl_phase1"),
        )

    def _ratio_case(self, bias_percent: int) -> TestCase:
        validate_bias_percent(bias_percent, self._config.low_side_floor_percent)
        case_id = ratio_case_id(bias_percent)
        k = 1.0 + (bias_percent / 100.0)
        sim_ratio = self._config.vehicle_arspd_ratio / (k * k)
        recipe = {
            "bias_percent": bias_percent,
            "k": k,
            "formula": "SIM_ARSPD_RATIO = ARSPD_RATIO / k^2",
            "vehicle_arspd_ratio": self._config.vehicle_arspd_ratio,
            "vehicle_arspd_ratio_verified": self._config.vehicle_arspd_ratio_verified,
            "low_side_floor_percent": self._config.low_side_floor_percent,
        }
        return TestCase(
            suite_name=defaults.SUITE_NAME,
            case_id=case_id,
            parameters=case_metadata(
                case_id=case_id,
                injection_payload={"SIM_ARSPD_RATIO": sim_ratio},
                ratio_recipe=recipe,
                calibration_required=self._config.calibration_required,
            ),
            scenario_name=defaults.SCENARIO_NAME,
            stimulus_name="sim_arspd_ratio_bias",
            mission_file=self._config.mission_file,
            acceptance_target_runs=self._config.runs_per_case,
            tags=("airspeed", "ratio_bias", "calibration_required"),
        )


def ratio_case_id(bias_percent: int) -> str:
    prefix = "p" if bias_percent > 0 else "m"
    return f"ratio_bias_{prefix}{abs(int(bias_percent)):02d}"


def case_metadata(
    *,
    case_id: str,
    injection_payload: dict[str, float],
    ratio_recipe: dict[str, Any] | None,
    calibration_required: bool,
) -> dict[str, Any]:
    validate_payload(injection_payload)
    readback = readback_rules(injection_payload)
    return {
        "case_id": case_id,
        "injection_payload": dict(injection_payload),
        "reset_payload": dict(defaults.SOURCE_DEFAULTS),
        "parameter_metadata": defaults.PARAMETER_METADATA,
        "readback_rules": readback,
        "trigger": dict(defaults.INJECTION_TRIGGER),
        "acceptance_requirements": {
            "injection_readback_required": True,
            "reference_wind_verified_required": True,
            "min_post_injection_s": defaults.MIN_POST_INJECTION_S,
            "required_artifacts": list(defaults.REQUIRED_ATTEMPT_ARTIFACTS),
            "bad_flight_counts_if_observation_valid": True,
        },
        "ratio_recipe": ratio_recipe,
        "calibration_required": calibration_required,
        "schema_validation": schema_validation_payload(),
    }


def validate_payload(payload: dict[str, float]) -> None:
    unknown = [name for name in payload if name not in defaults.REQUIRED_SIM_ARSPD_PARAMS]
    if unknown:
        raise ValueError(f"Unknown SIM_ARSPD payload names: {unknown}")


def schema_validation_payload() -> dict[str, Any]:
    defaults.validate_required_param_names(defaults.REQUIRED_SIM_ARSPD_PARAMS)
    return defaults.parameter_schema()


def readback_rules(payload: dict[str, float]) -> dict[str, dict[str, float]]:
    names = set(payload) | set(defaults.SOURCE_DEFAULTS)
    return {
        name: {
            "expected": float(payload.get(name, defaults.SOURCE_DEFAULTS[name])),
            "tolerance": float(defaults.PARAMETER_METADATA[name]["readback_tolerance"]),
        }
        for name in sorted(names)
    }


def resolve_ratio_case_with_vehicle_ratio(
    case: TestCase,
    vehicle_arspd_ratio: float,
) -> None:
    """Rewrite a ratio-bias case payload from the live vehicle ARSPD_RATIO."""
    recipe = case.parameters.get("ratio_recipe")
    if recipe is None:
        return
    if vehicle_arspd_ratio <= 0:
        raise ValueError("Live ARSPD_RATIO must be > 0 for ratio-bias cases")

    bias_percent = int(recipe["bias_percent"])
    k = 1.0 + (bias_percent / 100.0)
    payload = {"SIM_ARSPD_RATIO": vehicle_arspd_ratio / (k * k)}
    live_recipe = dict(recipe)
    live_recipe.update(
        {
            "vehicle_arspd_ratio": vehicle_arspd_ratio,
            "vehicle_arspd_ratio_verified": True,
            "vehicle_arspd_ratio_source": "MAVLink PARAM_VALUE after clean SITL boot",
        }
    )
    case.parameters["injection_payload"] = payload
    case.parameters["readback_rules"] = readback_rules(payload)
    case.parameters["ratio_recipe"] = live_recipe
    case.parameters["calibration_required"] = False


def list_case_ids(config: AirspeedFailureConfig) -> list[str]:
    return [case.case_id for case in AirspeedFailureCaseGenerator(config).iter_cases()]
