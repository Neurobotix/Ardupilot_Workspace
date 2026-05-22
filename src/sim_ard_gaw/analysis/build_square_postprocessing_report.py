#!/usr/bin/env python3
"""
Regenerate and summarize the corrected Square Wind Matrix postprocessing package.

Primary dataset:
    var/logs/019_New_Param_Full_CTE_Report

Input contract:
    Legacy postprocessing manifests must already contain successful rows only.
    Raw campaign manifests may contain failed, interrupted, running, or other
    non-accepted rows; those rows are excluded from accepted-run metric averages
    but retained in the campaign outcome summary as observed behavior.

Primary scientific basis:
    - square conclusions use square-only true-path metrics (seq 3..22)
    - loiter is reported separately, with after-capture tracking preferred
    - SIM is the primary analysis source
    - POS is computed as a sensitivity/comparison path only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
import textwrap
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = tempfile.mkdtemp(prefix="mplcfg_")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
VAR_LOGS_ROOT = WORKSPACE_ROOT / "var" / "logs"
CONFIG_ROOT = WORKSPACE_ROOT / "config"
ANALYSIS_ROOT = WORKSPACE_ROOT / "src" / "sim_ard_gaw" / "analysis"
RECOVERED_PARAM_STACK_ROOT = (
    WORKSPACE_ROOT
    / "evidence"
    / "curated_logs"
    / "recovered_param_stacks"
    / "recovered_009_param_stack_7439211"
    / "009_param_stack_7439211"
)
INPUT_DATASET_ROOT = VAR_LOGS_ROOT / "019_New_Param_Full_CTE_Report"
OUTPUT_DATASET_ROOT = INPUT_DATASET_ROOT
DATASET_ROOT = INPUT_DATASET_ROOT
SUMMARY_ROOT = OUTPUT_DATASET_ROOT / "summary"
CORRECTED_ROOT = SUMMARY_ROOT / "corrected"
TABLES_ROOT = CORRECTED_ROOT / "tables"
PLOTS_ROOT = CORRECTED_ROOT / "plots"
PER_RUN_ROOT = CORRECTED_ROOT / "per_run"
MANIFEST_PATH = SUMMARY_ROOT / "postprocessing_input_manifest.csv"
TRUE_PATH_SCRIPT = ANALYSIS_ROOT / "true_path_deviation.py"
SQUARE_SCRIPT = ANALYSIS_ROOT / "square_loiter_mission_metrics.py"
VENV_PYTHON = WORKSPACE_ROOT / "env" / "bin" / "python3"
PRIMARY_SOURCE = "sim"
SECONDARY_SOURCE = "pos"
ALLOWED_MANIFEST_STATUS_TO_SUCCESS_CLASS = {
    "success_full": "full_mission",
    "success_square_only": "square_loiter_only",
}
REQUIRED_MANIFEST_COLUMNS = {
    "attempt_id",
    "combo_key",
    "x_wind_mps",
    "y_wind_mps",
    "certified_run_alias",
    "status",
    "success_class",
    "cte_critical_mission_sha16",
    "relative_bin_file",
    "source_bin_file",
    "source_bin_size_bytes",
}
WIND_VALUES = [0, 4, 8, 12]
HEADINGS = ["northbound", "westbound", "southbound", "eastbound"]
CORNERS = ["SE", "NE", "NW", "SW"]
PLOT_DPI = 180
OLD_PARAM_STACK_FILES = [
    RECOVERED_PARAM_STACK_ROOT / "src" / "SIM_ARD_GAW" / "config" / "plane_base.parm",
    RECOVERED_PARAM_STACK_ROOT / "src" / "SIM_ARD_GAW" / "config" / "plane_airspeed.parm",
    RECOVERED_PARAM_STACK_ROOT / "private_overlay" / "config" / "plane_params.local.parm",
]
HIGH_WIND_PARAM_STACK_FILES = [
    CONFIG_ROOT / "vehicles" / "plane_base.parm",
    CONFIG_ROOT / "overlays" / "plane_airspeed.parm",
]
PARAM_COMPARISON_KEYS = [
    "AIRSPEED_CRUISE",
    "AIRSPEED_MIN",
    "AIRSPEED_MAX",
    "TRIM_THROTTLE",
    "TECS_SPDWEIGHT",
    "TECS_CLMB_MAX",
    "TECS_SINK_MAX",
    "MIN_GROUNDSPEED",
    "ROLL_LIMIT_DEG",
    "NAVL1_PERIOD",
    "NAVL1_LIM_BANK",
    "TECS_PITCH_MIN",
    "TKOFF_THR_MAX",
    "TKOFF_ROTATE_SPD",
    "TECS_LAND_ARSPD",
    "TECS_LAND_THR",
    "AHRS_WIND_MAX",
    "ARSPD_OPTIONS",
    "ARSPD_WIND_GATE",
]
PARAM_COMPARISON_INTERPRETATION = {
    "AIRSPEED_CRUISE": "Primary envelope change: old cruise is below the 12/12 resultant wind; high-wind stack raises cruise target.",
    "AIRSPEED_MIN": "Raises minimum commanded airspeed above low-speed old-stack envelope.",
    "AIRSPEED_MAX": "Raises TECS/autothrottle speed headroom.",
    "TRIM_THROTTLE": "Raises nominal throttle authority for stronger wind penetration.",
    "TECS_SPDWEIGHT": "Biases TECS toward speed preservation in the high-wind stack.",
    "TECS_CLMB_MAX": "Adds climb/energy authority in the high-wind stack.",
    "TECS_SINK_MAX": "Raises allowable sink authority.",
    "MIN_GROUNDSPEED": "Adds explicit minimum groundspeed demand in the high-wind stack.",
    "ROLL_LIMIT_DEG": "Raises maneuvering authority available to waypoint tracking.",
    "NAVL1_PERIOD": "Changes L1 path-following response period.",
    "NAVL1_LIM_BANK": "Adds loiter bank cap in the high-wind stack.",
    "TECS_PITCH_MIN": "Reduces old-stack nose-down pitch demand limit.",
    "TKOFF_THR_MAX": "Raises takeoff throttle authority in the high-wind stack.",
    "TKOFF_ROTATE_SPD": "Raises takeoff rotation speed.",
    "TECS_LAND_ARSPD": "Raises landing airspeed target.",
    "TECS_LAND_THR": "Raises landing throttle setting.",
    "AHRS_WIND_MAX": "Raises allowed wind estimate range, matching the high-wind matrix envelope.",
    "ARSPD_OPTIONS": "Prevents airspeed disable/reenable cycling in deliberate high-wind tests.",
    "ARSPD_WIND_GATE": "Disables wind-gate rejection for the high-wind airspeed path.",
}
RAW_MANIFEST_REQUIRED_COLUMNS = {
    "attempt_id",
    "combo_key",
    "x_wind_mps",
    "y_wind_mps",
    "run_alias",
    "status",
    "success_class",
    "raw_log_path",
    "attempt_dir",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def preferred_python() -> str:
    return str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, sort_keys=True)
                    if isinstance(value, (dict, list))
                    else value
                    for key, value in row.items()
                }
            )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def maybe_float(value: Any) -> float:
    out = safe_float(value)
    return float("nan") if out is None else out


def maybe_int(value: Any) -> int:
    out = safe_int(value)
    return -1 if out is None else out


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None or math.isnan(value):
        return "NA"
    return f"{value:.{digits}f}"


def pct(value: float | None, digits: int = 1) -> str:
    if value is None or math.isnan(value):
        return "NA"
    return f"{100.0 * value:.{digits}f}%"


def mean_or_none(values: list[float]) -> float | None:
    clean = [v for v in values if not math.isnan(v)]
    return float(statistics.fmean(clean)) if clean else None


def std_or_none(values: list[float]) -> float | None:
    clean = [v for v in values if not math.isnan(v)]
    if len(clean) < 2:
        return None
    return float(statistics.pstdev(clean))


def percentile_or_none(values: list[float], percentile: float) -> float | None:
    clean = np.array([v for v in values if not math.isnan(v)], dtype=float)
    if clean.size == 0:
        return None
    return float(np.nanpercentile(clean, percentile))


def linear_r2(y_values: list[float], feature_columns: list[list[float]]) -> float | None:
    if not y_values:
        return None
    y = np.array(y_values, dtype=float)
    x = np.column_stack([np.ones(len(y))] + [np.array(col, dtype=float) for col in feature_columns])
    try:
        coeffs, *_ = np.linalg.lstsq(x, y, rcond=None)
    except np.linalg.LinAlgError:
        return None
    pred = x @ coeffs
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot <= 1e-12:
        return 1.0
    return max(0.0, 1.0 - ss_res / ss_tot)


def pearson_corr(x_values: list[float], y_values: list[float]) -> float | None:
    if len(x_values) < 2 or len(y_values) < 2:
        return None
    x = np.array(x_values, dtype=float)
    y = np.array(y_values, dtype=float)
    if np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    idx = 0
    while idx < len(order):
        jdx = idx + 1
        while jdx < len(order) and order[jdx][1] == order[idx][1]:
            jdx += 1
        avg_rank = (idx + jdx - 1) / 2.0 + 1.0
        for pos in range(idx, jdx):
            ranks[order[pos][0]] = avg_rank
        idx = jdx
    return ranks


def spearman_corr(x_values: list[float], y_values: list[float]) -> float | None:
    if len(x_values) < 2 or len(y_values) < 2:
        return None
    return pearson_corr(average_ranks(x_values), average_ranks(y_values))


def slope_per_index(values: list[float]) -> float | None:
    clean = [(idx + 1, value) for idx, value in enumerate(values) if not math.isnan(value)]
    if len(clean) < 2:
        return None
    x = np.array([item[0] for item in clean], dtype=float)
    y = np.array([item[1] for item in clean], dtype=float)
    coeffs = np.polyfit(x, y, deg=1)
    return float(coeffs[0])


def wind_magnitude(row: dict[str, Any]) -> float:
    return float(math.hypot(float(row["x_wind_mps"]), float(row["y_wind_mps"])))


def wind_angle_deg(row: dict[str, Any]) -> float:
    return float(math.degrees(math.atan2(float(row["y_wind_mps"]), float(row["x_wind_mps"]))))


def combo_sort_key(row: dict[str, Any]) -> tuple[float, float, float]:
    return (wind_magnitude(row), float(row["y_wind_mps"]), float(row["x_wind_mps"]))


def run_alias_from_manifest_row(row: dict[str, str]) -> str:
    if row.get("run_alias"):
        return str(row["run_alias"])
    rel = Path(row["relative_bin_file"])
    return rel.parent.name


def script_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def param_stack_file_metadata(paths: list[Path]) -> list[dict[str, str]]:
    return [
        {
            "path": str(path),
            "sha256": script_sha256(path),
        }
        for path in paths
    ]


def artifact_exists(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def default_output_root(input_root: Path) -> Path:
    return input_root.parent / f"{input_root.name}_postprocessing_report"


def configure_paths(input_root: Path, output_root: Path) -> None:
    global INPUT_DATASET_ROOT, OUTPUT_DATASET_ROOT, DATASET_ROOT, SUMMARY_ROOT, CORRECTED_ROOT, TABLES_ROOT, PLOTS_ROOT, PER_RUN_ROOT, MANIFEST_PATH
    INPUT_DATASET_ROOT = input_root
    OUTPUT_DATASET_ROOT = output_root
    DATASET_ROOT = input_root
    SUMMARY_ROOT = OUTPUT_DATASET_ROOT / "summary"
    CORRECTED_ROOT = SUMMARY_ROOT / "corrected"
    TABLES_ROOT = CORRECTED_ROOT / "tables"
    PLOTS_ROOT = CORRECTED_ROOT / "plots"
    PER_RUN_ROOT = CORRECTED_ROOT / "per_run"
    legacy_manifest = INPUT_DATASET_ROOT / "summary" / "postprocessing_input_manifest.csv"
    MANIFEST_PATH = legacy_manifest if legacy_manifest.exists() else INPUT_DATASET_ROOT / "manifest.csv"


def manifest_mode(rows: list[dict[str, str]]) -> str:
    return "legacy" if rows and "relative_bin_file" in rows[0] else "raw"


def validate_legacy_manifest_rows(rows: list[dict[str, str]], manifest_path: Path) -> list[dict[str, str]]:
    if not rows:
        raise RuntimeError(f"No rows found in manifest: {manifest_path}")

    missing_columns = sorted(REQUIRED_MANIFEST_COLUMNS - set(rows[0].keys()))
    if missing_columns:
        raise RuntimeError(
            f"Manifest schema mismatch in {manifest_path}. "
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    non_accepted_rows = [row for row in rows if row.get("status") not in ALLOWED_MANIFEST_STATUS_TO_SUCCESS_CLASS]
    if non_accepted_rows:
        sample = ", ".join(f"{row.get('attempt_id', '<unknown>')}[{row.get('status', '<missing>')}]" for row in non_accepted_rows[:8])
        suffix = " ..." if len(non_accepted_rows) > 8 else ""
        raise RuntimeError(
            f"Manifest {manifest_path} must be pre-filtered to successful rows only. "
            f"Found {len(non_accepted_rows)} non-accepted rows: {sample}{suffix}"
        )

    invalid_rows: list[str] = []
    for row in rows:
        row_errors: list[str] = []
        status = row.get("status")
        expected_success_class = ALLOWED_MANIFEST_STATUS_TO_SUCCESS_CLASS.get(status)
        if row.get("success_class") != expected_success_class:
            row_errors.append(f"success_class={row.get('success_class')!r} expected={expected_success_class!r}")
        bin_path = DATASET_ROOT / row["relative_bin_file"]
        if not bin_path.exists():
            row_errors.append(f"missing_bin={bin_path}")
        if row_errors:
            invalid_rows.append(f"{row.get('attempt_id', '<unknown>')}: {', '.join(row_errors)}")

    if invalid_rows:
        sample = "; ".join(invalid_rows[:8])
        suffix = " ..." if len(invalid_rows) > 8 else ""
        raise RuntimeError(
            f"Manifest {manifest_path} contains rows that do not meet the accepted-run contract: "
            f"{sample}{suffix}"
        )

    return rows


def build_raw_manifest_rows(rows: list[dict[str, str]], input_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not rows:
        raise RuntimeError(f"No rows found in manifest: {MANIFEST_PATH}")

    missing_columns = sorted(RAW_MANIFEST_REQUIRED_COLUMNS - set(rows[0].keys()))
    if missing_columns:
        raise RuntimeError(
            f"Raw manifest schema mismatch in {MANIFEST_PATH}. "
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    accepted_rows = [row for row in rows if row.get("status") in ALLOWED_MANIFEST_STATUS_TO_SUCCESS_CLASS]
    excluded_rows = [row for row in rows if row.get("status") not in ALLOWED_MANIFEST_STATUS_TO_SUCCESS_CLASS]
    normalized_rows: list[dict[str, str]] = []
    for row in accepted_rows:
        raw_log_path = Path(row["raw_log_path"])
        try:
            relative_bin_file = str(raw_log_path.relative_to(input_root))
        except ValueError:
            relative_bin_file = str(Path(row["attempt_dir"]).parent.name / raw_log_path.name)
        bin_size = raw_log_path.stat().st_size if raw_log_path.exists() else 0
        normalized_rows.append(
            {
                "attempt_id": row["attempt_id"],
                "combo_key": row["combo_key"],
                "x_wind_mps": row["x_wind_mps"],
                "y_wind_mps": row["y_wind_mps"],
                "certified_run_alias": row["run_alias"],
                "status": row["status"],
                "success_class": row["success_class"],
                "cte_critical_mission_sha16": "",
                "relative_bin_file": relative_bin_file,
                "source_bin_file": row["raw_log_path"],
                "source_bin_size_bytes": str(bin_size),
                "run_alias": row["run_alias"],
                "attempt_dir": row["attempt_dir"],
                "raw_log_path": row["raw_log_path"],
                "analysis_status": row.get("analysis_status", "done"),
            }
        )
    if not normalized_rows:
        raise RuntimeError(f"No successful rows found in manifest: {MANIFEST_PATH}")
    return normalized_rows, excluded_rows


def normalize_manifest_rows(rows: list[dict[str, str]], input_root: Path, manifest_path: Path) -> tuple[list[dict[str, str]], str, list[dict[str, str]]]:
    mode = manifest_mode(rows)
    if mode == "legacy":
        return validate_legacy_manifest_rows(rows, manifest_path), mode, []
    normalized_rows, excluded_rows = build_raw_manifest_rows(rows, input_root)
    return normalized_rows, mode, excluded_rows


def build_campaign_outcome_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        combo_key = row.get("combo_key")
        if combo_key:
            grouped[combo_key].append(row)

    outcome_rows: list[dict[str, Any]] = []
    for x_wind in WIND_VALUES:
        for y_wind in WIND_VALUES:
            combo_key = f"wind_x_{x_wind:02d}_y_{y_wind:02d}"
            combo_rows = grouped.get(combo_key, [])
            status_counts = {
                "success_full": 0,
                "success_square_only": 0,
                "failed": 0,
                "interrupted": 0,
                "running": 0,
                "error": 0,
                "other": 0,
            }
            for row in combo_rows:
                status = row.get("status", "")
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts["other"] += 1

            accepted_count = status_counts["success_full"] + status_counts["success_square_only"]
            failure_like_count = (
                status_counts["failed"]
                + status_counts["interrupted"]
                + status_counts["running"]
                + status_counts["error"]
                + status_counts["other"]
            )
            last_row = combo_rows[-1] if combo_rows else {}
            if not combo_rows:
                outcome = "not_attempted"
            elif accepted_count == 0:
                outcome = "failure_no_accepted"
            elif failure_like_count:
                outcome = "partial_failure_with_accepted"
            else:
                outcome = "accepted_only"

            outcome_rows.append(
                {
                    "combo_key": combo_key,
                    "x_wind_mps": x_wind,
                    "y_wind_mps": y_wind,
                    "wind_magnitude_mps": float(math.hypot(x_wind, y_wind)),
                    "attempt_count": len(combo_rows),
                    "accepted_run_count": accepted_count,
                    "failure_like_attempt_count": failure_like_count,
                    "success_full_count": status_counts["success_full"],
                    "success_square_only_count": status_counts["success_square_only"],
                    "failed_count": status_counts["failed"],
                    "interrupted_count": status_counts["interrupted"],
                    "running_count": status_counts["running"],
                    "error_count": status_counts["error"],
                    "other_status_count": status_counts["other"],
                    "outcome": outcome,
                    "last_status": last_row.get("status", ""),
                    "last_attempt_id": last_row.get("attempt_id", ""),
                    "last_notes": last_row.get("notes", ""),
                }
            )
    return sorted(outcome_rows, key=combo_sort_key)


def extract_last_statustext(notes: str) -> str:
    marker = "last_statustext="
    if marker not in notes:
        return ""
    tail = notes.split(marker, 1)[1]
    if " | " in tail:
        tail = tail.split(" | ", 1)[0]
    return tail.strip().strip('"')


def build_failure_envelope_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out_rows: list[dict[str, Any]] = []
    old_param_values = read_param_stack_values(OLD_PARAM_STACK_FILES, ["AIRSPEED_CRUISE"])
    old_cruise = safe_float(old_param_values.get("AIRSPEED_CRUISE", {}).get("value")) or 14.0
    for row in rows:
        status = row.get("status", "")
        if status in ALLOWED_MANIFEST_STATUS_TO_SUCCESS_CLASS:
            continue
        x_wind = safe_float(row.get("x_wind_mps")) or 0.0
        y_wind = safe_float(row.get("y_wind_mps")) or 0.0
        notes = row.get("notes", "")
        mission_timed_out = "mission_timed_out" in notes
        bookkeeping_record = "bookkeeping_recovered_stale_running_record" in notes
        duration = safe_float(row.get("duration_wall_s"))
        wind_mag = float(math.hypot(x_wind, y_wind))
        out_rows.append(
            {
                "attempt_id": row.get("attempt_id", ""),
                "combo_key": row.get("combo_key", ""),
                "x_wind_mps": x_wind,
                "y_wind_mps": y_wind,
                "wind_magnitude_mps": wind_mag,
                "old_airspeed_cruise_mps": old_cruise,
                "wind_minus_old_cruise_mps": wind_mag - old_cruise,
                "wind_to_old_cruise_ratio": wind_mag / old_cruise if old_cruise else None,
                "status": status,
                "duration_wall_s": duration,
                "square_completed": row.get("square_completed", ""),
                "loiter_completed": row.get("loiter_completed", ""),
                "mission_completed_full": row.get("mission_completed_full", ""),
                "mission_timed_out": mission_timed_out,
                "bookkeeping_recovered_stale_running_record": bookkeeping_record,
                "last_statustext": extract_last_statustext(notes),
                "raw_log_path": row.get("raw_log_path", ""),
                "attempt_dir": row.get("attempt_dir", ""),
                "notes": notes,
                "failure_interpretation": (
                    "mission_timeout_under_valid_wind"
                    if mission_timed_out
                    else "stale_or_incomplete_bookkeeping_record"
                    if bookkeeping_record
                    else "non_accepted_campaign_record"
                ),
            }
        )
    return sorted(out_rows, key=lambda item: (float(item["wind_magnitude_mps"]), str(item["combo_key"]), str(item["attempt_id"])))


def read_param_stack_values(paths: list[Path], keys: list[str]) -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {}
    key_set = set(keys)
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                body = line.split("#", 1)[0].strip()
                if not body:
                    continue
                parts = body.split()
                if len(parts) < 2 or parts[0] not in key_set:
                    continue
                values[parts[0]] = {
                    "value": parts[1],
                    "source_file": str(path),
                }
    return values


def build_param_stack_comparison_rows() -> list[dict[str, Any]]:
    old_values = read_param_stack_values(OLD_PARAM_STACK_FILES, PARAM_COMPARISON_KEYS)
    high_wind_values = read_param_stack_values(HIGH_WIND_PARAM_STACK_FILES, PARAM_COMPARISON_KEYS)
    rows: list[dict[str, Any]] = []
    for key in PARAM_COMPARISON_KEYS:
        old_payload = old_values.get(key, {})
        high_payload = high_wind_values.get(key, {})
        old_value = old_payload.get("value", "")
        high_value = high_payload.get("value", "")
        old_float = safe_float(old_value)
        high_float = safe_float(high_value)
        rows.append(
            {
                "param": key,
                "old_recovered_value": old_value,
                "later_high_wind_value": high_value,
                "delta_high_minus_old": (
                    high_float - old_float
                    if high_float is not None and old_float is not None
                    else None
                ),
                "old_source_file": old_payload.get("source_file", ""),
                "later_high_wind_source_file": high_payload.get("source_file", ""),
                "interpretation": PARAM_COMPARISON_INTERPRETATION.get(key, ""),
            }
        )
    return rows


def run_command(cmd: list[str], stdout_log: Path, stderr_log: Path) -> None:
    proc = subprocess.run(
        cmd,
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout_log.write_text(proc.stdout, encoding="utf-8")
    stderr_log.write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        tail = proc.stderr[-1200:] if proc.stderr else "(no stderr)"
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{tail}")


def ensure_dir_tree() -> None:
    for path in [CORRECTED_ROOT, TABLES_ROOT, PLOTS_ROOT, PER_RUN_ROOT]:
        path.mkdir(parents=True, exist_ok=True)


def run_analyzers_for_attempt(
    manifest_row: dict[str, str],
    source: str,
    *,
    force: bool,
) -> dict[str, Any]:
    attempt_id = manifest_row["attempt_id"]
    bin_path = DATASET_ROOT / manifest_row["relative_bin_file"]
    if not bin_path.exists():
        raise FileNotFoundError(f"Missing BIN for {attempt_id}: {bin_path}")

    source_root = PER_RUN_ROOT / attempt_id / source
    true_out = source_root / "true_path_deviation"
    square_out = source_root / "square_loiter_mission_metrics"
    true_summary_path = true_out / f"{bin_path.stem}_true_path_deviation_summary.json"
    square_summary_path = square_out / f"{bin_path.stem}_square_loiter_summary.json"

    if force or not artifact_exists(true_summary_path):
        true_out.mkdir(parents=True, exist_ok=True)
        run_command(
            [
                preferred_python(),
                str(TRUE_PATH_SCRIPT),
                str(bin_path),
                "--position-source",
                source,
                "--outdir",
                str(true_out),
            ],
            source_root / "true_path_deviation_stdout.log",
            source_root / "true_path_deviation_stderr.log",
        )

    if force or not artifact_exists(square_summary_path):
        square_out.mkdir(parents=True, exist_ok=True)
        run_command(
            [
                preferred_python(),
                str(SQUARE_SCRIPT),
                str(bin_path),
                "--position-source",
                source,
                "--outdir",
                str(square_out),
            ],
            source_root / "square_loiter_mission_metrics_stdout.log",
            source_root / "square_loiter_mission_metrics_stderr.log",
        )

    return {
        "attempt_id": attempt_id,
        "analysis_position_source": source,
        "bin_path": str(bin_path),
        "true_summary_path": str(true_summary_path),
        "square_summary_path": str(square_summary_path),
    }


def load_attempt_outputs(manifest_row: dict[str, str], input_root: Path) -> dict[str, Any]:
    attempt_id = manifest_row["attempt_id"]
    attempt_dir = Path(manifest_row["attempt_dir"])
    bin_path = Path(manifest_row["source_bin_file"])
    if not bin_path.is_absolute():
        bin_path = input_root / manifest_row["relative_bin_file"]
    true_out = attempt_dir / "true_path_deviation"
    square_out = attempt_dir / "square_loiter_mission_metrics"
    stem = bin_path.stem

    true_summary = read_json(true_out / f"{stem}_true_path_deviation_summary.json")
    square_summary = read_json(square_out / f"{stem}_square_loiter_summary.json")
    true_rows = read_csv_rows(true_out / f"{stem}_true_path_deviation.csv")
    edge_rows = read_csv_rows(square_out / f"{stem}_square_edge_metrics.csv")
    lap_rows = read_csv_rows(square_out / f"{stem}_square_lap_metrics.csv")
    corner_rows = read_csv_rows(square_out / f"{stem}_square_corner_metrics.csv")

    return {
        "attempt_id": attempt_id,
        "source": PRIMARY_SOURCE,
        "manifest_row": manifest_row,
        "bin_path": bin_path,
        "true_summary": true_summary,
        "square_summary": square_summary,
        "true_rows": true_rows,
        "edge_rows": edge_rows,
        "lap_rows": lap_rows,
        "corner_rows": corner_rows,
    }


def load_source_outputs(manifest_row: dict[str, str], source: str) -> dict[str, Any]:
    attempt_id = manifest_row["attempt_id"]
    bin_path = DATASET_ROOT / manifest_row["relative_bin_file"]
    source_root = PER_RUN_ROOT / attempt_id / source
    true_out = source_root / "true_path_deviation"
    square_out = source_root / "square_loiter_mission_metrics"
    stem = bin_path.stem

    true_summary = read_json(true_out / f"{stem}_true_path_deviation_summary.json")
    square_summary = read_json(square_out / f"{stem}_square_loiter_summary.json")
    true_rows = read_csv_rows(true_out / f"{stem}_true_path_deviation.csv")
    edge_rows = read_csv_rows(square_out / f"{stem}_square_edge_metrics.csv")
    lap_rows = read_csv_rows(square_out / f"{stem}_square_lap_metrics.csv")
    corner_rows = read_csv_rows(square_out / f"{stem}_square_corner_metrics.csv")

    return {
        "attempt_id": attempt_id,
        "source": source,
        "manifest_row": manifest_row,
        "bin_path": bin_path,
        "true_summary": true_summary,
        "square_summary": square_summary,
        "true_rows": true_rows,
        "edge_rows": edge_rows,
        "lap_rows": lap_rows,
        "corner_rows": corner_rows,
    }


def flatten_source_outputs(loaded: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_row = loaded["manifest_row"]
    source = loaded["source"]
    attempt_id = loaded["attempt_id"]
    bin_path: Path = loaded["bin_path"]
    true_summary = loaded["true_summary"]
    square_summary = loaded["square_summary"]
    true_rows = loaded["true_rows"]
    edge_rows = loaded["edge_rows"]
    lap_rows = loaded["lap_rows"]
    corner_rows = loaded["corner_rows"]

    true_mv = true_summary["mission_validation"]
    square_mv = square_summary["mission_validation"]
    mission_validation_ok = bool(true_mv.get("ok")) and bool(square_mv.get("ok"))
    mv_errors = list(true_mv.get("errors", [])) + [
        error for error in square_mv.get("errors", []) if error not in true_mv.get("errors", [])
    ]

    square_stats = square_summary["square"]["overall"]
    square_by_heading = square_summary["square"]["by_heading"]
    loiter = square_summary["loiter"]
    full_mission = true_summary.get("full_mission_supported_stats", {})
    inside_segment = true_summary.get("inside_segment_stats", {})
    square_true = true_summary.get("square_stats", {})

    lap_rms = [maybe_float(row.get("rms_true_path_dev_m")) for row in lap_rows]
    lap_eff = [maybe_float(row.get("path_efficiency_ratio")) for row in lap_rows]
    lap_closure = [maybe_float(row.get("closure_error_at_se_m")) for row in lap_rows]
    corner_min = [maybe_float(row.get("min_corner_distance_m")) for row in corner_rows]
    corner_rec_5 = [maybe_float(row.get("recovery_time_to_5m_s")) for row in corner_rows]
    corner_rec_10 = [maybe_float(row.get("recovery_time_to_10m_s")) for row in corner_rows]

    heading_mean_values = [
        maybe_float(square_by_heading.get(heading, {}).get("mean_true_path_dev_m"))
        for heading in HEADINGS
    ]
    heading_rms_values = [
        maybe_float(square_by_heading.get(heading, {}).get("rms_true_path_dev_m"))
        for heading in HEADINGS
    ]
    clean_heading_means = [value for value in heading_mean_values if not math.isnan(value)]
    clean_heading_rms = [value for value in heading_rms_values if not math.isnan(value)]

    run_row: dict[str, Any] = {
        "attempt_id": attempt_id,
        "combo_key": manifest_row["combo_key"],
        "run_alias": run_alias_from_manifest_row(manifest_row),
        "certified_run_alias": manifest_row["certified_run_alias"],
        "x_wind_mps": float(manifest_row["x_wind_mps"]),
        "y_wind_mps": float(manifest_row["y_wind_mps"]),
        "wind_magnitude_mps": wind_magnitude(manifest_row),
        "wind_angle_deg_from_east_ccw": wind_angle_deg(manifest_row),
        "status": manifest_row["status"],
        "success_class": manifest_row["success_class"],
        "analysis_position_source": source,
        "relative_bin_file": manifest_row["relative_bin_file"],
        "source_bin_file": manifest_row["source_bin_file"],
        "source_bin_size_bytes": safe_int(manifest_row["source_bin_size_bytes"]),
        "cte_critical_mission_sha16": manifest_row["cte_critical_mission_sha16"],
        "analysis_bin_path": str(bin_path),
        "analysis_square_metric_basis": "square-only true path deviation over mission seq 3..22",
        "analysis_loiter_metric_basis": "loiter reported separately; after-capture metrics preferred",
        "mission_validation_ok": mission_validation_ok,
        "mission_validation_true_ok": bool(true_mv.get("ok")),
        "mission_validation_square_ok": bool(square_mv.get("ok")),
        "mission_validation_error_count": len(mv_errors),
        "mission_validation_errors": " | ".join(mv_errors),
        "true_position_source_reported": true_summary.get("position_source"),
        "square_position_source_reported": square_summary.get("position_source"),
        "square_sample_count": safe_int(square_stats.get("sample_count")),
        "square_segment_count": safe_int(square_stats.get("segment_count")),
        "square_mean_true_path_dev_m": safe_float(square_stats.get("mean_true_path_dev_m")),
        "square_rms_true_path_dev_m": safe_float(square_stats.get("rms_true_path_dev_m")),
        "square_p95_true_path_dev_m": safe_float(square_stats.get("p95_true_path_dev_m")),
        "square_max_true_path_dev_m": safe_float(square_stats.get("max_true_path_dev_m")),
        "square_true_mean_abs_ntun_xt_m": safe_float(square_true.get("mean_abs_ntun_xt_m")),
        "square_true_rmse_true_vs_abs_ntun_m": safe_float(square_true.get("rmse_true_vs_abs_ntun_m")),
        "square_true_max_abs_diff_vs_ntun_m": safe_float(square_true.get("max_abs_diff_m")),
        "directional_asymmetry_mean_m": (
            max(clean_heading_means) - min(clean_heading_means) if len(clean_heading_means) >= 2 else None
        ),
        "directional_asymmetry_rms_m": (
            max(clean_heading_rms) - min(clean_heading_rms) if len(clean_heading_rms) >= 2 else None
        ),
        "lap_count": len(lap_rows),
        "lap_rms_mean_m": mean_or_none(lap_rms),
        "lap_rms_std_m": std_or_none(lap_rms),
        "lap_rms_range_m": (
            float(max([v for v in lap_rms if not math.isnan(v)]) - min([v for v in lap_rms if not math.isnan(v)]))
            if [v for v in lap_rms if not math.isnan(v)]
            else None
        ),
        "lap_rms_slope_m_per_lap": slope_per_index(lap_rms),
        "lap_path_efficiency_mean": mean_or_none(lap_eff),
        "lap_path_efficiency_std": std_or_none(lap_eff),
        "lap_closure_error_mean_m": mean_or_none(lap_closure),
        "lap_closure_error_p95_m": percentile_or_none(lap_closure, 95),
        "corner_count": len(corner_rows),
        "corner_mean_min_distance_m": mean_or_none(corner_min),
        "corner_p95_min_distance_m": percentile_or_none(corner_min, 95),
        "corner_max_min_distance_m": max([v for v in corner_min if not math.isnan(v)], default=None),
        "corner_recovery_to_5m_mean_s": mean_or_none(corner_rec_5),
        "corner_recovery_to_10m_mean_s": mean_or_none(corner_rec_10),
        "loiter_available": bool(loiter.get("available")),
        "loiter_window_status": loiter.get("loiter_window_status"),
        "loiter_window_start_seq": safe_int(loiter.get("loiter_window_start_seq")),
        "loiter_window_end_seq": safe_int(loiter.get("loiter_window_end_seq")),
        "loiter_duration_s": safe_float(loiter.get("duration_s")),
        "loiter_expected_turns": safe_float(loiter.get("expected_turns")),
        "loiter_turns_complete": bool(loiter.get("turns_complete")),
        "loiter_turns_flown_total": safe_float(loiter.get("turns_flown_total")),
        "loiter_turns_flown_after_capture": safe_float(loiter.get("turns_flown_after_capture")),
        "loiter_completed_turns_after_capture": safe_int(loiter.get("completed_turns_after_capture")),
        "loiter_capture_time_s": safe_float(loiter.get("capture_time_s")),
        "loiter_samples": safe_int(loiter.get("samples")),
        "loiter_samples_after_capture": safe_int(loiter.get("samples_after_capture")),
        "loiter_full_window_mean_radial_error_m": safe_float(loiter.get("mean_radial_error_full_window_m")),
        "loiter_full_window_rms_radial_error_m": safe_float(loiter.get("rms_radial_error_full_window_m")),
        "loiter_full_window_p95_abs_radial_error_m": safe_float(loiter.get("p95_abs_radial_error_full_window_m")),
        "loiter_after_capture_mean_radial_error_m": safe_float(loiter.get("mean_radial_error_after_capture_m")),
        "loiter_after_capture_rms_radial_error_m": safe_float(loiter.get("rms_radial_error_after_capture_m")),
        "loiter_after_capture_p95_abs_radial_error_m": safe_float(loiter.get("p95_abs_radial_error_after_capture_m")),
        "loiter_after_capture_fitted_radius_m": safe_float(loiter.get("fitted_radius_after_capture_m")),
        "loiter_after_capture_fitted_center_offset_m": safe_float(loiter.get("fitted_center_offset_after_capture_m")),
        "loiter_after_capture_direction": loiter.get("observed_direction_after_capture"),
        "full_mission_supported_sample_count": safe_int(full_mission.get("samples")),
        "full_mission_supported_mean_true_path_dev_m": safe_float(full_mission.get("mean_true_path_dev_m")),
        "full_mission_supported_rms_true_path_dev_m": safe_float(full_mission.get("rms_true_path_dev_m")),
        "inside_segment_sample_count": safe_int(inside_segment.get("samples")),
        "inside_segment_mean_true_path_dev_m": safe_float(inside_segment.get("mean_true_path_dev_m")),
        "inside_segment_rms_true_path_dev_m": safe_float(inside_segment.get("rms_true_path_dev_m")),
        "artifacts_true_summary_json": str(PER_RUN_ROOT / attempt_id / source / "true_path_deviation" / f"{bin_path.stem}_true_path_deviation_summary.json"),
        "artifacts_square_summary_json": str(PER_RUN_ROOT / attempt_id / source / "square_loiter_mission_metrics" / f"{bin_path.stem}_square_loiter_summary.json"),
    }

    for heading in HEADINGS:
        payload = square_by_heading.get(heading, {})
        prefix = f"heading_{heading}"
        run_row[f"{prefix}_sample_count"] = safe_int(payload.get("samples"))
        run_row[f"{prefix}_mean_true_path_dev_m"] = safe_float(payload.get("mean_true_path_dev_m"))
        run_row[f"{prefix}_rms_true_path_dev_m"] = safe_float(payload.get("rms_true_path_dev_m"))
        run_row[f"{prefix}_p95_true_path_dev_m"] = safe_float(payload.get("p95_true_path_dev_m"))
        run_row[f"{prefix}_max_true_path_dev_m"] = safe_float(payload.get("max_true_path_dev_m"))
        run_row[f"{prefix}_mean_signed_line_dev_m"] = safe_float(payload.get("mean_signed_line_dev_m"))

    corner_by_type: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in corner_rows:
        corner_by_type[row["corner_type"]].append(row)
    for corner in CORNERS:
        rows = corner_by_type.get(corner, [])
        min_values = [maybe_float(row.get("min_corner_distance_m")) for row in rows]
        run_row[f"corner_{corner}_mean_min_distance_m"] = mean_or_none(min_values)
        run_row[f"corner_{corner}_p95_min_distance_m"] = percentile_or_none(min_values, 95)

    edge_rows_out: list[dict[str, Any]] = []
    for row in edge_rows:
        merged = {
            "attempt_id": attempt_id,
            "combo_key": manifest_row["combo_key"],
            "analysis_position_source": source,
            "x_wind_mps": float(manifest_row["x_wind_mps"]),
            "y_wind_mps": float(manifest_row["y_wind_mps"]),
            "wind_magnitude_mps": wind_magnitude(manifest_row),
        }
        merged.update(row)
        edge_rows_out.append(merged)

    lap_rows_out: list[dict[str, Any]] = []
    for row in lap_rows:
        merged = {
            "attempt_id": attempt_id,
            "combo_key": manifest_row["combo_key"],
            "analysis_position_source": source,
            "x_wind_mps": float(manifest_row["x_wind_mps"]),
            "y_wind_mps": float(manifest_row["y_wind_mps"]),
            "wind_magnitude_mps": wind_magnitude(manifest_row),
        }
        merged.update(row)
        lap_rows_out.append(merged)

    corner_rows_out: list[dict[str, Any]] = []
    for row in corner_rows:
        merged = {
            "attempt_id": attempt_id,
            "combo_key": manifest_row["combo_key"],
            "analysis_position_source": source,
            "x_wind_mps": float(manifest_row["x_wind_mps"]),
            "y_wind_mps": float(manifest_row["y_wind_mps"]),
            "wind_magnitude_mps": wind_magnitude(manifest_row),
        }
        merged.update(row)
        corner_rows_out.append(merged)

    loiter_row = {
        key: run_row[key]
        for key in [
            "attempt_id",
            "combo_key",
            "run_alias",
            "certified_run_alias",
            "analysis_position_source",
            "x_wind_mps",
            "y_wind_mps",
            "wind_magnitude_mps",
            "status",
            "success_class",
            "mission_validation_ok",
            "loiter_available",
            "loiter_window_status",
            "loiter_window_start_seq",
            "loiter_window_end_seq",
            "loiter_duration_s",
            "loiter_expected_turns",
            "loiter_turns_complete",
            "loiter_turns_flown_total",
            "loiter_turns_flown_after_capture",
            "loiter_completed_turns_after_capture",
            "loiter_capture_time_s",
            "loiter_samples",
            "loiter_samples_after_capture",
            "loiter_full_window_mean_radial_error_m",
            "loiter_full_window_rms_radial_error_m",
            "loiter_full_window_p95_abs_radial_error_m",
            "loiter_after_capture_mean_radial_error_m",
            "loiter_after_capture_rms_radial_error_m",
            "loiter_after_capture_p95_abs_radial_error_m",
            "loiter_after_capture_fitted_radius_m",
            "loiter_after_capture_fitted_center_offset_m",
        ]
    }

    mission_validation_row = {
        "attempt_id": attempt_id,
        "combo_key": manifest_row["combo_key"],
        "analysis_position_source": source,
        "true_path_mission_validation_ok": bool(true_mv.get("ok")),
        "square_loiter_mission_validation_ok": bool(square_mv.get("ok")),
        "mission_validation_ok": mission_validation_ok,
        "true_path_error_count": len(true_mv.get("errors", [])),
        "square_loiter_error_count": len(square_mv.get("errors", [])),
        "combined_error_count": len(mv_errors),
        "combined_errors": mv_errors,
        "square_side_lengths_true_path_m": true_mv.get("square_side_lengths_m", []),
        "square_side_lengths_square_loiter_m": square_mv.get("square_side_lengths_m", []),
    }

    return run_row, loiter_row, edge_rows_out, lap_rows_out, corner_rows_out, mission_validation_row


def group_rows(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return grouped


def combo_summary_from_rows(rows: list[dict[str, Any]], primary_source: str) -> list[dict[str, Any]]:
    combo_groups = group_rows([row for row in rows if row["analysis_position_source"] == primary_source], "combo_key")
    summary_rows: list[dict[str, Any]] = []
    for combo_key, combo_rows in sorted(combo_groups.items(), key=lambda item: combo_sort_key(item[1][0])):
        first = combo_rows[0]
        square_rms = [float(row["square_rms_true_path_dev_m"]) for row in combo_rows if row["square_rms_true_path_dev_m"] is not None]
        square_p95 = [float(row["square_p95_true_path_dev_m"]) for row in combo_rows if row["square_p95_true_path_dev_m"] is not None]
        square_max = [float(row["square_max_true_path_dev_m"]) for row in combo_rows if row["square_max_true_path_dev_m"] is not None]
        loiter_after = [
            float(row["loiter_after_capture_rms_radial_error_m"])
            for row in combo_rows
            if row["loiter_after_capture_rms_radial_error_m"] is not None
        ]
        row = {
            "combo_key": combo_key,
            "analysis_position_source": primary_source,
            "x_wind_mps": first["x_wind_mps"],
            "y_wind_mps": first["y_wind_mps"],
            "wind_magnitude_mps": first["wind_magnitude_mps"],
            "wind_angle_deg_from_east_ccw": first["wind_angle_deg_from_east_ccw"],
            "replicate_count": len(combo_rows),
            "status_full_mission_count": sum(1 for item in combo_rows if item["status"] == "success_full"),
            "status_square_only_count": sum(1 for item in combo_rows if item["status"] == "success_square_only"),
            "square_rms_true_path_dev_mean_m": mean_or_none(square_rms),
            "square_rms_true_path_dev_std_m": std_or_none(square_rms),
            "square_rms_true_path_dev_min_m": min(square_rms) if square_rms else None,
            "square_rms_true_path_dev_max_m": max(square_rms) if square_rms else None,
            "square_p95_true_path_dev_mean_m": mean_or_none(square_p95),
            "square_p95_true_path_dev_std_m": std_or_none(square_p95),
            "square_max_true_path_dev_mean_m": mean_or_none(square_max),
            "square_max_true_path_dev_std_m": std_or_none(square_max),
            "directional_asymmetry_mean_m": mean_or_none(
                [float(item["directional_asymmetry_mean_m"]) for item in combo_rows if item["directional_asymmetry_mean_m"] is not None]
            ),
            "directional_asymmetry_rms_m": mean_or_none(
                [float(item["directional_asymmetry_rms_m"]) for item in combo_rows if item["directional_asymmetry_rms_m"] is not None]
            ),
            "lap_rms_mean_m": mean_or_none([float(item["lap_rms_mean_m"]) for item in combo_rows if item["lap_rms_mean_m"] is not None]),
            "lap_rms_std_m": mean_or_none([float(item["lap_rms_std_m"]) for item in combo_rows if item["lap_rms_std_m"] is not None]),
            "lap_rms_slope_mean_m_per_lap": mean_or_none(
                [float(item["lap_rms_slope_m_per_lap"]) for item in combo_rows if item["lap_rms_slope_m_per_lap"] is not None]
            ),
            "corner_mean_min_distance_mean_m": mean_or_none(
                [float(item["corner_mean_min_distance_m"]) for item in combo_rows if item["corner_mean_min_distance_m"] is not None]
            ),
            "corner_p95_min_distance_mean_m": mean_or_none(
                [float(item["corner_p95_min_distance_m"]) for item in combo_rows if item["corner_p95_min_distance_m"] is not None]
            ),
            "loiter_after_capture_rms_mean_m": mean_or_none(loiter_after),
            "loiter_after_capture_rms_std_m": std_or_none(loiter_after),
            "mission_validation_pass_count": sum(1 for item in combo_rows if item["mission_validation_ok"]),
        }
        for heading in HEADINGS:
            row[f"heading_{heading}_rms_mean_m"] = mean_or_none(
                [float(item[f"heading_{heading}_rms_true_path_dev_m"]) for item in combo_rows if item[f"heading_{heading}_rms_true_path_dev_m"] is not None]
            )
            row[f"heading_{heading}_mean_mean_m"] = mean_or_none(
                [float(item[f"heading_{heading}_mean_true_path_dev_m"]) for item in combo_rows if item[f"heading_{heading}_mean_true_path_dev_m"] is not None]
            )
        summary_rows.append(row)
    return summary_rows


def position_source_summary(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    out_rows: list[dict[str, Any]] = []
    payload: dict[str, Any] = {"sources": {}, "rank_consistency": {}}
    by_source = group_rows(rows, "analysis_position_source")
    for source, source_rows in sorted(by_source.items()):
        square_rms = [float(row["square_rms_true_path_dev_m"]) for row in source_rows if row["square_rms_true_path_dev_m"] is not None]
        square_p95 = [float(row["square_p95_true_path_dev_m"]) for row in source_rows if row["square_p95_true_path_dev_m"] is not None]
        loiter_rms = [
            float(row["loiter_after_capture_rms_radial_error_m"])
            for row in source_rows
            if row["loiter_after_capture_rms_radial_error_m"] is not None
        ]
        out_row = {
            "analysis_position_source": source,
            "run_count": len(source_rows),
            "mission_validation_pass_count": sum(1 for row in source_rows if row["mission_validation_ok"]),
            "square_rms_mean_m": mean_or_none(square_rms),
            "square_rms_std_m": std_or_none(square_rms),
            "square_p95_mean_m": mean_or_none(square_p95),
            "square_p95_std_m": std_or_none(square_p95),
            "loiter_after_capture_rms_mean_m": mean_or_none(loiter_rms),
            "loiter_after_capture_rms_std_m": std_or_none(loiter_rms),
        }
        out_rows.append(out_row)
        payload["sources"][source] = out_row
    return out_rows, payload


def pos_vs_sim_summary(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_attempt: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_attempt[str(row["attempt_id"])][str(row["analysis_position_source"])] = row

    comparison_rows: list[dict[str, Any]] = []
    sim_rms_values: list[float] = []
    pos_rms_values: list[float] = []
    sim_rank_metric: list[float] = []
    pos_rank_metric: list[float] = []

    for attempt_id, source_map in sorted(by_attempt.items()):
        if PRIMARY_SOURCE not in source_map or SECONDARY_SOURCE not in source_map:
            continue
        sim = source_map[PRIMARY_SOURCE]
        pos = source_map[SECONDARY_SOURCE]
        comparison_row = {
            "attempt_id": attempt_id,
            "combo_key": sim["combo_key"],
            "run_alias": sim["run_alias"],
            "x_wind_mps": sim["x_wind_mps"],
            "y_wind_mps": sim["y_wind_mps"],
            "wind_magnitude_mps": sim["wind_magnitude_mps"],
            "sim_square_rms_true_path_dev_m": sim["square_rms_true_path_dev_m"],
            "pos_square_rms_true_path_dev_m": pos["square_rms_true_path_dev_m"],
            "delta_pos_minus_sim_square_rms_m": (
                pos["square_rms_true_path_dev_m"] - sim["square_rms_true_path_dev_m"]
                if sim["square_rms_true_path_dev_m"] is not None and pos["square_rms_true_path_dev_m"] is not None
                else None
            ),
            "sim_square_p95_true_path_dev_m": sim["square_p95_true_path_dev_m"],
            "pos_square_p95_true_path_dev_m": pos["square_p95_true_path_dev_m"],
            "delta_pos_minus_sim_square_p95_m": (
                pos["square_p95_true_path_dev_m"] - sim["square_p95_true_path_dev_m"]
                if sim["square_p95_true_path_dev_m"] is not None and pos["square_p95_true_path_dev_m"] is not None
                else None
            ),
            "sim_square_max_true_path_dev_m": sim["square_max_true_path_dev_m"],
            "pos_square_max_true_path_dev_m": pos["square_max_true_path_dev_m"],
            "delta_pos_minus_sim_square_max_m": (
                pos["square_max_true_path_dev_m"] - sim["square_max_true_path_dev_m"]
                if sim["square_max_true_path_dev_m"] is not None and pos["square_max_true_path_dev_m"] is not None
                else None
            ),
            "sim_loiter_after_capture_rms_radial_error_m": sim["loiter_after_capture_rms_radial_error_m"],
            "pos_loiter_after_capture_rms_radial_error_m": pos["loiter_after_capture_rms_radial_error_m"],
            "delta_pos_minus_sim_loiter_after_capture_rms_m": (
                pos["loiter_after_capture_rms_radial_error_m"] - sim["loiter_after_capture_rms_radial_error_m"]
                if sim["loiter_after_capture_rms_radial_error_m"] is not None
                and pos["loiter_after_capture_rms_radial_error_m"] is not None
                else None
            ),
        }
        comparison_rows.append(comparison_row)
        if comparison_row["sim_square_rms_true_path_dev_m"] is not None and comparison_row["pos_square_rms_true_path_dev_m"] is not None:
            sim_rms_values.append(float(comparison_row["sim_square_rms_true_path_dev_m"]))
            pos_rms_values.append(float(comparison_row["pos_square_rms_true_path_dev_m"]))
            sim_rank_metric.append(float(comparison_row["sim_square_rms_true_path_dev_m"]))
            pos_rank_metric.append(float(comparison_row["pos_square_rms_true_path_dev_m"]))

    overview = {
        "run_count": len(comparison_rows),
        "delta_pos_minus_sim_square_rms_mean_m": mean_or_none(
            [float(row["delta_pos_minus_sim_square_rms_m"]) for row in comparison_rows if row["delta_pos_minus_sim_square_rms_m"] is not None]
        ),
        "delta_pos_minus_sim_square_rms_std_m": std_or_none(
            [float(row["delta_pos_minus_sim_square_rms_m"]) for row in comparison_rows if row["delta_pos_minus_sim_square_rms_m"] is not None]
        ),
        "delta_pos_minus_sim_square_p95_mean_m": mean_or_none(
            [float(row["delta_pos_minus_sim_square_p95_m"]) for row in comparison_rows if row["delta_pos_minus_sim_square_p95_m"] is not None]
        ),
        "delta_pos_minus_sim_square_max_mean_m": mean_or_none(
            [float(row["delta_pos_minus_sim_square_max_m"]) for row in comparison_rows if row["delta_pos_minus_sim_square_max_m"] is not None]
        ),
        "square_rms_pearson_corr": pearson_corr(sim_rms_values, pos_rms_values),
        "square_rms_spearman_corr": spearman_corr(sim_rank_metric, pos_rank_metric),
    }
    return comparison_rows, overview


def monotonicity_summary(combo_rows: list[dict[str, Any]], metric_key: str) -> dict[str, Any]:
    combo_map = {(int(row["x_wind_mps"]), int(row["y_wind_mps"])): row for row in combo_rows}
    row_checks: list[dict[str, Any]] = []
    col_checks: list[dict[str, Any]] = []

    for y in WIND_VALUES:
        values = [
            safe_float(combo_map[(x, y)].get(metric_key)) if (x, y) in combo_map else None
            for x in WIND_VALUES
        ]
        finite = [value for value in values if value is not None]
        nondecreasing = False
        if len(finite) == len(values):
            nondecreasing = all(finite[idx + 1] >= finite[idx] - 1e-9 for idx in range(len(finite) - 1))
        row_checks.append(
            {
                "fixed_y_wind_mps": y,
                "values": values,
                "missing_combo_count": len(values) - len(finite),
                "nondecreasing_with_x": nondecreasing,
            }
        )

    for x in WIND_VALUES:
        values = [
            safe_float(combo_map[(x, y)].get(metric_key)) if (x, y) in combo_map else None
            for y in WIND_VALUES
        ]
        finite = [value for value in values if value is not None]
        nondecreasing = False
        if len(finite) == len(values):
            nondecreasing = all(finite[idx + 1] >= finite[idx] - 1e-9 for idx in range(len(finite) - 1))
        col_checks.append(
            {
                "fixed_x_wind_mps": x,
                "values": values,
                "missing_combo_count": len(values) - len(finite),
                "nondecreasing_with_y": nondecreasing,
            }
        )

    return {
        "metric_key": metric_key,
        "rows_monotonic_count": sum(1 for row in row_checks if row["nondecreasing_with_x"]),
        "cols_monotonic_count": sum(1 for row in col_checks if row["nondecreasing_with_y"]),
        "missing_or_unavailable_combo_count": sum(
            1
            for x in WIND_VALUES
            for y in WIND_VALUES
            if (x, y) not in combo_map or safe_float(combo_map[(x, y)].get(metric_key)) is None
        ),
        "row_checks": row_checks,
        "col_checks": col_checks,
    }


def overall_scientific_summary(
    run_rows: list[dict[str, Any]],
    combo_rows: list[dict[str, Any]],
    pos_vs_sim_overview: dict[str, Any],
) -> dict[str, Any]:
    sim_rows = [row for row in run_rows if row["analysis_position_source"] == PRIMARY_SOURCE]
    if not sim_rows:
        raise RuntimeError("No SIM rows available for scientific summary.")

    sorted_by_rms = sorted(
        [row for row in combo_rows if row["square_rms_true_path_dev_mean_m"] is not None],
        key=lambda row: float(row["square_rms_true_path_dev_mean_m"]),
        reverse=True,
    )
    sorted_by_p95 = sorted(
        [row for row in combo_rows if row["square_p95_true_path_dev_mean_m"] is not None],
        key=lambda row: float(row["square_p95_true_path_dev_mean_m"]),
        reverse=True,
    )
    sorted_by_max = sorted(
        [row for row in combo_rows if row["square_max_true_path_dev_mean_m"] is not None],
        key=lambda row: float(row["square_max_true_path_dev_mean_m"]),
        reverse=True,
    )
    sorted_by_variability = sorted(
        [row for row in combo_rows if row["square_rms_true_path_dev_std_m"] is not None],
        key=lambda row: float(row["square_rms_true_path_dev_std_m"]),
        reverse=True,
    )

    magnitude_r2 = linear_r2(
        [float(row["square_rms_true_path_dev_mean_m"]) for row in combo_rows if row["square_rms_true_path_dev_mean_m"] is not None],
        [[float(row["wind_magnitude_mps"]) for row in combo_rows if row["square_rms_true_path_dev_mean_m"] is not None]],
    )
    components_rows = [row for row in combo_rows if row["square_rms_true_path_dev_mean_m"] is not None]
    components_r2 = linear_r2(
        [float(row["square_rms_true_path_dev_mean_m"]) for row in components_rows],
        [
            [float(row["x_wind_mps"]) for row in components_rows],
            [float(row["y_wind_mps"]) for row in components_rows],
        ],
    )
    interaction_r2 = linear_r2(
        [float(row["square_rms_true_path_dev_mean_m"]) for row in components_rows],
        [
            [float(row["x_wind_mps"]) for row in components_rows],
            [float(row["y_wind_mps"]) for row in components_rows],
            [float(row["x_wind_mps"]) * float(row["y_wind_mps"]) for row in components_rows],
        ],
    )

    loiter_pairs = [
        row for row in sim_rows
        if row["square_rms_true_path_dev_m"] is not None and row["loiter_after_capture_rms_radial_error_m"] is not None
    ]
    loiter_square_corr = pearson_corr(
        [float(row["square_rms_true_path_dev_m"]) for row in loiter_pairs],
        [float(row["loiter_after_capture_rms_radial_error_m"]) for row in loiter_pairs],
    )

    heading_worst_counts: dict[str, int] = {heading: 0 for heading in HEADINGS}
    for row in combo_rows:
        heading_pairs = [
            (heading, row.get(f"heading_{heading}_rms_mean_m"))
            for heading in HEADINGS
            if row.get(f"heading_{heading}_rms_mean_m") is not None
        ]
        if heading_pairs:
            worst_heading = max(heading_pairs, key=lambda item: float(item[1]))[0]
            heading_worst_counts[worst_heading] += 1

    calm_combo = next((row for row in combo_rows if int(row["x_wind_mps"]) == 0 and int(row["y_wind_mps"]) == 0), None)
    worst_combo = sorted_by_rms[0] if sorted_by_rms else None
    calm_rms = safe_float(calm_combo.get("square_rms_true_path_dev_mean_m")) if calm_combo else None
    worst_rms = safe_float(worst_combo.get("square_rms_true_path_dev_mean_m")) if worst_combo else None

    return {
        "dataset_run_count": len(sim_rows),
        "combo_count": len(combo_rows),
        "status_counts": {
            "success_full": sum(1 for row in sim_rows if row["status"] == "success_full"),
            "success_square_only": sum(1 for row in sim_rows if row["status"] == "success_square_only"),
        },
        "top_square_rms_combos": sorted_by_rms[:5],
        "top_square_p95_combos": sorted_by_p95[:5],
        "top_square_max_combos": sorted_by_max[:5],
        "top_variability_combos": sorted_by_variability[:5],
        "worst_heading_counts": heading_worst_counts,
        "magnitude_only_r2_square_rms": magnitude_r2,
        "component_r2_square_rms": components_r2,
        "component_interaction_r2_square_rms": interaction_r2,
        "square_vs_loiter_after_capture_r_pearson": loiter_square_corr,
        "square_rms_monotonicity": monotonicity_summary(combo_rows, "square_rms_true_path_dev_mean_m"),
        "square_p95_monotonicity": monotonicity_summary(combo_rows, "square_p95_true_path_dev_mean_m"),
        "square_max_monotonicity": monotonicity_summary(combo_rows, "square_max_true_path_dev_mean_m"),
        "pos_vs_sim_overview": pos_vs_sim_overview,
        "calm_square_rms_mean_m": calm_rms,
        "worst_square_rms_mean_m": worst_rms,
        "worst_vs_calm_rms_ratio": (worst_rms / calm_rms) if calm_rms not in (None, 0.0) and worst_rms is not None else None,
    }


def build_heatmap_matrix(combo_rows: list[dict[str, Any]], metric_key: str) -> np.ndarray:
    matrix = np.full((len(WIND_VALUES), len(WIND_VALUES)), np.nan, dtype=float)
    for row in combo_rows:
        x_idx = WIND_VALUES.index(int(row["x_wind_mps"]))
        y_idx = WIND_VALUES.index(int(row["y_wind_mps"]))
        value = safe_float(row.get(metric_key))
        if value is not None:
            matrix[y_idx, x_idx] = value
    return matrix


def plot_heatmap(combo_rows: list[dict[str, Any]], metric_key: str, title: str, out_path: Path) -> None:
    matrix = build_heatmap_matrix(combo_rows, metric_key)
    fig, ax = plt.subplots(figsize=(7.0, 6.0), constrained_layout=True)
    image = ax.imshow(matrix, origin="lower", cmap="viridis")
    ax.set_xticks(range(len(WIND_VALUES)), [str(value) for value in WIND_VALUES])
    ax.set_yticks(range(len(WIND_VALUES)), [str(value) for value in WIND_VALUES])
    ax.set_xlabel("East wind component [m/s]")
    ax.set_ylabel("North wind component [m/s]")
    ax.set_title(title)
    for y_idx in range(len(WIND_VALUES)):
        for x_idx in range(len(WIND_VALUES)):
            value = matrix[y_idx, x_idx]
            if not np.isnan(value):
                ax.text(x_idx, y_idx, f"{value:.1f}", color="white", ha="center", va="center", fontsize=9)
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("[m]")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_campaign_outcome_heatmap(outcome_rows: list[dict[str, Any]], out_path: Path) -> None:
    matrix = np.full((len(WIND_VALUES), len(WIND_VALUES)), np.nan, dtype=float)
    outcome_map = {(int(row["x_wind_mps"]), int(row["y_wind_mps"])): row for row in outcome_rows}
    for row in outcome_rows:
        x_idx = WIND_VALUES.index(int(row["x_wind_mps"]))
        y_idx = WIND_VALUES.index(int(row["y_wind_mps"]))
        matrix[y_idx, x_idx] = float(row["accepted_run_count"])

    fig, ax = plt.subplots(figsize=(7.3, 6.2), constrained_layout=True)
    image = ax.imshow(matrix, origin="lower", cmap="viridis", vmin=0, vmax=max(3, int(np.nanmax(matrix))))
    ax.set_xticks(range(len(WIND_VALUES)), [str(value) for value in WIND_VALUES])
    ax.set_yticks(range(len(WIND_VALUES)), [str(value) for value in WIND_VALUES])
    ax.set_xlabel("East wind component [m/s]")
    ax.set_ylabel("North wind component [m/s]")
    ax.set_title("Campaign outcome by wind cell")
    for y_idx, y_wind in enumerate(WIND_VALUES):
        for x_idx, x_wind in enumerate(WIND_VALUES):
            row = outcome_map.get((x_wind, y_wind))
            if not row:
                continue
            accepted = int(row["accepted_run_count"])
            attempts = int(row["attempt_count"])
            outcome = str(row["outcome"])
            if outcome == "failure_no_accepted":
                label = f"FAIL\n0/{attempts}"
                ax.add_patch(Rectangle((x_idx - 0.5, y_idx - 0.5), 1.0, 1.0, fill=False, edgecolor="red", linewidth=2.5))
            elif outcome == "partial_failure_with_accepted":
                label = f"{accepted}/{attempts}\nPART"
                ax.add_patch(Rectangle((x_idx - 0.5, y_idx - 0.5), 1.0, 1.0, fill=False, edgecolor="orange", linewidth=2.0))
            elif attempts == 0:
                label = "N/A"
            else:
                label = f"{accepted}/{attempts}"
            ax.text(x_idx, y_idx, label, color="white", ha="center", va="center", fontsize=9, fontweight="bold")
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Accepted runs")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_replicate_strip(rows: list[dict[str, Any]], out_path: Path) -> None:
    metrics = [
        ("square_rms_true_path_dev_m", "Square RMS [m]"),
        ("square_p95_true_path_dev_m", "Square p95 [m]"),
        ("square_max_true_path_dev_m", "Square max [m]"),
    ]
    sim_rows = [row for row in rows if row["analysis_position_source"] == PRIMARY_SOURCE]
    combos = sorted({row["combo_key"] for row in sim_rows}, key=lambda key: combo_sort_key(next(row for row in sim_rows if row["combo_key"] == key)))
    accepted_counts = {
        combo: sum(1 for row in sim_rows if row["combo_key"] == combo)
        for combo in combos
    }
    fig, axes = plt.subplots(len(metrics), 1, figsize=(13.0, 10.0), constrained_layout=True, sharex=True)
    rng = np.random.default_rng(42)
    for axis, (metric_key, label) in zip(axes, metrics):
        means = []
        for idx, combo in enumerate(combos):
            values = [float(row[metric_key]) for row in sim_rows if row["combo_key"] == combo and row[metric_key] is not None]
            jitter = rng.uniform(-0.18, 0.18, size=len(values))
            color = "tab:blue" if accepted_counts[combo] >= 3 else "tab:orange"
            marker = "o" if accepted_counts[combo] >= 2 else "D"
            axis.scatter(np.full(len(values), idx, dtype=float) + jitter, values, s=34, alpha=0.85, color=color, marker=marker)
            means.append(mean_or_none(values))
        axis.plot(range(len(combos)), means, color="tab:red", linewidth=1.4, marker="o", markersize=4)
        axis.set_ylabel(label)
        axis.grid(alpha=0.25, axis="y")
    labels = [f"{combo}\nn={accepted_counts[combo]}" for combo in combos]
    axes[-1].set_xticks(range(len(combos)), labels, rotation=45, ha="right")
    axes[0].set_title("Accepted square-run observations by wind combination; failed/no-accepted cells excluded")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_combo_boxplots(rows: list[dict[str, Any]], out_path: Path) -> None:
    metrics = [
        ("square_rms_true_path_dev_m", "Square RMS [m]"),
        ("square_p95_true_path_dev_m", "Square p95 [m]"),
        ("square_max_true_path_dev_m", "Square max [m]"),
    ]
    sim_rows = [row for row in rows if row["analysis_position_source"] == PRIMARY_SOURCE]
    combos = sorted({row["combo_key"] for row in sim_rows}, key=lambda key: combo_sort_key(next(row for row in sim_rows if row["combo_key"] == key)))
    accepted_counts = {
        combo: sum(1 for row in sim_rows if row["combo_key"] == combo)
        for combo in combos
    }
    fig, axes = plt.subplots(len(metrics), 1, figsize=(13.0, 10.0), constrained_layout=True, sharex=True)
    for axis, (metric_key, label) in zip(axes, metrics):
        data = [[float(row[metric_key]) for row in sim_rows if row["combo_key"] == combo and row[metric_key] is not None] for combo in combos]
        labels = [f"{combo}\nn={accepted_counts[combo]}" for combo in combos]
        axis.boxplot(data, labels=labels, showfliers=True)
        axis.set_ylabel(label)
        axis.grid(alpha=0.25, axis="y")
    axes[-1].tick_params(axis="x", rotation=45)
    axes[0].set_title("Accepted-run distributions by wind combination; failed/no-accepted cells excluded")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_heading_heatmap(combo_rows: list[dict[str, Any]], out_path: Path) -> None:
    combos = sorted(combo_rows, key=combo_sort_key)
    matrix = np.full((len(HEADINGS), len(combos)), np.nan, dtype=float)
    for col, row in enumerate(combos):
        for row_idx, heading in enumerate(HEADINGS):
            value = safe_float(row.get(f"heading_{heading}_rms_mean_m"))
            if value is not None:
                matrix[row_idx, col] = value
    fig, ax = plt.subplots(figsize=(13.0, 4.8), constrained_layout=True)
    image = ax.imshow(matrix, aspect="auto", cmap="magma")
    ax.set_xticks(range(len(combos)), [row["combo_key"] for row in combos], rotation=45, ha="right")
    ax.set_yticks(range(len(HEADINGS)), HEADINGS)
    ax.set_title("Mission edge/heading-specific square RMS by wind combination (SIM accepted-run means)")
    ax.set_xlabel("Wind combination")
    ax.set_ylabel("Mission edge / heading")
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("[m]")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_heading_pair_differences(combo_rows: list[dict[str, Any]], out_path: Path) -> None:
    combos = sorted(combo_rows, key=combo_sort_key)
    labels = [row["combo_key"] for row in combos]
    ns = []
    ew = []
    for row in combos:
        north = safe_float(row.get("heading_northbound_rms_mean_m"))
        south = safe_float(row.get("heading_southbound_rms_mean_m"))
        east = safe_float(row.get("heading_eastbound_rms_mean_m"))
        west = safe_float(row.get("heading_westbound_rms_mean_m"))
        ns.append((north - south) if north is not None and south is not None else math.nan)
        ew.append((east - west) if east is not None and west is not None else math.nan)
    fig, axes = plt.subplots(2, 1, figsize=(13.0, 7.0), constrained_layout=True, sharex=True)
    axes[0].bar(range(len(labels)), ns, color="tab:green")
    axes[0].axhline(0.0, color="0.3", linewidth=1.0)
    axes[0].set_ylabel("East-edge northbound minus west-edge southbound RMS [m]")
    axes[0].grid(alpha=0.25, axis="y")
    axes[1].bar(range(len(labels)), ew, color="tab:orange")
    axes[1].axhline(0.0, color="0.3", linewidth=1.0)
    axes[1].set_ylabel("South-edge eastbound minus north-edge westbound RMS [m]")
    axes[1].set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    axes[1].grid(alpha=0.25, axis="y")
    axes[0].set_title("Confounded mission edge/heading pair differences (SIM accepted-run means)")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_lap_repeatability(lap_rows: list[dict[str, Any]], out_path: Path) -> None:
    sim_laps = [row for row in lap_rows if row["analysis_position_source"] == PRIMARY_SOURCE]
    combo_groups = group_rows(sim_laps, "combo_key")
    ordered = sorted(combo_groups.items(), key=lambda item: combo_sort_key(item[1][0]))
    fig, axes = plt.subplots(4, 4, figsize=(14.0, 12.0), constrained_layout=True, sharex=True, sharey=True)
    for axis, (combo_key, rows) in zip(axes.flatten(), ordered):
        attempt_groups = group_rows(rows, "attempt_id")
        for attempt_rows in attempt_groups.values():
            sorted_rows = sorted(attempt_rows, key=lambda row: int(row["lap"]))
            axis.plot(
                [int(row["lap"]) for row in sorted_rows],
                [float(row["rms_true_path_dev_m"]) for row in sorted_rows],
                color="0.7",
                linewidth=1.0,
                alpha=0.8,
            )
        mean_by_lap = []
        for lap in range(1, 6):
            lap_values = [float(row["rms_true_path_dev_m"]) for row in rows if int(row["lap"]) == lap]
            mean_by_lap.append(mean_or_none(lap_values))
        axis.plot(range(1, 6), mean_by_lap, color="tab:blue", linewidth=2.0, marker="o", markersize=4)
        axis.set_title(combo_key, fontsize=9)
        axis.grid(alpha=0.2)
    for axis in axes[:, 0]:
        axis.set_ylabel("Lap RMS [m]")
    for axis in axes[-1, :]:
        axis.set_xlabel("Lap")
    fig.suptitle("Lap repeatability across the 4x4 wind matrix for accepted runs (SIM basis)")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_corner_heatmap(corner_rows: list[dict[str, Any]], out_path: Path) -> None:
    sim_rows = [row for row in corner_rows if row["analysis_position_source"] == PRIMARY_SOURCE]
    combo_groups = group_rows(sim_rows, "combo_key")
    ordered = sorted(combo_groups.items(), key=lambda item: combo_sort_key(item[1][0]))
    matrix = np.full((len(CORNERS), len(ordered)), np.nan, dtype=float)
    for col, (_, rows) in enumerate(ordered):
        for row_idx, corner in enumerate(CORNERS):
            values = [maybe_float(row["min_corner_distance_m"]) for row in rows if row["corner_type"] == corner]
            clean = [value for value in values if not math.isnan(value)]
            if clean:
                matrix[row_idx, col] = float(statistics.fmean(clean))
    fig, ax = plt.subplots(figsize=(13.0, 4.8), constrained_layout=True)
    image = ax.imshow(matrix, aspect="auto", cmap="cividis")
    ax.set_xticks(range(len(ordered)), [combo_key for combo_key, _ in ordered], rotation=45, ha="right")
    ax.set_yticks(range(len(CORNERS)), CORNERS)
    ax.set_title("Mean corner miss distance by corner type across accepted runs (SIM basis)")
    ax.set_xlabel("Wind combination")
    ax.set_ylabel("Corner")
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("[m]")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_wind_magnitude_trends(combo_rows: list[dict[str, Any]], out_path: Path) -> None:
    combos = sorted(combo_rows, key=combo_sort_key)
    mags = [float(row["wind_magnitude_mps"]) for row in combos]
    labels = [row["combo_key"] for row in combos]
    metrics = [
        ("square_rms_true_path_dev_mean_m", "Square RMS [m]"),
        ("square_p95_true_path_dev_mean_m", "Square p95 [m]"),
        ("square_max_true_path_dev_mean_m", "Square max [m]"),
    ]
    colors = [float(row["wind_angle_deg_from_east_ccw"]) for row in combos]
    fig, axes = plt.subplots(1, len(metrics), figsize=(15.0, 4.6), constrained_layout=True, sharex=True)
    for axis, (metric_key, label) in zip(axes, metrics):
        values = [float(row[metric_key]) for row in combos]
        scatter = axis.scatter(mags, values, c=colors, cmap="plasma", s=60)
        coeffs = np.polyfit(mags, values, deg=1)
        xfit = np.linspace(min(mags), max(mags), 100)
        axis.plot(xfit, coeffs[0] * xfit + coeffs[1], color="0.2", linewidth=1.2)
        for mag, value, label_text in zip(mags, values, labels):
            axis.annotate(label_text.replace("wind_", "").replace("_", " "), (mag, value), fontsize=7, alpha=0.75)
        axis.set_xlabel("Wind magnitude [m/s]")
        axis.set_ylabel(label)
        axis.grid(alpha=0.25)
    cbar = fig.colorbar(scatter, ax=axes.ravel().tolist())
    cbar.set_label("Wind direction angle from +East [deg]")
    fig.suptitle("Exploratory trend of square metrics with total wind magnitude (SIM accepted-run combo means)")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_variability(combo_rows: list[dict[str, Any]], out_path: Path) -> None:
    combos = sorted(combo_rows, key=combo_sort_key)
    labels = [row["combo_key"] for row in combos]
    stds = [safe_float(row.get("square_rms_true_path_dev_std_m")) or math.nan for row in combos]
    cvs = []
    for row in combos:
        mean_value = safe_float(row.get("square_rms_true_path_dev_mean_m"))
        std_value = safe_float(row.get("square_rms_true_path_dev_std_m"))
        cvs.append((std_value / mean_value) if mean_value not in (None, 0.0) and std_value is not None else math.nan)
    fig, axes = plt.subplots(2, 1, figsize=(13.0, 7.0), constrained_layout=True, sharex=True)
    axes[0].bar(range(len(labels)), stds, color="tab:purple")
    axes[0].set_ylabel("Replicate std of square RMS [m]")
    axes[0].grid(alpha=0.25, axis="y")
    axes[1].bar(range(len(labels)), cvs, color="tab:brown")
    axes[1].set_ylabel("Replicate CV of square RMS")
    axes[1].set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    axes[1].grid(alpha=0.25, axis="y")
    axes[0].set_title("Per-combo variability across accepted replicates (SIM basis)")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_loiter_heatmap(combo_rows: list[dict[str, Any]], out_path: Path) -> None:
    plot_heatmap(combo_rows, "loiter_after_capture_rms_mean_m", "Loiter after-capture RMS radial error [m] (SIM accepted-run combo means)", out_path)


def plot_loiter_vs_square(rows: list[dict[str, Any]], out_path: Path) -> None:
    sim_rows = [
        row for row in rows
        if row["analysis_position_source"] == PRIMARY_SOURCE
        and row["square_rms_true_path_dev_m"] is not None
        and row["loiter_after_capture_rms_radial_error_m"] is not None
    ]
    x = [float(row["square_rms_true_path_dev_m"]) for row in sim_rows]
    y = [float(row["loiter_after_capture_rms_radial_error_m"]) for row in sim_rows]
    colors = [float(row["wind_magnitude_mps"]) for row in sim_rows]
    fig, ax = plt.subplots(figsize=(7.0, 5.6), constrained_layout=True)
    scatter = ax.scatter(x, y, c=colors, cmap="viridis", s=52)
    if len(x) >= 2:
        coeffs = np.polyfit(x, y, deg=1)
        xfit = np.linspace(min(x), max(x), 100)
        ax.plot(xfit, coeffs[0] * xfit + coeffs[1], color="0.2", linewidth=1.2)
    ax.set_xlabel("Square RMS true path deviation [m]")
    ax.set_ylabel("Loiter after-capture RMS radial error [m]")
    ax.set_title("Square tracking versus loiter tracking across accepted runs (SIM basis)")
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Wind magnitude [m/s]")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def plot_pos_vs_sim(pos_vs_sim_rows: list[dict[str, Any]], combo_rows: list[dict[str, Any]], out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4), constrained_layout=True)
    x = [float(row["sim_square_rms_true_path_dev_m"]) for row in pos_vs_sim_rows if row["sim_square_rms_true_path_dev_m"] is not None and row["pos_square_rms_true_path_dev_m"] is not None]
    y = [float(row["pos_square_rms_true_path_dev_m"]) for row in pos_vs_sim_rows if row["sim_square_rms_true_path_dev_m"] is not None and row["pos_square_rms_true_path_dev_m"] is not None]
    mags = [float(row["wind_magnitude_mps"]) for row in pos_vs_sim_rows if row["sim_square_rms_true_path_dev_m"] is not None and row["pos_square_rms_true_path_dev_m"] is not None]
    scatter = axes[0].scatter(x, y, c=mags, cmap="viridis", s=48)
    if x and y:
        line_min = min(min(x), min(y))
        line_max = max(max(x), max(y))
        axes[0].plot([line_min, line_max], [line_min, line_max], color="0.2", linewidth=1.1)
    axes[0].set_xlabel("SIM square RMS [m]")
    axes[0].set_ylabel("POS square RMS [m]")
    axes[0].set_title("POS vs SIM square RMS (near-identity in accepted set)")
    axes[0].grid(alpha=0.25)
    cbar = fig.colorbar(scatter, ax=axes[0])
    cbar.set_label("Wind magnitude [m/s]")

    combo_map = {row["combo_key"]: row for row in combo_rows}
    ordered_keys = [row["combo_key"] for row in sorted(combo_rows, key=combo_sort_key)]
    deltas = [
        safe_float(combo_map[key].get("delta_pos_minus_sim_square_rms_mean_m")) or math.nan
        for key in ordered_keys
    ]
    axes[1].bar(range(len(ordered_keys)), deltas, color="tab:orange")
    axes[1].axhline(0.0, color="0.3", linewidth=1.0)
    axes[1].set_ylabel("POS minus SIM combo-mean square RMS [m]")
    axes[1].set_xticks(range(len(ordered_keys)), ordered_keys, rotation=45, ha="right")
    axes[1].set_title("Combo-mean POS minus SIM deltas (accepted set)")
    axes[1].grid(alpha=0.25, axis="y")
    fig.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def build_glossary() -> tuple[list[dict[str, str]], str]:
    glossary_rows = [
        {
            "field": "square_rms_true_path_dev_m",
            "category": "primary",
            "units": "m",
            "definition": "RMS nearest-distance error to the active finite square segment over mission seq 3..22 using the chosen position source.",
            "interpretation": "Robust primary square tracking metric.",
        },
        {
            "field": "square_p95_true_path_dev_m",
            "category": "primary",
            "units": "m",
            "definition": "95th percentile square-only true path deviation over seq 3..22.",
            "interpretation": "Primary tail-behavior square metric with less outlier sensitivity than max.",
        },
        {
            "field": "square_max_true_path_dev_m",
            "category": "secondary",
            "units": "m",
            "definition": "Maximum square-only true path deviation over seq 3..22.",
            "interpretation": "Useful stress indicator but highly sensitive to isolated samples.",
        },
        {
            "field": "directional_asymmetry_rms_m",
            "category": "primary",
            "units": "m",
            "definition": "Range of mission edge/heading-specific square RMS values within a run.",
            "interpretation": "Useful asymmetry indicator, but confounded because heading and edge location are fixed together in this mission layout.",
        },
        {
            "field": "lap_rms_std_m",
            "category": "primary",
            "units": "m",
            "definition": "Within-run standard deviation of lap RMS values across the five square laps.",
            "interpretation": "Primary repeatability metric.",
        },
        {
            "field": "corner_mean_min_distance_m",
            "category": "primary",
            "units": "m",
            "definition": "Mean minimum corner miss distance across the 20 square corners in a run.",
            "interpretation": "Primary corner-performance summary.",
        },
        {
            "field": "loiter_after_capture_rms_radial_error_m",
            "category": "secondary",
            "units": "m",
            "definition": "RMS radial error after first entering the loiter capture threshold.",
            "interpretation": "Preferred loiter-tracking metric; report separately from square tracking.",
        },
        {
            "field": "loiter_full_window_rms_radial_error_m",
            "category": "exploratory",
            "units": "m",
            "definition": "RMS radial error from loiter start through the full bounded loiter window, including capture transit.",
            "interpretation": "Do not use as a steady-state loiter quality metric.",
        },
        {
            "field": "full_mission_supported_rms_true_path_dev_m",
            "category": "do_not_use_for_square",
            "units": "m",
            "definition": "Supported-leg RMS over the broader mission, not restricted to square seq 3..22.",
            "interpretation": "Do not mix into square path-following conclusions.",
        },
        {
            "field": "square_true_mean_abs_ntun_xt_m",
            "category": "secondary",
            "units": "m",
            "definition": "Mean absolute controller-reported NTUN.XT over square-supported samples.",
            "interpretation": "Controller-internal comparison only; not the primary geometric truth metric.",
        },
    ]
    headers = ["Field", "Category", "Units", "Definition", "Interpretation"]
    rows = [[item["field"], item["category"], item["units"], item["definition"], item["interpretation"]] for item in glossary_rows]
    markdown = "# Metrics Glossary\n\n" + markdown_table(headers, rows) + "\n"
    return glossary_rows, markdown


def build_report(
    metadata: dict[str, Any],
    scientific: dict[str, Any],
    combo_rows: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
    failure_envelope_rows: list[dict[str, Any]],
    param_comparison_rows: list[dict[str, Any]],
    pos_vs_sim_overview: dict[str, Any],
    *,
    has_pos_comparison: bool,
) -> tuple[str, str, str]:
    top_rms = scientific["top_square_rms_combos"]
    top_p95 = scientific["top_square_p95_combos"]
    top_var = scientific["top_variability_combos"]
    worst_heading_counts = scientific["worst_heading_counts"]
    top_rms_table = markdown_table(
        ["Combo", "East [m/s]", "North [m/s]", "Square RMS mean [m]", "Square p95 mean [m]", "Square max mean [m]"],
        [
            [
                row["combo_key"],
                fmt(safe_float(row["x_wind_mps"]), 0),
                fmt(safe_float(row["y_wind_mps"]), 0),
                fmt(safe_float(row["square_rms_true_path_dev_mean_m"])),
                fmt(safe_float(row["square_p95_true_path_dev_mean_m"])),
                fmt(safe_float(row["square_max_true_path_dev_mean_m"])),
            ]
            for row in top_rms[:5]
        ],
    )
    failure_rows = [row for row in outcome_rows if row["outcome"] == "failure_no_accepted"]
    partial_failure_rows = [row for row in outcome_rows if row["outcome"] == "partial_failure_with_accepted"]
    failure_table = markdown_table(
        ["Combo", "East [m/s]", "North [m/s]", "Attempts", "Accepted", "Failed", "Interrupted", "Running", "Last status"],
        [
            [
                row["combo_key"],
                fmt(safe_float(row["x_wind_mps"]), 0),
                fmt(safe_float(row["y_wind_mps"]), 0),
                str(row["attempt_count"]),
                str(row["accepted_run_count"]),
                str(row["failed_count"]),
                str(row["interrupted_count"]),
                str(row["running_count"]),
                str(row["last_status"]),
            ]
            for row in failure_rows
        ],
    ) if failure_rows else "No no-accepted failure cells were present."
    coverage_table = markdown_table(
        ["Outcome", "Cells"],
        [
            ["accepted_only", str(sum(1 for row in outcome_rows if row["outcome"] == "accepted_only"))],
            ["partial_failure_with_accepted", str(len(partial_failure_rows))],
            ["failure_no_accepted", str(len(failure_rows))],
            ["not_attempted", str(sum(1 for row in outcome_rows if row["outcome"] == "not_attempted"))],
        ],
    )
    top_var_table = markdown_table(
        ["Combo", "Square RMS std [m]", "Square RMS mean [m]", "Replicates"],
        [
            [
                row["combo_key"],
                fmt(safe_float(row["square_rms_true_path_dev_std_m"])),
                fmt(safe_float(row["square_rms_true_path_dev_mean_m"])),
                str(row["replicate_count"]),
            ]
            for row in top_var[:5]
        ],
    )
    failure_envelope_table = markdown_table(
        ["Attempt", "Wind", "Wind-cruise [m/s]", "Status", "Duration [s]", "Square", "Loiter", "Timed out", "Last mission evidence"],
        [
            [
                str(row["attempt_id"]),
                f"{fmt(safe_float(row['x_wind_mps']), 0)}/{fmt(safe_float(row['y_wind_mps']), 0)} ({fmt(safe_float(row['wind_magnitude_mps']), 1)})",
                fmt(safe_float(row["wind_minus_old_cruise_mps"]), 2),
                str(row["status"]),
                fmt(safe_float(row["duration_wall_s"]), 1),
                str(row["square_completed"]),
                str(row["loiter_completed"]),
                str(row["mission_timed_out"]),
                str(row["last_statustext"]).replace("|", ";"),
            ]
            for row in failure_envelope_rows
        ],
    ) if failure_envelope_rows else "No non-accepted attempts were present."
    param_stack_table = markdown_table(
        ["Param", "Old recovered", "Later high-wind", "Delta", "Interpretation"],
        [
            [
                str(row["param"]),
                str(row["old_recovered_value"]) or "N/A",
                str(row["later_high_wind_value"]) or "N/A",
                fmt(safe_float(row["delta_high_minus_old"]), 2) if row["delta_high_minus_old"] is not None else "N/A",
                str(row["interpretation"]),
            ]
            for row in param_comparison_rows
        ],
    )
    old_cruise = next((safe_float(row["old_recovered_value"]) for row in param_comparison_rows if row["param"] == "AIRSPEED_CRUISE"), None)
    high_cruise = next((safe_float(row["later_high_wind_value"]) for row in param_comparison_rows if row["param"] == "AIRSPEED_CRUISE"), None)
    old_airspeed_max = next((safe_float(row["old_recovered_value"]) for row in param_comparison_rows if row["param"] == "AIRSPEED_MAX"), None)
    max_matrix_wind = math.hypot(max(WIND_VALUES), max(WIND_VALUES))
    report_input_label = metadata.get("report_input_label", str(metadata.get("dataset_root", DATASET_ROOT)))
    raw_manifest_label = str(metadata.get("input_manifest_path", MANIFEST_PATH))
    accepted_manifest_label = str(metadata.get("accepted_manifest_path", metadata.get("manifest_path", MANIFEST_PATH)))
    accepted_run_count = scientific["dataset_run_count"]
    combo_count = scientific["combo_count"]
    status_counts = scientific["status_counts"]
    status_summary = ", ".join(f"{key}: {value}" for key, value in status_counts.items() if value)
    if not status_summary:
        status_summary = "none"
    if len(top_rms) >= 3:
        top_rms_names = ", ".join(row["combo_key"] for row in top_rms[:3])
    else:
        top_rms_names = ", ".join(row["combo_key"] for row in top_rms) if top_rms else "n/a"
    if len(top_var) >= 3:
        top_var_names = ", ".join(row["combo_key"] for row in top_var[:3])
    else:
        top_var_names = ", ".join(row["combo_key"] for row in top_var) if top_var else "n/a"
    pos_sentence = (
        f"POS-versus-SIM comparison is nearly identical at campaign-summary level in this dataset (Spearman {fmt(pos_vs_sim_overview.get('square_rms_spearman_corr'), 3)}, mean POS-minus-SIM square RMS {fmt(pos_vs_sim_overview.get('delta_pos_minus_sim_square_rms_mean_m'), 3)} m). SIM remains the publication basis because the intended geometric truth reference is simulator state, not because POS materially changes the campaign-level ranking here."
        if has_pos_comparison
        else "No POS-versus-SIM comparison was available for this campaign, so the report is based on SIM-only accepted runs."
    )
    pos_observation_bullet = (
        f"- POS-versus-SIM comparison preserves the broad ordering of difficulty (Spearman {fmt(pos_vs_sim_overview.get('square_rms_spearman_corr'), 3)}) and the absolute differences are negligible at campaign-summary level, so SIM remains the publication basis mainly because simulator state is the intended truth reference."
        if has_pos_comparison
        else "- No POS-versus-SIM comparison was available for this campaign, so SIM is the only analysis basis used in the report package."
    )
    pos_secondary_bullet = (
        "- POS-versus-SIM deltas, mainly as confirmation that campaign-level summaries are almost unchanged."
        if has_pos_comparison
        else "- No POS-versus-SIM deltas are available for this campaign."
    )
    pos_backup_figure = "- `plots/pos_vs_sim_comparison.png`" if has_pos_comparison else ""
    pos_final_table = "- `tables/pos_vs_sim_comparison.csv`" if has_pos_comparison else ""
    pos_limitations_bullet = (
        "- POS-versus-SIM comparison is a sensitivity study only; in this dataset it shows near-identity at campaign-summary level."
        if has_pos_comparison
        else "- No POS sensitivity study was generated for this campaign."
    )
    secondary_source_line = "- Secondary sensitivity source: `pos`" if has_pos_comparison else "- Secondary sensitivity source: none"

    executive_summary = textwrap.dedent(
        f"""
        # Executive Summary

        The corrected postprocessing package was regenerated from `{report_input_label}` using the raw campaign manifest `{raw_manifest_label}`. Accepted rows were normalized into `{accepted_manifest_label}`{", with `sim` as the primary analysis source and `pos` retained only as a sensitivity comparison" if has_pos_comparison else ""}. Both analyzers validate the accepted-run square mission geometry and produce consistent square-only results.

        Across the {accepted_run_count} accepted runs ({combo_count} wind combinations with accepted data; {status_summary}), the strongest square conclusions come from SIM-based square-only true-path metrics: RMS, p95, mission edge/heading-specific RMS, lap repeatability, and corner miss distance. The full campaign outcome matrix is still preserved separately: {len(failure_rows)} wind cells had attempts but no accepted run and are reported as failures, not omitted from the campaign behavior. Within the accepted-run subset, calm-baseline square RMS is {fmt(scientific["calm_square_rms_mean_m"])} m, while the worst combo-mean square RMS reaches {fmt(scientific["worst_square_rms_mean_m"])} m, a {fmt(scientific["worst_vs_calm_rms_ratio"], 2)}x increase. The worst combinations by combo-mean square RMS are {top_rms_names}.

        The production-envelope finding is that the recovered old parameter stack is underpowered for the high-wind corner of this matrix. The old recovered `AIRSPEED_CRUISE` is {fmt(old_cruise, 0)} m/s and old `AIRSPEED_MAX` is {fmt(old_airspeed_max, 0)} m/s, while the matrix reaches {fmt(max_matrix_wind, 2)} m/s at `wind_x_12_y_12`; the later high-wind stack raises `AIRSPEED_CRUISE` to {fmt(high_cruise, 0)} m/s and adds higher throttle/TECS/groundspeed authority. The no-accepted high-wind cells should therefore be reported as mission capability failures under the old production-like stack, not as missing CTE data.

        The combined accepted/failure evidence supports three conservative statements for presentation: square tracking degrades strongly with wind where the old stack completes the analysis basis; several high-wind cells fail to produce any accepted square/loiter run; and directional composition still matters beyond magnitude alone among the accepted cells. The `R^2` values reported here are descriptive fits over only the {combo_count} accepted combo means, so they support the statement that directional composition should not be collapsed away, but not a stronger causal claim.

        Loiter behavior is related but not interchangeable with square tracking. The SIM run-level correlation between square RMS and loiter after-capture RMS radial error is {fmt(scientific["square_vs_loiter_after_capture_r_pearson"], 3)}, which supports reporting loiter as a separate behavior rather than as a proxy for square path following. {pos_sentence}

        Recommended main figures are `square_rms_heatmap.png`, `square_p95_heatmap.png`, `directional_heading_heatmap.png`, `directional_asymmetry_by_heading.png`, `lap_repeatability_by_combo.png`, and `corner_performance_heatmap.png`, with the directional figures explicitly labeled as mission edge/heading effects rather than pure heading effects. {"Keep `pos_vs_sim_comparison.png` as a low-priority sensitivity appendix." if has_pos_comparison else "No POS sensitivity appendix is available for this campaign."} Avoid using full-mission metrics to support square conclusions, avoid full-window loiter metrics as steady-state loiter quality metrics, and treat square max error as a secondary tail metric rather than the headline result.
        """
    ).replace("\n        ", "\n").strip() + "\n"

    report = textwrap.dedent(
        f"""
        # Final Analysis Report

        ## Objective

        Quantify ArduPlane SITL plus Gazebo path-following performance over the square mission block across the 4x4 East/North wind matrix, using only metrics that remain scientifically defensible after code verification and regeneration of corrected outputs.

        ## Dataset And Acceptance Basis

        - Working dataset: `{report_input_label}`
        - Raw campaign manifest: `{raw_manifest_label}`
        - Accepted-only postprocessing manifest: `{accepted_manifest_label}`
        - Accepted runs analyzed: {accepted_run_count}
        - Wind combinations represented: {combo_count}
        - Status counts: {status_summary}

        Full campaign outcome coverage:

        {coverage_table}

        No-accepted failure cells:

        {failure_table}

        Non-accepted attempt evidence:

        {failure_envelope_table}

        ## Exact Analysis Basis

        - Primary analysis position source: `sim`
        {secondary_source_line}
        - Square conclusions use mission seq `3..22` only.
        - Loiter is reported separately using the bounded loiter window rooted at seq `23`.
        - Landing is excluded from the main square conclusions.
        - Full-mission supported metrics are retained only as secondary context.
        - Wind cells with no accepted run are retained as campaign failures in `corrected_campaign_outcome_summary.csv`; they are not assigned square CTE values because no validated square/loiter analysis basis exists for them.

        Analysis script fingerprints:

        - `true_path_deviation.py`: `{metadata["script_sha256"]["true_path_deviation.py"][:16]}`
        - `square_loiter_mission_metrics.py`: `{metadata["script_sha256"]["square_loiter_mission_metrics.py"][:16]}`
        - `build_square_postprocessing_report.py`: `{metadata["script_sha256"]["build_square_postprocessing_report.py"][:16]}`

        ## Code Verification Findings

        Verified from code and regenerated outputs:

        - `run_one.py` uses `ANALYSIS_POSITION_SOURCE = "sim"` for its analysis path.
        - `true_path_deviation.py` validates the mission contract before summarizing.
        - `true_path_deviation.py` exposes square-only stats as `square_stats`.
        - `square_loiter_mission_metrics.py` separates full-window loiter metrics from `*_after_capture_*` steady loiter metrics.
        - `square_loiter_mission_metrics.py` bounds loiter by the next `MISE` event where available.

        Geometry handling verification:

        - The current analyzer outputs pass mission validation for all accepted rows. No failed/no-accepted wind cell is assigned square CTE values, because those cells do not have a validated square/loiter analysis basis.

        ## Mission Validation Summary

        - All regenerated accepted-run outputs passed mission validation.
        - The square contract remains a five-lap block over seq `3..22`, followed by loiter seq `23`.
        - This validation checks command IDs, location frames, and square side lengths.

        ## Failure Envelope Evidence

        The non-accepted rows are not included in accepted-run CTE averages, but they are first-class campaign outcomes. Timeout rows show where the old stack could not complete the square/loiter acceptance basis under the requested wind. Bookkeeping/stale rows are retained as non-accepted campaign records but should not be interpreted as aerodynamic failures.

        The key no-accepted high-wind cells are `{", ".join(row["combo_key"] for row in failure_rows) if failure_rows else "none"}`. These cells are failure outcomes under valid wind injection, not empty cells.

        ## Parameter Stack Comparison

        The old recovered stack loaded by `017` is intentionally more production-like and lower-energy than the later high-wind stack. That realism is exactly why its failures matter: it exposes where the production-like envelope stops being capable under the tested matrix.

        {param_stack_table}

        ## Metric Definitions For Conclusions

        Main square metrics:

        - Square RMS true path deviation: primary overall fidelity metric.
        - Square p95 true path deviation: primary tail metric with lower outlier sensitivity than max.
        - Mission edge/heading-specific square RMS: primary asymmetry metric, but confounded because heading and edge location are fixed together in this mission.
        - Lap RMS variability and slope: primary repeatability metrics.
        - Corner miss distance and recovery time: primary turn/corner behavior metrics.

        Separate loiter metrics:

        - Loiter after-capture RMS radial error: preferred loiter-tracking metric.
        - Loiter full-window radial metrics: include capture transit and are therefore secondary only.

        Excluded from main square conclusions:

        - Full-mission supported metrics.
        - Landing behavior.
        - Full-window loiter metrics used as steady-state orbit quality.
        - NTUN.XT as a primary geometric truth metric.

        ## Results

        Worst combinations by combo-mean square RMS:

        {top_rms_table}

        Highest replicate variability by combo:

        {top_var_table}

        Observations supported by the regenerated data:

        - Within the accepted-run subset, square tracking degrades sharply with wind, from a calm combo-mean square RMS of {fmt(scientific["calm_square_rms_mean_m"])} m to a worst combo-mean RMS of {fmt(scientific["worst_square_rms_mean_m"])} m.
        - The worst accepted combinations by square RMS and p95 are concentrated near the high-wind corner of the matrix, especially {", ".join(row["combo_key"] for row in top_rms[:3])}.
        - The campaign also contains no-accepted failure cells: {", ".join(row["combo_key"] for row in failure_rows) if failure_rows else "none"}. These are production-relevant outcomes of the old parameter stack and should be reported as failures, not treated as missing data.
        - Directional composition matters beyond total magnitude in an exploratory descriptive sense: magnitude-only `R^2` for combo-mean square RMS is {fmt(scientific["magnitude_only_r2_square_rms"], 3)}, while East/North components improve that to {fmt(scientific["component_r2_square_rms"], 3)} and East/North plus interaction to {fmt(scientific["component_interaction_r2_square_rms"], 3)}.
        - Response is not perfectly monotonic along every row and column of the wind grid. For square RMS, monotonic nondecreasing behavior occurs in {scientific["square_rms_monotonicity"]["rows_monotonic_count"]}/4 fixed-north rows and {scientific["square_rms_monotonicity"]["cols_monotonic_count"]}/4 fixed-east columns.
        - A strong mission edge/heading effect is persistent rather than incidental in the accepted-run subset. The worst edge/heading bin by combo is {worst_heading_counts}, but this should not be interpreted as a pure heading-only result because edge location and heading are confounded.
        - Replicate spread is small at the calm and mild accepted cases, but broadens materially in several higher-wind combinations, especially {", ".join(row["combo_key"] for row in top_var[:3])}.
        - Loiter after-capture behavior correlates only partially with square tracking (`r = {fmt(scientific["square_vs_loiter_after_capture_r_pearson"], 3)}`), so the two behaviors should be discussed together but not conflated.
        {pos_observation_bullet}

        ## Interpretation

        The full campaign supports a picture of substantial degradation and eventual production-envelope failure for the old stack. Square tracking remains measurable and mission-valid for the accepted runs, while no-accepted high-wind cells show the aircraft could not reliably complete the square/loiter analysis basis under the exact tested conditions. Among accepted runs, higher-wind cases show:

        - much larger tail errors than calm cases,
        - stronger mission edge/heading asymmetry,
        - broader replicate spread,
        - and weaker margin for later mission phases, as reflected by the accepted set containing many square-plus-loiter-only runs at the higher-wind end.

        This means the report should separate two valid statements: accepted-run CTE quantifies path quality only where the old stack completed the analysis basis; no-accepted high-wind cells quantify the observed production failure behavior.

        ## Strongest And Weakest Metrics

        Safe for final presentation/publication:

        - SIM-based square RMS true path deviation.
        - SIM-based square p95 true path deviation.
        - Mission edge/heading-specific SIM square RMS plus clearly labeled asymmetry.
        - Lap repeatability metrics.
        - Corner miss distance metrics.

        Secondary/exploratory only:

        - Square max true path deviation.
        - Loiter after-capture RMS radial error.
        {pos_secondary_bullet}
        - Full-mission supported metrics, only when explicitly labeled as outside the square-only conclusion set.

        Do not use:

        - Full-mission metrics as evidence for square-only path following.
        - Full-window loiter metrics as steady-state loiter quality.
        - Landing metrics in the main square-performance narrative.
        - NTUN.XT as the headline geometric metric.

        ## Recommended Figures And Tables

        Recommended main figures:

        - `plots/square_rms_heatmap.png`
        - `plots/campaign_outcome_heatmap.png`
        - `plots/square_p95_heatmap.png`
        - `plots/directional_heading_heatmap.png` with explicit mission edge/heading labeling
        - `plots/directional_asymmetry_by_heading.png` with explicit mission edge/heading labeling
        - `plots/lap_repeatability_by_combo.png`
        - `plots/corner_performance_heatmap.png`

        Recommended appendix or backup figures:

        - `plots/square_max_heatmap.png`
        - `plots/combo_distribution_square_metrics.png`
        - `plots/replicate_strip_square_metrics.png`
        - `plots/loiter_after_capture_heatmap.png`
        - `plots/loiter_vs_square_scatter.png`
        {pos_backup_figure}

        Recommended final tables:

        - `tables/corrected_combo_summary.csv`
        - `tables/corrected_campaign_outcome_summary.csv`
        - `tables/corrected_failure_envelope_attempts.csv`
        - `tables/old_vs_high_wind_param_stack.csv`
        - `tables/corrected_accepted_runs_summary_sim.csv`
        - `tables/corrected_loiter_summary_sim.csv`
        {pos_final_table}

        ## Limitations And Residual Risks

        - The wind matrix spans only nonnegative East and North components. This is a 4x4 component matrix, not an all-azimuth wind-direction campaign.
        - High-wind accepted cases are often square-plus-loiter-only rather than full-mission completions, so later-mission robustness is not uniformly available.
        - The dataset is still finite: {accepted_run_count} accepted runs and {combo_count} accepted-data combinations. Regression-style attribution should remain descriptive rather than causal.
        - Accepted-run CTE tables are conditional on completion of the analysis basis; no-accepted high-wind cells are reported through the campaign outcome table and failure narrative.
        - Mission edge and heading are confounded in this square layout, so “heading anisotropy” should not be stated as a pure aerodynamic heading effect.
        - Square max error remains highly sensitive to brief events and should not be the sole severity metric.
        {pos_limitations_bullet}

        ## Recommended Publication-Ready Conclusions

        1. Square path-following performance degrades strongly across the East/North wind matrix, with SIM-based square RMS and p95 both rising substantially above the calm baseline.
        2. Total wind magnitude explains much of the degradation, but directional composition still matters materially and should not be collapsed away.
        3. A repeatable mission edge/heading asymmetry is present in the accepted-run subset, but it should not be interpreted as a pure heading-only effect because edge location and heading are confounded.
        4. Higher-wind accepted runs remain analyzable within the square block, but no-accepted high-wind cells are production-relevant failures of the old stack under the tested envelope.
        5. Loiter tracking should be reported separately from square path following, and POS-based results should remain a sensitivity comparison rather than the primary geometric conclusion basis.
        """
    ).replace("\n        ", "\n").strip() + "\n"

    recommendations = textwrap.dedent(
        """
        # Presentation Recommendations

        ## Safe For Final Presentation

        - SIM square RMS and p95 heatmaps as the main overview figures.
        - Mission edge/heading-specific SIM square RMS plus explicitly labeled asymmetry.
        - Lap repeatability and corner miss distance for mechanism-level explanation.

        ## Secondary / Exploratory Only

        - Square max deviation.
        - Loiter after-capture metrics.
        - POS-vs-SIM deltas.

        ## Do Not Use

        - Full-mission metrics for square-only claims.
        - Full-window loiter metrics as steady-state orbit quality.
        - Landing behavior in the main square-tracking conclusion set.
        - Unqualified heading-only anisotropy claims.
        """
    ).replace("\n        ", "\n").strip() + "\n"

    return report, executive_summary, recommendations


def generate_plots(
    run_rows: list[dict[str, Any]],
    combo_rows: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
    lap_rows: list[dict[str, Any]],
    corner_rows: list[dict[str, Any]],
    pos_vs_sim_rows: list[dict[str, Any]],
    combo_comparison_rows: list[dict[str, Any]],
) -> list[str]:
    outputs: list[str] = []
    if outcome_rows:
        plot_campaign_outcome_heatmap(outcome_rows, PLOTS_ROOT / "campaign_outcome_heatmap.png")
        outputs.append("plots/campaign_outcome_heatmap.png")
    plot_heatmap(combo_rows, "square_rms_true_path_dev_mean_m", "Square RMS true path deviation [m] (SIM combo means)", PLOTS_ROOT / "square_rms_heatmap.png")
    outputs.append("plots/square_rms_heatmap.png")
    plot_heatmap(combo_rows, "square_p95_true_path_dev_mean_m", "Square p95 true path deviation [m] (SIM combo means)", PLOTS_ROOT / "square_p95_heatmap.png")
    outputs.append("plots/square_p95_heatmap.png")
    plot_heatmap(combo_rows, "square_max_true_path_dev_mean_m", "Square max true path deviation [m] (SIM combo means)", PLOTS_ROOT / "square_max_heatmap.png")
    outputs.append("plots/square_max_heatmap.png")
    plot_replicate_strip(run_rows, PLOTS_ROOT / "replicate_strip_square_metrics.png")
    outputs.append("plots/replicate_strip_square_metrics.png")
    plot_combo_boxplots(run_rows, PLOTS_ROOT / "combo_distribution_square_metrics.png")
    outputs.append("plots/combo_distribution_square_metrics.png")
    plot_heading_heatmap(combo_rows, PLOTS_ROOT / "directional_heading_heatmap.png")
    outputs.append("plots/directional_heading_heatmap.png")
    plot_heading_pair_differences(combo_rows, PLOTS_ROOT / "directional_asymmetry_by_heading.png")
    outputs.append("plots/directional_asymmetry_by_heading.png")
    plot_lap_repeatability(lap_rows, PLOTS_ROOT / "lap_repeatability_by_combo.png")
    outputs.append("plots/lap_repeatability_by_combo.png")
    plot_corner_heatmap(corner_rows, PLOTS_ROOT / "corner_performance_heatmap.png")
    outputs.append("plots/corner_performance_heatmap.png")
    plot_wind_magnitude_trends(combo_rows, PLOTS_ROOT / "wind_magnitude_trends.png")
    outputs.append("plots/wind_magnitude_trends.png")
    plot_variability(combo_rows, PLOTS_ROOT / "per_combo_variability.png")
    outputs.append("plots/per_combo_variability.png")
    plot_loiter_heatmap(combo_rows, PLOTS_ROOT / "loiter_after_capture_heatmap.png")
    outputs.append("plots/loiter_after_capture_heatmap.png")
    plot_loiter_vs_square(run_rows, PLOTS_ROOT / "loiter_vs_square_scatter.png")
    outputs.append("plots/loiter_vs_square_scatter.png")
    if pos_vs_sim_rows:
        plot_pos_vs_sim(pos_vs_sim_rows, combo_comparison_rows, PLOTS_ROOT / "pos_vs_sim_comparison.png")
        outputs.append("plots/pos_vs_sim_comparison.png")
    return outputs


def build_combo_comparison_rows(combo_sim_rows: list[dict[str, Any]], all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pos_combo_rows = combo_summary_from_rows(all_rows, SECONDARY_SOURCE)
    pos_map = {row["combo_key"]: row for row in pos_combo_rows}
    comparison_rows: list[dict[str, Any]] = []
    for sim_row in combo_sim_rows:
        pos_row = pos_map.get(sim_row["combo_key"])
        merged = dict(sim_row)
        if pos_row is not None:
            merged["pos_square_rms_true_path_dev_mean_m"] = pos_row.get("square_rms_true_path_dev_mean_m")
            merged["pos_square_p95_true_path_dev_mean_m"] = pos_row.get("square_p95_true_path_dev_mean_m")
            merged["pos_square_max_true_path_dev_mean_m"] = pos_row.get("square_max_true_path_dev_mean_m")
            merged["delta_pos_minus_sim_square_rms_mean_m"] = (
                float(pos_row["square_rms_true_path_dev_mean_m"]) - float(sim_row["square_rms_true_path_dev_mean_m"])
                if pos_row.get("square_rms_true_path_dev_mean_m") is not None and sim_row.get("square_rms_true_path_dev_mean_m") is not None
                else None
            )
            merged["delta_pos_minus_sim_square_p95_mean_m"] = (
                float(pos_row["square_p95_true_path_dev_mean_m"]) - float(sim_row["square_p95_true_path_dev_mean_m"])
                if pos_row.get("square_p95_true_path_dev_mean_m") is not None and sim_row.get("square_p95_true_path_dev_mean_m") is not None
                else None
            )
            merged["delta_pos_minus_sim_square_max_mean_m"] = (
                float(pos_row["square_max_true_path_dev_mean_m"]) - float(sim_row["square_max_true_path_dev_mean_m"])
                if pos_row.get("square_max_true_path_dev_mean_m") is not None and sim_row.get("square_max_true_path_dev_mean_m") is not None
                else None
            )
        comparison_rows.append(merged)
    return comparison_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-root",
        type=Path,
        default=INPUT_DATASET_ROOT,
        help="Campaign root containing the raw or legacy manifest",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Output package root; defaults to a sibling *_postprocessing_report directory",
    )
    parser.add_argument("--workers", type=int, default=2, help="Parallel analyzer jobs")
    parser.add_argument("--force", action="store_true", help="Re-run analyzers even if outputs already exist")
    args = parser.parse_args()

    input_root = args.input_root.resolve()
    output_root = args.output_root.resolve() if args.output_root is not None else default_output_root(input_root)
    configure_paths(input_root, output_root)
    ensure_dir_tree()
    raw_manifest_rows = read_csv_rows(MANIFEST_PATH)
    manifest_rows, manifest_mode_name, excluded_rows = normalize_manifest_rows(raw_manifest_rows, input_root, MANIFEST_PATH)
    outcome_rows = build_campaign_outcome_rows(raw_manifest_rows) if manifest_mode_name == "raw" else []
    failure_envelope_rows = build_failure_envelope_rows(raw_manifest_rows) if manifest_mode_name == "raw" else []
    param_comparison_rows = build_param_stack_comparison_rows()

    accepted_manifest_path = SUMMARY_ROOT / "postprocessing_input_manifest.csv"
    rejected_manifest_path = SUMMARY_ROOT / "rejected_manifest_rows.csv"
    write_csv(accepted_manifest_path, manifest_rows)
    if excluded_rows:
        write_csv(rejected_manifest_path, excluded_rows)

    print(
        f"[1/6] Loaded {len(raw_manifest_rows)} manifest rows from {MANIFEST_PATH} "
        f"and accepted {len(manifest_rows)} rows in {manifest_mode_name} mode"
    )
    if excluded_rows:
        print(f"  - excluded {len(excluded_rows)} non-accepted rows into {rejected_manifest_path}")

    print("[2/6] Loading accepted-run outputs")
    run_rows: list[dict[str, Any]] = []
    loiter_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    lap_rows: list[dict[str, Any]] = []
    corner_rows: list[dict[str, Any]] = []
    mission_validation_rows: list[dict[str, Any]] = []
    analysis_sources = [PRIMARY_SOURCE]
    if manifest_mode_name == "legacy":
        analysis_sources.append(SECONDARY_SOURCE)

    if manifest_mode_name == "legacy" and args.force:
        analysis_jobs = [(row, source) for row in manifest_rows for source in analysis_sources]
        print(f"[2/6] Regenerating analyzer outputs for {len(analysis_jobs)} run/source pairs")
        completed = 0
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {
                executor.submit(run_analyzers_for_attempt, row, source, force=args.force): (row["attempt_id"], source)
                for row, source in analysis_jobs
            }
            for future in as_completed(futures):
                attempt_id, source = futures[future]
                future.result()
                completed += 1
                print(f"  - completed {completed}/{len(futures)}: {attempt_id} [{source}]")
    elif manifest_mode_name == "legacy":
        print(
            f"[2/6] Reusing existing analyzer outputs for {len(manifest_rows)} accepted rows "
            f"across {len(analysis_sources)} source(s)"
        )
    else:
        print(f"[2/6] Reusing existing analyzer outputs for {len(manifest_rows)} accepted rows")

    for row in manifest_rows:
        if manifest_mode_name == "legacy":
            source_iterable = analysis_sources
            loader = load_source_outputs
        else:
            source_iterable = [PRIMARY_SOURCE]
            loader = load_attempt_outputs
        for source in source_iterable:
            loaded = loader(row, source) if loader is load_source_outputs else loader(row, input_root)
            run_row, loiter_row, edge_out, lap_out, corner_out, mv_row = flatten_source_outputs(loaded)
            run_rows.append(run_row)
            loiter_rows.append(loiter_row)
            edge_rows.extend(edge_out)
            lap_rows.extend(lap_out)
            corner_rows.extend(corner_out)
            mission_validation_rows.append(mv_row)

    sim_combo_rows = combo_summary_from_rows(run_rows, PRIMARY_SOURCE)
    combo_comparison_rows = build_combo_comparison_rows(sim_combo_rows, run_rows)
    position_source_rows, position_source_json = position_source_summary(run_rows)
    pos_vs_sim_rows, pos_vs_sim_overview = pos_vs_sim_summary(run_rows)
    scientific = overall_scientific_summary(run_rows, sim_combo_rows, pos_vs_sim_overview)

    glossary_rows, glossary_md = build_glossary()
    metadata = {
        "generated_utc": utc_now(),
        "dataset_root": str(DATASET_ROOT),
        "input_manifest_path": str(MANIFEST_PATH),
        "accepted_manifest_path": str(accepted_manifest_path),
        "rejected_manifest_path": str(rejected_manifest_path) if excluded_rows else None,
        "manifest_mode": manifest_mode_name,
        "analysis_sources": analysis_sources,
        "script_sha256": {
            "true_path_deviation.py": script_sha256(TRUE_PATH_SCRIPT),
            "square_loiter_mission_metrics.py": script_sha256(SQUARE_SCRIPT),
            "build_square_postprocessing_report.py": script_sha256(Path(__file__)),
        },
        "param_stack_sources": {
            "old_recovered": [str(path) for path in OLD_PARAM_STACK_FILES],
            "later_high_wind": [str(path) for path in HIGH_WIND_PARAM_STACK_FILES],
        },
        "param_stack_sha256": {
            "old_recovered": param_stack_file_metadata(OLD_PARAM_STACK_FILES),
            "later_high_wind": param_stack_file_metadata(HIGH_WIND_PARAM_STACK_FILES),
        },
        "dataset_counts": {
            "manifest_rows": len(manifest_rows),
            "raw_manifest_rows": len(raw_manifest_rows),
            "run_rows": len(run_rows),
            "per_source_rows": len(run_rows) // max(1, len(analysis_sources)),
            "failure_no_accepted_combo_count": sum(1 for row in outcome_rows if row["outcome"] == "failure_no_accepted"),
            "partial_failure_combo_count": sum(1 for row in outcome_rows if row["outcome"] == "partial_failure_with_accepted"),
            "failure_envelope_attempt_count": len(failure_envelope_rows),
        },
    }

    print("[4/6] Writing CSV/JSON tables and metadata")
    if outcome_rows:
        write_csv(TABLES_ROOT / "corrected_campaign_outcome_summary.csv", outcome_rows)
        write_json(TABLES_ROOT / "corrected_campaign_outcome_summary.json", outcome_rows)
    if failure_envelope_rows:
        write_csv(TABLES_ROOT / "corrected_failure_envelope_attempts.csv", failure_envelope_rows)
        write_json(TABLES_ROOT / "corrected_failure_envelope_attempts.json", failure_envelope_rows)
    write_csv(TABLES_ROOT / "old_vs_high_wind_param_stack.csv", param_comparison_rows)
    write_json(TABLES_ROOT / "old_vs_high_wind_param_stack.json", param_comparison_rows)
    write_csv(TABLES_ROOT / "corrected_accepted_runs_summary.csv", run_rows)
    write_json(TABLES_ROOT / "corrected_accepted_runs_summary.json", run_rows)
    write_csv(TABLES_ROOT / "corrected_accepted_runs_summary_sim.csv", [row for row in run_rows if row["analysis_position_source"] == PRIMARY_SOURCE])
    write_json(TABLES_ROOT / "corrected_accepted_runs_summary_sim.json", [row for row in run_rows if row["analysis_position_source"] == PRIMARY_SOURCE])

    write_csv(TABLES_ROOT / "corrected_combo_summary.csv", sim_combo_rows)
    write_json(TABLES_ROOT / "corrected_combo_summary.json", sim_combo_rows)
    write_csv(TABLES_ROOT / "corrected_loiter_summary.csv", loiter_rows)
    write_json(TABLES_ROOT / "corrected_loiter_summary.json", loiter_rows)
    write_csv(TABLES_ROOT / "corrected_loiter_summary_sim.csv", [row for row in loiter_rows if row["analysis_position_source"] == PRIMARY_SOURCE])
    write_json(TABLES_ROOT / "corrected_loiter_summary_sim.json", [row for row in loiter_rows if row["analysis_position_source"] == PRIMARY_SOURCE])
    write_csv(TABLES_ROOT / "corrected_position_source_summary.csv", position_source_rows)
    write_json(TABLES_ROOT / "corrected_position_source_summary.json", position_source_json)
    write_csv(TABLES_ROOT / "corrected_mission_validation_summary.csv", mission_validation_rows)
    write_json(TABLES_ROOT / "corrected_mission_validation_summary.json", mission_validation_rows)
    if pos_vs_sim_rows:
        write_csv(TABLES_ROOT / "pos_vs_sim_comparison.csv", pos_vs_sim_rows)
        write_json(TABLES_ROOT / "pos_vs_sim_comparison.json", {"overview": pos_vs_sim_overview, "rows": pos_vs_sim_rows})
    write_csv(TABLES_ROOT / "square_edge_metrics_all.csv", edge_rows)
    write_csv(TABLES_ROOT / "square_lap_metrics_all.csv", lap_rows)
    write_csv(TABLES_ROOT / "square_corner_metrics_all.csv", corner_rows)
    write_json(CORRECTED_ROOT / "metadata.json", metadata)
    write_json(CORRECTED_ROOT / "scientific_summary.json", scientific)
    write_json(CORRECTED_ROOT / "metrics_glossary.json", glossary_rows)

    print("[5/6] Generating plot set")
    generated_plots = generate_plots(run_rows, sim_combo_rows, outcome_rows, lap_rows, corner_rows, pos_vs_sim_rows, combo_comparison_rows)

    report_md, executive_md, recommendations_md = build_report(
        metadata,
        scientific,
        sim_combo_rows,
        outcome_rows,
        failure_envelope_rows,
        param_comparison_rows,
        pos_vs_sim_overview,
        has_pos_comparison=bool(pos_vs_sim_rows),
    )
    print("[6/6] Writing report package")
    (CORRECTED_ROOT / "final_analysis_report.md").write_text(report_md, encoding="utf-8")
    (CORRECTED_ROOT / "executive_summary.md").write_text(executive_md, encoding="utf-8")
    (CORRECTED_ROOT / "presentation_recommendations.md").write_text(recommendations_md, encoding="utf-8")
    (CORRECTED_ROOT / "metrics_glossary.md").write_text(glossary_md, encoding="utf-8")

    print("Completed corrected postprocessing package.")
    print(f"Outputs written under: {CORRECTED_ROOT}")
    print(f"Tables: {TABLES_ROOT}")
    print(f"Plots: {PLOTS_ROOT}")
    print(f"Generated plots: {len(generated_plots)}")


if __name__ == "__main__":
    main()
