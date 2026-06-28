"""Airspeed fault stimulus metadata and Phase-2 live interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.models import AttemptContext, TestCase
from ...core.stimulus import StimulusAdapter
from . import defaults
from .config import AirspeedFailureConfig


@dataclass
class AirspeedFailureStimulus(StimulusAdapter):
    config: AirspeedFailureConfig

    def apply(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        artifact = build_injection_artifact(case)
        ctx.stimulus_result = artifact
        defaults.write_json(ctx.attempt_dir / "airspeed_injection.json", artifact)
        return artifact

    def verify(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        if not self.config.launch_stack:
            return {"phase": "phase1_no_sitl", "live_readback_performed": False}
        return {
            "phase": "live_pending_monitor",
            "live_readback_performed": False,
            "terminal_verification_pending": True,
        }


def terminal_live_verification(
    *,
    injection_triggered: bool,
    injection_readback_ok: bool,
    reset_status: dict[str, Any],
    schedule_required: bool,
    schedule_complete: bool,
) -> dict[str, Any]:
    reset_compare = reset_status.get("compare")
    reset_state = str(reset_status.get("status") or "not_attempted")
    reset_readback_ok = bool(
        reset_state == "ok"
        and isinstance(reset_compare, dict)
        and reset_compare.get("ok") is True
    )
    return {
        "phase": "live_terminal",
        "terminal_verification_pending": False,
        "live_readback_performed": injection_triggered,
        "injection_readback_ok": injection_readback_ok,
        "reset_readback_performed": reset_state in {"ok", "failed"},
        "reset_readback_ok": reset_readback_ok,
        "schedule_required": schedule_required,
        "schedule_complete": schedule_complete if schedule_required else None,
    }


def build_injection_artifact(case: TestCase) -> dict[str, Any]:
    ramp_recipe = case.parameters.get("ramp_recipe")
    pulse_ladder_recipe = case.parameters.get("pulse_ladder_recipe")
    if ramp_recipe is not None:
        schedule_kind = "ramp"
    elif pulse_ladder_recipe is not None:
        schedule_kind = "pulse_ladder"
    elif case.parameters.get("injection_schedule"):
        schedule_kind = "bias_schedule"
    else:
        schedule_kind = None
    return {
        "case_id": case.case_id,
        "requested_payload": dict(case.parameters["injection_payload"]),
        "injection_schedule": list(case.parameters.get("injection_schedule", [])),
        "bias_schedule_kind": schedule_kind,
        "reset_payload": dict(case.parameters["reset_payload"]),
        "trigger": dict(case.parameters["trigger"]),
        "readback_rules": dict(case.parameters["readback_rules"]),
        "ratio_recipe": case.parameters.get("ratio_recipe"),
        "ramp_recipe": ramp_recipe,
        "pulse_ladder_recipe": pulse_ladder_recipe,
        "calibration_required": bool(case.parameters.get("calibration_required")),
        "readback_status_shape": {
            "injection": "pending_phase2",
            "reset": "pending_phase2",
            "missing_params_are_pre_injection_failure": True,
        },
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
