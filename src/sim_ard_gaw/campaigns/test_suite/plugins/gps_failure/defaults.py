"""Defaults for the gps_failure test-suite plugin."""
from __future__ import annotations

import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SRC_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = Path(os.environ.get("ARDUPILOT_WORKSPACE", SRC_ROOT.parent)).resolve()
ASSETS_ROOT = WORKSPACE_ROOT / "assets"
CONFIG_ROOT = WORKSPACE_ROOT / "config"
VAR_ROOT = WORKSPACE_ROOT / "var"
VENV_PYTHON = WORKSPACE_ROOT / "env" / "bin" / "python3"

SUITE_NAME = "gps_failure"
SCENARIO_NAME = "gps_failure_behavior"
LANE_NAME = "GPS Failure Behavior"
CAMPAIGN_ROOT_PREFIX = "gps_failure_behavior"
DEFAULT_CAMPAIGN_ROOT_PARENT = VAR_ROOT / "runs"

MISSION_FILE = ASSETS_ROOT / "missions" / "gps_failure_behavior_mission.waypoints"
SITL_TARGET = "plane-cte"
GAZEBO_TARGET = "gazebo-plane-cte"
PLANE_BASE_PARAM_FILE = CONFIG_ROOT / "vehicles" / "plane_base.parm"
PLANE_GPS_PARAM_FILE = CONFIG_ROOT / "overlays" / "plane_gps.parm"

INJECTION_TRIGGER = {
    "source": "MISSION_CURRENT",
    "seq": 4,
    "edge": "first seq==4 after front-half progress",
    "front_half_required_sequences": [1, 2, 3],
    "mode": "AUTO",
    "armed_required": True,
    "late_or_missed_result": "pre_injection_failure",
}

SOURCE_DEFAULTS = {
    "SIM_GPS1_ENABLE": 1.0,
    "SIM_GPS1_GLTCH_X": 0.0,
    "SIM_GPS1_GLTCH_Y": 0.0,
    "SIM_GPS1_GLTCH_Z": 0.0,
    "SIM_GPS1_JAM": 0.0,
}
REQUIRED_SIM_GPS_PARAMS = tuple(SOURCE_DEFAULTS.keys())

PARAMETER_METADATA = {
    "SIM_GPS1_ENABLE": {
        "units": "enum 0/1",
        "semantics": "GPS instance enable. hard_denial sets this to 0, then restores 1.",
        "readback_tolerance": 0.0,
    },
    "SIM_GPS1_GLTCH_X": {
        "units": "degrees latitude offset",
        "semantics": (
            "Latitude glitch offset. slow_drift and step_glitch convert north metres "
            "to degrees explicitly with the gps_failure.glitch helpers."
        ),
        "readback_tolerance": 1e-9,
    },
    "SIM_GPS1_GLTCH_Y": {
        "units": "degrees longitude offset",
        "semantics": (
            "Longitude glitch offset. slow_drift and step_glitch convert east metres "
            "to degrees explicitly at the vehicle/reference latitude."
        ),
        "readback_tolerance": 1e-9,
    },
    "SIM_GPS1_GLTCH_Z": {
        "units": "metres altitude offset",
        "semantics": "Altitude glitch reset/default guard; not an active v1 fault axis.",
        "readback_tolerance": 1e-6,
    },
    "SIM_GPS1_JAM": {
        "units": "enum 0/1",
        "semantics": "RF jamming model enable. jamming cases set this to 1.",
        "readback_tolerance": 0.0,
    },
}

FAULT_TYPES = ("slow_drift", "step_glitch", "hard_denial", "jamming")
BEHAVIOR_CLASSES = (
    "nominal",
    "silent_drift",
    "detected_rejected",
    "reset_captured",
    "autopilot_contained",
    "loss_of_control",
    "pre_injection_failure",
)
ANALYSIS_STATE_CLASSES = ("analysis_incomplete",)

DRIFT_RATES_MPS = (0.2, 0.5, 1.0, 2.0, 4.0, 8.0)
GLITCH_MAGNITUDES_M = (10, 25, 50, 100, 200, 500)
DENIAL_DURATIONS_S = (5, 15, 30, 60)
JAMMING_REPEAT_COUNT = 5
JAMMING_DURATION_S = 45.0

MIN_POST_INJECTION_S = 90.0
REQUIRED_ATTEMPT_ARTIFACTS = (
    "gps_injection.json",
    "gps_behavior_summary.json",
    "ekf_innovation_metrics.json",
    "truth_vs_belief.json",
    "mode_timeline.json",
    "attitude_altitude_envelope.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def default_campaign_root() -> Path:
    return DEFAULT_CAMPAIGN_ROOT_PARENT / f"{CAMPAIGN_ROOT_PREFIX}_{timestamp_token()}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def preferred_python() -> str:
    return str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def case_attempt_id(case_id: str, target_run_index: int, attempt_index: int) -> str:
    return f"{case_id}__rep_{target_run_index:02d}__attempt_{attempt_index:03d}"


def attempt_dir(root: Path, case_id: str, attempt_index: int) -> Path:
    return root / case_id / "runs" / f"attempt_{attempt_index:03d}"


def phase1_param_files() -> list[Path]:
    return [PLANE_BASE_PARAM_FILE, PLANE_GPS_PARAM_FILE]


def validate_required_param_names(names: Iterable[str]) -> None:
    present = set(names)
    missing = [name for name in REQUIRED_SIM_GPS_PARAMS if name not in present]
    if missing:
        raise ValueError(f"Missing required SIM_GPS parameters: {missing}")


def parameter_schema() -> dict[str, Any]:
    return {
        "required_names": list(REQUIRED_SIM_GPS_PARAMS),
        "source_defaults": dict(SOURCE_DEFAULTS),
        "metadata": copy.deepcopy(PARAMETER_METADATA),
        "fault_types": list(FAULT_TYPES),
        "behavior_classes": list(BEHAVIOR_CLASSES),
        "analysis_state_classes": list(ANALYSIS_STATE_CLASSES),
        "phase1_param_stack": [str(path) for path in phase1_param_files()],
        "phase1_probe_mode": "name-existence validation only; live SITL probe is Phase 2",
        "overlay_status": (
            "plane_gps.parm is checked in and statically validated; "
            "live parameter readback remains Phase 2"
        ),
    }
