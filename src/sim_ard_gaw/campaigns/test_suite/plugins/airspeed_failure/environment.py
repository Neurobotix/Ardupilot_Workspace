"""Environment adapter for airspeed_failure.

Phase 1 intentionally does not launch SITL or Gazebo. The live launch path is a
Phase 2 body and fails closed until smoke work implements it.
"""
from __future__ import annotations

from . import defaults
from .config import AirspeedFailureConfig
from ...core.environment import EnvironmentAdapter
from ...core.models import AttemptContext, TestCase


class AirspeedFailureEnvironment(EnvironmentAdapter):
    def __init__(self, config: AirspeedFailureConfig) -> None:
        self._config = config

    def prepare_case(self, case: TestCase) -> None:
        return None

    def launch(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return None
        raise NotImplementedError("airspeed_failure live launch is Phase 2 work")

    def assert_ready(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return None
        raise NotImplementedError("airspeed_failure MAVLink readiness is Phase 2 work")

    def cleanup(self, case: TestCase, ctx: AttemptContext) -> None:
        return None


def reference_wind_artifact_schema() -> dict[str, object]:
    return {
        "artifact": "reference_wind.json",
        "required_fields": [
            "requested_mps",
            "frame",
            "world_name",
            "topic",
            "wind_info_topic",
            "publication_timing",
            "method",
            "echo_parsed_mps",
            "echo_tolerance_mps",
            "verified",
            "realized_arsp_minus_gps_eastbound_mps",
            "sign_confirmation",
            "note",
        ],
    }


def build_reference_wind_artifact(*, verified: bool = False) -> dict[str, object]:
    return {
        "requested_mps": dict(defaults.REFERENCE_WIND_MPS),
        "frame": "gazebo_world_enu",
        "frame_note": defaults.WIND_FRAME_NOTE,
        "world_name": defaults.WORLD_NAME,
        "topic": defaults.WIND_TOPIC,
        "wind_info_topic": defaults.WIND_INFO_TOPIC,
        "publication_timing": "before_mission_start",
        "method": "gz_topic_publish",
        "echo_tolerance_mps": defaults.WIND_ECHO_TOLERANCE_MPS,
        "echo_parsed_mps": None,
        "verified": verified,
        "realized_arsp_minus_gps_eastbound_mps": None,
        "sign_confirmation": {
            "status": "pending_phase2",
            "expected_eastbound_arsp_minus_gps_mps": 5.0,
        },
        "note": (
            "Phase 1 schema only; Phase 2 must confirm frame/sign against "
            "realized ARSP-GPS on healthy_reference."
        ),
        "phase": "phase1_schema" if not verified else "phase2_live",
    }
