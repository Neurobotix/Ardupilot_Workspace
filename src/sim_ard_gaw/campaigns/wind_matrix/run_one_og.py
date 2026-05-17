#!/usr/bin/env python3
"""
run_one.py — Wind injector + passive mission monitor for the Square Wind Matrix campaign.

Design principle: this script NEVER sends MAVLink commands to the vehicle.
It only injects wind via gz topic and then passively watches the MAVLink stream
until the mission finishes (vehicle DISARMS). The user retains full control
via the MAVProxy console — zero competition, zero conflicts.

Workflow
--------
Terminal A:  scripts/ops/launch.sh plane-cte        ← MAVProxy / SITL for the CTE lane
Terminal B:  scripts/ops/launch.sh gazebo-plane-cte ← calm-by-default CTE world

Terminal C:  python run_one.py --x 0 --y 4 --rep 1
             → confirms sim is alive (reads one heartbeat)
             → injects wind
             → prints 3 commands to type in Terminal A
             → waits passively until vehicle DISARMS after landing

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
from typing import Any

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = tempfile.mkdtemp(prefix="mplcfg_")
import matplotlib
matplotlib.use("Agg")
import numpy as np
from pymavlink import mavutil

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
DEFAULT_CTE_SITL_BIN_DIR = VAR_ROOT / "runs" / "sitl" / "plane-cte" / "logs"
VENV_PYTHON       = WORKSPACE_ROOT / "env" / "bin" / "python3"
WORKSPACE_GAZEBO_PLUGIN_DIR = WORKSPACE_ROOT / "build" / "ardupilot_gazebo"
WORKSPACE_GAZEBO_PLUGIN_FILE = WORKSPACE_GAZEBO_PLUGIN_DIR / "libArduPilotPlugin.so"

TRUE_PATH_SCRIPT      = ANALYSIS_ROOT / "true_path_deviation.py"
SQUARE_METRICS_SCRIPT = ANALYSIS_ROOT / "square_loiter_mission_metrics.py"
MISSION_FILE          = ASSETS_ROOT / "missions" / "square_500m_five_laps_loiter5_land.waypoints"
DEFAULT_CAMPAIGN_ROOT = VAR_ROOT / "logs" / "009_Square_Wind_Matrix_CTE"
PLANE_BASE_PARAM_FILE = CONFIG_ROOT / "vehicles" / "plane_base.parm"
PLANE_AIRSPEED_PARAM_FILE = CONFIG_ROOT / "overlays" / "plane_airspeed.parm"
PLANE_PARAM_LOCAL_OVERRIDE = WORKSPACE_ROOT / ".private" / "config" / "plane_params.local.parm"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WORLD_NAME   = "mini_talon_wind_runway"
WIND_TOPIC   = f"/world/{WORLD_NAME}/wind/"
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
STACK_CLEANUP_TIMEOUT_S = 30.0

# Mission layout for square_500m_five_laps_loiter5_land.waypoints.
MISSION_SQUARE_START_SEQ = 3
MISSION_SQUARE_END_SEQ = 22
MISSION_LOITER_SEQ = 23
MISSION_LOITER_TO_ALT_SEQ = 25
MISSION_FINAL_SEQ = 29

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
    env.setdefault("GZ_SIM_RESOURCE_PATH",
                   ":".join(str(p) for p in resource_paths if p.exists()))
    if not WORKSPACE_GAZEBO_PLUGIN_FILE.exists():
        raise RuntimeError(
            "Workspace Gazebo plugin build is required and missing: "
            f"{WORKSPACE_GAZEBO_PLUGIN_FILE}. Installed plugin fallback is forbidden."
        )
    env["GZ_SIM_SYSTEM_PLUGIN_PATH"] = str(WORKSPACE_GAZEBO_PLUGIN_DIR)
    path_parts = env.get("PATH", "").split(":")
    for extra in [str(ARDUPILOT_ROOT / "Tools" / "autotest"),
                  str(VENV_PYTHON.parent)]:
        if extra and extra not in path_parts:
            path_parts.insert(0, extra)
    env["PATH"] = ":".join(path_parts)
    return env


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
        "target_run_index", "attempt_index", "status", "success_class",
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


def combo_successes(manifest: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [
        a for a in manifest.get("attempts", [])
        if a.get("combo_key") == key
        and a.get("status") in SUCCESS_STATUSES
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

def inject_wind(x_mps: float, y_mps: float) -> None:
    payload = f"linear_velocity:{{x:{x_mps:.3f},y:{y_mps:.3f},z:0.000}}, enable_wind:true"
    cmd = ["gz", "topic", "-t", WIND_TOPIC, "-m", "gz.msgs.Wind", "-p", payload]
    log(f"Injecting wind  x={x_mps} m/s (East)  y={y_mps} m/s (North)")
    log(f"  {shlex.join(cmd)}")
    for attempt in range(8):
        r = subprocess.run(cmd, capture_output=True, text=True,
                           check=False, env=runtime_env())
        if r.returncode == 0:
            log("Wind injection OK.")
            return
        log(f"  Attempt {attempt+1} failed: {(r.stderr or r.stdout).strip()}")
        time.sleep(1.5)
    raise RuntimeError("Wind injection failed after 8 attempts — is Gazebo running?")


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


def monitor_until_disarm(master: mavutil.mavfile, monitor_log: Path,
                          timeout_s: float, *,
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
        "mission_loaded":        False,
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
                    elif seq >= MISSION_LOITER_SEQ and not state["saw_front_half_progress"]:
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
                    elif seq >= MISSION_LOITER_SEQ and not state["saw_front_half_progress"]:
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

def collect_bin_log(before_names: set[str], started_wall: float) -> Path | None:
    candidates = []
    for p in DEFAULT_CTE_SITL_BIN_DIR.glob("*.BIN"):
        try:
            mtime = p.stat().st_mtime
        except FileNotFoundError:
            continue
        if p.name not in before_names or mtime >= started_wall - 2.0:
            candidates.append((mtime, p))
    if not candidates:
        return None
    return max(candidates, key=lambda t: t[0])[1]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def run_analysis(bin_path: Path, attempt_dir: Path) -> None:
    true_out   = attempt_dir / "true_path_deviation"
    square_out = attempt_dir / "square_loiter_mission_metrics"
    env = runtime_env()
    scripts = [
        ("true_path_deviation",
         [preferred_python(), str(TRUE_PATH_SCRIPT), str(bin_path), "--outdir", str(true_out)]),
        ("square_loiter_metrics",
         [preferred_python(), str(SQUARE_METRICS_SCRIPT), str(bin_path), "--outdir", str(square_out)]),
    ]
    for name, cmd in scripts:
        log(f"Running {name} …")
        r = subprocess.run(cmd, capture_output=True, text=True,
                           check=False, cwd=str(WORKSPACE_ROOT), env=env)
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

    delta = np.array([
        maybe_float(r.get("delta_true_minus_abs_ntun_m"))
        for r in true_rows
        if r.get("active_leg_supported") == "True"
    ], dtype=float)
    delta = delta[~np.isnan(delta)]

    sq_overall = square_summary.get("square", {}).get("overall", {})
    by_heading = square_summary.get("square", {}).get("by_heading", {})
    loiter_pl  = square_summary.get("loiter", {})

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
                "mean_abs_ntun_xt_m": clean_float(
                    true_summary.get("overall_supported_stats", {})
                    .get("mean_abs_ntun_xt_m")),
                "mean_delta_true_minus_abs_ntun_m": clean_float(
                    float(np.nanmean(delta)) if delta.size else math.nan),
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
            "capture_time_s":        clean_float(loiter_pl.get("capture_time_s")),
            "mean_radial_error_m":   clean_float(loiter_pl.get("mean_radial_error_m")),
            "rms_radial_error_m":    clean_float(loiter_pl.get("rms_radial_error_m")),
            "p95_abs_radial_error_m": clean_float(loiter_pl.get("p95_abs_radial_error_m")),
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
) -> None:
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
            return

    attempt_idx = next_attempt_index(campaign_root, manifest, key)
    attempt_name = attempt_id(key, rep, attempt_idx)
    copied_bin_name = named_bin_filename(key, rep, attempt_idx)
    attempt_dir = combo_runs_dir(campaign_root, key) / attempt_key(attempt_idx)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    monitor_log = attempt_dir / "monitor.log"

    start_wall = time.time()

    # Snapshot existing BIN files
    before_bins: set[str] = (
        {p.name for p in DEFAULT_CTE_SITL_BIN_DIR.glob("*.BIN")}
        if DEFAULT_CTE_SITL_BIN_DIR.exists() else set()
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
        "notes":                   [],
    }
    manifest["attempts"].append(record)
    save_manifest(campaign_root, manifest)

    try:
        write_json(attempt_dir / "run_config.json", {
            "attempt_id":                     attempt_name,
            "experiment_lane":                CTE_LANE_NAME,
            "x_wind_mps":                     x_wind,
            "y_wind_mps":                     y_wind,
            "target_run_index":               rep,
            "attempt_index":                  attempt_idx,
            "world_name":                     WORLD_NAME,
            "wind_topic":                     WIND_TOPIC,
            "wind_frame":                     WIND_FRAME_NOTE,
            "world_default_wind_mps":         {"x": 0.0, "y": 0.0, "z": 0.0},
            "wind_injection_source":          "run_one.py via Gazebo wind topic",
            "mission_file":                   str(MISSION_FILE),
            "expected_named_bin_file":        copied_bin_name,
            "mavlink_addr":                   mavlink_addr,
            "mission_timeout_s":              mission_timeout,
            "sitl_launch_command":            CTE_SITL_COMMAND,
            "gazebo_launch_command":          CTE_GAZEBO_COMMAND,
            "sitl_wipe_eeprom_expected":      True,
            "param_files_loaded_at_sitl_start": cte_param_file_stack(),
            "param_stack_order_note":         "Files are applied in listed order; later files override earlier ones.",
            "local_param_override_present":   PLANE_PARAM_LOCAL_OVERRIDE.exists(),
        })
        shutil.copy2(MISSION_FILE, attempt_dir / MISSION_FILE.name)

        # ── Step 1: confirm Gazebo + SITL are up ─────────────────────────
        master = wait_for_heartbeat(mavlink_addr, heartbeat_timeout)

        # ── Step 2: inject wind ───────────────────────────────────────────
        inject_wind(float(x_wind), float(y_wind))

        # ── Step 3: tell user what to type in MAVProxy ────────────────────
        print()
        print("=" * 60)
        print("  ACTION REQUIRED — type these in your MAVProxy console:")
        print("=" * 60)
        print(f"  1. wp load {MISSION_FILE}")
        print('  2. wait for "Flight plan received"')
        print( "  3. arm throttle force")
        print( "  4. mode AUTO")
        print("=" * 60)
        print()
        log("Waiting for vehicle to arm and fly …")

        # ── Step 4: passive monitor until DISARM ─────────────────────────
        state = monitor_until_disarm(
            master,
            monitor_log,
            mission_timeout,
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
        time.sleep(3.0)
        bin_path = collect_bin_log(before_bins, start_wall)
        if bin_path is None:
            raise RuntimeError(
                "No new .BIN log found — did SITL write a log?  "
                f"Check {DEFAULT_CTE_SITL_BIN_DIR}/")
        log(f"BIN log: {bin_path}")
        dest_bin = attempt_dir / copied_bin_name
        shutil.copy2(bin_path, dest_bin)
        record["raw_log_path"] = str(dest_bin)
        record["notes"].append(f"source_bin_name={bin_path.name}")
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
                run_analysis(dest_bin, attempt_dir)
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

    log(f"Done.  status={record['status']}  "
        f"duration={record['duration_wall_s']}s")
    log(f"Attempt dir: {attempt_dir}")
    if str(record["status"]).startswith("success"):
        play_success_sound()


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
    p.add_argument("--mavlink", type=str, default=DEFAULT_MAVLINK,
                   metavar="ADDR",
                   help=f"MAVLink receive address (default: {DEFAULT_MAVLINK}). "
                        f"Matches --out=udp:127.0.0.1:14551 in launch.sh plane-cte.")
    p.add_argument("--heartbeat-timeout", type=float, default=DEFAULT_HEARTBEAT_TIMEOUT)
    p.add_argument("--mission-timeout",   type=float, default=DEFAULT_MISSION_TIMEOUT)
    p.add_argument(
        "--accept-square-only",
        action="store_true",
        help=(
            "Stop after the square and loiter phases are complete and accept "
            "the run even if landing later would fail."
        ),
    )
    args = p.parse_args()

    if not (1 <= args.rep <= RUNS_PER_COMBO):
        sys.exit(f"ERROR: --rep must be 1..{RUNS_PER_COMBO}")

    print()
    log("=" * 60)
    log("Square Wind Matrix — run_one.py")
    log(f"  Wind : x={args.x} m/s (East)   y={args.y} m/s (North)")
    log(f"  Rep  : {args.rep}/{RUNS_PER_COMBO}")
    log(f"  Listen: {args.mavlink}")
    log("=" * 60)
    print()
    log("Make sure these are running:")
    log(f"  Terminal A:  {CTE_SITL_COMMAND}")
    log(f"  Terminal B:  {CTE_GAZEBO_COMMAND}")
    print()

    run_one(
        x_wind=args.x,
        y_wind=args.y,
        rep=args.rep,
        campaign_root=args.campaign_root,
        mavlink_addr=args.mavlink,
        heartbeat_timeout=args.heartbeat_timeout,
        mission_timeout=args.mission_timeout,
        accept_square_only=args.accept_square_only,
    )


if __name__ == "__main__":
    main()
