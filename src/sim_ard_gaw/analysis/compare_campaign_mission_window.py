#!/usr/bin/env python3
"""Compare square/loiter metrics across campaigns using mission sequence windows.

This script is intended for the fixed-harness old-param vs new-param square wind
campaigns where mission duration is not comparable.  It reads each BIN directly,
uses mission execution records to isolate the shared mission contract, and reports:

    square: seq 3..22
    loiter: seq 23, bounded by the next mission event where available
    excluded: seq >= 24 landing setup/landing

For the first trial, pass one old-param BIN and one new-param BIN.  Later the same
script can be run with multiple --old-bin/--new-bin values; run-level rows are
kept separate and combo-level deltas are aggregated across valid runs.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    from . import square_loiter_mission_metrics as square_metrics
except ImportError:  # direct script execution from this directory
    import square_loiter_mission_metrics as square_metrics  # type: ignore[no-redef]


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
VAR_LOGS_ROOT = WORKSPACE_ROOT / "var" / "logs"
DEFAULT_OUTDIR = (
    VAR_LOGS_ROOT
    / "mission_window_comparison"
    / "sample_017_old_params_vs_018_new_params"
)
DEFAULT_OLD_CAMPAIGN_ROOT = (
    VAR_LOGS_ROOT / "017_params_old_009_matrix_r3_plugin_fixed"
)
DEFAULT_OLD_ACCEPTED_MANIFEST = (
    DEFAULT_OLD_CAMPAIGN_ROOT / "internal_wind_audit" / "accepted_bins.txt"
)

BIN_NAME_RE = re.compile(
    r"wind_x_(?P<x>\d+)_y_(?P<y>\d+)__rep_(?P<rep>\d+)__attempt_(?P<attempt>\d+)\.BIN$"
)

HEADINGS = ("northbound", "westbound", "southbound", "eastbound")
SQUARE_START_SEQ = square_metrics.SQUARE_EDGE_SEQ_RANGE.start
SQUARE_END_SEQ = square_metrics.SQUARE_EDGE_SEQ_RANGE.stop - 1
STEADY_START_SEQ = SQUARE_START_SEQ + 4
LOITER_SEQ = square_metrics.LOITER_SEQ
LANDING_CUT_SEQ = 24


@dataclass
class BinMetrics:
    label: str
    side: str
    bin_path: str
    combo_key: str
    rep: int | None
    attempt: int | None
    position_source: str
    old_manifest_path: str | None
    old_manifest_ok: bool | None
    old_manifest_error: str
    mission_validation_ok: bool
    mission_validation_errors: str
    required_shared_contract_ok: bool
    required_shared_contract_errors: str
    square_valid: bool
    square_valid_error: str
    loiter_valid: bool
    loiter_valid_error: str
    square_start_seq: int
    square_end_seq: int
    steady_start_seq: int
    loiter_seq: int
    landing_cut_seq: int
    square_segment_count: int
    square_sample_count: int
    square_start_time_s: float | None
    square_end_time_s: float | None
    loiter_start_time_s: float | None
    loiter_end_time_s: float | None
    loiter_window_status: str
    loiter_window_end_seq: int | None
    landing_cut_time_s: float | None
    all_mean_true_path_dev_m: float
    all_rms_true_path_dev_m: float
    all_p95_true_path_dev_m: float
    all_max_true_path_dev_m: float
    steady_mean_true_path_dev_m: float
    steady_rms_true_path_dev_m: float
    steady_p95_true_path_dev_m: float
    steady_max_true_path_dev_m: float
    loiter_available: bool
    loiter_duration_s: float | None
    loiter_rms_radial_error_after_capture_m: float | None
    loiter_turns_flown_after_capture: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--old-bin",
        action="append",
        type=Path,
        default=[],
        help="Old-param fixed-harness campaign BIN to analyze. May be repeated.",
    )
    parser.add_argument(
        "--new-bin",
        action="append",
        type=Path,
        default=[],
        help="New-param fixed-harness campaign BIN to analyze. May be repeated.",
    )
    parser.add_argument(
        "--position-source",
        choices=("sim", "pos"),
        default="sim",
        help="Position source to use for metrics. Defaults to SIM ground truth.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help=f"Output directory. Defaults to {DEFAULT_OUTDIR}.",
    )
    parser.add_argument(
        "--old-accepted-manifest",
        type=Path,
        default=DEFAULT_OLD_ACCEPTED_MANIFEST,
        help=(
            "Manifest of old-param BINs accepted by internal wind audit. "
            "Old-param BINs must be listed here unless --allow-invalid is used."
        ),
    )
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help=(
            "Write audit rows even when invalid inputs are present and return success. "
            "Invalid rows are still excluded from combo deltas."
        ),
    )
    return parser.parse_args()


def finite_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def round_float(value: Any, digits: int = 6) -> float | None:
    result = finite_or_none(value)
    if result is None:
        return None
    return round(result, digits)


def round_float_or_nan(value: Any, digits: int = 6) -> float:
    result = round_float(value, digits=digits)
    return result if result is not None else math.nan


def fmt_float(value: Any, digits: int = 3) -> str:
    result = finite_or_none(value)
    return f"{result:.{digits}f}" if result is not None else "nan"


def parse_bin_name(path: Path) -> tuple[str, int | None, int | None]:
    match = BIN_NAME_RE.search(path.name)
    if match is None:
        return path.stem, None, None
    x = int(match.group("x"))
    y = int(match.group("y"))
    rep = int(match.group("rep"))
    attempt = int(match.group("attempt"))
    return f"wind_x_{x:02d}_y_{y:02d}", rep, attempt


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def load_accepted_manifest(manifest_path: Path | None) -> set[str] | None:
    if manifest_path is None:
        return None
    manifest_path = manifest_path.resolve()
    if not manifest_path.exists():
        return None
    accepted: set[str] = set()
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            accepted.add(line)
    return accepted


def check_old_manifest(
    path: Path,
    *,
    side: str,
    accepted_manifest: set[str] | None,
    manifest_path: Path | None,
) -> tuple[str | None, bool | None, str]:
    if side != "old_params":
        return None, None, ""
    manifest_label = str(manifest_path.resolve()) if manifest_path is not None else None
    if accepted_manifest is None:
        return manifest_label, False, "old accepted manifest missing or unreadable"

    if path_is_relative_to(path, DEFAULT_OLD_CAMPAIGN_ROOT):
        manifest_key = path.relative_to(DEFAULT_OLD_CAMPAIGN_ROOT).as_posix()
    else:
        manifest_key = path.as_posix()

    if manifest_key not in accepted_manifest:
        return manifest_label, False, f"old BIN not listed in accepted manifest: {manifest_key}"
    return manifest_label, True, ""


def sample_stats(values: list[float]) -> dict[str, float]:
    arr = np.array(values, dtype=float)
    if not arr.size:
        return {
            "samples": 0.0,
            "mean_true_path_dev_m": math.nan,
            "rms_true_path_dev_m": math.nan,
            "p95_true_path_dev_m": math.nan,
            "max_true_path_dev_m": math.nan,
        }
    return {
        "samples": float(arr.size),
        "mean_true_path_dev_m": float(np.mean(arr)),
        "rms_true_path_dev_m": float(np.sqrt(np.mean(arr**2))),
        "p95_true_path_dev_m": float(np.nanpercentile(arr, 95.0)),
        "max_true_path_dev_m": float(np.max(arr)),
    }


def first_execution_by_seq(
    executions: list[square_metrics.MissionExecution],
) -> dict[int, square_metrics.MissionExecution]:
    by_seq: dict[int, square_metrics.MissionExecution] = {}
    for item in sorted(executions, key=lambda entry: entry.time_us):
        by_seq.setdefault(item.seq, item)
    return by_seq


def validate_shared_contract(
    commands: dict[int, square_metrics.MissionCommand],
    executions: list[square_metrics.MissionExecution],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    execution_by_seq = first_execution_by_seq(executions)

    for seq in range(SQUARE_START_SEQ, SQUARE_END_SEQ + 1):
        cmd = commands.get(seq)
        if cmd is None:
            errors.append(f"missing CMD seq {seq}")
        elif cmd.cmd_id != square_metrics.MAV_CMD_NAV_WAYPOINT:
            errors.append(f"CMD seq {seq} expected waypoint 16, got {cmd.cmd_id}")
        if seq not in execution_by_seq:
            errors.append(f"missing MISE seq {seq}")

    loiter_cmd = commands.get(LOITER_SEQ)
    if loiter_cmd is None:
        errors.append(f"missing CMD seq {LOITER_SEQ}")
    elif loiter_cmd.cmd_id != square_metrics.MAV_CMD_NAV_LOITER_TURNS:
        errors.append(f"CMD seq {LOITER_SEQ} expected loiter turns 18, got {loiter_cmd.cmd_id}")
    if LOITER_SEQ not in execution_by_seq:
        errors.append(f"missing MISE seq {LOITER_SEQ}")

    cut_cmd = commands.get(LANDING_CUT_SEQ)
    if cut_cmd is None:
        errors.append(f"missing CMD seq {LANDING_CUT_SEQ}; cannot verify landing exclusion boundary")
    elif cut_cmd.cmd_id != 189:
        errors.append(f"CMD seq {LANDING_CUT_SEQ} expected DO_LAND_START 189, got {cut_cmd.cmd_id}")

    return not errors, errors


def flatten_segment_rows(
    segment_rows: dict[int, list[dict[str, float | int | str | bool]]],
    *,
    start_seq: int,
    end_seq: int,
) -> list[dict[str, float | int | str | bool]]:
    rows: list[dict[str, float | int | str | bool]] = []
    for seq in range(start_seq, end_seq + 1):
        rows.extend(segment_rows.get(seq, []))
    return rows


def validation_text(errors: list[str]) -> str:
    return "; ".join(errors)


def analyze_bin(
    path: Path,
    *,
    label: str,
    side: str,
    position_source: str,
    accepted_manifest: set[str] | None,
    manifest_path: Path | None,
) -> BinMetrics:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"BIN not found: {path}")
    manifest_label, manifest_ok, manifest_error = check_old_manifest(
        path,
        side=side,
        accepted_manifest=accepted_manifest,
        manifest_path=manifest_path,
    )

    commands, executions, positions = square_metrics.load_log_data(path, position_source)
    ref_cmd = commands.get(0)
    if ref_cmd is not None and ref_cmd.has_location:
        ref_lat_deg = ref_cmd.lat_deg
        ref_lng_deg = ref_cmd.lng_deg
    else:
        ref_lat_deg = positions[0].lat_deg
        ref_lng_deg = positions[0].lng_deg

    mission_validation = square_metrics.validate_campaign_mission(
        commands,
        ref_lat_deg,
        ref_lng_deg,
    )
    shared_ok, shared_errors = validate_shared_contract(commands, executions)

    square_segments = square_metrics.build_square_segments(
        commands,
        executions,
        ref_lat_deg,
        ref_lng_deg,
    )
    segment_rows = square_metrics.compute_square_segment_rows(
        square_segments,
        positions,
        ref_lat_deg,
        ref_lng_deg,
    )
    all_rows = flatten_segment_rows(
        segment_rows,
        start_seq=SQUARE_START_SEQ,
        end_seq=SQUARE_END_SEQ,
    )
    steady_rows = flatten_segment_rows(
        segment_rows,
        start_seq=STEADY_START_SEQ,
        end_seq=SQUARE_END_SEQ,
    )
    all_stats = sample_stats([float(row["true_path_dev_m"]) for row in all_rows])
    steady_stats = sample_stats([float(row["true_path_dev_m"]) for row in steady_rows])

    loiter_summary, _loiter_rows = square_metrics.build_loiter_metrics(
        commands,
        executions,
        positions,
        ref_lat_deg,
        ref_lng_deg,
    )
    execution_by_seq = first_execution_by_seq(executions)
    square_start = execution_by_seq.get(SQUARE_START_SEQ)
    square_end = execution_by_seq.get(LOITER_SEQ)
    loiter_start = execution_by_seq.get(LOITER_SEQ)
    landing_cut = execution_by_seq.get(LANDING_CUT_SEQ)
    combo_key, rep, attempt = parse_bin_name(path)
    square_errors: list[str] = []
    if side == "old_params" and not manifest_ok:
        square_errors.append(manifest_error)
    if not mission_validation["ok"]:
        square_errors.extend(str(item) for item in mission_validation.get("errors", []))
    if not shared_ok:
        square_errors.extend(shared_errors)
    if len(square_segments) != square_metrics.EXPECTED_SQUARE_SEGMENTS:
        square_errors.append(
            f"square segment count {len(square_segments)} != {square_metrics.EXPECTED_SQUARE_SEGMENTS}"
        )
    if int(all_stats["samples"]) <= 0:
        square_errors.append("no square samples in seq 3..22")

    loiter_errors: list[str] = []
    if square_errors:
        loiter_errors.append("square window invalid")
    if not loiter_summary.get("available"):
        loiter_errors.append(f"loiter unavailable: {loiter_summary.get('reason', 'unknown')}")
    if loiter_summary.get("loiter_window_status") != "bounded_by_next_mise":
        loiter_errors.append(
            f"loiter window status {loiter_summary.get('loiter_window_status')} != bounded_by_next_mise"
        )
    if loiter_summary.get("loiter_window_end_seq") != LANDING_CUT_SEQ:
        loiter_errors.append(
            f"loiter end seq {loiter_summary.get('loiter_window_end_seq')} != {LANDING_CUT_SEQ}"
        )

    return BinMetrics(
        label=label,
        side=side,
        bin_path=str(path),
        combo_key=combo_key,
        rep=rep,
        attempt=attempt,
        position_source=position_source,
        old_manifest_path=manifest_label,
        old_manifest_ok=manifest_ok,
        old_manifest_error=manifest_error,
        mission_validation_ok=bool(mission_validation["ok"]),
        mission_validation_errors="; ".join(str(item) for item in mission_validation.get("errors", [])),
        required_shared_contract_ok=shared_ok,
        required_shared_contract_errors=validation_text(shared_errors),
        square_valid=not square_errors,
        square_valid_error=validation_text(square_errors),
        loiter_valid=not loiter_errors,
        loiter_valid_error=validation_text(loiter_errors),
        square_start_seq=SQUARE_START_SEQ,
        square_end_seq=SQUARE_END_SEQ,
        steady_start_seq=STEADY_START_SEQ,
        loiter_seq=LOITER_SEQ,
        landing_cut_seq=LANDING_CUT_SEQ,
        square_segment_count=len(square_segments),
        square_sample_count=int(all_stats["samples"]),
        square_start_time_s=round_float(square_start.time_us * 1.0e-6 if square_start else None),
        square_end_time_s=round_float(square_end.time_us * 1.0e-6 if square_end else None),
        loiter_start_time_s=round_float(loiter_start.time_us * 1.0e-6 if loiter_start else None),
        loiter_end_time_s=round_float(loiter_summary.get("loiter_window_end_time_s")),
        loiter_window_status=str(loiter_summary.get("loiter_window_status", "unavailable")),
        loiter_window_end_seq=loiter_summary.get("loiter_window_end_seq"),
        landing_cut_time_s=round_float(landing_cut.time_us * 1.0e-6 if landing_cut else None),
        all_mean_true_path_dev_m=round_float_or_nan(all_stats["mean_true_path_dev_m"]),
        all_rms_true_path_dev_m=round_float_or_nan(all_stats["rms_true_path_dev_m"]),
        all_p95_true_path_dev_m=round_float_or_nan(all_stats["p95_true_path_dev_m"]),
        all_max_true_path_dev_m=round_float_or_nan(all_stats["max_true_path_dev_m"]),
        steady_mean_true_path_dev_m=round_float_or_nan(steady_stats["mean_true_path_dev_m"]),
        steady_rms_true_path_dev_m=round_float_or_nan(steady_stats["rms_true_path_dev_m"]),
        steady_p95_true_path_dev_m=round_float_or_nan(steady_stats["p95_true_path_dev_m"]),
        steady_max_true_path_dev_m=round_float_or_nan(steady_stats["max_true_path_dev_m"]),
        loiter_available=bool(loiter_summary.get("available")),
        loiter_duration_s=round_float(loiter_summary.get("duration_s")),
        loiter_rms_radial_error_after_capture_m=round_float(
            loiter_summary.get("rms_radial_error_after_capture_m")
        ),
        loiter_turns_flown_after_capture=round_float(
            loiter_summary.get("turns_flown_after_capture")
        ),
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mean_or_nan(rows: list[BinMetrics], attr: str) -> float:
    values = [finite_or_none(getattr(row, attr)) for row in rows]
    cleaned = [value for value in values if value is not None]
    return round_float_or_nan(float(np.mean(cleaned)) if cleaned else math.nan)


def sample_std_or_nan(rows: list[BinMetrics], attr: str) -> float:
    values = [finite_or_none(getattr(row, attr)) for row in rows]
    cleaned = [value for value in values if value is not None]
    if len(cleaned) < 2:
        return math.nan
    return round_float_or_nan(float(np.std(cleaned, ddof=1)))


def build_combo_rows(old_rows: list[BinMetrics], new_rows: list[BinMetrics]) -> list[dict[str, Any]]:
    combos = sorted({row.combo_key for row in old_rows + new_rows})
    rows: list[dict[str, Any]] = []
    for combo_key in combos:
        old_all = [row for row in old_rows if row.combo_key == combo_key]
        new_all = [row for row in new_rows if row.combo_key == combo_key]
        old_square = [row for row in old_all if row.square_valid]
        new_square = [row for row in new_all if row.square_valid]
        old_loiter = [row for row in old_square if row.loiter_valid]
        new_loiter = [row for row in new_square if row.loiter_valid]

        old_square_rms = mean_or_nan(old_square, "all_rms_true_path_dev_m")
        new_square_rms = mean_or_nan(new_square, "all_rms_true_path_dev_m")
        old_square_p95 = mean_or_nan(old_square, "all_p95_true_path_dev_m")
        new_square_p95 = mean_or_nan(new_square, "all_p95_true_path_dev_m")
        old_steady_rms = mean_or_nan(old_square, "steady_rms_true_path_dev_m")
        new_steady_rms = mean_or_nan(new_square, "steady_rms_true_path_dev_m")
        old_loiter_rms = mean_or_nan(old_loiter, "loiter_rms_radial_error_after_capture_m")
        new_loiter_rms = mean_or_nan(new_loiter, "loiter_rms_radial_error_after_capture_m")

        rows.append(
            {
                "combo_key": combo_key,
                "old_n_total": len(old_all),
                "new_n_total": len(new_all),
                "old_n_square_valid": len(old_square),
                "new_n_square_valid": len(new_square),
                "square_comparison_valid": bool(old_square and new_square),
                "old_n_square_invalid": len(old_all) - len(old_square),
                "new_n_square_invalid": len(new_all) - len(new_square),
                "old_n_loiter_valid": len(old_loiter),
                "new_n_loiter_valid": len(new_loiter),
                "loiter_comparison_valid": bool(old_loiter and new_loiter),
                "old_square_rms_mean_m": old_square_rms,
                "new_square_rms_mean_m": new_square_rms,
                "delta_new_minus_old_square_rms_mean_m": round_float(
                    new_square_rms - old_square_rms
                ),
                "old_square_rms_std_m": sample_std_or_nan(old_square, "all_rms_true_path_dev_m"),
                "new_square_rms_std_m": sample_std_or_nan(new_square, "all_rms_true_path_dev_m"),
                "old_square_p95_mean_m": old_square_p95,
                "new_square_p95_mean_m": new_square_p95,
                "delta_new_minus_old_square_p95_mean_m": round_float(
                    new_square_p95 - old_square_p95
                ),
                "old_steady_rms_mean_m": old_steady_rms,
                "new_steady_rms_mean_m": new_steady_rms,
                "delta_new_minus_old_steady_rms_mean_m": round_float(
                    new_steady_rms - old_steady_rms
                ),
                "old_loiter_rms_after_capture_mean_m": old_loiter_rms,
                "new_loiter_rms_after_capture_mean_m": new_loiter_rms,
                "delta_new_minus_old_loiter_rms_after_capture_mean_m": round_float(
                    new_loiter_rms - old_loiter_rms
                ),
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    old_bins = [path.resolve() for path in args.old_bin]
    new_bins = [path.resolve() for path in args.new_bin]
    if not old_bins or not new_bins:
        raise SystemExit("Pass at least one --old-bin and one --new-bin for this comparison.")
    accepted_manifest = load_accepted_manifest(args.old_accepted_manifest)

    old_rows = [
        analyze_bin(
            path,
            label=f"old_{idx:02d}",
            side="old_params",
            position_source=args.position_source,
            accepted_manifest=accepted_manifest,
            manifest_path=args.old_accepted_manifest,
        )
        for idx, path in enumerate(old_bins, start=1)
    ]
    new_rows = [
        analyze_bin(
            path,
            label=f"new_{idx:02d}",
            side="new_params",
            position_source=args.position_source,
            accepted_manifest=None,
            manifest_path=None,
        )
        for idx, path in enumerate(new_bins, start=1)
    ]
    all_rows = old_rows + new_rows
    invalid_rows = [row for row in all_rows if not row.square_valid]
    combo_rows = build_combo_rows(old_rows, new_rows)

    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    metrics_rows = [asdict(row) for row in all_rows]
    write_csv(outdir / "mission_window_metrics.csv", metrics_rows)
    write_json(outdir / "mission_window_metrics.json", metrics_rows)
    write_csv(outdir / "mission_window_combo_deltas.csv", combo_rows)
    write_json(outdir / "mission_window_combo_deltas.json", combo_rows)

    print(f"Analyzed {len(old_rows)} old BIN(s) and {len(new_rows)} new BIN(s)")
    print(f"Mission window: square seq {SQUARE_START_SEQ}..{SQUARE_END_SEQ}; loiter seq {LOITER_SEQ}; exclude seq >= {LANDING_CUT_SEQ}")
    for row in all_rows:
        print(
            f"{row.label} {row.combo_key}: "
            f"contract_ok={row.required_shared_contract_ok}, "
            f"square_valid={row.square_valid}, "
            f"square_segments={row.square_segment_count}, "
            f"square_rms={row.all_rms_true_path_dev_m:.3f} m, "
            f"loiter_status={row.loiter_window_status}, "
            f"loiter_end_seq={row.loiter_window_end_seq}"
        )
    for row in combo_rows:
        print(
            f"Combo {row['combo_key']}: "
            f"valid square n old/new={row['old_n_square_valid']}/{row['new_n_square_valid']}, "
            "delta square RMS mean new-old="
            f"{fmt_float(row['delta_new_minus_old_square_rms_mean_m'])} m, "
            "delta steady RMS mean new-old="
            f"{fmt_float(row['delta_new_minus_old_steady_rms_mean_m'])} m"
        )
    print(f"Output directory: {outdir}")
    if invalid_rows and not args.allow_invalid:
        invalid_text = "; ".join(
            f"{row.label} {row.combo_key}: {row.square_valid_error}" for row in invalid_rows
        )
        print(f"Invalid input row(s); outputs written but deltas exclude them: {invalid_text}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
