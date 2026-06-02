"""Foundation defaults and naming helpers for the sensor_failure plugin.

Phase 4 second plugin. GPS-only scope. These constants are deliberately
GPS-fault-specific; the runtime environment helpers are reused from the proven
wind_matrix plugin (importing them is itself evidence those helpers were
generic, not wind-specific).

The SIM_GPS1_* parameter names and units below were verified live on
2026-06-02 against this workspace's SITL build (ArduPlane, tcp:127.0.0.1:5760)
and `src/ardupilot/libraries/SITL/SIM_GPS.cpp`. Do NOT trust the old 021 design
example names (`SIM_GPS_GLITCH_X`): they are wrong for this build. The real
per-instance subgroup prefix is `SIM_GPS1_` and the glitch is a Vector3 whose
X/Y are added to latitude/longitude in DEGREES and Z to altitude in METRES.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Reuse the proven, sensor-agnostic runtime/env helpers from the wind plugin.
# These are NOT wind-specific at the workspace/venv/Gazebo-plugin level; reusing
# them across a maximally different sensor is part of the genericity proof.
from ..wind_matrix.defaults import (  # noqa: F401  (re-exported for the plugin)
    ARDUPILOT_ROOT,
    ASSETS_ROOT,
    CONFIG_ROOT,
    VAR_ROOT,
    VENV_PYTHON,
    WORKSPACE_ROOT,
    file_sha256,
    gazebo_plugin_diagnostics,
    preferred_python,
    runtime_env,
)

# --- Paths -----------------------------------------------------------------
MISSION_FILE = (
    ASSETS_ROOT / "missions" / "square_500m_five_laps_loiter5_land.waypoints"
)
PLANE_BASE_PARAM_FILE = CONFIG_ROOT / "vehicles" / "plane_base.parm"
PLANE_AIRSPEED_PARAM_FILE = CONFIG_ROOT / "overlays" / "plane_airspeed.parm"
PLANE_PARAM_LOCAL_OVERRIDE = (
    WORKSPACE_ROOT / ".private" / "config" / "plane_params.local.parm"
)
DEFAULT_CAMPAIGN_ROOT = VAR_ROOT / "runs" / "sensor_failure_gps"

# A calm world: GPS faults come from SITL params, not Gazebo wind. We reuse the
# same world the wind plugin uses but always write it with zero wind.
PLANE_WORLD = ASSETS_ROOT / "worlds" / "mini_talon_wind_runway.sdf"

# --- MAVLink / timeouts ----------------------------------------------------
DEFAULT_MAVLINK = "udpin:0.0.0.0:14551"
DEFAULT_HEARTBEAT_TIMEOUT = 120.0
DEFAULT_MISSION_TIMEOUT = 1800.0
DEFAULT_READY_TIMEOUT = 120.0
DEFAULT_UPLOAD_TIMEOUT = 60.0
DEFAULT_ARM_TIMEOUT = 60.0
DEFAULT_MODE_TIMEOUT = 30.0
DEFAULT_STACK_SETTLE = 8.0
DEFAULT_RETRY_DELAY = 2.0
DEFAULT_MAX_ATTEMPTS_PER_CASE = 8
AUTO_ARM_TO_AUTO_SETTLE_S = 5.0
FORCE_ARM_MAGIC = 21196.0
BIN_FLUSH_DELAY_S = 3.0
ANALYSIS_HEADROOM_S = 30.0
CLEANUP_TIMEOUT_S = 30.0
VERIFY_MISSION_ITEM_TIMEOUT_S = 5.0
DEFAULT_REPEATS = 3

# --- GPS fault-injection ground truth (verified live 2026-06-02) -----------
# Per-instance subgroup prefix for the first simulated GPS.
SIM_GPS1_PREFIX = "SIM_GPS1_"
# Enable flag: live value 1.0; set to 0 for a hard GPS denial.
SIM_GPS1_ENABLE = "SIM_GPS1_ENABLE"
# Glitch vector components (see module docstring for units).
SIM_GPS1_GLTCH_X = "SIM_GPS1_GLTCH_X"  # latitude offset, DEGREES
SIM_GPS1_GLTCH_Y = "SIM_GPS1_GLTCH_Y"  # longitude offset, DEGREES
SIM_GPS1_GLTCH_Z = "SIM_GPS1_GLTCH_Z"  # altitude offset, METRES
# Available for future GPS cases (architected, not built now).
SIM_GPS1_NUMSATS = "SIM_GPS1_NUMSATS"
SIM_GPS1_JAM = "SIM_GPS1_JAM"

# Standard ArduPilot SITL home (CMAC). Verified live: -35.3632622.
SITL_HOME_LAT_DEG = -35.3632622
METERS_PER_DEG_LAT = 111320.0

# Mid-square injection: trigger once the vehicle is established in lap 1.
DEFAULT_INJECTION_WAYPOINT = 6

# Post-injection observation window before we stop the monitor (seconds). The
# resilience response (failsafe / dead-reckoning) is judged within this window;
# we do NOT require mission completion for a pass.
DEFAULT_POST_INJECT_WINDOW_S = 90.0

# --- Behavioral characterization ------------------------------------------
# This plugin CHARACTERIZES what the vehicle does when GPS is corrupted
# mid-flight; it does not gate pass/fail against absolute guessed bounds.
# Behavior is classified RELATIVE to a pre-fault / no-fault baseline envelope in
# analyzers.py. The only GPS-magnitude constant the cases need is the glitch
# offset; recognized recovery modes are informational for the report.
GLITCH_OFFSET_M = 50.0
# Informational: ArduPlane modes that indicate a deliberate failsafe/recovery
# response to GPS loss (EKF failsafe + dead-reckoning + FS_LONG_ACTN). Recorded
# in the summary, not used as a pass gate.
SAFE_RECOVERY_MODES = ("RTL", "FBWA", "FBWB", "CRUISE", "LOITER", "GUIDED", "CIRCLE")


def gps_glitch_offsets_deg_m(
    offset_m: float,
    *,
    home_lat_deg: float = SITL_HOME_LAT_DEG,
) -> tuple[float, float, float]:
    """Convert a horizontal glitch magnitude in metres to the SIM_GPS1_GLTCH
    vector (lat_deg, lon_deg, alt_m) at the given latitude.

    X (latitude) and Y (longitude) are returned in DEGREES because SIM_GPS adds
    them directly to lat/lon degrees; Z (altitude) is left at 0.0 metres for a
    purely horizontal glitch.
    """
    lat_deg = offset_m / METERS_PER_DEG_LAT
    m_per_deg_lon = METERS_PER_DEG_LAT * math.cos(math.radians(home_lat_deg))
    lon_deg = offset_m / m_per_deg_lon
    return (lat_deg, lon_deg, 0.0)


# --- Naming helpers --------------------------------------------------------
def case_runs_dir(root: Path, case_id: str) -> Path:
    return root / case_id / "runs"


def attempt_key(n: int) -> str:
    return f"attempt_{n:03d}"


def attempt_dir(root: Path, case_id: str, attempt_idx: int) -> Path:
    return case_runs_dir(root, case_id) / attempt_key(attempt_idx)


def attempt_id(case_id: str, rep: int, attempt_idx: int) -> str:
    return f"{case_id}__rep_{rep:02d}__attempt_{attempt_idx:03d}"


def named_bin_filename(case_id: str, rep: int, attempt_idx: int) -> str:
    return f"{attempt_id(case_id, rep, attempt_idx)}.BIN"


def run_alias(n: int) -> str:
    return f"run_{n:02d}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def default_param_files(*, include_local: bool = True) -> list[Path]:
    files = [PLANE_BASE_PARAM_FILE, PLANE_AIRSPEED_PARAM_FILE]
    if include_local and PLANE_PARAM_LOCAL_OVERRIDE.exists():
        files.append(PLANE_PARAM_LOCAL_OVERRIDE.resolve())
    return files


def normalize_param_file_stack(
    param_file_stack: Any = None,
) -> list[str]:
    if param_file_stack is None:
        return [str(path) for path in default_param_files()]
    return [str(Path(path).expanduser().resolve()) for path in param_file_stack]


def resolve_param_files(
    *,
    param_base: Path,
    param_airspeed: Path,
    param_local: Path | None,
    no_param_local: bool,
) -> list[Path]:
    if param_local is not None and no_param_local:
        raise ValueError("--param-local and --no-param-local are mutually exclusive")
    files = [
        param_base.expanduser().resolve(),
        param_airspeed.expanduser().resolve(),
    ]
    if param_local is not None:
        files.append(param_local.expanduser().resolve())
    elif not no_param_local and PLANE_PARAM_LOCAL_OVERRIDE.exists():
        files.append(PLANE_PARAM_LOCAL_OVERRIDE.resolve())
    missing = [path for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Parameter file(s) missing: " + ", ".join(str(path) for path in missing)
        )
    return files


def sitl_bin_dir(use_dir: Path | None) -> Path:
    effective = use_dir if use_dir is not None else DEFAULT_CAMPAIGN_ROOT
    return effective / "logs"
