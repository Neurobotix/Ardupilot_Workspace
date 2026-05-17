#!/usr/bin/env python3
"""
run_one.py — Wind injector + passive mission monitor for the Square Wind Matrix campaign.

Design principle: manual mode never sends MAVLink commands to the vehicle.
It injects wind via gz topic and then passively watches the MAVLink stream
until the mission finishes (vehicle DISARMS). With `--auto`, the script also
uploads the mission, arms, and switches to AUTO over MAVLink.

Workflow
--------
Terminal A:  scripts/ops/launch.sh plane-cte        ← MAVProxy / SITL for the CTE lane
Terminal B:  scripts/ops/launch.sh gazebo-plane-cte ← calm-by-default CTE world

Terminal C:  python run_one.py --x 0 --y 4 --rep 1
             → confirms sim is alive (reads one heartbeat)
             → injects wind
             → prints 3 commands to type in Terminal A
             → waits passively until vehicle DISARMS after landing

Terminal C (automated):  python run_one.py --x 0 --y 4 --rep 1 --auto
             → confirms sim is alive
             → injects wind
             → uploads mission, arms, switches to AUTO
             → waits until vehicle DISARMS after landing

Terminal A (after script prints the commands):
             wp load <mission_file>
             arm throttle force
             mode AUTO

Launch order matters for the manual CTE lane:
  • start Terminal A first, because launch.sh plane-cte wipes EEPROM on startup
  • start Terminal B second

After DISARM the script automatically:
  • copies the newest .BIN log
  • runs true_path_deviation.py
  • runs square_loiter_mission_metrics.py
  • writes run_summary.json
  • updates manifest.csv / manifest.json

Wind convention (Gazebo ENU world frame)
-----------------------------------------
  x = East wind component  (m/s)
  y = North wind component (m/s)
  z = 0 (always)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = tempfile.mkdtemp(prefix="mplcfg_")
import matplotlib
matplotlib.use("Agg")
import numpy as np
from pymavlink import mavutil, mavwp

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sim_ard_gaw.campaigns.manifest_safety import campaign_manifest_lock
from sim_ard_gaw.campaigns.mission_contract import (
    SQUARE_WIND_MISSION_CONTRACT,
    validate_square_wind_mission_contract,
)
from sim_ard_gaw.campaigns.provenance import parameter_file_provenance
from sim_ard_gaw.campaigns.status import annotate_terminal_status
from sim_ard_gaw.campaigns.wind_world import SdfWindError, read_world_wind

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSPACE_ROOT    = Path(os.environ.get("ARDUPILOT_WORKSPACE", SRC_ROOT.parent)).resolve()
ASSETS_ROOT       = WORKSPACE_ROOT / "assets"
CONFIG_ROOT       = WORKSPACE_ROOT / "config"
VAR_ROOT          = WORKSPACE_ROOT / "var"
RUNTIME_ROOT      = WORKSPACE_ROOT / "src" / "sim_ard_gaw"
ANALYSIS_ROOT     = RUNTIME_ROOT / "analysis"
LAUNCH_SCRIPT     = RUNTIME_ROOT / "launch" / "launch.sh"
ARDUPILOT_ROOT    = WORKSPACE_ROOT / "src" / "ardupilot"
VENV_PYTHON       = WORKSPACE_ROOT / "env" / "bin" / "python3"
WORKSPACE_GAZEBO_PLUGIN_DIR = WORKSPACE_ROOT / "build" / "ardupilot_gazebo"
WORKSPACE_GAZEBO_PLUGIN_FILE = WORKSPACE_GAZEBO_PLUGIN_DIR / "libArduPilotPlugin.so"

TRUE_PATH_SCRIPT      = ANALYSIS_ROOT / "true_path_deviation.py"
SQUARE_METRICS_SCRIPT = ANALYSIS_ROOT / "square_loiter_mission_metrics.py"
MISSION_FILE          = ASSETS_ROOT / "missions" / "square_500m_five_laps_loiter5_land.waypoints"
DEFAULT_CAMPAIGN_ROOT = VAR_ROOT / "logs" / "009_Square_Wind_Matrix_CTE"
PLANE_BASE_PARAM_FILE = CONFIG_ROOT / "vehicles" / "plane_base.parm"
PLANE_AIRSPEED_PARAM_FILE = CONFIG_ROOT / "overlays" / "plane_airspeed.parm"
ANALYSIS_POSITION_SOURCE = "sim"
PLANE_PARAM_LOCAL_OVERRIDE = WORKSPACE_ROOT / ".private" / "config" / "plane_params.local.parm"
DEFAULT_CTE_SITL_USE_DIR = VAR_ROOT / "runs" / "sitl" / "plane-cte"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WORLD_NAME   = "mini_talon_wind_runway"
WIND_TOPIC   = f"/world/{WORLD_NAME}/wind/"
WIND_INFO_TOPIC = f"/world/{WORLD_NAME}/wind_info"
WIND_VALUES  = [0, 4, 8, 12]
RUNS_PER_COMBO = 5
CTE_LANE_NAME = "Cross Tracking Error (CTE)"
CTE_GAZEBO_COMMAND = "scripts/ops/launch.sh gazebo-plane-cte"
CTE_SITL_COMMAND = "scripts/ops/launch.sh plane-cte"

# mavlink output port from launch.sh plane-cte: --out=udp:127.0.0.1:14551
# We listen on that port passively (MAVProxy pushes to it)
DEFAULT_MAVLINK = "udpin:0.0.0.0:14551"

DEFAULT_HEARTBEAT_TIMEOUT = 30.0   # seconds to wait for first heartbeat
DEFAULT_MISSION_TIMEOUT   = 12000.0 # seconds to wait for DISARM (full 5-lap mission)
DEFAULT_READY_TIMEOUT     = 60.0
DEFAULT_UPLOAD_TIMEOUT    = 60.0
DEFAULT_ARM_TIMEOUT       = 60.0
DEFAULT_MODE_TIMEOUT      = 30.0
FORCE_ARM_MAGIC           = 21196.0
VERIFY_MISSION_ITEM_TIMEOUT_S = 5.0
BIN_FLUSH_DELAY_S = 3.0
ANALYSIS_HEADROOM_S = 30.0
STACK_CLEANUP_TIMEOUT_S = 30.0
WIND_INJECTION_MAX_ATTEMPTS = 8
WIND_INJECTION_RETRY_S = 1.5
WIND_ECHO_SETTLE_S = 0.2
WIND_ECHO_TIMEOUT_S = 5.0
WIND_ECHO_TOLERANCE_MPS = 0.01
STRICT_WIND_ECHO_VERIFY = os.environ.get("SIM_ARD_GAW_STRICT_WIND_ECHO_VERIFY", "1") != "0"
WIND_INFO_CAPTURE_TIMEOUT_S = 3.0
CAPTURE_WIND_INFO = os.environ.get("SIM_ARD_GAW_CAPTURE_WIND_INFO", "1") != "0"
SDF_WIND_TOLERANCE_MPS = 0.001
READY_HEARTBEATS_REQUIRED = 2
AUTO_ARM_TO_AUTO_SETTLE_S = 5.0
AUTO_WIND_INJECTION_MIN_RELALT_M = 20.0
AUTO_WIND_INJECTION_ALT_TIMEOUT_S = 180.0
AUTO_WIND_PHASES = ("after-takeoff", "before-arm")
DEFAULT_AUTO_WIND_PHASE = "after-takeoff"
ENTRY_WAYPOINT_MAX_PASS_DISTANCE_M = 200
PASSED_WAYPOINT_RE = re.compile(r"Passed waypoint #(?P<seq>\d+) dist (?P<dist>\d+)m")

# Mission layout for square_500m_five_laps_loiter5_land.waypoints.
MISSION_SQUARE_START_SEQ = SQUARE_WIND_MISSION_CONTRACT.square_start_seq
MISSION_SQUARE_END_SEQ = SQUARE_WIND_MISSION_CONTRACT.square_end_seq
MISSION_LOITER_SEQ = SQUARE_WIND_MISSION_CONTRACT.loiter_seq
MISSION_LOITER_TO_ALT_SEQ = SQUARE_WIND_MISSION_CONTRACT.loiter_to_alt_seq
MISSION_FINAL_SEQ = SQUARE_WIND_MISSION_CONTRACT.final_seq

WIND_FRAME_NOTE = (
    "Gazebo world-frame ENU: +X=East, +Y=North. "
    "ArduPilot Gazebo plugin handles NED<->ENU internally."
)
SUCCESS_STATUSES = {"success_full", "success_square_only"}
TERMINAL_NO_ANALYSIS_STATUSES = {"failed", "error", "interrupted"}
ANALYSIS_NOT_RUN = "not_run"
ANALYSIS_PARTIAL_RUN_SUMMARY_FAILED = "partial: run_summary_failed"
STALE_RUNNING_NOTE = "bookkeeping_recovered_stale_running_record"

# ---------------------------------------------------------------------------
# Tiny utilities
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def preferred_python() -> str:
    return str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def cte_param_file_stack() -> list[str]:
    stack = [
        PLANE_BASE_PARAM_FILE,
        PLANE_AIRSPEED_PARAM_FILE,
    ]
    if PLANE_PARAM_LOCAL_OVERRIDE.exists():
        stack.append(PLANE_PARAM_LOCAL_OVERRIDE)
    return [str(path) for path in stack]


def normalize_param_file_stack(
    param_file_stack: Sequence[Path | str] | None = None,
) -> list[str]:
    if param_file_stack is None:
        return cte_param_file_stack()
    return [str(Path(path).expanduser().resolve()) for path in param_file_stack]


def _prepend_path_entry(entry: str, current: str) -> str:
    """Prepend a path entry, removing stale duplicates already in the path."""
    if not entry:
        return current
    parts = [part for part in current.split(":") if part and part != entry]
    return ":".join([entry, *parts])


def runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    resource_paths = [
        ASSETS_ROOT / "models", ASSETS_ROOT / "worlds",
        WORKSPACE_ROOT / "src" / "SITL_Models" / "Gazebo" / "models",
        WORKSPACE_ROOT / "src" / "SITL_Models" / "Gazebo" / "worlds",
        WORKSPACE_ROOT / "src" / "ardupilot_gazebo" / "models",
        WORKSPACE_ROOT / "src" / "ardupilot_gazebo" / "worlds",
        Path("/usr/local/share/ardupilot_gazebo/models"),
        Path("/usr/local/share/ardupilot_gazebo/worlds"),
    ]
    resource_path = env.get("GZ_SIM_RESOURCE_PATH", "")
    if not WORKSPACE_GAZEBO_PLUGIN_FILE.exists():
        raise RuntimeError(
            "Workspace Gazebo plugin build is required and missing: "
            f"{WORKSPACE_GAZEBO_PLUGIN_FILE}. Installed plugin fallback is forbidden."
        )
    for path in resource_paths:
        resource_path = _prepend_path_entry(str(path), resource_path)

    env["GZ_SIM_RESOURCE_PATH"] = resource_path
    env["GZ_SIM_SYSTEM_PLUGIN_PATH"] = str(WORKSPACE_GAZEBO_PLUGIN_DIR)
    path_parts = env.get("PATH", "").split(":")
    for extra in [str(ARDUPILOT_ROOT / "Tools" / "autotest"),
                  str(VENV_PYTHON.parent)]:
        if extra and extra not in path_parts:
            path_parts.insert(0, extra)
    env["PATH"] = ":".join(path_parts)
    return env


def file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gazebo_plugin_diagnostics(env: dict[str, str] | None = None) -> dict[str, Any]:
    effective_env = env if env is not None else runtime_env()
    plugin_path = effective_env.get("GZ_SIM_SYSTEM_PLUGIN_PATH", "")
    known_dirs = [WORKSPACE_GAZEBO_PLUGIN_DIR]
    known_plugins = []
    for directory in known_dirs:
        plugin_file = directory / "libArduPilotPlugin.so"
        stat = plugin_file.stat() if plugin_file.exists() else None
        known_plugins.append({
            "directory": str(directory),
            "plugin_file": str(plugin_file),
            "exists": plugin_file.exists(),
            "sha256": file_sha256(plugin_file),
            "mtime_s": stat.st_mtime if stat is not None else None,
            "size_bytes": stat.st_size if stat is not None else None,
        })
    return {
        "policy": "workspace_build_only",
        "gz_sim_system_plugin_path": plugin_path,
        "gz_sim_system_plugin_path_entries": [
            part for part in plugin_path.split(":") if part
        ],
        "known_ardupilot_plugin_binaries": known_plugins,
    }


def sitl_bin_dir(use_dir: Path | None) -> Path:
    effective_use_dir = use_dir if use_dir is not None else DEFAULT_CTE_SITL_USE_DIR
    return effective_use_dir / "logs"


def cleanup_stack_for_analysis() -> None:
    launch_script = LAUNCH_SCRIPT
    try:
        subprocess.run(
            [str(launch_script), "cleanup"],
            cwd=str(launch_script.parent),
            env=runtime_env(),
            check=False,
            timeout=STACK_CLEANUP_TIMEOUT_S,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        pass


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def clean_float(v: Any) -> float | None:
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def clean_int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def remaining_deadline_s(slot_deadline_monotonic: float | None) -> float | None:
    if slot_deadline_monotonic is None:
        return None
    return slot_deadline_monotonic - time.monotonic()


def clamp_timeout_to_slot(
    requested_timeout_s: float,
    slot_deadline_monotonic: float | None,
    *,
    phase: str,
    reserve_s: float = 0.0,
) -> float:
    if slot_deadline_monotonic is None:
        return requested_timeout_s
    remaining = slot_deadline_monotonic - time.monotonic() - reserve_s
    if remaining <= 0.0:
        raise TimeoutError(f"Slot deadline exhausted before {phase}.")
    return min(requested_timeout_s, remaining)


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def combo_key(x: int, y: int) -> str:
    return f"wind_x_{x:02d}_y_{y:02d}"


def attempt_key(n: int) -> str:
    return f"attempt_{n:03d}"


def run_alias(n: int) -> str:
    return f"run_{n:02d}"


def attempt_id(key: str, rep: int, attempt_idx: int) -> str:
    return f"{key}__rep_{rep:02d}__attempt_{attempt_idx:03d}"


def named_bin_filename(key: str, rep: int, attempt_idx: int) -> str:
    return f"{attempt_id(key, rep, attempt_idx)}.BIN"


def combo_runs_dir(root: Path, key: str) -> Path:
    return root / key / "runs"


def coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_prefixed_index(name: str, prefix: str) -> int | None:
    if not name.startswith(prefix):
        return None
    return coerce_int(name[len(prefix):])


def normalize_manifest_text(value: Any) -> str:
    return " ".join(str(value).split())


def summarize_exception_text(value: Any) -> str:
    lines = [
        line.strip() for line in str(value).splitlines()
        if line.strip() and not set(line.strip()) <= {"^"}
    ]
    if not lines:
        return normalize_manifest_text(value)

    head = re.sub(r":\s*\^+$", "", lines[0]).strip()
    tail = lines[-1]
    if tail != head and ("Error:" in tail or tail.endswith("Error")):
        return normalize_manifest_text(f"{head} ({tail})")
    return normalize_manifest_text(head)


def note_once(record: dict[str, Any], note: str) -> None:
    notes = record.get("notes")
    if notes is None:
        record["notes"] = []
        notes = record["notes"]
    elif not isinstance(notes, list):
        record["notes"] = [normalize_manifest_text(notes)]
        notes = record["notes"]
    note = normalize_manifest_text(note)
    if note not in notes:
        notes.append(note)


def write_text_atomic(path: Path, text: str, newline: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline=newline,
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as fh:
            fh.write(text)
            tmp_path = Path(fh.name)
        tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def symlink_points_to(link: Path, target: Path) -> bool:
    if not link.is_symlink():
        return False
    try:
        current_target = (link.parent / link.readlink()).resolve(strict=False)
    except OSError:
        return False
    return current_target == target.resolve(strict=False)


def ensure_run_alias_link(link: Path, target: Path) -> None:
    if not target.exists():
        raise RuntimeError(f"Run alias target does not exist: {target}")

    if link.is_symlink():
        if symlink_points_to(link, target):
            return
        link.unlink()
    elif link.exists():
        raise RuntimeError(f"Run alias path exists and is not a symlink: {link}")

    rel_target = Path(os.path.relpath(str(target), start=str(link.parent)))
    link.symlink_to(rel_target)


def reconcile_manifest_bookkeeping(root: Path, manifest: dict[str, Any]) -> list[str]:
    attempts = manifest.setdefault("attempts", [])
    if not isinstance(attempts, list):
        raise RuntimeError("Manifest field 'attempts' must be a list.")

    changes: list[str] = []
    stale_alias_links: list[tuple[Path, Path]] = []
    seen_attempt_ids: set[str] = set()
    seen_attempt_indices: set[tuple[str, int]] = set()
    seen_success_reps: set[tuple[str, int]] = set()
    seen_run_aliases: set[tuple[str, str]] = set()

    for record in attempts:
        if not isinstance(record, dict):
            raise RuntimeError("Manifest attempts must contain JSON objects.")

        notes = record.get("notes")
        if notes is None:
            record["notes"] = []
            changes.append("Initialized missing notes list in manifest record.")
        elif not isinstance(notes, list):
            record["notes"] = [str(notes)]
            changes.append(
                f"Normalized notes field for {record.get('attempt_id', '<unknown attempt>')}."
            )

        attempt_name = str(record.get("attempt_id", "")).strip()
        if attempt_name:
            if attempt_name in seen_attempt_ids:
                raise RuntimeError(f"Duplicate attempt_id in manifest: {attempt_name}")
            seen_attempt_ids.add(attempt_name)

        combo = str(record.get("combo_key", "")).strip()
        attempt_idx = coerce_int(record.get("attempt_index"))
        if combo and attempt_idx is not None and attempt_idx >= 1:
            expected_attempt_dir = combo_runs_dir(root, combo) / attempt_key(attempt_idx)
            if record.get("attempt_dir") != str(expected_attempt_dir):
                record["attempt_dir"] = str(expected_attempt_dir)
                changes.append(f"{attempt_name or combo}: normalized attempt_dir.")
            attempt_index_key = (combo, attempt_idx)
            if attempt_index_key in seen_attempt_indices:
                raise RuntimeError(
                    f"Duplicate attempt_index {attempt_idx} for combo {combo} in manifest."
                )
            seen_attempt_indices.add(attempt_index_key)

        status = str(record.get("status", "")).strip()
        analysis_status = str(record.get("analysis_status", "")).strip()

        if status == "running":
            record["status"] = "interrupted"
            status = "interrupted"
            if analysis_status in {"", "pending"}:
                record["analysis_status"] = ANALYSIS_NOT_RUN
            note_once(record, STALE_RUNNING_NOTE)
            changes.append(
                f"{attempt_name or combo}: recovered stale running record as interrupted."
            )
        elif status in TERMINAL_NO_ANALYSIS_STATUSES and analysis_status in {"", "pending"}:
            record["analysis_status"] = ANALYSIS_NOT_RUN
            changes.append(
                f"{attempt_name or combo}: normalized analysis_status to {ANALYSIS_NOT_RUN}."
            )

        if status in SUCCESS_STATUSES:
            if not combo:
                raise RuntimeError(f"{attempt_name or '<unknown attempt>'}: missing combo_key.")

            target_run_idx = coerce_int(record.get("target_run_index"))
            if target_run_idx is None or target_run_idx < 1:
                raise RuntimeError(
                    f"{attempt_name or combo}: invalid target_run_index "
                    f"{record.get('target_run_index')!r}."
                )

            success_rep_key = (combo, target_run_idx)
            if success_rep_key in seen_success_reps:
                raise RuntimeError(
                    f"Duplicate successful rep {target_run_idx} for combo {combo} in manifest."
                )
            seen_success_reps.add(success_rep_key)

            expected_alias = run_alias(target_run_idx)
            old_alias = str(record.get("run_alias", "")).strip() or None
            attempt_dir_text = str(record.get("attempt_dir", "")).strip()
            if old_alias != expected_alias:
                record["run_alias"] = expected_alias
                changes.append(
                    f"{attempt_name or combo}: normalized run_alias to {expected_alias}."
                )
                if old_alias and attempt_dir_text:
                    stale_alias_links.append(
                        (combo_runs_dir(root, combo) / old_alias, Path(attempt_dir_text))
                    )

            run_alias_key = (combo, expected_alias)
            if run_alias_key in seen_run_aliases:
                raise RuntimeError(
                    f"Duplicate run_alias {expected_alias} for combo {combo} in manifest."
                )
            seen_run_aliases.add(run_alias_key)

            if not attempt_dir_text:
                raise RuntimeError(f"{attempt_name or combo}: missing attempt_dir for success.")
            if not Path(attempt_dir_text).exists():
                raise RuntimeError(
                    f"{attempt_name or combo}: successful attempt_dir is missing: {attempt_dir_text}"
                )
        elif record.get("run_alias") is not None:
            record["run_alias"] = None
            changes.append(f"{attempt_name or combo}: cleared run_alias from non-success record.")

    for record in attempts:
        status = str(record.get("status", "")).strip()
        if status not in SUCCESS_STATUSES:
            continue
        combo = str(record.get("combo_key", "")).strip()
        alias = str(record.get("run_alias", "")).strip()
        attempt_dir_text = str(record.get("attempt_dir", "")).strip()
        if combo and alias and attempt_dir_text:
            ensure_run_alias_link(combo_runs_dir(root, combo) / alias, Path(attempt_dir_text))

    for stale_link, attempt_dir in stale_alias_links:
        if stale_link.is_symlink() and symlink_points_to(stale_link, attempt_dir):
            stale_link.unlink()
            changes.append(f"Removed stale alias link {stale_link.name}.")

    return changes


def ring_terminal_bell(count: int = 3, delay_s: float = 0.15) -> bool:
    stream = sys.stderr if sys.stderr.isatty() else sys.stdout if sys.stdout.isatty() else None
    if stream is None:
        return False
    for idx in range(count):
        stream.write("\a")
        stream.flush()
        if idx + 1 < count:
            time.sleep(delay_s)
    return True


def play_success_sound() -> None:
    canberra = shutil.which("canberra-gtk-play")
    if canberra:
        try:
            subprocess.Popen(
                [canberra, "-i", "complete", "-d", "run_one.py finished successfully"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return
        except OSError:
            pass
    ring_terminal_bell()


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def load_manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    default: dict[str, Any] = {
        "campaign_root": str(root),
        "created_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "attempts": [],
    }
    return read_json(path, default)


def save_manifest(root: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at_utc"] = utc_now()
    for record in manifest.get("attempts", []):
        analysis_status = record.get("analysis_status")
        if analysis_status is not None:
            record["analysis_status"] = normalize_manifest_text(analysis_status)
        annotate_terminal_status(record)
        notes = record.get("notes")
        if isinstance(notes, list):
            record["notes"] = [normalize_manifest_text(note) for note in notes]
        elif notes is not None:
            record["notes"] = [normalize_manifest_text(notes)]
    write_text_atomic(
        root / "manifest.json",
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )
    fieldnames = [
        "attempt_id", "combo_key", "x_wind_mps", "y_wind_mps",
        "target_run_index", "attempt_index", "status", "terminal_status", "success_class",
        "mission_completed_full", "square_completed", "loiter_completed",
        "analysis_status",
        "raw_log_path", "attempt_dir", "run_alias",
        "start_time_utc", "end_time_utc", "duration_wall_s", "notes",
    ]
    csv_buffer = io.StringIO(newline="")
    w = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    w.writeheader()
    for a in manifest.get("attempts", []):
        row = {f: a.get(f) for f in fieldnames}
        if isinstance(row.get("notes"), list):
            row["notes"] = " | ".join(row["notes"])
        w.writerow(row)
    write_text_atomic(root / "manifest.csv", csv_buffer.getvalue(), newline="")


def save_campaign_summary(root: Path, manifest: dict[str, Any]) -> None:
    """Write a lightweight campaign status summary."""
    attempts = [
        record for record in manifest.get("attempts", [])
        if isinstance(record, dict)
    ]
    target_runs = coerce_int(manifest.get("target_run_count")) or RUNS_PER_COMBO
    require_analysis: bool = bool(manifest.get("require_analysis", False))
    combos: list[dict[str, Any]] = []

    for x in WIND_VALUES:
        for y in WIND_VALUES:
            key = combo_key(x, y)
            combo_attempts = [a for a in attempts if a.get("combo_key") == key]
            successes = [
                a for a in combo_attempts
                if a.get("status") in SUCCESS_STATUSES
                and (not require_analysis or a.get("analysis_status") == "done")
            ]
            pending = [a for a in combo_attempts if str(a.get("status")) == "running"]
            last = combo_attempts[-1] if combo_attempts else {}
            combos.append({
                "combo_key": key,
                "x_wind_mps": x,
                "y_wind_mps": y,
                "accepted_runs": len(successes),
                "remaining_runs": max(0, target_runs - len(successes)),
                "attempt_count": len(combo_attempts),
                "pending_attempt_count": len(pending),
                "last_status": last.get("status"),
                "last_attempt_id": last.get("attempt_id"),
            })

    summary = {
        "campaign_root": str(root),
        "updated_at_utc": utc_now(),
        "target_run_count": target_runs,
        "require_analysis": require_analysis,
        "accepted_total": sum(item["accepted_runs"] for item in combos),
        "remaining_total": sum(item["remaining_runs"] for item in combos),
        "combos": combos,
    }
    summary_dir = root / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    write_json(summary_dir / "campaign_summary.json", summary)

    fieldnames = [
        "combo_key", "x_wind_mps", "y_wind_mps",
        "accepted_runs", "remaining_runs",
        "attempt_count", "pending_attempt_count",
        "last_status", "last_attempt_id",
    ]
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    for item in combos:
        writer.writerow({field: item.get(field) for field in fieldnames})
    write_text_atomic(summary_dir / "campaign_summary.csv", csv_buffer.getvalue(), newline="")


def combo_successes(
    manifest: dict[str, Any],
    key: str,
    *,
    require_analysis: bool = False,
) -> list[dict[str, Any]]:
    return [
        a for a in manifest.get("attempts", [])
        if a.get("combo_key") == key
        and a.get("status") in SUCCESS_STATUSES
        and (not require_analysis or a.get("analysis_status") == "done")
    ]


def next_attempt_index(root: Path, manifest: dict[str, Any], key: str) -> int:
    indices: set[int] = set()
    for attempt in manifest.get("attempts", []):
        if attempt.get("combo_key") != key:
            continue
        idx = coerce_int(attempt.get("attempt_index"))
        if idx is not None and idx >= 1:
            indices.add(idx)

    runs_dir = combo_runs_dir(root, key)
    if runs_dir.exists():
        for child in runs_dir.iterdir():
            idx = parse_prefixed_index(child.name, "attempt_")
            if idx is not None and idx >= 1:
                indices.add(idx)

    next_idx = max(indices, default=0) + 1
    while (runs_dir / attempt_key(next_idx)).exists():
        next_idx += 1
    return next_idx


# ---------------------------------------------------------------------------
# Wind injection  (only external action — no MAVLink involved)
# ---------------------------------------------------------------------------

WIND_FLOAT_RE = re.compile(
    r"(?P<field>x|y|z):\s*(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
)


def parse_wind_echo(stdout: str) -> dict[str, float | bool] | None:
    values: dict[str, float] = {}
    enable_wind: bool | None = None
    for match in WIND_FLOAT_RE.finditer(stdout):
        values[match.group("field")] = float(match.group("value"))
    enabled_match = re.search(r"enable_wind:\s*(true|false)", stdout, re.IGNORECASE)
    if enabled_match is not None:
        enable_wind = enabled_match.group(1).lower() == "true"
    if not values and enable_wind is None:
        return None
    parsed: dict[str, float | bool] = {
        "x": values.get("x", 0.0),
        "y": values.get("y", 0.0),
        "z": values.get("z", 0.0),
    }
    if enable_wind is not None:
        parsed["enable_wind"] = enable_wind
    return parsed


def wind_echo_matches(parsed: dict[str, float | bool] | None, x_mps: float, y_mps: float) -> bool:
    if parsed is None:
        return False
    if parsed.get("enable_wind") is False:
        return False
    expected = {"x": x_mps, "y": y_mps, "z": 0.0}
    for axis, want in expected.items():
        got = parsed.get(axis)
        if not isinstance(got, float) or abs(got - want) > WIND_ECHO_TOLERANCE_MPS:
            return False
    return True


def start_wind_echo() -> tuple[subprocess.Popen[str], list[str]]:
    cmd = ["gz", "topic", "-e", "-t", WIND_TOPIC, "-n", "1"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=runtime_env(),
    )
    time.sleep(WIND_ECHO_SETTLE_S)
    return proc, cmd


def finish_wind_echo(proc: subprocess.Popen[str]) -> dict[str, Any]:
    try:
        stdout, stderr = proc.communicate(timeout=WIND_ECHO_TIMEOUT_S)
        timed_out = False
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        timed_out = True
    return {
        "returncode": proc.returncode,
        "timed_out": timed_out,
        "stdout": normalize_manifest_text(stdout.strip()),
        "stderr": normalize_manifest_text(stderr.strip()),
    }


def capture_wind_info_snapshot(timeout_s: float) -> dict[str, Any]:
    cmd = ["gz", "topic", "-e", "-t", WIND_INFO_TOPIC, "-n", "1"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=runtime_env(),
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
        timed_out = False
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        timed_out = True
    stdout_text = normalize_manifest_text(stdout.strip())
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "timed_out": timed_out,
        "stdout": stdout_text,
        "stderr": normalize_manifest_text(stderr.strip()),
        "parsed_wind_mps": parse_wind_echo(stdout_text),
        "note": (
            "Live Gazebo wind_info snapshot. This can show ramp-in progress "
            "and is not treated as a pass/fail check."
        ),
    }


def inject_wind(
    x_mps: float,
    y_mps: float,
    *,
    timeout_s: float | None = None,
    strict_echo_verify: bool = STRICT_WIND_ECHO_VERIFY,
) -> dict[str, Any]:
    payload = f"linear_velocity:{{x:{x_mps:.3f},y:{y_mps:.3f},z:0.000}}, enable_wind:true"
    cmd = ["gz", "topic", "-t", WIND_TOPIC, "-m", "gz.msgs.Wind", "-p", payload]
    log(f"Injecting wind  x={x_mps} m/s (East)  y={y_mps} m/s (North)")
    log(f"  {shlex.join(cmd)}")
    deadline = time.monotonic() + timeout_s if timeout_s is not None else None
    attempt_logs: list[dict[str, Any]] = []
    for attempt in range(WIND_INJECTION_MAX_ATTEMPTS):
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("Slot deadline exhausted during wind injection.")
        echo_proc = None
        echo_cmd: list[str] | None = None
        if strict_echo_verify:
            echo_proc, echo_cmd = start_wind_echo()
        r = subprocess.run(cmd, capture_output=True, text=True,
                           check=False, env=runtime_env())
        echo_result = finish_wind_echo(echo_proc) if echo_proc is not None else None
        parsed_echo = parse_wind_echo(echo_result["stdout"]) if echo_result is not None else None
        echo_verified = wind_echo_matches(parsed_echo, x_mps, y_mps) if strict_echo_verify else None
        attempt_logs.append({
            "attempt_number": attempt + 1,
            "returncode": r.returncode,
            "stdout": normalize_manifest_text(r.stdout.strip()),
            "stderr": normalize_manifest_text(r.stderr.strip()),
            "echo_command": echo_cmd,
            "echo_result": echo_result,
            "echo_parsed_wind": parsed_echo,
            "echo_verified": echo_verified,
        })
        if r.returncode == 0 and (not strict_echo_verify or echo_verified):
            if strict_echo_verify:
                log("Wind injection OK and verified on Gazebo topic echo.")
            else:
                log("Wind injection publish OK. Echo verification disabled.")
            live_wind_info = None
            if CAPTURE_WIND_INFO:
                live_timeout_s = WIND_INFO_CAPTURE_TIMEOUT_S
                if deadline is not None:
                    live_timeout_s = min(live_timeout_s, max(0.0, deadline - time.monotonic()))
                if live_timeout_s > 0.0:
                    live_wind_info = capture_wind_info_snapshot(live_timeout_s)
                    parsed_live = live_wind_info.get("parsed_wind_mps")
                    if isinstance(parsed_live, dict):
                        log(
                            "Live wind_info snapshot "
                            f"x={parsed_live.get('x')} y={parsed_live.get('y')} z={parsed_live.get('z')}"
                        )
            return {
                "status": "ok",
                "wind_topic": WIND_TOPIC,
                "wind_info_topic": WIND_INFO_TOPIC,
                "payload": payload,
                "command": cmd,
                "verification": (
                    "gz topic echo matched requested wind payload"
                    if strict_echo_verify
                    else "publisher returned success; Gazebo echo verification disabled"
                ),
                "strict_echo_verification": strict_echo_verify,
                "echo_command": echo_cmd,
                "echo_parsed_wind": parsed_echo,
                "echo_tolerance_mps": WIND_ECHO_TOLERANCE_MPS,
                "x_wind_mps": x_mps,
                "y_wind_mps": y_mps,
                "live_wind_info_capture_enabled": CAPTURE_WIND_INFO,
                "live_wind_info_snapshot": live_wind_info,
                "attempt_count": attempt + 1,
                "publisher_attempts": attempt_logs,
            }
        if r.returncode == 0 and strict_echo_verify:
            log(
                f"  Attempt {attempt+1} published but echo verification failed: "
                f"{echo_result['stderr'] or echo_result['stdout']}"
            )
        else:
            log(f"  Attempt {attempt+1} failed: {(r.stderr or r.stdout).strip()}")
        if attempt + 1 < WIND_INJECTION_MAX_ATTEMPTS:
            sleep_s = WIND_INJECTION_RETRY_S
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    raise TimeoutError("Slot deadline exhausted during wind injection retries.")
                sleep_s = min(sleep_s, remaining)
            time.sleep(sleep_s)
    raise RuntimeError(
        f"Wind injection failed after {WIND_INJECTION_MAX_ATTEMPTS} attempts — is Gazebo running?"
    )


def parse_sdf_world_wind(world_path: Path) -> dict[str, float] | None:
    try:
        return read_world_wind(world_path)
    except (OSError, SdfWindError):
        return None


def preloaded_wind_artifact(
    x_mps: float,
    y_mps: float,
    *,
    source_world: Path,
    archived_world: Path,
    refresh_runtime_wind: bool = True,
    refresh_strict_echo_verify: bool = False,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    parsed_wind = parse_sdf_world_wind(archived_world)
    if parsed_wind is None:
        raise RuntimeError(f"Could not parse <wind><linear_velocity> from {archived_world}")
    if (
        abs(parsed_wind["x"] - x_mps) > SDF_WIND_TOLERANCE_MPS
        or abs(parsed_wind["y"] - y_mps) > SDF_WIND_TOLERANCE_MPS
        or abs(parsed_wind["z"]) > SDF_WIND_TOLERANCE_MPS
    ):
        raise RuntimeError(
            "Archived Gazebo world wind does not match requested combo: "
            f"requested=({x_mps}, {y_mps}, 0.0), parsed={parsed_wind}"
        )
    runtime_refresh_result = None
    if refresh_runtime_wind:
        log(
            "Refreshing preloaded wind on Gazebo topic "
            f"x={x_mps} m/s (East) y={y_mps} m/s (North)"
        )
        runtime_refresh_result = inject_wind(
            x_mps,
            y_mps,
            timeout_s=timeout_s,
            strict_echo_verify=refresh_strict_echo_verify,
        )
    live_wind_info = None
    if not refresh_runtime_wind and CAPTURE_WIND_INFO:
        live_timeout_s = WIND_INFO_CAPTURE_TIMEOUT_S
        if timeout_s is not None:
            live_timeout_s = min(live_timeout_s, max(0.0, timeout_s))
        if live_timeout_s > 0.0:
            live_wind_info = capture_wind_info_snapshot(live_timeout_s)
    return {
        "status": "ok",
        "method": (
            "preloaded_gazebo_world_plus_runtime_topic_refresh"
            if refresh_runtime_wind
            else "preloaded_gazebo_world"
        ),
        "wind_topic": WIND_TOPIC,
        "payload": runtime_refresh_result.get("payload") if runtime_refresh_result else None,
        "command": runtime_refresh_result.get("command") if runtime_refresh_result else None,
        "verification": (
            "Archived SDF <wind><linear_velocity> matches the requested combo; "
            "the same wind was then published to the Gazebo wind topic after heartbeat."
            if refresh_runtime_wind
            else "Gazebo was launched from an archived SDF whose <wind><linear_velocity> matches the requested combo."
        ),
        "strict_echo_verification": (
            runtime_refresh_result.get("strict_echo_verification")
            if runtime_refresh_result
            else False
        ),
        "source_world_file": str(source_world),
        "archived_world_file": str(archived_world),
        "archived_world_wind_mps": parsed_wind,
        "sdf_wind_tolerance_mps": SDF_WIND_TOLERANCE_MPS,
        "runtime_refresh_enabled": refresh_runtime_wind,
        "runtime_refresh_strict_echo_verification": refresh_strict_echo_verify,
        "runtime_refresh_result": runtime_refresh_result,
        "live_wind_info_capture_enabled": CAPTURE_WIND_INFO,
        "live_wind_info_snapshot": (
            runtime_refresh_result.get("live_wind_info_snapshot")
            if runtime_refresh_result
            else live_wind_info
        ),
        "x_wind_mps": x_mps,
        "y_wind_mps": y_mps,
    }


# ---------------------------------------------------------------------------
# Passive MAVLink monitor  (receive-only, no commands sent)
# ---------------------------------------------------------------------------

def wait_for_heartbeat(mavlink_addr: str, timeout: float) -> mavutil.mavfile:
    """Connect and wait for the first heartbeat. Returns the connection."""
    log(f"Listening for heartbeat on {mavlink_addr}  (timeout {timeout:.0f}s) …")
    master = mavutil.mavlink_connection(mavlink_addr)
    hb = master.wait_heartbeat(timeout=timeout)
    if hb is None:
        raise TimeoutError(f"No heartbeat received within {timeout:.0f}s — is SITL running?")
    log(f"Heartbeat received  sysid={master.target_system}  "
        f"mode={mavutil.mode_string_v10(hb)}")
    return master


def wait_for_vehicle_ready(
    master: mavutil.mavfile,
    timeout: float,
    *,
    force_arm: bool,
) -> None:
    """Wait until the vehicle is initialized enough for automated launch."""
    deadline = time.time() + timeout
    auto_available = False
    ready_heartbeats = 0
    gps_ready = False
    ekf_ready = False
    last_prearm_text: str | None = None
    last_prearm_at = 0.0
    while time.time() < deadline:
        mode_map = master.mode_mapping()
        if mode_map and "AUTO" in mode_map:
            auto_available = True

        msg = master.recv_match(
            type=[
                "HEARTBEAT",
                "STATUSTEXT",
                "GPS_RAW_INT",
                "EKF_STATUS_REPORT",
            ],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue

        mt = msg.get_type()
        if mt == "GPS_RAW_INT":
            fix_type = coerce_int(getattr(msg, "fix_type", None))
            satellites = coerce_int(getattr(msg, "satellites_visible", None))
            if fix_type is not None and fix_type >= 3:
                gps_ready = True
            if satellites is not None and satellites >= 6:
                gps_ready = True
            continue

        if mt == "EKF_STATUS_REPORT":
            flags = coerce_int(getattr(msg, "flags", None))
            if flags is not None:
                required = (
                    getattr(mavutil.mavlink, "EKF_ATTITUDE", 1)
                    | getattr(mavutil.mavlink, "EKF_VELOCITY_HORIZ", 2)
                    | getattr(mavutil.mavlink, "EKF_POS_HORIZ_ABS", 8)
                )
                if (flags & required) == required:
                    ekf_ready = True
            continue

        if mt == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if not text:
                continue
            lower = text.lower()
            if "prearm" in lower:
                last_prearm_at = time.time()
                last_prearm_text = text
                if not force_arm:
                    log(f"  STATUSTEXT: {text}")
            if "gps" in lower and "detected" in lower:
                gps_ready = True
            if "ekf3" in lower and "using gps" in lower:
                gps_ready = True
                ekf_ready = True
            if "ahrs: ekf3 active" in lower:
                ekf_ready = True
            continue

        mode = mavutil.mode_string_v10(msg)
        system_status = coerce_int(getattr(msg, "system_status", None))
        initialized = (
            mode not in {"INITIALISING", "INITIALIZING"}
            and system_status not in {
                mavutil.mavlink.MAV_STATE_UNINIT,
                mavutil.mavlink.MAV_STATE_BOOT,
                mavutil.mavlink.MAV_STATE_CALIBRATING,
            }
        )
        prearm_clear = force_arm or (time.time() - last_prearm_at > 2.0)

        if auto_available and initialized and prearm_clear and gps_ready and ekf_ready:
            ready_heartbeats += 1
            if ready_heartbeats >= READY_HEARTBEATS_REQUIRED:
                log("Vehicle readiness confirmed: AUTO available, GPS ready, EKF active.")
                return
        else:
            ready_heartbeats = 0

    suffix = (
        f" Last prearm text: {last_prearm_text}"
        if last_prearm_text is not None and not force_arm
        else ""
    )
    raise TimeoutError(f"Vehicle did not become ready within {timeout:.0f}s.{suffix}")


def settle_after_arm_before_auto(master: mavutil.mavfile, settle_s: float) -> None:
    """Give ArduPlane a short manual-like pause after arm before AUTO."""
    if settle_s <= 0.0:
        return
    log(f"Settling {settle_s:.1f}s after arm before AUTO.")
    deadline = time.time() + settle_s
    while time.time() < deadline:
        msg = master.recv_match(
            type=["HEARTBEAT", "STATUSTEXT"],
            blocking=True,
            timeout=min(0.5, max(0.0, deadline - time.time())),
        )
        if msg is None or msg.get_type() != "STATUSTEXT":
            continue
        text = str(getattr(msg, "text", "")).strip()
        if not text:
            continue
        lower = text.lower()
        if any(token in lower for token in ("prearm", "arm", "ekf", "gps")):
            log(f"  STATUSTEXT: {text}")


def wait_for_relative_altitude(
    master: mavutil.mavfile,
    min_relalt_m: float,
    timeout: float,
) -> None:
    """Wait until the vehicle is airborne enough for the wind stimulus."""
    if min_relalt_m <= 0.0:
        return
    log(
        f"Waiting for relative altitude >= {min_relalt_m:.1f} m "
        "before applying wind."
    )
    try:
        master.mav.request_data_stream_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_POSITION,
            2,
            1,
        )
    except Exception:
        pass
    deadline = time.time() + timeout
    best_relalt_m: float | None = None
    while time.time() < deadline:
        msg = master.recv_match(
            type=["GLOBAL_POSITION_INT", "STATUSTEXT", "HEARTBEAT"],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue
        mt = msg.get_type()
        if mt == "GLOBAL_POSITION_INT":
            relalt_m = float(getattr(msg, "relative_alt", 0)) / 1000.0
            best_relalt_m = (
                relalt_m
                if best_relalt_m is None
                else max(best_relalt_m, relalt_m)
            )
            if relalt_m >= min_relalt_m:
                log(f"Relative altitude {relalt_m:.1f} m reached; applying wind.")
                return
        elif mt == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text and any(token in text.lower() for token in ("takeoff", "reached", "mission", "ekf", "gps")):
                log(f"  STATUSTEXT: {text}")
    suffix = (
        f" Highest relative altitude seen: {best_relalt_m:.1f} m."
        if best_relalt_m is not None
        else " No GLOBAL_POSITION_INT relative altitude received."
    )
    raise TimeoutError(
        f"Vehicle did not reach {min_relalt_m:.1f} m relative altitude "
        f"within {timeout:.0f}s before wind injection.{suffix}"
    )


def mission_item_count(mission_file: Path) -> int:
    loader = mavwp.MAVWPLoader()
    loader.load(str(mission_file))
    return loader.count()


def mission_item_int(
    wp: Any,
    target_system: int,
    target_component: int,
) -> mavutil.mavlink.MAVLink_mission_item_int_message:
    """Convert a mission item to MISSION_ITEM_INT for upload."""
    if wp.get_type() == "MISSION_ITEM_INT":
        wp.target_system = target_system
        wp.target_component = target_component
        return wp

    return mavutil.mavlink.MAVLink_mission_item_int_message(
        target_system,
        target_component,
        int(wp.seq),
        int(wp.frame),
        int(wp.command),
        int(wp.current),
        int(wp.autocontinue),
        float(wp.param1),
        float(wp.param2),
        float(wp.param3),
        float(wp.param4),
        int(float(wp.x) * 1.0e7),
        int(float(wp.y) * 1.0e7),
        float(wp.z),
    )


def upload_mission(
    master: mavutil.mavfile, mission_file: Path, timeout: float
) -> list[Any]:
    """Upload a QGC WPL mission over MAVLink.

    Returns the list of MISSION_ITEM_INT messages that were sent, so the
    caller can verify the vehicle's loaded mission matches item-by-item.
    """
    if not mission_file.exists():
        raise FileNotFoundError(f"Mission file not found: {mission_file}")

    loader = mavwp.MAVWPLoader()
    loader.load(str(mission_file))
    items = [
        mission_item_int(loader.wp(idx), master.target_system, master.target_component)
        for idx in range(loader.count())
    ]
    if not items:
        raise RuntimeError(f"Mission file has no items: {mission_file}")

    log(f"Uploading mission ({len(items)} items): {mission_file}")
    master.waypoint_clear_all_send()
    # ArduPlane always responds to MISSION_CLEAR_ALL with a MISSION_ACK.
    # Drain it here so it doesn't land in the upload loop and trip the
    # "unexpected MISSION_ACK" guard (the old time.sleep(0.5) was not enough).
    _t0 = time.time()
    while time.time() - _t0 < 3.0:
        _m = master.recv_match(
            type=["MISSION_ACK", "STATUSTEXT"], blocking=True, timeout=0.3
        )
        if _m is not None and _m.get_type() == "MISSION_ACK":
            break
    master.waypoint_count_send(len(items))

    sent: set[int] = set()
    deadline = time.time() + timeout
    # Single loop: handles MISSION_REQUEST* for each item AND the final MISSION_ACK.
    # Keeping it as one loop means re-requests for the last item are served correctly
    # instead of being silently dropped by a separate second-phase loop.
    while True:
        if time.time() >= deadline:
            raise TimeoutError(
                f"Mission upload timed out after {timeout:.0f}s "
                f"(sent {len(sent)}/{len(items)} items)."
            )
        msg = master.recv_match(
            type=["MISSION_REQUEST", "MISSION_REQUEST_INT", "MISSION_ACK", "STATUSTEXT"],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue

        mt = msg.get_type()
        if mt == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text:
                lower = text.lower()
                if any(token in lower for token in ("mission", "upload", "plan")):
                    log(f"  STATUSTEXT: {text}")
            continue

        if mt == "MISSION_ACK":
            result = getattr(msg, "type", None)
            if result == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                if len(sent) == len(items):
                    log("Mission upload acknowledged.")
                    return items
                # Any ACCEPTED received before every item has been uploaded
                # is either a late CLEAR_ALL ACK or a spurious rebroadcast.
                # Ignore it regardless of how many items have been sent so
                # far — only the final ACK matching len(items) can end the
                # upload. This makes the handling protocol-based rather
                # than relying on the drain window.
                log(f"  Ignoring early MISSION_ACK (sent {len(sent)}/{len(items)})")
                continue
            raise RuntimeError(f"Mission upload failed: {msg}")

        seq = int(getattr(msg, "seq", -1))
        if seq < 0 or seq >= len(items):
            raise RuntimeError(f"Vehicle requested invalid mission item seq={seq}.")

        item = items[seq]
        item.target_system = master.target_system
        item.target_component = master.target_component
        item.seq = seq
        item.pack(master.mav)
        master.mav.send(item)
        sent.add(seq)


def verify_mission(
    master: mavutil.mavfile,
    uploaded_items: list[Any],
    timeout: float,
) -> None:
    """Download the vehicle's current mission and verify it matches ours.

    Guards against stale mission state by checking item count and all flyable
    mission items match what we just uploaded. The QGC WPL home row at seq 0
    is requested and counted, but not strict-compared because ArduPlane may
    normalize its downloaded fields even when the mission loaded correctly.
    Some commands also round-trip only the subset of params ArduPlane actually
    stores internally, so the compare is command-aware where needed. Raises on
    any mismatch so the run is aborted before arming.
    """
    expected_count = len(uploaded_items)
    log(f"Verifying mission identity ({expected_count} items) …")
    mission_type = mavutil.mavlink.MAV_MISSION_TYPE_MISSION

    master.mav.mission_request_list_send(
        master.target_system,
        master.target_component,
        mission_type,
    )

    # 1. MISSION_COUNT
    deadline = time.time() + timeout
    reported_count: int | None = None
    while time.time() < deadline:
        msg = master.recv_match(
            type=["MISSION_COUNT", "STATUSTEXT"], blocking=True, timeout=1.0,
        )
        if msg is None:
            continue
        if msg.get_type() == "MISSION_COUNT":
            reported_count = int(msg.count)
            break
    if reported_count is None:
        raise TimeoutError(
            f"Mission verification: no MISSION_COUNT received within {timeout:.0f}s."
        )
    if reported_count != expected_count:
        raise RuntimeError(
            f"Mission verification: vehicle reports {reported_count} items, "
            f"we uploaded {expected_count}."
        )

    # 2. Download each item and compare
    per_item_timeout = VERIFY_MISSION_ITEM_TIMEOUT_S
    for seq in range(expected_count):
        master.mav.mission_request_int_send(
            master.target_system,
            master.target_component,
            seq,
            mission_type,
        )
        item_deadline = time.time() + per_item_timeout
        got = None
        while time.time() < item_deadline:
            msg = master.recv_match(
                type=["MISSION_ITEM_INT", "MISSION_ITEM", "STATUSTEXT"],
                blocking=True, timeout=1.0,
            )
            if msg is None:
                continue
            mt = msg.get_type()
            if mt not in ("MISSION_ITEM_INT", "MISSION_ITEM"):
                continue
            if int(msg.seq) != seq:
                continue
            got = msg
            break
        if got is None:
            raise TimeoutError(
                f"Mission verification: no item received for seq={seq}."
            )

        want = uploaded_items[seq]
        if seq == 0 and int(getattr(want, "current", 0)) == 1:
            log(
                "  Mission verification: seq 0 is the WPL home row; "
                "skipping strict field compare."
            )
            continue

        mismatches: list[str] = []
        if int(got.command) != int(want.command):
            mismatches.append(f"command {int(got.command)}!={int(want.command)}")
        if int(got.frame) != int(want.frame):
            mismatches.append(f"frame {int(got.frame)}!={int(want.frame)}")
        if int(got.current) != int(want.current):
            mismatches.append(f"current {int(got.current)}!={int(want.current)}")
        if int(got.autocontinue) != int(want.autocontinue):
            mismatches.append(
                f"autocontinue {int(got.autocontinue)}!={int(want.autocontinue)}"
            )
        # MISSION_ITEM returns lat/lon as float degrees; MISSION_ITEM_INT as int32 (1e7 deg).
        if got.get_type() == "MISSION_ITEM_INT":
            got_x = int(got.x)
            got_y = int(got.y)
        else:
            got_x = int(round(float(got.x) * 1.0e7))
            got_y = int(round(float(got.y) * 1.0e7))
        if got_x != int(want.x):
            mismatches.append(f"x {got_x}!={int(want.x)}")
        if got_y != int(want.y):
            mismatches.append(f"y {got_y}!={int(want.y)}")
        if abs(float(got.z) - float(want.z)) > 0.01:
            mismatches.append(f"z {float(got.z):.3f}!={float(want.z):.3f}")
        param_indexes = (1, 2, 3, 4)
        if int(want.command) == mavutil.mavlink.MAV_CMD_NAV_LOITER_TO_ALT:
            # ArduPlane ingests LOITER_TO_ALT using param2/param4 and does not
            # round-trip param1 on download, so verify only the fields Plane
            # actually preserves and flies.
            param_indexes = (2, 4)
        for i in param_indexes:
            got_p = float(getattr(got, f"param{i}"))
            want_p = float(getattr(want, f"param{i}"))
            if int(want.command) == mavutil.mavlink.MAV_CMD_NAV_LAND and i == 4:
                # Plane stores LAND param4 as a direction flag and always
                # downloads it back as +/-1. Any non-negative upload value
                # collapses to +1 on readback.
                want_p = -1.0 if want_p < 0.0 else 1.0
            if abs(got_p - want_p) > 1e-3:
                mismatches.append(f"param{i} {got_p:.3f}!={want_p:.3f}")
        if mismatches:
            raise RuntimeError(
                f"Mission verification: seq {seq} differs ({'; '.join(mismatches)})."
            )

    # 3. Complete the download protocol with a final ACK.
    master.mav.mission_ack_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_MISSION_ACCEPTED,
        mission_type,
    )

    log(f"Mission identity verified: {expected_count} items match.")


def arm_vehicle(master: mavutil.mavfile, timeout: float, force_arm: bool) -> None:
    """Arm the vehicle and wait for the armed heartbeat state."""
    deadline = time.time() + timeout
    next_send = 0.0
    param2 = FORCE_ARM_MAGIC if force_arm else 0.0
    while time.time() < deadline:
        now = time.time()
        if now >= next_send:
            master.mav.command_long_send(
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1,
                param2,
                0,
                0,
                0,
                0,
                0,
            )
            next_send = now + 2.0

        msg = master.recv_match(
            type=["HEARTBEAT", "STATUSTEXT", "COMMAND_ACK"],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue

        mt = msg.get_type()
        if mt == "HEARTBEAT":
            armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            if armed:
                log(f"Vehicle armed in mode={mavutil.mode_string_v10(msg)}.")
                return
            continue

        if mt == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text:
                lower = text.lower()
                if any(token in lower for token in ("arm", "prearm", "gyro", "gps")):
                    log(f"  STATUSTEXT: {text}")
            continue

        if getattr(msg, "command", None) == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
            result = getattr(msg, "result", None)
            if result not in (
                mavutil.mavlink.MAV_RESULT_ACCEPTED,
                mavutil.mavlink.MAV_RESULT_IN_PROGRESS,
                mavutil.mavlink.MAV_RESULT_TEMPORARILY_REJECTED,
            ):
                raise RuntimeError(f"Arm command rejected: {msg}")

    raise TimeoutError(f"Vehicle did not arm within {timeout:.0f}s.")


def set_auto_mode(master: mavutil.mavfile, timeout: float) -> None:
    """Switch the vehicle to AUTO and wait until heartbeats confirm it."""
    deadline = time.time() + timeout
    next_send = 0.0
    while time.time() < deadline:
        now = time.time()
        if now >= next_send:
            master.set_mode_apm("AUTO")
            next_send = now + 2.0

        msg = master.recv_match(
            type=["HEARTBEAT", "STATUSTEXT", "COMMAND_ACK"],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue

        mt = msg.get_type()
        if mt == "HEARTBEAT":
            if mavutil.mode_string_v10(msg) == "AUTO":
                log("Vehicle entered AUTO mode.")
                return
            continue

        if mt == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text:
                lower = text.lower()
                if any(token in lower for token in ("auto", "mode", "mission")):
                    log(f"  STATUSTEXT: {text}")
            continue

        if getattr(msg, "command", None) == mavutil.mavlink.MAV_CMD_DO_SET_MODE:
            result = getattr(msg, "result", None)
            if result not in (
                mavutil.mavlink.MAV_RESULT_ACCEPTED,
                mavutil.mavlink.MAV_RESULT_IN_PROGRESS,
                mavutil.mavlink.MAV_RESULT_TEMPORARILY_REJECTED,
            ):
                raise RuntimeError(f"AUTO mode command rejected: {msg}")

    raise TimeoutError(f"Vehicle did not enter AUTO within {timeout:.0f}s.")


def monitor_until_disarm(master: mavutil.mavfile, monitor_log: Path,
                          timeout_s: float, *,
                          mission_pre_loaded: bool = False,
                          stop_on_square_loiter: bool = False) -> dict[str, Any]:
    """
    Passive listener. Records mission progress and returns when the vehicle
    DISARMS (clean landing) or the timeout expires.

    No commands are sent. The user flies the mission via MAVProxy console.
    """
    log(f"Passive monitoring started (timeout {timeout_s/60:.0f} min) …")
    log("Waiting for vehicle to ARM …")

    deadline = time.time() + timeout_s
    state: dict[str, Any] = {
        "armed_ever":            False,
        "armed_now":             False,
        "armed_before_mission_loaded": False,
        "mission_seq":           None,
        "mission_loaded":        mission_pre_loaded,
        "saw_front_half_progress": False,
        "reached":               [],
        "mission_completed_full": False,
        "square_completed":      False,
        "loiter_started":        False,
        "loiter_completed":      False,
        "landing_started":       False,
        "invalid_start_reason":  None,
        "disarm_time_utc":       None,
        "last_mode":             None,
        "statustext":            [],
        "timed_out":             False,
        "completed_square_loiter_early": False,
    }

    with monitor_log.open("a", encoding="utf-8") as fh:
        while time.time() < deadline:
            msg = master.recv_match(
                type=["HEARTBEAT", "MISSION_CURRENT",
                      "MISSION_ITEM_REACHED", "STATUSTEXT"],
                blocking=True, timeout=1.0,
            )
            if msg is None:
                continue

            mt = msg.get_type()
            fh.write(f"{utc_now()} {mt} {msg.to_dict()}\n")
            fh.flush()

            if mt == "HEARTBEAT":
                mode = mavutil.mode_string_v10(msg)
                state["last_mode"] = mode
                armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)

                if armed and not state["armed_ever"]:
                    state["armed_ever"] = True
                    state["armed_now"]  = True
                    log(f"Vehicle ARMED  mode={mode}")
                    if not state["mission_loaded"]:
                        state["armed_before_mission_loaded"] = True
                        log("WARNING: Vehicle armed before mission upload completed.")

                if not armed and state["armed_ever"] and state["armed_now"]:
                    state["armed_now"]       = False
                    state["disarm_time_utc"] = utc_now()
                    if (state["mission_seq"] is not None
                            and int(state["mission_seq"]) >= MISSION_FINAL_SEQ
                            and state["saw_front_half_progress"]):
                        state["mission_completed_full"] = True
                    log(f"Vehicle DISARMED  seq={state['mission_seq']}  "
                        f"full={state['mission_completed_full']}")
                    break   # done

            elif mt == "MISSION_CURRENT":
                seq = int(msg.seq)
                total = coerce_int(getattr(msg, "total", None))
                state["mission_seq"] = seq
                if total is not None and total >= MISSION_FINAL_SEQ:
                    state["mission_loaded"] = True

                if state["armed_now"] and state["mission_loaded"]:
                    if 1 <= seq <= MISSION_SQUARE_END_SEQ:
                        state["saw_front_half_progress"] = True
                    elif (seq >= MISSION_LOITER_SEQ
                          and not state["saw_front_half_progress"]
                          and not mission_pre_loaded):
                        # In auto mode we uploaded the mission and armed from seq=0
                        # ourselves, so a late-joining monitor that missed the
                        # front-half progression must not mis-classify the run.
                        state["invalid_start_reason"] = (
                            f"mission jumped to seq={seq} before front-half progress"
                        )
                        log(f"WARNING: {state['invalid_start_reason']}")
                        break

                if state["saw_front_half_progress"] and seq >= MISSION_LOITER_SEQ:
                    state["square_completed"] = True
                    state["loiter_started"]   = True
                if state["saw_front_half_progress"] and seq >= MISSION_LOITER_TO_ALT_SEQ:
                    state["loiter_completed"] = True
                    state["landing_started"] = True
                if stop_on_square_loiter and state["square_completed"] and state["loiter_completed"]:
                    state["completed_square_loiter_early"] = True
                    log("Square and loiter phases complete; stopping early before landing.")
                    break

            elif mt == "MISSION_ITEM_REACHED":
                seq = int(msg.seq)
                state["reached"].append(seq)
                if state["armed_now"] and state["mission_loaded"]:
                    if 1 <= seq <= MISSION_SQUARE_END_SEQ:
                        state["saw_front_half_progress"] = True
                    elif (seq >= MISSION_LOITER_SEQ
                          and not state["saw_front_half_progress"]
                          and not mission_pre_loaded):
                        state["invalid_start_reason"] = (
                            f"mission jumped to reached seq={seq} before front-half progress"
                        )
                        log(f"WARNING: {state['invalid_start_reason']}")
                        break
                if state["saw_front_half_progress"] and seq >= MISSION_SQUARE_END_SEQ:
                    state["square_completed"] = True
                if state["saw_front_half_progress"] and seq >= MISSION_LOITER_SEQ:
                    state["loiter_started"] = True
                if state["saw_front_half_progress"] and seq >= MISSION_LOITER_TO_ALT_SEQ:
                    state["loiter_completed"] = True
                    state["landing_started"] = True
                if state["saw_front_half_progress"] and seq >= MISSION_FINAL_SEQ:
                    state["mission_completed_full"] = True
                if stop_on_square_loiter and state["square_completed"] and state["loiter_completed"]:
                    state["completed_square_loiter_early"] = True
                    log("Square and loiter phases complete; stopping early before landing.")
                    break
                log(f"  Reached wp {seq}")

            elif mt == "STATUSTEXT":
                text = str(getattr(msg, "text", "")).strip()
                if text:
                    state["statustext"].append(text)
                    lower = text.lower()
                    pass_match = PASSED_WAYPOINT_RE.search(text)
                    if pass_match:
                        seq = int(pass_match.group("seq"))
                        dist_m = int(pass_match.group("dist"))
                        entry_seq = MISSION_SQUARE_START_SEQ - 1
                        if seq == entry_seq and dist_m > ENTRY_WAYPOINT_MAX_PASS_DISTANCE_M:
                            state["invalid_start_reason"] = (
                                f"entry waypoint #{seq} passed from {dist_m}m "
                                f"(limit {ENTRY_WAYPOINT_MAX_PASS_DISTANCE_M}m)"
                            )
                            log(f"WARNING: {state['invalid_start_reason']}")
                            break
                    if "flight plan received" in lower:
                        state["mission_loaded"] = True
                    if "mission complete" in lower and state["saw_front_half_progress"]:
                        state["mission_completed_full"] = True
                    if any(k in lower for k in
                           ("arm", "disarm", "auto", "reached", "mission")):
                        log(f"  STATUSTEXT: {text}")
        else:
            state["timed_out"] = True
            log("WARNING: monitoring timed out — vehicle never disarmed.")

    return state


# ---------------------------------------------------------------------------
# Log collection
# ---------------------------------------------------------------------------

def collect_bin_log(
    before_names: set[str],
    started_wall: float,
    *,
    log_dir: Path | None = None,
    strict_new_names: bool = False,
) -> Path | None:
    search_dir = log_dir if log_dir is not None else sitl_bin_dir(None)
    if not search_dir.exists():
        return None

    new_name_candidates: list[tuple[float, Path]] = []
    fallback_candidates: list[tuple[float, Path]] = []
    for p in search_dir.glob("*.BIN"):
        try:
            mtime = p.stat().st_mtime
        except FileNotFoundError:
            continue
        if p.name not in before_names:
            new_name_candidates.append((mtime, p))
            continue
        if not strict_new_names and mtime >= started_wall - 2.0:
            fallback_candidates.append((mtime, p))

    if strict_new_names:
        if not new_name_candidates:
            return None
        if len(new_name_candidates) > 1:
            raise RuntimeError(
                "Multiple new .BIN logs found in isolated SITL dir: "
                + ", ".join(sorted(str(path.name) for _, path in new_name_candidates))
            )
        return new_name_candidates[0][1]

    if new_name_candidates:
        return max(new_name_candidates, key=lambda t: t[0])[1]
    if fallback_candidates:
        return max(fallback_candidates, key=lambda t: t[0])[1]
    return None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def run_analysis(
    bin_path: Path,
    attempt_dir: Path,
    *,
    analysis_position_source: str = ANALYSIS_POSITION_SOURCE,
    slot_deadline_monotonic: float | None = None,
) -> None:
    true_out   = attempt_dir / "true_path_deviation"
    square_out = attempt_dir / "square_loiter_mission_metrics"
    env = runtime_env()
    scripts = [
        ("true_path_deviation",
         [
             preferred_python(),
             str(TRUE_PATH_SCRIPT),
             str(bin_path),
             "--position-source",
             analysis_position_source,
             "--outdir",
             str(true_out),
         ]),
        ("square_loiter_metrics",
         [
             preferred_python(),
             str(SQUARE_METRICS_SCRIPT),
             str(bin_path),
             "--position-source",
             analysis_position_source,
             "--outdir",
             str(square_out),
         ]),
    ]
    for name, cmd in scripts:
        log(f"Running {name} …")
        timeout_s = remaining_deadline_s(slot_deadline_monotonic)
        if timeout_s is not None and timeout_s <= 0.0:
            raise TimeoutError(f"Slot deadline exhausted before {name}.")
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=str(WORKSPACE_ROOT),
                env=env,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"{name} timed out before the slot deadline ({exc.timeout:.1f}s)."
            ) from exc
        (attempt_dir / f"{name}_stdout.log").write_text(r.stdout, encoding="utf-8")
        (attempt_dir / f"{name}_stderr.log").write_text(r.stderr, encoding="utf-8")
        if r.returncode != 0:
            raise RuntimeError(
                f"{name} exited {r.returncode}: {r.stderr[-400:].strip()}")
    log("Analysis complete.")


def build_run_summary(record: dict[str, Any], bin_path: Path,
                       attempt_dir: Path) -> dict[str, Any]:
    stem = bin_path.stem
    true_summary   = read_json(attempt_dir / "true_path_deviation" /
                                f"{stem}_true_path_deviation_summary.json", {})
    square_summary = read_json(attempt_dir / "square_loiter_mission_metrics" /
                                f"{stem}_square_loiter_summary.json", {})
    true_rows   = csv_rows(attempt_dir / "true_path_deviation" /
                           f"{stem}_true_path_deviation.csv")
    lap_rows    = csv_rows(attempt_dir / "square_loiter_mission_metrics" /
                           f"{stem}_square_lap_metrics.csv")
    corner_rows = csv_rows(attempt_dir / "square_loiter_mission_metrics" /
                           f"{stem}_square_corner_metrics.csv")

    square_seq_range = (
        square_summary.get("notes", {}).get("mission_expected_square_seq_range")
        if isinstance(square_summary.get("notes", {}), dict)
        else None
    )
    if (
        not isinstance(square_seq_range, list)
        or len(square_seq_range) != 2
        or any(not isinstance(v, (int, float)) for v in square_seq_range)
    ):
        square_seq_range = [MISSION_SQUARE_START_SEQ, MISSION_SQUARE_END_SEQ]
    square_seq_start = int(square_seq_range[0])
    square_seq_end = int(square_seq_range[1])

    sq_devs = np.array([
        maybe_float(r.get("true_path_dev_m"))
        for r in true_rows
        if r.get("active_leg_supported") == "True"
        and r.get("active_leg_end_seq")
        and square_seq_start <= int(r["active_leg_end_seq"]) <= square_seq_end
    ], dtype=float)
    sq_devs = sq_devs[~np.isnan(sq_devs)]

    square_ntun = np.array([
        maybe_float(r.get("ntun_abs_xt_m"))
        for r in true_rows
        if r.get("active_leg_supported") == "True"
        and r.get("active_leg_end_seq")
        and square_seq_start <= int(r["active_leg_end_seq"]) <= square_seq_end
    ], dtype=float)
    square_ntun = square_ntun[~np.isnan(square_ntun)]

    square_delta = np.array([
        maybe_float(r.get("delta_true_minus_abs_ntun_m"))
        for r in true_rows
        if r.get("active_leg_supported") == "True"
        and r.get("active_leg_end_seq")
        and square_seq_start <= int(r["active_leg_end_seq"]) <= square_seq_end
    ], dtype=float)
    square_delta = square_delta[~np.isnan(square_delta)]

    sq_overall = square_summary.get("square", {}).get("overall", {})
    by_heading = square_summary.get("square", {}).get("by_heading", {})
    loiter_pl  = square_summary.get("loiter", {})
    true_square_stats = true_summary.get("square_stats", {})
    true_full_mission_stats = (
        true_summary.get("full_mission_supported_stats")
        or true_summary.get("overall_supported_stats", {})
    )

    heading_metrics: dict[str, Any] = {
        h: {
            "samples":              int(d.get("samples", 0)),
            "mean_true_path_dev_m": clean_float(d.get("mean_true_path_dev_m")),
            "rms_true_path_dev_m":  clean_float(d.get("rms_true_path_dev_m")),
            "p95_true_path_dev_m":  clean_float(d.get("p95_true_path_dev_m")),
            "max_true_path_dev_m":  clean_float(d.get("max_true_path_dev_m")),
        }
        for h, d in by_heading.items()
    }

    corner_by_type: dict[str, list] = defaultdict(list)
    for r in corner_rows:
        corner_by_type[r.get("corner_type", "?")].append(r)
    corner_metrics = {
        ct: {
            "count": len(crows),
            "mean_min_corner_distance_m": clean_float(
                statistics.fmean(
                    [v for r in crows
                     if not math.isnan(v := maybe_float(r.get("min_corner_distance_m")))]
                ) if crows else math.nan
            ),
        }
        for ct, crows in corner_by_type.items()
    }

    directional_means = [
        h["mean_true_path_dev_m"]
        for h in heading_metrics.values()
        if h["mean_true_path_dev_m"] is not None
    ]
    dir_asym = (max(directional_means) - min(directional_means)
                if len(directional_means) >= 2 else math.nan)

    lap_rms = [
        maybe_float(r.get("rms_true_path_dev_m")) for r in lap_rows
    ]
    lap_rms_clean = [v for v in lap_rms if not math.isnan(v)]

    summary: dict[str, Any] = {
        "attempt_id":             record["attempt_id"],
        "combo_key":              record["combo_key"],
        "x_wind_mps":             record["x_wind_mps"],
        "y_wind_mps":             record["y_wind_mps"],
        "run_alias":              record.get("run_alias"),
        "status":                 record["status"],
        "mission_completed_full": bool(record.get("mission_completed_full", False)),
        "square_completed":       bool(record.get("square_completed", False)),
        "loiter_completed":       bool(record.get("loiter_completed", False)),
        "raw_log_path":           str(bin_path),
        "wind_frame":             WIND_FRAME_NOTE,
        "analysis_position_sources": {
            "true_path_deviation": true_summary.get("position_source"),
            "square_loiter_mission_metrics": square_summary.get("position_source"),
        },
        "artifacts": {
            "true_path_deviation_summary":
                str(attempt_dir / "true_path_deviation" /
                    f"{stem}_true_path_deviation_summary.json"),
            "true_path_deviation_csv":
                str(attempt_dir / "true_path_deviation" /
                    f"{stem}_true_path_deviation.csv"),
            "square_loiter_summary":
                str(attempt_dir / "square_loiter_mission_metrics" /
                    f"{stem}_square_loiter_summary.json"),
        },
        "square": {
            "overall": {
                "segment_count":        int(sq_overall.get("segment_count", 0)),
                "sample_count":         int(sq_overall.get("sample_count", 0)),
                "mean_true_path_dev_m": clean_float(sq_overall.get("mean_true_path_dev_m")),
                "rms_true_path_dev_m":  clean_float(sq_overall.get("rms_true_path_dev_m")),
                "p95_true_path_dev_m":  clean_float(sq_overall.get("p95_true_path_dev_m")),
                "p99_true_path_dev_m":  clean_float(
                    float(np.nanpercentile(sq_devs, 99)) if sq_devs.size else math.nan),
                "max_true_path_dev_m":  clean_float(sq_overall.get("max_true_path_dev_m")),
            },
            "ntun_comparison": {
                "definition": "square-only supported rows with active_leg_end_seq in 3..22",
                "mean_abs_ntun_xt_m": clean_float(
                    true_square_stats.get(
                        "mean_abs_ntun_xt_m",
                        float(np.nanmean(square_ntun)) if square_ntun.size else math.nan,
                    )),
                "mean_delta_true_minus_abs_ntun_m": clean_float(
                    float(np.nanmean(square_delta)) if square_delta.size else math.nan),
                "full_mission_supported_mean_abs_ntun_xt_m": clean_float(
                    true_full_mission_stats.get("mean_abs_ntun_xt_m")),
            },
            "lap_repeatability": {
                "count": len(lap_rows),
                "mean_rms_true_path_dev_m": clean_float(
                    statistics.fmean(lap_rms_clean) if lap_rms_clean else math.nan),
                "std_rms_true_path_dev_m": clean_float(
                    statistics.pstdev(lap_rms_clean) if len(lap_rms_clean) >= 2
                    else math.nan),
            },
            "directional_asymmetry_m": clean_float(dir_asym),
            "by_heading": heading_metrics,
            "corners":    corner_metrics,
        },
        "loiter": None,
    }

    if loiter_pl.get("available"):
        summary["loiter"] = {
            "window": {
                "start_seq": clean_int(loiter_pl.get("loiter_window_start_seq")),
                "end_seq": clean_int(loiter_pl.get("loiter_window_end_seq")),
                "start_time_s": clean_float(loiter_pl.get("loiter_window_start_time_s")),
                "end_time_s": clean_float(loiter_pl.get("loiter_window_end_time_s")),
                "status": loiter_pl.get("loiter_window_status"),
            },
            "expected_turns": clean_float(loiter_pl.get("expected_turns")),
            "turns_complete": bool(loiter_pl.get("turns_complete", False)),
            "turns_flown_total": clean_float(loiter_pl.get("turns_flown_total")),
            "turns_flown_after_capture": clean_float(loiter_pl.get("turns_flown_after_capture")),
            "completed_turns_after_capture": clean_int(loiter_pl.get("completed_turns_after_capture")),
            "full_window": {
                "definition": "loiter start through window end; includes capture/transit",
                "capture_time_s": clean_float(loiter_pl.get("capture_time_s")),
                "mean_radial_error_m": clean_float(
                    loiter_pl.get("mean_radial_error_full_window_m", loiter_pl.get("mean_radial_error_m"))),
                "rms_radial_error_m": clean_float(
                    loiter_pl.get("rms_radial_error_full_window_m", loiter_pl.get("rms_radial_error_m"))),
                "p95_abs_radial_error_m": clean_float(
                    loiter_pl.get("p95_abs_radial_error_full_window_m", loiter_pl.get("p95_abs_radial_error_m"))),
            },
            "tracking_after_capture": {
                "definition": "samples at or after loiter capture threshold",
                "samples": clean_int(loiter_pl.get("samples_after_capture")),
                "mean_radial_error_m": clean_float(loiter_pl.get("mean_radial_error_after_capture_m")),
                "rms_radial_error_m": clean_float(loiter_pl.get("rms_radial_error_after_capture_m")),
                "p95_abs_radial_error_m": clean_float(loiter_pl.get("p95_abs_radial_error_after_capture_m")),
                "fitted_radius_m": clean_float(loiter_pl.get("fitted_radius_after_capture_m")),
                "fitted_center_offset_m": clean_float(loiter_pl.get("fitted_center_offset_after_capture_m")),
            },
        }

    return summary


# ---------------------------------------------------------------------------
# Scaffold
# ---------------------------------------------------------------------------

def ensure_scaffold(root: Path) -> None:
    for sub in ("scripts", "summary"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    for x in WIND_VALUES:
        for y in WIND_VALUES:
            d = root / combo_key(x, y)
            (d / "plots").mkdir(parents=True, exist_ok=True)
            (d / "runs").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_one(
    x_wind: int,
    y_wind: int,
    rep: int,
    campaign_root: Path,
    mavlink_addr: str,
    heartbeat_timeout: float,
    mission_timeout: float,
    accept_square_only: bool,
    *,
    mission_file: Path = MISSION_FILE,
    ready_timeout: float = DEFAULT_READY_TIMEOUT,
    upload_timeout: float = DEFAULT_UPLOAD_TIMEOUT,
    arm_timeout: float = DEFAULT_ARM_TIMEOUT,
    mode_timeout: float = DEFAULT_MODE_TIMEOUT,
    manual_control: bool = True,
    force_arm: bool = True,
    wipe_eeprom: bool = True,
    require_analysis: bool = False,
    before_bin_names: set[str] | None = None,
    sitl_log_dir: Path | None = None,
    slot_deadline_monotonic: float | None = None,
    preloaded_wind_world: Path | None = None,
    preloaded_wind_refresh: bool = True,
    auto_wind_phase: str = DEFAULT_AUTO_WIND_PHASE,
    param_file_stack: Sequence[Path | str] | None = None,
) -> dict[str, Any]:
    """Run one compatibility attempt under the campaign manifest root lock."""
    with campaign_manifest_lock(campaign_root):
        return _run_one_locked(
            x_wind=x_wind,
            y_wind=y_wind,
            rep=rep,
            campaign_root=campaign_root,
            mavlink_addr=mavlink_addr,
            heartbeat_timeout=heartbeat_timeout,
            mission_timeout=mission_timeout,
            accept_square_only=accept_square_only,
            mission_file=mission_file,
            ready_timeout=ready_timeout,
            upload_timeout=upload_timeout,
            arm_timeout=arm_timeout,
            mode_timeout=mode_timeout,
            manual_control=manual_control,
            force_arm=force_arm,
            wipe_eeprom=wipe_eeprom,
            require_analysis=require_analysis,
            before_bin_names=before_bin_names,
            sitl_log_dir=sitl_log_dir,
            slot_deadline_monotonic=slot_deadline_monotonic,
            preloaded_wind_world=preloaded_wind_world,
            preloaded_wind_refresh=preloaded_wind_refresh,
            auto_wind_phase=auto_wind_phase,
            param_file_stack=param_file_stack,
        )


def _run_one_locked(
    x_wind: int,
    y_wind: int,
    rep: int,
    campaign_root: Path,
    mavlink_addr: str,
    heartbeat_timeout: float,
    mission_timeout: float,
    accept_square_only: bool,
    *,
    mission_file: Path = MISSION_FILE,
    ready_timeout: float = DEFAULT_READY_TIMEOUT,
    upload_timeout: float = DEFAULT_UPLOAD_TIMEOUT,
    arm_timeout: float = DEFAULT_ARM_TIMEOUT,
    mode_timeout: float = DEFAULT_MODE_TIMEOUT,
    manual_control: bool = True,
    force_arm: bool = True,
    wipe_eeprom: bool = True,
    require_analysis: bool = False,
    before_bin_names: set[str] | None = None,
    sitl_log_dir: Path | None = None,
    slot_deadline_monotonic: float | None = None,
    preloaded_wind_world: Path | None = None,
    preloaded_wind_refresh: bool = True,
    auto_wind_phase: str = DEFAULT_AUTO_WIND_PHASE,
    param_file_stack: Sequence[Path | str] | None = None,
) -> dict[str, Any]:
    campaign_root = campaign_root.resolve()
    mission_file = mission_file.resolve()
    effective_param_file_stack = normalize_param_file_stack(param_file_stack)
    param_provenance_rows = parameter_file_provenance(effective_param_file_stack)
    mission_contract = validate_square_wind_mission_contract(mission_file)
    if auto_wind_phase not in AUTO_WIND_PHASES:
        raise ValueError(
            f"auto_wind_phase must be one of {AUTO_WIND_PHASES}, got {auto_wind_phase!r}"
        )
    if sitl_log_dir is not None:
        sitl_log_dir = sitl_log_dir.resolve()
    if preloaded_wind_world is not None:
        preloaded_wind_world = preloaded_wind_world.resolve()
    ensure_scaffold(campaign_root)
    manifest = load_manifest(campaign_root)
    bookkeeping_changes = reconcile_manifest_bookkeeping(campaign_root, manifest)
    if bookkeeping_changes:
        for change in bookkeeping_changes:
            log(f"Bookkeeping: {change}")
        save_manifest(campaign_root, manifest)
    key = combo_key(x_wind, y_wind)

    # Skip if this rep already succeeded
    for s in combo_successes(manifest, key):
        if s.get("target_run_index") == rep:
            log(f"Rep {rep} of {key} already succeeded "
                f"({s['attempt_id']}). Nothing to do.")
            return s

    attempt_idx = next_attempt_index(campaign_root, manifest, key)
    attempt_name = attempt_id(key, rep, attempt_idx)
    copied_bin_name = named_bin_filename(key, rep, attempt_idx)
    attempt_dir = combo_runs_dir(campaign_root, key) / attempt_key(attempt_idx)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    archived_preloaded_wind_world = (
        attempt_dir / "gazebo_world.sdf"
        if preloaded_wind_world is not None
        else None
    )
    monitor_log = attempt_dir / "monitor.log"

    start_wall = time.time()

    # Snapshot existing BIN files. Callers that can snapshot *before* SITL
    # launches (the round-robin runner) should pass before_bin_names so the
    # new log is identified by name rather than by the mtime fallback.
    bin_search_dir = sitl_bin_dir(sitl_log_dir)
    before_bins: set[str] = (
        set(before_bin_names) if before_bin_names is not None
        else (
            {p.name for p in bin_search_dir.glob("*.BIN")}
            if bin_search_dir.exists() else set()
        )
    )

    record: dict[str, Any] = {
        "attempt_id":              attempt_name,
        "combo_key":               key,
        "x_wind_mps":              x_wind,
        "y_wind_mps":              y_wind,
        "target_run_index":        rep,
        "attempt_index":           attempt_idx,
        "status":                  "running",
        "success_class":           None,
        "mission_completed_full":  False,
        "square_completed":        False,
        "loiter_completed":        False,
        "analysis_status":         "pending",
        "raw_log_path":            None,
        "attempt_dir":             str(attempt_dir),
        "run_alias":               None,
        "start_time_utc":          utc_now(),
        "end_time_utc":            None,
        "duration_wall_s":         None,
        "mission_contract":         mission_contract.as_dict(),
        "param_file_provenance":    param_provenance_rows,
        "notes":                   [],
    }
    manifest["attempts"].append(record)
    save_manifest(campaign_root, manifest)

    try:
        if preloaded_wind_world is not None:
            world_default_wind_mps = {"x": float(x_wind), "y": float(y_wind), "z": 0.0}
            wind_injection_source = (
                "generated Gazebo world launched with static <wind><linear_velocity>, "
                + (
                    f"then refreshed via Gazebo wind topic during {auto_wind_phase}"
                    if preloaded_wind_refresh
                    else "with no runtime wind topic refresh"
                )
            )
        else:
            world_default_wind_mps = {"x": 0.0, "y": 0.0, "z": 0.0}
            wind_injection_source = (
                f"run_one.py via Gazebo wind topic during {auto_wind_phase}"
                if not manual_control
                else "run_one.py via Gazebo wind topic before user mission control"
            )

        write_json(attempt_dir / "run_config.json", {
            "attempt_id":                     attempt_name,
            "experiment_lane":                CTE_LANE_NAME,
            "x_wind_mps":                     x_wind,
            "y_wind_mps":                     y_wind,
            "target_run_index":               rep,
            "attempt_index":                  attempt_idx,
            "world_name":                     WORLD_NAME,
            "wind_topic":                     WIND_TOPIC,
            "wind_info_topic":                WIND_INFO_TOPIC,
            "wind_frame":                     WIND_FRAME_NOTE,
            "world_default_wind_mps":         world_default_wind_mps,
            "wind_injection_source":          wind_injection_source,
            "gazebo_world_file":              str(preloaded_wind_world) if preloaded_wind_world is not None else None,
            "archived_gazebo_world_file":     str(archived_preloaded_wind_world) if archived_preloaded_wind_world is not None else None,
            "preloaded_wind_refresh":         preloaded_wind_refresh if preloaded_wind_world is not None else None,
            "mission_file":                   str(mission_file),
            "mission_contract":               mission_contract.as_dict(),
            "analysis_position_source":       ANALYSIS_POSITION_SOURCE,
            "expected_named_bin_file":        copied_bin_name,
            "bin_collection_method":         (
                "isolated_sitl_use_dir"
                if sitl_log_dir is not None
                else "launcher_var_use_dir_snapshot_with_mtime_fallback"
            ),
            "mavlink_addr":                   mavlink_addr,
            "mission_timeout_s":              mission_timeout,
            "sitl_launch_command":            CTE_SITL_COMMAND,
            "sitl_use_dir":                   str(sitl_log_dir) if sitl_log_dir is not None else None,
            "sitl_bin_dir":                   str(bin_search_dir),
            "gazebo_launch_command":          CTE_GAZEBO_COMMAND,
            "gazebo_plugin_runtime":          gazebo_plugin_diagnostics(),
            "sitl_wipe_eeprom_expected":      wipe_eeprom,
            "param_files_loaded_at_sitl_start": effective_param_file_stack,
            "param_file_provenance":          param_provenance_rows,
            "param_stack_order_note":         "Files are applied in listed order; later files override earlier ones.",
            "local_param_override_present":   any(
                Path(path).name == PLANE_PARAM_LOCAL_OVERRIDE.name
                for path in effective_param_file_stack
            ),
            "manual_control":                 manual_control,
            "force_arm":                      force_arm,
            "auto_wind_phase":                auto_wind_phase if not manual_control else None,
            "auto_arm_to_auto_settle_s":       AUTO_ARM_TO_AUTO_SETTLE_S if not manual_control else 0.0,
            "auto_wind_injection_min_relalt_m": (
                AUTO_WIND_INJECTION_MIN_RELALT_M
                if (not manual_control and auto_wind_phase == "after-takeoff")
                else None
            ),
            "auto_wind_injection_alt_timeout_s": (
                AUTO_WIND_INJECTION_ALT_TIMEOUT_S
                if (not manual_control and auto_wind_phase == "after-takeoff")
                else None
            ),
            "entry_waypoint_max_pass_distance_m": ENTRY_WAYPOINT_MAX_PASS_DISTANCE_M,
        })
        shutil.copy2(mission_file, attempt_dir / mission_file.name)
        if preloaded_wind_world is not None:
            if not preloaded_wind_world.exists():
                raise FileNotFoundError(f"Preloaded wind world does not exist: {preloaded_wind_world}")
            shutil.copy2(preloaded_wind_world, archived_preloaded_wind_world)

        wind_injection_written = False

        def apply_requested_wind(application_phase: str) -> None:
            nonlocal wind_injection_written
            if wind_injection_written:
                raise RuntimeError("Wind injection artifact was already written for this attempt.")
            if preloaded_wind_world is not None:
                log(
                    "Wind preloaded in Gazebo world "
                    f"x={float(x_wind)} m/s (East) y={float(y_wind)} m/s (North)"
                )
                wind_injection_result = preloaded_wind_artifact(
                    float(x_wind),
                    float(y_wind),
                    source_world=preloaded_wind_world,
                    archived_world=archived_preloaded_wind_world,
                    refresh_runtime_wind=preloaded_wind_refresh,
                    refresh_strict_echo_verify=STRICT_WIND_ECHO_VERIFY,
                    timeout_s=remaining_deadline_s(slot_deadline_monotonic),
                )
            else:
                wind_injection_result = inject_wind(
                    float(x_wind),
                    float(y_wind),
                    timeout_s=remaining_deadline_s(slot_deadline_monotonic),
                )
            wind_injection_result["application_phase"] = application_phase
            wind_injection_result["auto_wind_phase"] = (
                auto_wind_phase if not manual_control else None
            )
            write_json(attempt_dir / "wind_injection.json", wind_injection_result)
            note_once(
                record,
                "wind_injection_artifact="
                + str(attempt_dir / "wind_injection.json"),
            )
            wind_injection_written = True

        # ── Step 1: confirm Gazebo + SITL are up ─────────────────────────
        master = wait_for_heartbeat(
            mavlink_addr,
            clamp_timeout_to_slot(
                heartbeat_timeout,
                slot_deadline_monotonic,
                phase="heartbeat wait",
            ),
        )
        if not manual_control:
            # Only gate on AUTO mode availability in auto mode; manual mode
            # never sends MAVLink commands, so the gate is not needed and
            # would add a new timeout-based failure path to the old workflow.
            wait_for_vehicle_ready(
                master,
                clamp_timeout_to_slot(
                    ready_timeout,
                    slot_deadline_monotonic,
                    phase="vehicle readiness",
                ),
                force_arm=force_arm,
            )

        # ── Step 2: either instruct the user or automate mission control ─
        if manual_control:
            apply_requested_wind("manual-before-user-mission-control")
            print()
            print("=" * 60)
            print("  ACTION REQUIRED — type these in your MAVProxy console:")
            print("=" * 60)
            print(f"  1. wp load {mission_file}")
            print('  2. wait for "Flight plan received"')
            print( "  3. arm throttle force")
            print( "  4. mode AUTO")
            print("=" * 60)
            print()
            log("Waiting for vehicle to arm and fly …")
        else:
            if preloaded_wind_world is not None and not preloaded_wind_refresh:
                apply_requested_wind("auto-startup-preloaded-only")
            elif auto_wind_phase == "before-arm":
                apply_requested_wind("auto-before-arm")

            uploaded_items = upload_mission(
                master,
                mission_file,
                clamp_timeout_to_slot(
                    upload_timeout,
                    slot_deadline_monotonic,
                    phase="mission upload",
                ),
            )
            verify_mission(
                master,
                uploaded_items,
                clamp_timeout_to_slot(
                    upload_timeout,
                    slot_deadline_monotonic,
                    phase="mission verification",
                ),
            )
            arm_vehicle(
                master,
                clamp_timeout_to_slot(
                    arm_timeout,
                    slot_deadline_monotonic,
                    phase="vehicle arm",
                ),
                force_arm=force_arm,
            )
            settle_after_arm_before_auto(
                master,
                clamp_timeout_to_slot(
                    AUTO_ARM_TO_AUTO_SETTLE_S,
                    slot_deadline_monotonic,
                    phase="post-arm AUTO settle",
                    reserve_s=BIN_FLUSH_DELAY_S + ANALYSIS_HEADROOM_S,
                ),
            )
            set_auto_mode(
                master,
                clamp_timeout_to_slot(
                    mode_timeout,
                    slot_deadline_monotonic,
                    phase="AUTO mode switch",
                ),
            )
            log("Mission uploaded and vehicle launched automatically.")
            if auto_wind_phase == "after-takeoff" and not wind_injection_written:
                wait_for_relative_altitude(
                    master,
                    AUTO_WIND_INJECTION_MIN_RELALT_M,
                    clamp_timeout_to_slot(
                        AUTO_WIND_INJECTION_ALT_TIMEOUT_S,
                        slot_deadline_monotonic,
                        phase="pre-wind takeoff altitude wait",
                        reserve_s=BIN_FLUSH_DELAY_S + ANALYSIS_HEADROOM_S,
                    ),
                )
                apply_requested_wind("auto-after-takeoff")

        # ── Step 3: passive monitor until DISARM ─────────────────────────
        state = monitor_until_disarm(
            master,
            monitor_log,
            clamp_timeout_to_slot(
                mission_timeout,
                slot_deadline_monotonic,
                phase="mission monitor",
                reserve_s=BIN_FLUSH_DELAY_S + ANALYSIS_HEADROOM_S,
            ),
            mission_pre_loaded=not manual_control,
            stop_on_square_loiter=accept_square_only,
        )

        record["mission_completed_full"] = bool(state.get("mission_completed_full", False))
        record["square_completed"]       = bool(state.get("square_completed", False))
        record["loiter_completed"]       = bool(state.get("loiter_completed", False))
        if state.get("completed_square_loiter_early"):
            note_once(record, "completed_square_loiter_early")
        if state.get("timed_out"):
            record["notes"].append("mission_timed_out")
        if state.get("armed_before_mission_loaded"):
            note_once(record, "armed_before_mission_loaded")
        if state.get("invalid_start_reason"):
            note_once(record, f"invalid_start: {state['invalid_start_reason']}")
        if state.get("statustext"):
            record["notes"].append(f"last_statustext={state['statustext'][-3:]}")

        # ── Step 5: collect log ───────────────────────────────────────────
        if state.get("completed_square_loiter_early"):
            cleanup_stack_for_analysis()
        # Small wait so SITL flushes the log to disk
        flush_wait_s = clamp_timeout_to_slot(
            BIN_FLUSH_DELAY_S,
            slot_deadline_monotonic,
            phase="BIN flush wait",
            reserve_s=ANALYSIS_HEADROOM_S,
        )
        time.sleep(flush_wait_s)
        bin_path = collect_bin_log(
            before_bins,
            start_wall,
            log_dir=bin_search_dir,
            strict_new_names=sitl_log_dir is not None,
        )
        if bin_path is None:
            raise RuntimeError(
                f"No new .BIN log found in {bin_search_dir} — did SITL write a log?"
            )
        log(f"BIN log: {bin_path}")
        dest_bin = attempt_dir / copied_bin_name
        shutil.copy2(bin_path, dest_bin)
        record["raw_log_path"] = str(dest_bin)
        record["notes"].append(f"source_bin_name={bin_path.name}")
        record["notes"].append(
            "bin_collection_method="
            + (
                "isolated_sitl_use_dir"
                if sitl_log_dir is not None
                else "launcher_var_use_dir_snapshot_with_mtime_fallback"
            )
        )
        log(f"Copied BIN to: {dest_bin}")

        # ── Step 6: classify success ──────────────────────────────────────
        full = record["mission_completed_full"]
        sq   = record["square_completed"]
        loiter_done = record["loiter_completed"]

        invalid_start_reason_value = state.get("invalid_start_reason")
        invalid_start_reason = (
            str(invalid_start_reason_value).strip()
            if invalid_start_reason_value is not None
            else ""
        )

        if invalid_start_reason:
            status, cls = "failed", None
            record["notes"].append(f"invalid_start_reason={invalid_start_reason}")
        elif full:
            status, cls = "success_full", "full_mission"
        elif sq and loiter_done and accept_square_only:
            status, cls = "success_square_only", "square_loiter_only"
        else:
            status, cls = "failed", None
            record["notes"].append(
                "full="
                f"{full} square={sq} loiter_completed={loiter_done} "
                f"accept_square_only={accept_square_only}"
            )

        record["status"] = status
        record["success_class"] = cls

        # ── Step 7: analysis (successes only) ────────────────────────────
        if status in SUCCESS_STATUSES:
            record["run_alias"] = run_alias(rep)
            try:
                ensure_run_alias_link(
                    combo_runs_dir(campaign_root, key) / str(record["run_alias"]),
                    attempt_dir,
                )
                run_analysis(
                    dest_bin,
                    attempt_dir,
                    analysis_position_source=ANALYSIS_POSITION_SOURCE,
                    slot_deadline_monotonic=slot_deadline_monotonic,
                )
                record["analysis_status"] = "done"

                try:
                    rsum = build_run_summary(record, dest_bin, attempt_dir)
                    write_json(attempt_dir / "run_summary.json", rsum)
                    log("run_summary.json written.")
                except Exception as exc:
                    log(f"WARNING: run_summary.json failed: {exc}")
                    record["analysis_status"] = ANALYSIS_PARTIAL_RUN_SUMMARY_FAILED
                    note_once(record, f"run_summary_failed: {summarize_exception_text(exc)}")

            except Exception as exc:
                log(f"Analysis failed: {exc}")
                record["analysis_status"] = f"failed: {summarize_exception_text(exc)}"
                note_once(record, f"analysis_error: {summarize_exception_text(exc)}")
        else:
            record["analysis_status"] = ANALYSIS_NOT_RUN
            log(f"Run status={status} — skipping analysis.")

        # With require_analysis, a mission-success whose analysis did not fully
        # complete must free its rep slot. Otherwise the retry would be assigned
        # a shifted rep number (run_02 onward) and the final campaign would be
        # missing run_01. Downgrade the status and drop the alias so a fresh
        # attempt can take this rep cleanly.
        if (require_analysis
                and record["status"] in SUCCESS_STATUSES
                and record["analysis_status"] != "done"):
            old_alias = record.get("run_alias")
            if old_alias:
                alias_link = combo_runs_dir(campaign_root, key) / str(old_alias)
                if alias_link.is_symlink():
                    alias_link.unlink()
            record["run_alias"] = None
            record["status"] = "failed_analysis"
            record["success_class"] = None
            note_once(record, "downgraded_to_failed_analysis_for_require_analysis")
            log(f"Downgraded to failed_analysis "
                f"(analysis_status={record['analysis_status']}) so rep {rep} "
                f"slot remains free for retry.")

    except Exception as exc:
        log(f"ERROR: {exc}")
        record["status"] = "error"
        if str(record.get("analysis_status", "")).strip() in {"", "pending"}:
            record["analysis_status"] = ANALYSIS_NOT_RUN
        note_once(record, f"exception: {summarize_exception_text(exc)}")
    finally:
        record["end_time_utc"]    = utc_now()
        record["duration_wall_s"] = round(time.time() - start_wall, 1)
        save_manifest(campaign_root, manifest)
        save_campaign_summary(campaign_root, manifest)

    log(f"Done.  status={record['status']}  "
        f"duration={record['duration_wall_s']}s")
    log(f"Attempt dir: {attempt_dir}")
    if str(record["status"]).startswith("success"):
        play_success_sound()
    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--x",  type=int, required=True, choices=WIND_VALUES,
                   metavar="X", help="East wind component (m/s)")
    p.add_argument("--y",  type=int, required=True, choices=WIND_VALUES,
                   metavar="Y", help="North wind component (m/s)")
    p.add_argument("--rep", type=int, required=True,
                   metavar="N", help=f"Repetition index 1..{RUNS_PER_COMBO}")
    p.add_argument("--campaign-root", type=Path, default=DEFAULT_CAMPAIGN_ROOT,
                   metavar="DIR")
    p.add_argument("--mission-file", type=Path, default=MISSION_FILE,
                   metavar="FILE")
    p.add_argument("--mavlink", type=str, default=DEFAULT_MAVLINK,
                   metavar="ADDR",
                   help=f"MAVLink receive address (default: {DEFAULT_MAVLINK}). "
                        f"Matches --out=udp:127.0.0.1:14551 in launch.sh plane-cte.")
    p.add_argument("--heartbeat-timeout", type=float, default=DEFAULT_HEARTBEAT_TIMEOUT)
    p.add_argument("--mission-timeout",   type=float, default=DEFAULT_MISSION_TIMEOUT)
    p.add_argument("--ready-timeout", type=float, default=DEFAULT_READY_TIMEOUT)
    p.add_argument("--upload-timeout", type=float, default=DEFAULT_UPLOAD_TIMEOUT)
    p.add_argument("--arm-timeout", type=float, default=DEFAULT_ARM_TIMEOUT)
    p.add_argument("--mode-timeout", type=float, default=DEFAULT_MODE_TIMEOUT)
    p.add_argument(
        "--accept-square-only",
        action="store_true",
        help=(
            "Stop after the square and loiter phases are complete and accept "
            "the run even if landing later would fail."
        ),
    )
    p.add_argument("--auto", action="store_true",
                   help="Upload the mission, arm, and switch to AUTO via MAVLink.")
    p.add_argument(
        "--auto-wind-phase",
        choices=AUTO_WIND_PHASES,
        default=DEFAULT_AUTO_WIND_PHASE,
        help=(
            "When --auto is used, choose when runtime topic wind is applied. "
            "Default: after-takeoff."
        ),
    )
    p.add_argument(
        "--preloaded-wind-world",
        type=Path,
        default=None,
        metavar="SDF",
        help="Gazebo world already containing the requested <wind><linear_velocity>.",
    )
    p.add_argument(
        "--no-preloaded-wind-refresh",
        action="store_true",
        help="With --preloaded-wind-world, validate the SDF only and skip runtime topic refresh.",
    )
    p.add_argument("--no-force-arm", action="store_true")
    args = p.parse_args()

    if not (1 <= args.rep <= RUNS_PER_COMBO):
        sys.exit(f"ERROR: --rep must be 1..{RUNS_PER_COMBO}")

    print()
    log("=" * 60)
    log("Square Wind Matrix — run_one.py")
    log(f"  Wind : x={args.x} m/s (East)   y={args.y} m/s (North)")
    log(f"  Rep  : {args.rep}/{RUNS_PER_COMBO}")
    log(f"  Listen: {args.mavlink}")
    log(f"  Control: {'auto' if args.auto else 'manual'}")
    if args.auto:
        log(f"  Auto wind phase: {args.auto_wind_phase}")
    if args.preloaded_wind_world is not None:
        log(f"  Preloaded world: {args.preloaded_wind_world}")
    log("=" * 60)
    print()
    if args.auto:
        log("This run will upload the mission and launch AUTO over MAVLink.")
    else:
        log("Make sure these are running:")
        log(f"  Terminal A:  {CTE_SITL_COMMAND}")
        log(f"  Terminal B:  {CTE_GAZEBO_COMMAND}")
    print()

    run_one(
        x_wind=args.x,
        y_wind=args.y,
        rep=args.rep,
        campaign_root=args.campaign_root,
        mission_file=args.mission_file,
        mavlink_addr=args.mavlink,
        heartbeat_timeout=args.heartbeat_timeout,
        mission_timeout=args.mission_timeout,
        ready_timeout=args.ready_timeout,
        upload_timeout=args.upload_timeout,
        arm_timeout=args.arm_timeout,
        mode_timeout=args.mode_timeout,
        accept_square_only=args.accept_square_only,
        manual_control=not args.auto,
        force_arm=not args.no_force_arm,
        preloaded_wind_world=args.preloaded_wind_world,
        preloaded_wind_refresh=not args.no_preloaded_wind_refresh,
        auto_wind_phase=args.auto_wind_phase,
    )


if __name__ == "__main__":
    main()
