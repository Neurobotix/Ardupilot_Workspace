"""GPS fault stimulus metadata for the Phase-1 no-SITL plugin."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.models import AttemptContext, TestCase
from ...core.stimulus import StimulusAdapter
from . import defaults
from .config import GpsFailureConfig


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
            "phase": "live_not_implemented",
            "live_readback_performed": False,
            "terminal_verification_pending": True,
        }


def build_injection_artifact(case: TestCase) -> dict[str, Any]:
    fault_recipe = case.parameters.get("fault_recipe")
    return {
        "case_id": case.case_id,
        "fault_type": case.parameters["fault_type"],
        "requested_payload": dict(case.parameters["injection_payload"]),
        "injection_schedule": list(case.parameters.get("injection_schedule", [])),
        "fault_recipe": fault_recipe,
        "payload_resolution": payload_resolution_status(fault_recipe),
        "reset_payload": dict(case.parameters["reset_payload"]),
        "trigger": dict(case.parameters["trigger"]),
        "readback_rules": dict(case.parameters["readback_rules"]),
        "readback_status_shape": {
            "injection": "pending_phase2",
            "reset": "pending_phase2",
            "missing_params_are_pre_injection_failure": True,
        },
    }


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
    for name, expected in expected_payload.items():
        if name not in actual_readback:
            mismatches.append({"param": name, "reason": "missing"})
            continue
        tolerance = float(defaults.PARAMETER_METADATA[name]["readback_tolerance"])
        actual = float(actual_readback[name])
        if abs(actual - float(expected)) > tolerance:
            mismatches.append(
                {
                    "param": name,
                    "expected": float(expected),
                    "actual": actual,
                    "tolerance": tolerance,
                }
            )
    return {"ok": not mismatches, "mismatches": mismatches}
