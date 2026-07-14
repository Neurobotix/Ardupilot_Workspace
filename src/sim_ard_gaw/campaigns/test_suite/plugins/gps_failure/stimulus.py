"""GPS fault stimulus metadata for the Phase-1 no-SITL plugin."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import math
from typing import Any

from ...core.models import AttemptContext, TestCase
from ...core.stimulus import StimulusAdapter
from . import defaults
from .config import GpsFailureConfig
from .runtime import GpsInjectionPlan, build_live_injection_plan


@dataclass
class GpsFailureStimulus(StimulusAdapter):
    config: GpsFailureConfig

    def apply(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        artifact = build_injection_artifact(case)
        ctx.stimulus_result = artifact
        defaults.write_json(ctx.attempt_dir / "gps_injection.json", artifact)
        return artifact

    def verify(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        if not self.config.launch_stack:
            return {"phase": "phase1_no_sitl", "live_readback_performed": False}
        return {
            "phase": "phase2_live_pending_monitor_verification",
            "live_readback_performed": False,
            "terminal_verification_pending": True,
        }


def build_injection_artifact(case: TestCase) -> dict[str, Any]:
    fault_recipe = case.parameters.get("fault_recipe")
    return {
        "case_id": case.case_id,
        "fault_type": case.parameters["fault_type"],
        "requested_payload": copy.deepcopy(case.parameters["injection_payload"]),
        "injection_schedule": copy.deepcopy(case.parameters.get("injection_schedule", [])),
        "fault_recipe": copy.deepcopy(fault_recipe),
        "payload_resolution": payload_resolution_status(fault_recipe),
        "reset_payload": copy.deepcopy(case.parameters["reset_payload"]),
        "trigger": copy.deepcopy(case.parameters["trigger"]),
        "readback_rules": copy.deepcopy(case.parameters["readback_rules"]),
        "readback_status_shape": {
            "injection": "pending_phase2",
            "reset": "pending_phase2",
            "missing_params_are_pre_injection_failure": True,
        },
        "live_plan_contract": {
            "preview_helper": (
                "sim_ard_gaw.campaigns.test_suite.plugins.gps_failure."
                "runtime.build_live_injection_plan"
            ),
            "authorized_helper": (
                "sim_ard_gaw.campaigns.test_suite.plugins.gps_failure."
                "runtime.build_authorized_injection_plan"
            ),
            "plan_only": True,
            "preview_is_not_executable": True,
            "execution_requires_validated_trigger": case.parameters["fault_type"]
            != "nominal",
            "requires_trigger_event": bool(
                fault_recipe and fault_recipe.get("requires_live_resolution")
            ),
            "live_readback_performed": False,
        },
    }


def build_live_plan_preview(
    case: TestCase,
    trigger_event: dict[str, Any],
) -> GpsInjectionPlan:
    """Build a live injection plan without executing MAVLink writes."""

    return build_live_injection_plan(case, trigger_event)


def payload_resolution_status(fault_recipe: dict[str, Any] | None) -> dict[str, Any]:
    if not fault_recipe or not fault_recipe.get("requires_live_resolution"):
        return {"requires_live_resolution": False, "reason": "concrete_payload_or_nominal"}
    return {
        "requires_live_resolution": True,
        "reason": "SIM_GPS1_GLTCH degree payload depends on trigger-time latitude/time",
        "frame": fault_recipe.get("frame"),
        "conversion": fault_recipe.get("conversion"),
        "preview_only_available_with_reference_latitude": True,
    }


def compare_readback(
    expected_payload: dict[str, float],
    actual_readback: dict[str, float],
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    for name, expected_raw in expected_payload.items():
        expected = _finite_float(f"{name} expected", expected_raw)
        if name not in actual_readback:
            mismatches.append({"param": name, "reason": "missing"})
            continue
        tolerance = _finite_float(
            f"{name} tolerance",
            defaults.PARAMETER_METADATA[name]["readback_tolerance"],
        )
        if tolerance < 0:
            raise ValueError(f"{name} tolerance must be >= 0")
        actual = _finite_float(f"{name} actual", actual_readback[name])
        if abs(actual - expected) > tolerance:
            mismatches.append(
                {
                    "param": name,
                    "expected": expected,
                    "actual": actual,
                    "tolerance": tolerance,
                }
            )
    return {"ok": not mismatches, "mismatches": mismatches}


def _finite_float(name: str, value: object) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be finite") from None
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed
