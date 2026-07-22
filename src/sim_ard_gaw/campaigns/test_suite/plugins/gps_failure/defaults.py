"""Defaults for the gps_failure test-suite plugin."""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SRC_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = Path(os.environ.get("ARDUPILOT_WORKSPACE", SRC_ROOT.parent)).resolve()
ASSETS_ROOT = WORKSPACE_ROOT / "assets"
CONFIG_ROOT = WORKSPACE_ROOT / "config"
VAR_ROOT = WORKSPACE_ROOT / "var"
VENV_PYTHON = WORKSPACE_ROOT / "env" / "bin" / "python3"
WORKSPACE_GAZEBO_PLUGIN_DIR = WORKSPACE_ROOT / "build" / "ardupilot_gazebo"
WORKSPACE_GAZEBO_PLUGIN_FILE = (
    WORKSPACE_GAZEBO_PLUGIN_DIR / "libArduPilotPlugin.so"
)

SUITE_NAME = "gps_failure"
SCENARIO_NAME = "gps_failure_behavior"
LANE_NAME = "GPS Failure Behavior"
CAMPAIGN_ROOT_PREFIX = "gps_failure_behavior"
DEFAULT_CAMPAIGN_ROOT_PARENT = VAR_ROOT / "runs"

MISSION_FILE = ASSETS_ROOT / "missions" / "gps_failure_behavior_mission.waypoints"
GAZEBO_WORLD_FILE = ASSETS_ROOT / "worlds" / "mini_talon_gps_runway.sdf"
# Dedicated GPS failure launch identities. These are NOT the CTE/airspeed
# targets: plane-cte/gazebo-plane-cte load plane_airspeed.parm and the local
# plane override, which ADR-0021 rejects for GPS. plane-gps loads exactly
# plane_base.parm -> plane_gps.parm with no airspeed overlay and no local
# override; gazebo-plane-gps is the dedicated sensor-neutral GPS runway world
# (GPS/NavSat, calm, no wind/airspeed) whose east-facing pose matches the
# behavior mission. A plugin-owned live launcher must use these
# identities and this explicit stack, never plane-cte.
SITL_TARGET = "plane-gps"
GAZEBO_TARGET = "gazebo-plane-gps"
PLANE_BASE_PARAM_FILE = CONFIG_ROOT / "vehicles" / "plane_base.parm"
PLANE_GPS_PARAM_FILE = CONFIG_ROOT / "overlays" / "plane_gps.parm"

INJECTION_TRIGGER = {
    "source": "MISSION_CURRENT",
    "seq": 4,
    "edge": "first seq==4 after front-half progress",
    "front_half_required_sequences": [1, 3],
    "front_half_optional_sequences": [2],
    "pre_trigger_ignored_sequences": [0],
    "mode": "AUTO",
    "armed_required": True,
    "heartbeat_max_age_s": 1.0,
    "simstate_max_age_s": 1.0,
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

KNEE_READBACK_PARAMS = (
    "EK3_POS_I_GATE",
    "EK3_GLITCH_RAD",
    "FS_EKF_THRESH",
    "EK3_GPS_CHECK",
)
SOURCE_CONTRACT_PARAMS = (
    "EK3_SRC1_POSXY",
    "EK3_SRC1_VELXY",
    "EK3_SRC1_POSZ",
    "EK3_SRC1_VELZ",
    "EK3_SRC1_YAW",
)
LIVE_READBACK_PARAMS = (
    *REQUIRED_SIM_GPS_PARAMS,
    *KNEE_READBACK_PARAMS,
    *SOURCE_CONTRACT_PARAMS,
)

PHASE2_PROTECTED_CASE_IDS = (
    "nominal",
    "slow_drift_0p5_mps",
    "hard_denial_15s",
)

TELEMETRY_MESSAGE_TYPES = (
    "HEARTBEAT",
    "MISSION_CURRENT",
    "MISSION_ITEM_REACHED",
    "STATUSTEXT",
    "GLOBAL_POSITION_INT",
    "ATTITUDE",
    "NAV_CONTROLLER_OUTPUT",
    "SIMSTATE",
    "EKF_STATUS_REPORT",
    "GPS_RAW_INT",
)

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
        # MAVLink PARAM_VALUE carries float precision. At large slow-drift
        # offsets, 1e-9 deg can fail on harmless float rounding. 1e-8 deg is
        # still sub-millimetre scale for this lane's geography.
        "readback_tolerance": 1e-8,
    },
    "SIM_GPS1_GLTCH_Y": {
        "units": "degrees longitude offset",
        "semantics": (
            "Longitude glitch offset. slow_drift and step_glitch convert east metres "
            "to degrees explicitly at the vehicle/reference latitude."
        ),
        # MAVLink PARAM_VALUE carries float precision. At large slow-drift
        # offsets, 1e-9 deg can fail on harmless float rounding. 1e-8 deg is
        # still sub-millimetre scale for this lane's geography.
        "readback_tolerance": 1e-8,
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

PHASE2_NON_JAMMING_CAMPAIGN_CASE_IDS = (
    "nominal",
    "slow_drift_0p2_mps",
    "slow_drift_0p5_mps",
    "slow_drift_1p0_mps",
    "slow_drift_2p0_mps",
    "slow_drift_4p0_mps",
    "slow_drift_8p0_mps",
    "slow_drift_accumulation_ramp",
    "step_glitch_010m",
    "step_glitch_025m",
    "step_glitch_050m",
    "step_glitch_100m",
    "step_glitch_200m",
    "step_glitch_500m",
    "hard_denial_05s",
    "hard_denial_15s",
    "hard_denial_30s",
    "hard_denial_60s",
)

MIN_POST_INJECTION_S = 90.0
NOMINAL_MIN_POST_INJECTION_S = 20.0
PHASE2_MONITOR_TIMEOUT_S = 1800.0
SLOW_DRIFT_UPDATE_PERIOD_S = 5.0
CLEANUP_TIMEOUT_S = 30.0
HEARTBEAT_TIMEOUT_S = 30.0
VEHICLE_READY_TIMEOUT_S = 120.0
TRIGGER_HEARTBEAT_MAX_AGE_S = 1.0
TRIGGER_SIMSTATE_MAX_AGE_S = 1.0
TRIGGER_BOOT_TIME_MAX_AGE_S = 1.0
MAX_ABS_ROLL_DEG = 60.0
MAX_ABS_PITCH_DEG = 35.0
MAX_ALTITUDE_LOSS_M = 30.0
BIN_LIVE_ALTITUDE_TOLERANCE_M = 5.0
BIN_LIVE_ATTITUDE_TOLERANCE_DEG = 5.0
LOW_ALTITUDE_ABORT_M = 15.0
PLANNED_RTL_MIN_SEQ = 8
RTL_STABILIZE_S = 10.0
UPLOAD_TIMEOUT_S = 60.0
ARM_TIMEOUT_S = 60.0
MODE_TIMEOUT_S = 30.0
AUTO_ARM_TO_AUTO_SETTLE_S = 5.0
FORCE_ARM_MAGIC = 21196.0
READY_HEARTBEATS_REQUIRED = 2
READINESS_STREAM_REFRESH_S = 5.0
VERIFY_MISSION_ITEM_TIMEOUT_S = 5.0
REQUIRED_ATTEMPT_ARTIFACTS = (
    "run_config.json",
    "gps_injection.json",
    "source_contract.json",
    "stimulus_fidelity.json",
    "gps_lifecycle_windows.json",
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
    """Write strict JSON atomically, preserving any previous artifact on error."""

    encoded = json.dumps(
        data,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temp_path.unlink(missing_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def preferred_python() -> str:
    return str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def log(message: str) -> None:
    print(message, flush=True)


def case_attempt_id(case_id: str, target_run_index: int, attempt_index: int) -> str:
    return f"{case_id}__rep_{target_run_index:02d}__attempt_{attempt_index:03d}"


def attempt_dir(root: Path, case_id: str, attempt_index: int) -> Path:
    return root / case_id / "runs" / f"attempt_{attempt_index:03d}"


def sitl_state_dir(root: Path, case_id: str, attempt_index: int) -> Path:
    return root / "_sitl_state" / case_id / f"attempt_{attempt_index:03d}"


def default_param_files() -> list[Path]:
    return [PLANE_BASE_PARAM_FILE, PLANE_GPS_PARAM_FILE]


def validate_required_param_names(names: Iterable[str]) -> None:
    present = set(names)
    missing = [name for name in REQUIRED_SIM_GPS_PARAMS if name not in present]
    if missing:
        raise ValueError(f"Missing required SIM_GPS parameters: {missing}")


def parameter_schema() -> dict[str, Any]:
    return {
        "required_names": list(REQUIRED_SIM_GPS_PARAMS),
        "live_readback_names": list(LIVE_READBACK_PARAMS),
        "knee_readback_names": list(KNEE_READBACK_PARAMS),
        "source_contract_names": list(SOURCE_CONTRACT_PARAMS),
        "phase2_protected_case_ids": list(PHASE2_PROTECTED_CASE_IDS),
        "phase2_non_jamming_campaign_case_ids": list(
            PHASE2_NON_JAMMING_CAMPAIGN_CASE_IDS
        ),
        "telemetry_message_types": list(TELEMETRY_MESSAGE_TYPES),
        "source_defaults": dict(SOURCE_DEFAULTS),
        "metadata": copy.deepcopy(PARAMETER_METADATA),
        "fault_types": list(FAULT_TYPES),
        "behavior_classes": list(BEHAVIOR_CLASSES),
        "analysis_state_classes": list(ANALYSIS_STATE_CLASSES),
        "sitl_target": SITL_TARGET,
        "gazebo_target": GAZEBO_TARGET,
        "launch_target_note": (
            "dedicated GPS identities; plane-gps loads plane_base.parm -> "
            "plane_gps.parm only (no airspeed overlay, no local override); "
            "exercised by governed raw validation runs, no curated Phase-2 "
            "evidence yet"
        ),
        "static_param_stack": [str(path) for path in default_param_files()],
        "static_probe_mode": (
            "static name-existence validation only; live readback is "
            "re-verified on every live attempt"
        ),
        "overlay_status": (
            "plane_gps.parm is checked in and statically validated; "
            "live readback is re-verified on every live attempt"
        ),
    }
