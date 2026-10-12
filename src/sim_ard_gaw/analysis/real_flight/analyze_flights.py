#!/usr/bin/env python3
"""Analyze vibration, redundant IMUs, and EKF3 behavior in real flight logs.

The script performs a discovery pass to locate the main airborne interval and a
measurement pass to calculate phase-aware metrics.  It writes only beneath the
chosen output directory; raw DataFlash logs are never modified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pymavlink import mavutil

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parents[3]
if str(WORKSPACE / "src") not in sys.path:
    sys.path.insert(0, str(WORKSPACE / "src"))

from sim_ard_gaw.analysis.real_flight.analysis_core import (  # noqa: E402
    Interval,
    describe,
    dominant_frequency,
    effective_rate_hz,
    hann_psd,
    integrate_band_rms,
    monotonic_increment,
    pearson_correlation,
    phase_for_time,
    select_airborne_interval,
    separated_peaks,
    threshold_fraction,
)


DEFAULT_INPUT = WORKSPACE / "var" / "real_flights"
DEFAULT_OUTPUT = WORKSPACE / "var" / "analysis" / "real_flight_imu_analysis_20260901" / "results"

FLIGHT_IDENTITIES = {
    "2025-12-30_094938_shahin_e.bin": ("shahin_e", "Shahin electrical"),
    "2026-02-03_143217_shahin_f.bin": ("shahin_f", "Shahin fuel"),
    "2026-07-27_101745_b73_1.bin": ("b73_1", "B73 flight 1"),
    "2026-07-28_103518_shaba7.bin": ("shaba7", "Shaba7"),
    "2026-07-29_105334_b73_2.bin": ("b73_2", "B73 flight 2"),
}

DISCOVERY_TYPES = ["GPS", "GPA", "POS", "MSG", "ARM", "MODE", "PARM"]
MEASUREMENT_TYPES = [
    "GPS",
    "GPA",
    "POS",
    "CTUN",
    "VIBE",
    "IMU",
    "XKF1",
    "XKF2",
    "XKF3",
    "XKF4",
    "XKF5",
    "XKFS",
    "XKT",
    "ISBH",
    "ISBD",
    "FTNS",
    "PM",
    "ERR",
]
PARAMETER_NAMES = {
    "AHRS_EKF_TYPE",
    "EK3_PRIMARY",
    "EK3_IMU_MASK",
    "EK3_POS_I_GATE",
    "EK3_VEL_I_GATE",
    "EK3_HGT_I_GATE",
    "EK3_MAG_I_GATE",
    "INS_FAST_SAMPLE",
    "INS_GYRO_FILTER",
    "INS_ACCEL_FILTER",
    "INS_GYRO_RATE",
    "INS_LOG_BAT_MASK",
    "INS_LOG_BAT_OPT",
    "INS_LOG_BAT_LGIN",
    "INS_HNTCH_ENABLE",
    "INS_HNTCH_FREQ",
    "INS_HNTCH_BW",
    "INS_HNTCH_ATT",
    "INS_HNTCH_MODE",
    "INS_HNTCH_REF",
    "INS_HNTCH_OPTS",
    "LOG_BITMASK",
}

PLANE_MODE_NAMES = {
    0: "MANUAL",
    1: "CIRCLE",
    2: "STABILIZE",
    3: "TRAINING",
    4: "ACRO",
    5: "FBWA",
    6: "FBWB",
    7: "CRUISE",
    8: "AUTOTUNE",
    10: "AUTO",
    11: "RTL",
    12: "LOITER",
    13: "TAKEOFF",
    14: "AVOID_ADSB",
    15: "GUIDED",
    17: "QSTABILIZE",
    18: "QHOVER",
    19: "QLOITER",
    20: "QLAND",
    21: "QRTL",
    22: "QAUTOTUNE",
    23: "QACRO",
    24: "THERMAL",
}


def message_dict(message: Any) -> dict[str, Any]:
    row = message.to_dict()
    row.pop("mavpackettype", None)
    return row


def time_s(row: dict[str, Any], field_name: str = "TimeUS") -> float | None:
    value = row.get(field_name)
    if value is None:
        return None
    return float(value) * 1.0e-6


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Interval):
        return {"start_s": value.start_s, "end_s": value.end_s, "duration_s": value.duration_s}
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=json_default) + "\n")


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not materialized:
        path.write_text("")
        return
    field_names: list[str] = []
    for row in materialized:
        for key in row:
            if key not in field_names:
                field_names.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(materialized)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class Discovery:
    path: Path
    flight_id: str
    aircraft: str
    sha256: str
    size_bytes: int
    message_counts: dict[str, int]
    parameters: dict[str, float]
    messages: list[dict[str, Any]]
    arms: list[dict[str, Any]]
    modes: list[dict[str, Any]]
    gps: list[dict[str, Any]]
    positions: list[dict[str, Any]]
    firmware: str | None
    log_start_s: float
    log_end_s: float
    airborne: Interval


def infer_identity(path: Path) -> tuple[str, str]:
    if path.name in FLIGHT_IDENTITIES:
        return FLIGHT_IDENTITIES[path.name]
    slug = re.sub(r"[^a-z0-9]+", "_", path.stem.lower()).strip("_")
    return slug, path.stem


def discover_log(path: Path) -> Discovery:
    flight_id, aircraft = infer_identity(path)
    connection = mavutil.mavlink_connection(str(path), robust_parsing=True)
    gps: list[dict[str, Any]] = []
    positions: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    arms: list[dict[str, Any]] = []
    modes: list[dict[str, Any]] = []
    parameters: dict[str, float] = {}
    observed_times: list[float] = []
    try:
        while True:
            message = connection.recv_match(type=DISCOVERY_TYPES, blocking=False)
            if message is None:
                break
            kind = message.get_type()
            row = message_dict(message)
            timestamp = time_s(row)
            if timestamp is not None:
                observed_times.append(timestamp)
            if kind == "GPS":
                gps.append(row)
            elif kind == "POS":
                positions.append(row)
            elif kind == "MSG":
                messages.append(row)
            elif kind == "ARM":
                arms.append(row)
            elif kind == "MODE":
                modes.append(row)
            elif kind == "PARM" and row.get("Name") in PARAMETER_NAMES:
                parameters[str(row["Name"])] = float(row["Value"])
        if isinstance(connection.counts, dict):
            message_counts = {
                str(key): int(value) for key, value in connection.counts.items()
            }
        else:
            message_counts = {
                str(name): int(connection.counts[message_id])
                for name, message_id in connection.name_to_id.items()
                if message_id < len(connection.counts) and connection.counts[message_id]
            }
    finally:
        connection.close()

    primary_gps = [row for row in gps if int(row.get("I", 0)) == 0]
    gps_times = [value for row in primary_gps if (value := time_s(row)) is not None]
    gps_speeds = [float(row.get("Spd", math.nan)) for row in primary_gps]
    airborne = select_airborne_interval(gps_times, gps_speeds)
    if airborne is None:
        raise RuntimeError(f"Could not identify sustained airborne interval in {path}")
    firmware = next(
        (
            str(row.get("Message"))
            for row in messages
            if str(row.get("Message", "")).startswith("ArduPlane ")
        ),
        None,
    )
    if not observed_times:
        raise RuntimeError(f"No timestamped discovery messages in {path}")
    return Discovery(
        path=path,
        flight_id=flight_id,
        aircraft=aircraft,
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
        message_counts=message_counts,
        parameters=parameters,
        messages=messages,
        arms=arms,
        modes=modes,
        gps=gps,
        positions=positions,
        firmware=firmware,
        log_start_s=min(observed_times),
        log_end_s=max(observed_times),
        airborne=airborne,
    )


@dataclass
class Batch:
    number: int
    sensor_type: int
    instance: int
    multiplier: float
    sample_count: int
    sample_time_s: float
    sample_rate_hz: float
    next_sequence: int = 0
    has_hole: bool = False
    axes: dict[str, list[int]] = field(
        default_factory=lambda: {"X": [], "Y": [], "Z": []}
    )

    @classmethod
    def from_header(cls, row: dict[str, Any]) -> "Batch":
        return cls(
            number=int(row["N"]),
            sensor_type=int(row["type"]),
            instance=int(row["instance"]),
            multiplier=float(row["mul"]),
            sample_count=int(row["smp_cnt"]),
            sample_time_s=float(row["SampleUS"]) * 1.0e-6,
            sample_rate_hz=float(row["smp_rate"]),
        )

    def add_data(self, row: dict[str, Any]) -> None:
        if int(row.get("N", -1)) != self.number:
            self.has_hole = True
            return
        sequence = int(row.get("seqno", -1))
        if sequence != self.next_sequence:
            self.has_hole = True
            return
        self.next_sequence += 1
        for lower, upper in (("x", "X"), ("y", "Y"), ("z", "Z")):
            self.axes[upper].extend(int(value) for value in row.get(lower, []))

    @property
    def valid(self) -> bool:
        return (
            not self.has_hole
            and self.multiplier > 0.0
            and all(len(values) == self.sample_count for values in self.axes.values())
        )


@dataclass
class SpectralAccumulator:
    frequency_hz: np.ndarray = field(default_factory=lambda: np.arange(0.0, 501.0, 1.0))
    sums: dict[str, np.ndarray] = field(default_factory=dict)
    count: int = 0
    sample_rates_hz: list[float] = field(default_factory=list)

    def add(self, frequencies: np.ndarray, axis_psd: dict[str, np.ndarray]) -> None:
        for axis, power in axis_psd.items():
            interpolated = np.interp(self.frequency_hz, frequencies, power, left=0.0, right=0.0)
            if axis not in self.sums:
                self.sums[axis] = np.zeros_like(self.frequency_hz)
            self.sums[axis] += interpolated
        self.count += 1

    def means(self) -> dict[str, np.ndarray]:
        if self.count == 0:
            return {}
        return {axis: values / self.count for axis, values in self.sums.items()}


def process_batch(
    batch: Batch,
    flight_id: str,
    spectral: dict[tuple[int, int], SpectralAccumulator],
) -> dict[str, Any] | None:
    if not batch.valid:
        return None
    axis_psd: dict[str, np.ndarray] = {}
    frequencies: np.ndarray | None = None
    for axis, raw_values in batch.axes.items():
        scaled = np.asarray(raw_values, dtype=float) / batch.multiplier
        if batch.sensor_type == 1:
            scaled = np.degrees(scaled)
        axis_frequency, power = hann_psd(scaled, batch.sample_rate_hz)
        if axis_frequency.size == 0:
            return None
        frequencies = axis_frequency
        axis_psd[axis] = power
    assert frequencies is not None
    total_psd = sum(axis_psd.values())
    peak_hz, peak_psd = dominant_frequency(
        frequencies, total_psd, high_hz=min(500.0, 0.48 * batch.sample_rate_hz)
    )
    key = (batch.sensor_type, batch.instance)
    accumulator = spectral.setdefault(key, SpectralAccumulator())
    accumulator.add(frequencies, axis_psd)
    accumulator.sample_rates_hz.append(batch.sample_rate_hz)
    sensor_name = "accel" if batch.sensor_type == 0 else "gyro"
    return {
        "flight_id": flight_id,
        "batch_number": batch.number,
        "time_s": batch.sample_time_s,
        "sensor": sensor_name,
        "imu_instance": batch.instance,
        "sample_rate_hz": batch.sample_rate_hz,
        "sample_count": batch.sample_count,
        "dominant_frequency_hz": peak_hz,
        "dominant_psd": peak_psd,
        "rms_20_80": integrate_band_rms(frequencies, total_psd, 20.0, 80.0),
        "rms_80_150": integrate_band_rms(frequencies, total_psd, 80.0, 150.0),
        "rms_150_300": integrate_band_rms(frequencies, total_psd, 150.0, 300.0),
        "rms_300_500": integrate_band_rms(frequencies, total_psd, 300.0, 500.0),
    }


def collect_measurements(discovery: Discovery) -> dict[str, Any]:
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    spectral: dict[tuple[int, int], SpectralAccumulator] = {}
    spectral_batches: list[dict[str, Any]] = []
    batch_status = Counter()
    pending: Batch | None = None
    connection = mavutil.mavlink_connection(str(discovery.path), robust_parsing=True)

    def finalize_pending() -> None:
        nonlocal pending
        if pending is None:
            return
        if discovery.airborne.contains(pending.sample_time_s):
            result = process_batch(pending, discovery.flight_id, spectral)
            if result is None:
                batch_status["invalid"] += 1
            else:
                spectral_batches.append(result)
                batch_status["valid_airborne"] += 1
        else:
            batch_status["outside_airborne"] += 1
        pending = None

    try:
        while True:
            message = connection.recv_match(type=MEASUREMENT_TYPES, blocking=False)
            if message is None:
                break
            kind = message.get_type()
            row = message_dict(message)
            if kind == "ISBH":
                finalize_pending()
                pending = Batch.from_header(row)
                continue
            if kind == "ISBD":
                if pending is None:
                    batch_status["data_without_header"] += 1
                else:
                    pending.add_data(row)
                continue
            timestamp = time_s(row)
            if timestamp is None:
                continue
            if kind in {"VIBE", "CTUN", "GPS", "GPA", "POS"}:
                row["time_s"] = timestamp
                rows[kind].append(row)
            elif discovery.airborne.contains(timestamp):
                row["time_s"] = timestamp
                rows[kind].append(row)
        finalize_pending()
    finally:
        connection.close()

    throttle_times = np.asarray([row["time_s"] for row in rows["CTUN"]], dtype=float)
    throttle_values = np.asarray([float(row.get("ThO", math.nan)) for row in rows["CTUN"]])
    mode_rows = sorted(
        (
            (timestamp, int(row.get("ModeNum", row.get("Mode", -1))))
            for row in discovery.modes
            if (timestamp := time_s(row)) is not None
        ),
        key=lambda item: item[0],
    )
    mode_times = np.asarray([item[0] for item in mode_rows], dtype=float)
    mode_values = np.asarray([item[1] for item in mode_rows], dtype=int)
    for row in rows["VIBE"]:
        row["phase"] = phase_for_time(float(row["time_s"]), discovery.airborne)
        if throttle_times.size:
            row["throttle"] = float(np.interp(row["time_s"], throttle_times, throttle_values))
        if mode_times.size:
            mode_index = int(np.searchsorted(mode_times, row["time_s"], side="right") - 1)
            mode_number = int(mode_values[max(0, mode_index)])
            row["mode_num"] = mode_number
            row["mode_name"] = PLANE_MODE_NAMES.get(mode_number, f"MODE_{mode_number}")
        row["vibe_max_axis"] = max(float(row[field]) for field in ("VibeX", "VibeY", "VibeZ"))
    for row in spectral_batches:
        if throttle_times.size:
            row["throttle"] = float(np.interp(row["time_s"], throttle_times, throttle_values))
        row["elapsed_airborne_s"] = float(row["time_s"] - discovery.airborne.start_s)
    return {
        "rows": rows,
        "spectral": spectral,
        "spectral_batches": spectral_batches,
        "batch_status": dict(batch_status),
    }


def add_description(prefix: str, values: Iterable[float], row: dict[str, Any]) -> None:
    for key, value in describe(values).items():
        row[f"{prefix}_{key}"] = value


def summarize_vibration(discovery: Discovery, measurements: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in measurements["rows"]["VIBE"]:
        grouped[(int(row.get("IMU", 0)), str(row["phase"]))].append(row)
    output: list[dict[str, Any]] = []
    for (instance, phase), group in sorted(grouped.items()):
        clip_values = [float(row.get("Clip", 0.0)) for row in group]
        throttle = [float(row.get("throttle", math.nan)) for row in group]
        max_axis = [float(row["vibe_max_axis"]) for row in group]
        for axis in ("X", "Y", "Z"):
            values = [float(row[f"Vibe{axis}"]) for row in group]
            result: dict[str, Any] = {
                "flight_id": discovery.flight_id,
                "aircraft": discovery.aircraft,
                "phase": phase,
                "imu_instance": instance,
                "axis": axis,
                "message_rate_hz": effective_rate_hz(row["time_s"] for row in group),
                "fraction_above_30": threshold_fraction(values, 30.0),
                "fraction_above_60": threshold_fraction(values, 60.0),
                "clip_increment": monotonic_increment(clip_values),
                "clip_start": clip_values[0] if clip_values else None,
                "clip_end": clip_values[-1] if clip_values else None,
                "vibe_throttle_pearson_r": pearson_correlation(throttle, max_axis),
            }
            add_description("vibe", values, result)
            output.append(result)
    return output


def summarize_vibration_by_mode(
    discovery: Discovery, measurements: dict[str, Any]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in measurements["rows"]["VIBE"]:
        if row["phase"] != "airborne" or "mode_num" not in row:
            continue
        grouped[(int(row.get("IMU", 0)), int(row["mode_num"]), str(row["mode_name"]))].append(row)
    output: list[dict[str, Any]] = []
    for (instance, mode_number, mode_name), group in sorted(grouped.items()):
        if len(group) < 5:
            continue
        message_rate = effective_rate_hz(row["time_s"] for row in group)
        for axis in ("X", "Y", "Z"):
            values = [float(row[f"Vibe{axis}"]) for row in group]
            result: dict[str, Any] = {
                "flight_id": discovery.flight_id,
                "aircraft": discovery.aircraft,
                "imu_instance": instance,
                "mode_num": mode_number,
                "mode_name": mode_name,
                "axis": axis,
                "duration_covered_s": (
                    None if message_rate is None else float(len(group) / message_rate)
                ),
                "fraction_above_30": threshold_fraction(values, 30.0),
                "fraction_above_60": threshold_fraction(values, 60.0),
            }
            add_description("vibe", values, result)
            output.append(result)
    return output


def clip_event_rows(discovery: Discovery, measurements: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in measurements["rows"]["VIBE"]:
        grouped[int(row.get("IMU", 0))].append(row)
    output: list[dict[str, Any]] = []
    for instance, group in sorted(grouped.items()):
        group.sort(key=lambda row: float(row["time_s"]))
        if not group:
            continue
        previous = float(group[0].get("Clip", 0.0))
        for row in group[1:]:
            current = float(row.get("Clip", previous))
            if current > previous:
                output.append(
                    {
                        "flight_id": discovery.flight_id,
                        "aircraft": discovery.aircraft,
                        "imu_instance": instance,
                        "time_s": row["time_s"],
                        "elapsed_airborne_s": float(row["time_s"] - discovery.airborne.start_s),
                        "seconds_to_airborne_end": float(discovery.airborne.end_s - row["time_s"]),
                        "phase": row["phase"],
                        "clip_increment": current - previous,
                        "clip_total": current,
                        "vibe_x": row["VibeX"],
                        "vibe_y": row["VibeY"],
                        "vibe_z": row["VibeZ"],
                        "vibe_max_axis": row["vibe_max_axis"],
                        "throttle": row.get("throttle"),
                        "mode_num": row.get("mode_num"),
                        "mode_name": row.get("mode_name"),
                    }
                )
            previous = current
    return output


def summarize_imu(discovery: Discovery, measurements: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in measurements["rows"]["IMU"]:
        grouped[int(row.get("I", 0))].append(row)
    output: list[dict[str, Any]] = []
    for instance, group in sorted(grouped.items()):
        temperatures = [float(row.get("T", math.nan)) for row in group]
        gyro_norm = [
            math.degrees(
                math.sqrt(sum(float(row.get(field, 0.0)) ** 2 for field in ("GyrX", "GyrY", "GyrZ")))
            )
            for row in group
        ]
        accel_norm = [
            math.sqrt(sum(float(row.get(field, 0.0)) ** 2 for field in ("AccX", "AccY", "AccZ")))
            for row in group
        ]
        result: dict[str, Any] = {
            "flight_id": discovery.flight_id,
            "aircraft": discovery.aircraft,
            "imu_instance": instance,
            "message_rate_hz": effective_rate_hz(row["time_s"] for row in group),
            "gyro_error_increment": monotonic_increment(float(row.get("EG", 0.0)) for row in group),
            "accel_error_increment": monotonic_increment(float(row.get("EA", 0.0)) for row in group),
            "gyro_healthy_fraction": float(np.mean([bool(row.get("GH", 0)) for row in group])),
            "accel_healthy_fraction": float(np.mean([bool(row.get("AH", 0)) for row in group])),
            "reported_gyro_rate_hz_p50": describe(float(row.get("GHz", math.nan)) for row in group)["p50"],
            "reported_accel_rate_hz_p50": describe(float(row.get("AHz", math.nan)) for row in group)["p50"],
        }
        add_description("temperature_c", temperatures, result)
        add_description("gyro_norm_deg_s", gyro_norm, result)
        add_description("accel_norm_m_s2", accel_norm, result)
        output.append(result)
    return output


def summarize_imu_pair(discovery: Discovery, measurements: dict[str, Any]) -> list[dict[str, Any]]:
    vibe_groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in measurements["rows"]["VIBE"]:
        if row["phase"] == "airborne":
            vibe_groups[int(row.get("IMU", 0))].append(row)
    if len(vibe_groups) < 2:
        return []
    instances = sorted(vibe_groups)
    reference = vibe_groups[instances[0]]
    comparison = vibe_groups[instances[1]]
    reference_times = np.asarray([row["time_s"] for row in reference], dtype=float)
    reference_values = np.asarray([row["vibe_max_axis"] for row in reference], dtype=float)
    comparison_times = np.asarray([row["time_s"] for row in comparison], dtype=float)
    comparison_values = np.asarray([row["vibe_max_axis"] for row in comparison], dtype=float)
    interpolated = np.interp(reference_times, comparison_times, comparison_values)
    difference = reference_values - interpolated
    result: dict[str, Any] = {
        "flight_id": discovery.flight_id,
        "aircraft": discovery.aircraft,
        "imu_a": instances[0],
        "imu_b": instances[1],
        "vibe_max_axis_pearson_r": pearson_correlation(reference_values, interpolated),
    }
    add_description("vibe_max_axis_difference", difference, result)
    add_description("vibe_max_axis_abs_difference", np.abs(difference), result)
    return [result]


def summarize_gps(discovery: Discovery, measurements: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in measurements["rows"]["GPS"]:
        if discovery.airborne.contains(float(row["time_s"])):
            grouped[int(row.get("I", 0))].append(row)
    output: list[dict[str, Any]] = []
    for instance, group in sorted(grouped.items()):
        satellites = np.asarray([float(row.get("NSats", math.nan)) for row in group])
        result: dict[str, Any] = {
            "flight_id": discovery.flight_id,
            "aircraft": discovery.aircraft,
            "gps_instance": instance,
            "message_rate_hz": effective_rate_hz(row["time_s"] for row in group),
            "fix_3d_or_better_fraction": float(np.mean([float(row.get("Status", 0)) >= 3 for row in group])),
            "satellites_p05": float(np.nanpercentile(satellites, 5)) if satellites.size else None,
        }
        add_description("hdop", (float(row.get("HDop", math.nan)) for row in group), result)
        add_description("speed_m_s", (float(row.get("Spd", math.nan)) for row in group), result)
        output.append(result)
    return output


def summarize_ekf(discovery: Discovery, measurements: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    rows = measurements["rows"]
    derived_specs = {
        "XKF3": {
            "velocity_horizontal_innovation_m_s": lambda row: math.hypot(float(row["IVN"]), float(row["IVE"])),
            "velocity_down_innovation_abs_m_s": lambda row: abs(float(row["IVD"])),
            "position_horizontal_innovation_m": lambda row: math.hypot(float(row["IPN"]), float(row["IPE"])),
            "height_innovation_abs_m": lambda row: abs(float(row["IPD"])),
            "airspeed_innovation_abs_m_s": lambda row: abs(float(row["IVT"])),
            "consolidated_error_score": lambda row: float(row["ErSc"]),
        },
        "XKF2": {
            "accel_bias_x": lambda row: float(row["AX"]),
            "accel_bias_y": lambda row: float(row["AY"]),
            "accel_bias_z": lambda row: float(row["AZ"]),
        },
        "XKF1": {
            "gyro_bias_x_deg_s": lambda row: float(row["GX"]),
            "gyro_bias_y_deg_s": lambda row: float(row["GY"]),
            "gyro_bias_z_deg_s": lambda row: float(row["GZ"]),
        },
        "XKF5": {
            "angular_error_rad": lambda row: float(row["eAng"]),
            "velocity_error_m_s": lambda row: float(row["eVel"]),
            "position_error_m": lambda row: float(row["ePos"]),
        },
    }
    for message_name, metrics in derived_specs.items():
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in rows[message_name]:
            grouped[int(row.get("C", 0))].append(row)
        for core, group in sorted(grouped.items()):
            for metric, extractor in metrics.items():
                result: dict[str, Any] = {
                    "flight_id": discovery.flight_id,
                    "aircraft": discovery.aircraft,
                    "ekf_core": core,
                    "source_message": message_name,
                    "metric": metric,
                }
                add_description("value", (extractor(row) for row in group), result)
                output.append(result)

    grouped_xkf4: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows["XKF4"]:
        grouped_xkf4[int(row.get("C", 0))].append(row)
    ratio_names = {
        "SV": "gps_velocity_test_ratio",
        "SP": "gps_position_test_ratio",
        "SH": "height_test_ratio",
        "SM": "mag_test_ratio",
        "SVT": "airspeed_test_ratio",
    }
    for core, group in sorted(grouped_xkf4.items()):
        for field_name, metric in ratio_names.items():
            values = [float(row.get(field_name, math.nan)) for row in group]
            result = {
                "flight_id": discovery.flight_id,
                "aircraft": discovery.aircraft,
                "ekf_core": core,
                "source_message": "XKF4",
                "metric": metric,
                "fraction_at_or_above_one": threshold_fraction(values, np.nextafter(1.0, 0.0)),
            }
            add_description("value", values, result)
            output.append(result)
        status_result: dict[str, Any] = {
            "flight_id": discovery.flight_id,
            "aircraft": discovery.aircraft,
            "ekf_core": core,
            "source_message": "XKF4",
            "metric": "status_flags",
            "filter_fault_nonzero_fraction": float(np.mean([int(row.get("FS", 0)) != 0 for row in group])),
            "using_gps_fraction": float(np.mean([(int(row.get("SS", 0)) & 8192) != 0 for row in group])),
            "gps_glitching_fraction": float(np.mean([(int(row.get("SS", 0)) & 16384) != 0 for row in group])),
            "dead_reckoning_fraction": float(np.mean([(int(row.get("SS", 0)) & 262144) != 0 for row in group])),
            "rejecting_airspeed_fraction": float(np.mean([(int(row.get("SS", 0)) & 131072) != 0 for row in group])),
            "primary_core_fraction": float(np.mean([int(row.get("PI", -1)) == core for row in group])),
            "position_timeout_fraction": float(np.mean([(int(row.get("TS", 0)) & 1) != 0 for row in group])),
            "velocity_timeout_fraction": float(np.mean([(int(row.get("TS", 0)) & 2) != 0 for row in group])),
            "height_timeout_fraction": float(np.mean([(int(row.get("TS", 0)) & 4) != 0 for row in group])),
            "mag_timeout_fraction": float(np.mean([(int(row.get("TS", 0)) & 8) != 0 for row in group])),
            "airspeed_timeout_fraction": float(np.mean([(int(row.get("TS", 0)) & 16) != 0 for row in group])),
            "drag_timeout_fraction": float(np.mean([(int(row.get("TS", 0)) & 32) != 0 for row in group])),
        }
        output.append(status_result)
    return output


def summarize_spectra(
    discovery: Discovery, measurements: dict[str, Any]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for (sensor_type, instance), accumulator in sorted(measurements["spectral"].items()):
        means = accumulator.means()
        if not means:
            continue
        total = sum(means.values())
        sensor = "accel" if sensor_type == 0 else "gyro"
        peak_hz, peak_power = dominant_frequency(accumulator.frequency_hz, total)
        peaks = separated_peaks(accumulator.frequency_hz, total)
        batch_rows = [
            row
            for row in measurements["spectral_batches"]
            if row["sensor"] == sensor and int(row["imu_instance"]) == instance
        ]
        high_frequency_batches = [
            row for row in batch_rows if float(row["dominant_frequency_hz"]) >= 60.0
        ]
        result: dict[str, Any] = {
            "flight_id": discovery.flight_id,
            "aircraft": discovery.aircraft,
            "sensor": sensor,
            "imu_instance": instance,
            "valid_airborne_batches": accumulator.count,
            "sample_rate_hz_p50": describe(accumulator.sample_rates_hz)["p50"],
            "aggregate_dominant_frequency_hz": peak_hz,
            "aggregate_dominant_psd": peak_power,
            "top_peaks_hz": ";".join(f"{frequency:.1f}" for frequency, _ in peaks),
            "high_frequency_batch_count": len(high_frequency_batches),
            "high_frequency_peak_throttle_pearson_r": pearson_correlation(
                (float(row["dominant_frequency_hz"]) for row in high_frequency_batches),
                (float(row.get("throttle", math.nan)) for row in high_frequency_batches),
            ),
        }
        add_description(
            "batch_dominant_frequency_hz",
            (float(row["dominant_frequency_hz"]) for row in batch_rows),
            result,
        )
        for low_hz, high_hz in ((20, 80), (80, 150), (150, 300), (300, 500)):
            result[f"aggregate_rms_{low_hz}_{high_hz}"] = integrate_band_rms(
                accumulator.frequency_hz, total, float(low_hz), float(high_hz)
            )
        output.append(result)
    return output


def event_rows(discovery: Discovery) -> list[dict[str, Any]]:
    keywords = re.compile(r"(EKF|IMU|GPS|airspeed|fence|engine|arm|vibration|lane switch|reset)", re.I)
    output = []
    for row in discovery.messages:
        message = str(row.get("Message", ""))
        if keywords.search(message):
            timestamp = time_s(row)
            output.append(
                {
                    "flight_id": discovery.flight_id,
                    "aircraft": discovery.aircraft,
                    "time_s": timestamp,
                    "elapsed_airborne_s": None if timestamp is None else timestamp - discovery.airborne.start_s,
                    "phase": None if timestamp is None else phase_for_time(timestamp, discovery.airborne),
                    "message": message,
                }
            )
    return output


def plot_vibration(discovery: Discovery, measurements: dict[str, Any], output_dir: Path) -> None:
    rows = [row for row in measurements["rows"]["VIBE"] if row["phase"] == "airborne"]
    instances = sorted({int(row.get("IMU", 0)) for row in rows})
    if not instances:
        return
    figure, axes = plt.subplots(len(instances), 1, figsize=(13, 4 * len(instances)), sharex=True)
    axes_array = np.atleast_1d(axes)
    for axis_plot, instance in zip(axes_array, instances):
        group = [row for row in rows if int(row.get("IMU", 0)) == instance]
        elapsed = np.asarray([row["time_s"] - discovery.airborne.start_s for row in group]) / 60.0
        for axis_name in ("X", "Y", "Z"):
            axis_plot.plot(elapsed, [row[f"Vibe{axis_name}"] for row in group], label=axis_name, linewidth=0.8)
        axis_plot.axhline(30.0, color="darkorange", linestyle="--", linewidth=1.0, label="30 m/s² guidance")
        axis_plot.axhline(60.0, color="red", linestyle=":", linewidth=1.0, label="60 m/s² severe guidance")
        axis_plot.set_ylabel(f"VIBE IMU {instance}\n(m/s²)")
        axis_plot.grid(alpha=0.25)
        axis_plot.legend(ncol=5, fontsize=8, loc="upper right")
    axes_array[-1].set_xlabel("Minutes from detected airborne start")
    figure.suptitle(f"{discovery.aircraft}: airborne VIBE time history")
    figure.tight_layout()
    figure.savefig(output_dir / "vibration_time_history.png", dpi=160)
    plt.close(figure)


def plot_ekf(discovery: Discovery, measurements: dict[str, Any], output_dir: Path) -> None:
    ratio_rows = measurements["rows"]["XKF4"]
    innovation_rows = measurements["rows"]["XKF3"]
    if not ratio_rows:
        return
    cores = sorted({int(row.get("C", 0)) for row in ratio_rows})
    figure, axes = plt.subplots(len(cores), 2, figsize=(15, 4 * len(cores)), sharex=True)
    axes_array = np.atleast_2d(axes)
    for index, core in enumerate(cores):
        core_ratios = [row for row in ratio_rows if int(row.get("C", 0)) == core]
        elapsed = np.asarray([row["time_s"] - discovery.airborne.start_s for row in core_ratios]) / 60.0
        for field_name, label in (("SV", "GPS velocity"), ("SP", "GPS position"), ("SH", "height"), ("SVT", "airspeed")):
            axes_array[index, 0].plot(elapsed, [row[field_name] for row in core_ratios], label=label, linewidth=0.8)
        axes_array[index, 0].axhline(1.0, color="red", linestyle="--", linewidth=1.0, label="rejection boundary")
        axes_array[index, 0].set_ylim(bottom=0.0)
        axes_array[index, 0].set_ylabel(f"Core {core} test ratio")
        axes_array[index, 0].grid(alpha=0.25)
        axes_array[index, 0].legend(fontsize=8, ncol=3)

        core_innovations = [row for row in innovation_rows if int(row.get("C", 0)) == core]
        innovation_elapsed = np.asarray(
            [row["time_s"] - discovery.airborne.start_s for row in core_innovations]
        ) / 60.0
        if core_innovations:
            axes_array[index, 1].plot(
                innovation_elapsed,
                [math.hypot(float(row["IVN"]), float(row["IVE"])) for row in core_innovations],
                label="horizontal velocity (m/s)",
                linewidth=0.8,
            )
            axes_array[index, 1].plot(
                innovation_elapsed,
                [math.hypot(float(row["IPN"]), float(row["IPE"])) for row in core_innovations],
                label="horizontal position (m)",
                linewidth=0.8,
            )
        axes_array[index, 1].set_ylabel(f"Core {core} innovation magnitude")
        axes_array[index, 1].grid(alpha=0.25)
        axes_array[index, 1].legend(fontsize=8)
    axes_array[-1, 0].set_xlabel("Minutes from detected airborne start")
    axes_array[-1, 1].set_xlabel("Minutes from detected airborne start")
    figure.suptitle(f"{discovery.aircraft}: EKF3 measurement consistency")
    figure.tight_layout()
    figure.savefig(output_dir / "ekf_consistency_time_history.png", dpi=160)
    plt.close(figure)


def plot_spectra(discovery: Discovery, measurements: dict[str, Any], output_dir: Path) -> None:
    for (sensor_type, instance), accumulator in sorted(measurements["spectral"].items()):
        means = accumulator.means()
        if not means:
            continue
        sensor = "accel" if sensor_type == 0 else "gyro"
        figure, axis_plot = plt.subplots(figsize=(11, 5))
        for axis_name, power in means.items():
            axis_plot.plot(
                accumulator.frequency_hz,
                10.0 * np.log10(np.maximum(power, 1.0e-20)),
                label=axis_name,
                linewidth=0.9,
            )
        total = sum(means.values())
        axis_plot.plot(
            accumulator.frequency_hz,
            10.0 * np.log10(np.maximum(total, 1.0e-20)),
            color="black",
            label="XYZ total",
            linewidth=1.2,
        )
        notch_frequency = discovery.parameters.get("INS_HNTCH_FREQ")
        if notch_frequency is not None:
            axis_plot.axvline(notch_frequency, color="purple", linestyle="--", label="configured notch base")
        axis_plot.set_xlim(20.0, 500.0)
        axis_plot.set_xlabel("Frequency (Hz)")
        units = "(m/s²)²/Hz" if sensor == "accel" else "(deg/s)²/Hz"
        axis_plot.set_ylabel(f"PSD dB re 1 {units}")
        axis_plot.set_title(
            f"{discovery.aircraft}: post-filter {sensor} spectrum, IMU {instance}\n"
            f"mean of {accumulator.count} airborne batches"
        )
        axis_plot.grid(alpha=0.25)
        axis_plot.legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(output_dir / f"spectrum_{sensor}_imu_{instance}.png", dpi=160)
        plt.close(figure)


def plot_spectral_peak_vs_throttle(
    discovery: Discovery, measurements: dict[str, Any], output_dir: Path
) -> None:
    rows = [
        row
        for row in measurements["spectral_batches"]
        if float(row["dominant_frequency_hz"]) >= 60.0
        and math.isfinite(float(row.get("throttle", math.nan)))
    ]
    groups = sorted({(str(row["sensor"]), int(row["imu_instance"])) for row in rows})
    if not groups:
        return
    figure, axes = plt.subplots(len(groups), 1, figsize=(10, 3.2 * len(groups)), sharex=True)
    axes_array = np.atleast_1d(axes)
    for axis_plot, (sensor, instance) in zip(axes_array, groups):
        group = [
            row
            for row in rows
            if row["sensor"] == sensor and int(row["imu_instance"]) == instance
        ]
        throttle = [float(row["throttle"]) for row in group]
        frequency = [float(row["dominant_frequency_hz"]) for row in group]
        correlation = pearson_correlation(throttle, frequency)
        axis_plot.scatter(throttle, frequency, s=10, alpha=0.45)
        axis_plot.set_ylabel(f"{sensor} IMU {instance}\npeak Hz")
        axis_plot.grid(alpha=0.25)
        axis_plot.text(
            0.02,
            0.92,
            f"r = {correlation:.2f}" if correlation is not None else "r = n/a",
            transform=axis_plot.transAxes,
            va="top",
        )
    axes_array[-1].set_xlabel("Throttle output (%)")
    figure.suptitle(
        f"{discovery.aircraft}: high-frequency dominant peak vs throttle\n"
        "association supports propulsion-order interpretation; it does not identify a component"
    )
    figure.tight_layout()
    figure.savefig(output_dir / "spectral_peak_vs_throttle.png", dpi=160)
    plt.close(figure)


def plot_largest_clip_event_context(
    discovery: Discovery,
    measurements: dict[str, Any],
    clip_events: list[dict[str, Any]],
    output_dir: Path,
) -> None:
    airborne_events = [event for event in clip_events if event["phase"] == "airborne"]
    if not airborne_events:
        return
    event = max(airborne_events, key=lambda item: float(item["vibe_max_axis"]))
    center_s = float(event["time_s"])
    start_s = center_s - 3.0
    end_s = center_s + 4.0
    vibe_rows = [
        row for row in measurements["rows"]["VIBE"] if start_s <= float(row["time_s"]) <= end_s
    ]
    xkf4_rows = [
        row for row in measurements["rows"]["XKF4"] if start_s <= float(row["time_s"]) <= end_s
    ]
    gps_rows = [
        row
        for row in measurements["rows"]["GPS"]
        if int(row.get("I", 0)) == 0 and start_s <= float(row["time_s"]) <= end_s
    ]
    position_rows = [
        row for row in measurements["rows"]["POS"] if start_s <= float(row["time_s"]) <= end_s
    ]

    figure, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    for instance in sorted({int(row.get("IMU", 0)) for row in vibe_rows}):
        group = [row for row in vibe_rows if int(row.get("IMU", 0)) == instance]
        axes[0].plot(
            [float(row["time_s"]) - center_s for row in group],
            [float(row["vibe_max_axis"]) for row in group],
            marker=".",
            label=f"IMU {instance} max axis",
        )
    axes[0].axhline(30.0, color="darkorange", linestyle="--", linewidth=1.0)
    axes[0].axhline(60.0, color="red", linestyle=":", linewidth=1.0)
    axes[0].set_ylabel("VIBE max axis\n(m/s²)")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    for core in sorted({int(row.get("C", 0)) for row in xkf4_rows}):
        group = [row for row in xkf4_rows if int(row.get("C", 0)) == core]
        axes[1].plot(
            [float(row["time_s"]) - center_s for row in group],
            [float(row["SV"]) for row in group],
            marker=".",
            label=f"EKF core {core} GPS velocity ratio",
        )
    axes[1].axhline(1.0, color="red", linestyle="--", linewidth=1.0, label="rejection boundary")
    axes[1].set_ylabel("XKF4.SV")
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    if gps_rows:
        axes[2].plot(
            [float(row["time_s"]) - center_s for row in gps_rows],
            [float(row["Spd"]) for row in gps_rows],
            color="tab:blue",
            marker=".",
            label="GPS speed",
        )
    axes[2].set_ylabel("GPS speed (m/s)", color="tab:blue")
    axes[2].tick_params(axis="y", labelcolor="tab:blue")
    altitude_axis = axes[2].twinx()
    if position_rows:
        altitude_axis.plot(
            [float(row["time_s"]) - center_s for row in position_rows],
            [float(row["RelHomeAlt"]) for row in position_rows],
            color="tab:green",
            marker=".",
            label="relative-home altitude",
        )
    altitude_axis.set_ylabel("Relative-home altitude (m)", color="tab:green")
    altitude_axis.tick_params(axis="y", labelcolor="tab:green")
    axes[2].grid(alpha=0.25)
    axes[2].set_xlabel("Seconds relative to largest clip event")

    for axis_plot in axes:
        axis_plot.axvline(0.0, color="black", linestyle="-", linewidth=1.0, label="largest clip")
    primary_changes = []
    if xkf4_rows:
        initial_primary = int(xkf4_rows[0].get("PI", -1))
        primary_changes = [
            row for row in xkf4_rows if int(row.get("PI", -1)) != initial_primary
        ]
    if primary_changes:
        switch_elapsed = float(primary_changes[0]["time_s"]) - center_s
        for axis_plot in axes:
            axis_plot.axvline(
                switch_elapsed,
                color="purple",
                linestyle=":",
                linewidth=1.2,
                label="primary-core change",
            )
    figure.suptitle(
        f"{discovery.aircraft}: largest airborne clipping event context\n"
        f"clip +{float(event['clip_increment']):.0f}, mode {event.get('mode_name')}, "
        f"{float(event['seconds_to_airborne_end']):.1f} s before detected flight end"
    )
    figure.tight_layout()
    figure.savefig(output_dir / "largest_clip_event_context.png", dpi=160)
    plt.close(figure)


def plot_fleet_vibration(vibration_rows: list[dict[str, Any]], output_dir: Path) -> None:
    rows = [row for row in vibration_rows if row["phase"] == "airborne"]
    labels = []
    values = []
    colors = []
    for row in rows:
        labels.append(f"{row['flight_id']}\nIMU{row['imu_instance']} {row['axis']}")
        value = float(row["vibe_p95"])
        values.append(value)
        colors.append("tab:green" if value < 30.0 else ("darkorange" if value < 60.0 else "tab:red"))
    if not rows:
        return
    figure, axis_plot = plt.subplots(figsize=(max(14, len(rows) * 0.55), 6))
    axis_plot.bar(np.arange(len(rows)), values, color=colors)
    axis_plot.axhline(30.0, color="darkorange", linestyle="--", label="30 m/s² guidance")
    axis_plot.axhline(60.0, color="red", linestyle=":", label="60 m/s² severe guidance")
    axis_plot.set_xticks(np.arange(len(rows)), labels, rotation=65, ha="right", fontsize=8)
    axis_plot.set_ylabel("Airborne VIBE p95 (m/s²)")
    axis_plot.set_title("Fleet comparison: 95th-percentile vibration by IMU and axis")
    axis_plot.grid(axis="y", alpha=0.25)
    axis_plot.legend()
    figure.tight_layout()
    figure.savefig(output_dir / "fleet_vibration_p95.png", dpi=160)
    plt.close(figure)


def analyze_one(discovery: Discovery, output_root: Path) -> dict[str, Any]:
    print(f"measurement pass: {discovery.path.name}", flush=True)
    measurements = collect_measurements(discovery)
    flight_output = output_root / "flights" / discovery.flight_id
    flight_output.mkdir(parents=True, exist_ok=True)

    vibration = summarize_vibration(discovery, measurements)
    vibration_by_mode = summarize_vibration_by_mode(discovery, measurements)
    clip_events = clip_event_rows(discovery, measurements)
    imu = summarize_imu(discovery, measurements)
    imu_pair = summarize_imu_pair(discovery, measurements)
    gps = summarize_gps(discovery, measurements)
    ekf = summarize_ekf(discovery, measurements)
    spectra = summarize_spectra(discovery, measurements)
    events = event_rows(discovery)

    write_csv(flight_output / "vibration_summary.csv", vibration)
    write_csv(flight_output / "vibration_by_mode.csv", vibration_by_mode)
    write_csv(flight_output / "clip_events.csv", clip_events)
    write_csv(flight_output / "imu_summary.csv", imu)
    write_csv(flight_output / "imu_pair_summary.csv", imu_pair)
    write_csv(flight_output / "gps_summary.csv", gps)
    write_csv(flight_output / "ekf_summary.csv", ekf)
    write_csv(flight_output / "spectral_summary.csv", spectra)
    write_csv(flight_output / "spectral_batches.csv", measurements["spectral_batches"])
    write_csv(flight_output / "events.csv", events)
    write_csv(flight_output / "vibe_timeseries.csv", measurements["rows"]["VIBE"])
    write_csv(flight_output / "xkf4_timeseries.csv", measurements["rows"]["XKF4"])
    write_csv(flight_output / "xkf3_timeseries.csv", measurements["rows"]["XKF3"])

    plot_vibration(discovery, measurements, flight_output)
    plot_ekf(discovery, measurements, flight_output)
    plot_spectra(discovery, measurements, flight_output)
    plot_spectral_peak_vs_throttle(discovery, measurements, flight_output)
    plot_largest_clip_event_context(discovery, measurements, clip_events, flight_output)

    rel_altitude = [
        float(row.get("RelHomeAlt", math.nan))
        for row in discovery.positions
        if (timestamp := time_s(row)) is not None and discovery.airborne.contains(timestamp)
    ]
    summary = {
        "flight_id": discovery.flight_id,
        "aircraft": discovery.aircraft,
        "source_log": str(discovery.path),
        "source_size_bytes": discovery.size_bytes,
        "source_sha256": discovery.sha256,
        "firmware": discovery.firmware,
        "log_start_boot_s": discovery.log_start_s,
        "log_end_boot_s": discovery.log_end_s,
        "log_duration_s": discovery.log_end_s - discovery.log_start_s,
        "airborne": discovery.airborne,
        "airborne_relative_altitude_m": describe(rel_altitude),
        "parameters": discovery.parameters,
        "message_counts": discovery.message_counts,
        "batch_status": measurements["batch_status"],
        "data_capabilities": {
            "vibe": bool(measurements["rows"]["VIBE"]),
            "imu": bool(measurements["rows"]["IMU"]),
            "ekf3": bool(measurements["rows"]["XKF4"]),
            "batch_spectra": bool(spectra),
            "imu_instances": sorted({int(row.get("I", 0)) for row in measurements["rows"]["IMU"]}),
            "vibe_instances": sorted({int(row.get("IMU", 0)) for row in measurements["rows"]["VIBE"]}),
            "ekf_cores": sorted({int(row.get("C", 0)) for row in measurements["rows"]["XKF4"]}),
        },
        "messages": discovery.messages,
    }
    write_json(flight_output / "flight_summary.json", summary)
    return {
        "summary": summary,
        "vibration": vibration,
        "vibration_by_mode": vibration_by_mode,
        "clip_events": clip_events,
        "imu": imu,
        "imu_pair": imu_pair,
        "gps": gps,
        "ekf": ekf,
        "spectra": spectra,
        "events": events,
    }


def inventory_row(result: dict[str, Any]) -> dict[str, Any]:
    summary = result["summary"]
    capabilities = summary["data_capabilities"]
    return {
        "flight_id": summary["flight_id"],
        "aircraft": summary["aircraft"],
        "source_log": summary["source_log"],
        "source_size_bytes": summary["source_size_bytes"],
        "source_sha256": summary["source_sha256"],
        "firmware": summary["firmware"],
        "log_duration_s": summary["log_duration_s"],
        "airborne_start_boot_s": summary["airborne"].start_s,
        "airborne_end_boot_s": summary["airborne"].end_s,
        "airborne_duration_s": summary["airborne"].duration_s,
        "vibe_available": capabilities["vibe"],
        "ekf3_available": capabilities["ekf3"],
        "batch_spectra_available": capabilities["batch_spectra"],
        "imu_instances": ";".join(str(value) for value in capabilities["imu_instances"]),
        "vibe_instances": ";".join(str(value) for value in capabilities["vibe_instances"]),
        "ekf_cores": ";".join(str(value) for value in capabilities["ekf_cores"]),
        "ins_log_bat_mask": summary["parameters"].get("INS_LOG_BAT_MASK"),
        "ins_log_bat_opt": summary["parameters"].get("INS_LOG_BAT_OPT"),
        "ek3_imu_mask": summary["parameters"].get("EK3_IMU_MASK"),
        "ek3_primary": summary["parameters"].get("EK3_PRIMARY"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("logs", nargs="*", type=Path, help="Optional explicit .bin files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    logs = [path.resolve() for path in args.logs]
    if not logs:
        logs = sorted(args.input_dir.resolve().glob("*.bin"))
    if not logs:
        print(f"No .bin logs found under {args.input_dir}", file=sys.stderr)
        return 2

    discoveries = []
    for path in logs:
        print(f"discovery pass: {path.name}", flush=True)
        discoveries.append(discover_log(path))

    results = [analyze_one(discovery, output_root) for discovery in discoveries]
    inventory = [inventory_row(result) for result in results]
    vibration = [row for result in results for row in result["vibration"]]
    vibration_by_mode = [row for result in results for row in result["vibration_by_mode"]]
    clip_events = [row for result in results for row in result["clip_events"]]
    imu = [row for result in results for row in result["imu"]]
    imu_pair = [row for result in results for row in result["imu_pair"]]
    gps = [row for result in results for row in result["gps"]]
    ekf = [row for result in results for row in result["ekf"]]
    spectra = [row for result in results for row in result["spectra"]]
    events = [row for result in results for row in result["events"]]

    write_csv(output_root / "flight_inventory.csv", inventory)
    write_csv(output_root / "fleet_vibration_summary.csv", vibration)
    write_csv(output_root / "fleet_vibration_by_mode.csv", vibration_by_mode)
    write_csv(output_root / "fleet_clip_events.csv", clip_events)
    write_csv(output_root / "fleet_imu_summary.csv", imu)
    write_csv(output_root / "fleet_imu_pair_summary.csv", imu_pair)
    write_csv(output_root / "fleet_gps_summary.csv", gps)
    write_csv(output_root / "fleet_ekf_summary.csv", ekf)
    write_csv(output_root / "fleet_spectral_summary.csv", spectra)
    write_csv(output_root / "fleet_events.csv", events)
    write_json(
        output_root / "analysis_manifest.json",
        {
            "analysis_date": "2026-09-01",
            "analysis_scope": "normal GPS-aided real flights; observational IMU/INS characterization",
            "airborne_detection": {
                "primary_signal": "GPS instance 0 ground speed",
                "minimum_speed_mps": 8.0,
                "bridge_gap_s": 30.0,
                "minimum_duration_s": 10.0,
                "pad_s": 2.0,
            },
            "vibration_guidance_m_s2": {
                "mostly_below": 30.0,
                "nearly_always_problematic_above": 60.0,
                "source": "https://ardupilot.org/copter/docs/common-measuring-vibration.html",
            },
            "spectral_method": "Hann-window one-sided PSD matching pymavlink mavfft_isb normalization",
            "spectral_scope": "post-filter batches where INS_LOG_BAT_OPT=2; no pre/post attenuation claim",
            "inputs": inventory,
        },
    )
    plot_fleet_vibration(vibration, output_root)
    print(f"analysis complete: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
