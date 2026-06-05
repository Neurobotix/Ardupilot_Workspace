"""Defaults for the airspeed_failure test-suite plugin."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SRC_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = Path(os.environ.get("ARDUPILOT_WORKSPACE", SRC_ROOT.parent)).resolve()
ASSETS_ROOT = WORKSPACE_ROOT / "assets"
CONFIG_ROOT = WORKSPACE_ROOT / "config"
VAR_ROOT = WORKSPACE_ROOT / "var"

SUITE_NAME = "airspeed_failure"
SCENARIO_NAME = "airspeed_failure_behavior"
LANE_NAME = "Airspeed Failure Behavior"
CAMPAIGN_ROOT_PREFIX = "airspeed_failure_behavior"
DEFAULT_CAMPAIGN_ROOT_PARENT = VAR_ROOT / "runs"

MISSION_FILE = ASSETS_ROOT / "missions" / "airspeed_failure_behavior_mission.waypoints"
SITL_TARGET = "plane-cte"
GAZEBO_TARGET = "gazebo-plane-cte"
SITL_LAUNCH_COMMAND = "scripts/ops/launch.sh plane-cte"
GAZEBO_LAUNCH_COMMAND = "scripts/ops/launch.sh gazebo-plane-cte"
PLANE_BASE_PARAM_FILE = CONFIG_ROOT / "vehicles" / "plane_base.parm"
PLANE_AIRSPEED_PARAM_FILE = CONFIG_ROOT / "overlays" / "plane_airspeed.parm"

WORLD_NAME = "mini_talon_wind_runway"
WIND_TOPIC = f"/world/{WORLD_NAME}/wind/"
WIND_INFO_TOPIC = f"/world/{WORLD_NAME}/wind_info"
REFERENCE_WIND_MPS = {"x": -5.0, "y": 0.0, "z": 0.0}
WIND_ECHO_TOLERANCE_MPS = 0.01
WIND_FRAME_NOTE = (
    "Gazebo world-frame ENU: +X=East, +Y=North. x=-5 is a westward wind, "
    "intended as headwind on the Eastbound measurement leg."
)

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
    "SIM_ARSPD_RND": 2.0,
    "SIM_ARSPD_OFS": 2013.0,
    "SIM_ARSPD_FAIL": 0.0,
    "SIM_ARSPD_FAILP": 0.0,
    "SIM_ARSPD_PITOT": 0.0,
    "SIM_ARSPD_SIGN": 0.0,
    "SIM_ARSPD_RATIO": 1.99,
}
REQUIRED_SIM_ARSPD_PARAMS = tuple(SOURCE_DEFAULTS.keys())

PARAMETER_METADATA = {
    "SIM_ARSPD_RND": {
        "units": "Pa",
        "semantics": "Noise amplitude on differential pressure; source default 2.0.",
        "readback_tolerance": 1e-3,
    },
    "SIM_ARSPD_OFS": {
        "units": "Pa-domain analog offset",
        "semantics": (
            "Name-existence probe only for ARSPD_TYPE 100; not used by active "
            "case payloads because TYPE 100 reads raw pressure before this offset."
        ),
        "readback_tolerance": 1e-3,
    },
    "SIM_ARSPD_FAIL": {
        "units": "m/s forced value when positive",
        "semantics": "Forced airspeed value, not a boolean enable.",
        "readback_tolerance": 0.0,
    },
    "SIM_ARSPD_FAILP": {
        "units": "Pa",
        "semantics": "Failure pressure; gates the pitot failure branch.",
        "readback_tolerance": 1e-3,
    },
    "SIM_ARSPD_PITOT": {
        "units": "Pa",
        "semantics": "Pitot term, active only when SIM_ARSPD_FAILP is non-zero.",
        "readback_tolerance": 1e-3,
    },
    "SIM_ARSPD_SIGN": {
        "units": "enum 0/1",
        "semantics": "Differential-pressure sign flip.",
        "readback_tolerance": 0.0,
    },
    "SIM_ARSPD_RATIO": {
        "units": "ratio",
        "semantics": (
            "SITL-side ratio. Reported bias is produced by mismatch with the "
            "vehicle ARSPD_RATIO: SIM_ARSPD_RATIO = ARSPD_RATIO / k^2."
        ),
        "readback_tolerance": 1e-3,
    },
}

FIXED_CASE_PAYLOADS = {
    "healthy_reference": {},
    "noise_5": {"SIM_ARSPD_RND": 5.0},
    "noise_10": {"SIM_ARSPD_RND": 10.0},
    "pitot_500pa": {"SIM_ARSPD_FAILP": 500.0},
    "fail_primary": {"SIM_ARSPD_FAIL": 1.0},
    "sign_reversed": {"SIM_ARSPD_SIGN": 1.0},
}
FIXED_CASE_ORDER = tuple(FIXED_CASE_PAYLOADS.keys())
V1_RATIO_BIAS_PERCENTS = (10, 30, 50, -10, -30, -50)
FULL_RATIO_BIAS_PERCENTS = tuple(range(10, 101, 10)) + tuple(range(-10, -51, -10))
DEFAULT_VEHICLE_ARSPD_RATIO = 2.0
DEFAULT_LOW_SIDE_FLOOR_PERCENT = -70

MIN_POST_INJECTION_S = 20.0
ALT_LOSS_MAX_M = 30.0
PLANNED_RTL_MIN_SEQ = 8

REQUIRED_ATTEMPT_ARTIFACTS = (
    "reference_wind.json",
    "airspeed_injection.json",
    "airspeed_behavior_summary.json",
    "airspeed_signal_metrics.json",
    "mission_progress.json",
    "mode_timeline.json",
    "altitude_speed_envelope.json",
)
OPTIONAL_ATTEMPT_ARTIFACTS = ("tecs_response.json",)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def default_campaign_root() -> Path:
    return DEFAULT_CAMPAIGN_ROOT_PARENT / f"{CAMPAIGN_ROOT_PREFIX}_{timestamp_token()}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def case_attempt_id(case_id: str, target_run_index: int, attempt_index: int) -> str:
    return f"{case_id}__rep_{target_run_index:02d}__attempt_{attempt_index:03d}"


def attempt_dir(root: Path, case_id: str, attempt_index: int) -> Path:
    return root / case_id / "runs" / f"attempt_{attempt_index:03d}"


def default_param_files() -> list[Path]:
    return [PLANE_BASE_PARAM_FILE, PLANE_AIRSPEED_PARAM_FILE]


def validate_required_param_names(names: Iterable[str]) -> None:
    present = set(names)
    missing = [name for name in REQUIRED_SIM_ARSPD_PARAMS if name not in present]
    if missing:
        raise ValueError(f"Missing required SIM_ARSPD parameters: {missing}")


def parameter_schema() -> dict[str, Any]:
    return {
        "required_names": list(REQUIRED_SIM_ARSPD_PARAMS),
        "source_defaults": dict(SOURCE_DEFAULTS),
        "metadata": PARAMETER_METADATA,
        "phase1_probe_mode": "name-existence validation only; live SITL probe is Phase 2",
    }
