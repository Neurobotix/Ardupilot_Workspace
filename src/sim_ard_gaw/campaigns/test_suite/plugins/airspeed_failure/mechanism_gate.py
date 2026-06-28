"""Time-aligned BIN mechanism gate for airspeed-bias observations."""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Sequence


CLAMP_BAND_TOLERANCE_MPS = 2.0
TRACK_TOLERANCE_MPS = 3.0
RAW_EXCESS_REQUIRED_MPS = 5.0
WIND_MAX_READBACK_TOLERANCE = 1e-3
COMMANDED_CRUISE_TOLERANCE_MPS = 1.5
MAX_ALIGNMENT_SKEW_S = 0.25
MIN_ALIGNED_SAMPLES = 10

MECHANISM_STATUSES = (
    "clamp_verified",
    "unclamped_tracking_verified",
    "clamp_not_exercised",
    "sensor_rejected_before_verification",
    "mechanism_unverified",
)


@dataclass
class GateCheck:
    name: str
    ok: bool
    detail: str


@dataclass
class GateResult:
    interpretable: bool
    tier: str
    mechanism_status: str
    checks: list[GateCheck] = field(default_factory=list)
    signals: "RunSignals | None" = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "interpretable": self.interpretable,
            "tier": self.tier,
            "mechanism_status": self.mechanism_status,
            "observation_quality_class": self.mechanism_status,
            "checks": [
                {"name": check.name, "ok": check.ok, "detail": check.detail}
                for check in self.checks
            ],
            "signals": self.signals.as_dict() if self.signals is not None else None,
        }


@dataclass
class RunSignals:
    ahrs_wind_max: float | None
    raw_arsp_late: float | None
    believed_as_late: float | None
    gnd_speed_late: float | None
    tecs_target_late: float | None
    commanded_cruise_expected: float | None
    arsp_use_all_one: bool
    raw_arsp_max: float | None
    eas2tas_late: float | None = 1.0
    aligned_u1_sample_count: int = 0
    aligned_sensor_sample_count: int = 0
    clamp_exercised_sample_count: int = 0
    clamp_error_mean_mps: float | None = None
    tracking_error_mean_mps: float | None = None
    demand_error_mean_mps: float | None = None
    sensor_disable_intervals: list[dict[str, float | None]] = field(default_factory=list)
    sensor_source_rejection_intervals: list[dict[str, float | None]] = field(
        default_factory=list
    )
    sensor_source_all_one: bool = False
    airspeed_source_types_present: list[int] = field(default_factory=list)
    arsp_health_mean: float | None = None
    arsp_health_probability_mean: float | None = None
    arsp_test_ratio_mean: float | None = None
    true_airspeed_mean: float | None = None
    altitude_mean: float | None = None
    throttle_mean: float | None = None
    pitch_mean: float | None = None
    aoa_mean: float | None = None
    elevator_mean: float | None = None
    window_start_s: float | None = None
    window_end_s: float | None = None
    max_alignment_skew_s: float = MAX_ALIGNMENT_SKEW_S

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ScheduleWindowSignals:
    event_index: int
    phase: str
    bias_percent: float
    requested_ratio: float
    observed_ratio: float
    window_start_s: float
    window_end_s: float
    signals: RunSignals

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_index": self.event_index,
            "phase": self.phase,
            "bias_percent": self.bias_percent,
            "requested_ratio": self.requested_ratio,
            "observed_ratio": self.observed_ratio,
            "window_start_s": self.window_start_s,
            "window_end_s": self.window_end_s,
            "signals": self.signals.as_dict(),
        }


@dataclass
class DecodedBin:
    series: dict[str, list[tuple[float, dict[str, Any]]]]
    ahrs_wind_max: float | None
    ratio_param_events: list[tuple[float, float]]


def evaluate(signals: RunSignals, *, tier: str, expected_wind_max: float) -> GateResult:
    checks: list[GateCheck] = []
    wm = signals.ahrs_wind_max
    wind_ok = wm is not None and abs(wm - expected_wind_max) <= WIND_MAX_READBACK_TOLERANCE
    checks.append(
        GateCheck("ahrs_wind_max_readback", wind_ok, f"read {wm}, expected {expected_wind_max}")
    )

    status, mechanism_check = _mechanism_check(signals, tier)
    checks.append(mechanism_check)
    checks.append(_check_commanded_cruise(signals))
    sensor_sample_count = _sensor_sample_count(signals)
    present = all(
        value is not None
        for value in (
            signals.raw_arsp_late,
            signals.believed_as_late,
            signals.gnd_speed_late,
            signals.tecs_target_late,
            signals.eas2tas_late,
        )
    ) and sensor_sample_count >= MIN_ALIGNED_SAMPLES
    checks.append(
        GateCheck(
            "time_aligned_signals_present",
            present,
            (
                "aligned CTUN.AsT=1 rows="
                f"{sensor_sample_count}, required={MIN_ALIGNED_SAMPLES}"
            ),
        )
    )

    interpretable = (
        status in {"clamp_verified", "unclamped_tracking_verified"}
        and all(check.ok for check in checks)
    )
    if not wind_ok:
        status = "mechanism_unverified"
    elif status in {"clamp_verified", "unclamped_tracking_verified"} and not interpretable:
        status = "mechanism_unverified"
    return GateResult(interpretable, tier, status, checks, signals)


def _mechanism_check(signals: RunSignals, tier: str) -> tuple[str, GateCheck]:
    if tier == "protected":
        if signals.clamp_exercised_sample_count <= 0:
            if signals.sensor_source_rejection_intervals or signals.sensor_disable_intervals:
                status = "sensor_rejected_before_verification"
            else:
                status = "clamp_not_exercised"
            return status, GateCheck(
                "protected_clamp",
                False,
                "raw airspeed did not exercise the source-derived clamp while ARSP.U=1",
            )
        error = signals.clamp_error_mean_mps
        ok = error is not None and abs(error) <= CLAMP_BAND_TOLERANCE_MPS
        return (
            "clamp_verified" if ok else "mechanism_unverified",
            GateCheck(
                "protected_clamp",
                ok,
                f"mean |CTUN.As-source clamp|={error} m/s; tolerance={CLAMP_BAND_TOLERANCE_MPS}",
            ),
        )
    if tier == "diagnostic":
        if (
            _sensor_sample_count(signals) < MIN_ALIGNED_SAMPLES
            and signals.sensor_source_rejection_intervals
        ):
            return "sensor_rejected_before_verification", GateCheck(
                "unclamped_tracking",
                False,
                "sensor rejected before enough U=1 tracking rows were available",
            )
        error = signals.tracking_error_mean_mps
        ok = error is not None and abs(error) <= TRACK_TOLERANCE_MPS
        return (
            "unclamped_tracking_verified" if ok else "mechanism_unverified",
            GateCheck(
                "unclamped_tracking",
                ok,
                f"mean |CTUN.As-ARSP.Airspeed|={error} m/s; tolerance={TRACK_TOLERANCE_MPS}",
            ),
        )
    return "mechanism_unverified", GateCheck("mechanism_tier", False, f"unknown tier {tier!r}")


def _sensor_sample_count(signals: RunSignals) -> int:
    if signals.aligned_sensor_sample_count > 0 or signals.airspeed_source_types_present:
        return signals.aligned_sensor_sample_count
    # Compatibility for callers constructing pre-AsT RunSignals directly.
    return signals.aligned_u1_sample_count


def _check_commanded_cruise(signals: RunSignals) -> GateCheck:
    if signals.demand_error_mean_mps is not None:
        error = abs(signals.demand_error_mean_mps)
        ok = error <= COMMANDED_CRUISE_TOLERANCE_MPS
        return GateCheck(
            "commanded_cruise",
            ok,
            f"mean |TECS.spdem-intended_EAS*E2T|={error:.2f} m/s",
        )
    target = signals.tecs_target_late
    expected = signals.commanded_cruise_expected
    e2t = signals.eas2tas_late
    if target is None or expected is None or e2t is None:
        return GateCheck("commanded_cruise", False, "missing TECS target, intended EAS, or E2T")
    error = abs(target - expected * e2t)
    return GateCheck(
        "commanded_cruise",
        error <= COMMANDED_CRUISE_TOLERANCE_MPS,
        f"TECS target {target:.2f} vs intended TAS {expected * e2t:.2f}",
    )


def extract_signals_from_bin(
    bin_path: str,
    *,
    expected_cruise: float | None,
    reader: Callable[[str], Any] | None = None,
    window_start_utc: str | None = None,
    window_end_utc: str | None = None,
    window_start_s: float | None = None,
    window_end_s: float | None = None,
) -> RunSignals:
    decoded = _decode_bin(bin_path, reader=reader)
    start = window_start_s if window_start_s is not None else _parse_utc(window_start_utc)
    end = window_end_s if window_end_s is not None else _parse_utc(window_end_utc)
    return _extract_signals(decoded, expected_cruise=expected_cruise, start=start, end=end)


def extract_schedule_signals_from_bin(
    bin_path: str,
    *,
    expected_cruise: float | None,
    injection_events: Sequence[dict[str, Any]],
    reader: Callable[[str], Any] | None = None,
) -> tuple[list[ScheduleWindowSignals], list[str]]:
    """Extract schedule windows from in-BIN ratio transitions.

    Runtime schedule timestamps use wall time, while DataFlash messages use the
    SITL simulation clock.  The two clocks drift during long runs, so logged
    ``SIM_ARSPD_RATIO`` PARM changes are the authoritative window anchors.
    """

    decoded = _decode_bin(bin_path, reader=reader)
    matched, errors = _match_schedule_ratio_windows(
        decoded.ratio_param_events,
        injection_events,
    )
    windows: list[ScheduleWindowSignals] = []
    for event, observed_ratio, start, end in matched:
        step = event.get("step") if isinstance(event, dict) else None
        requested_ratio = _event_ratio(event)
        if not isinstance(step, dict) or requested_ratio is None:
            continue
        if step.get("phase") != "fault_observe":
            continue
        windows.append(
            ScheduleWindowSignals(
                event_index=int(step.get("event_index") or 0),
                phase=str(step.get("phase") or "unknown"),
                bias_percent=float(step.get("bias_percent") or 0.0),
                requested_ratio=requested_ratio,
                observed_ratio=observed_ratio,
                window_start_s=start,
                window_end_s=end,
                signals=_extract_signals(
                    decoded,
                    expected_cruise=expected_cruise,
                    start=start,
                    end=end,
                ),
            )
        )
    return windows, errors


def _decode_bin(
    bin_path: str,
    *,
    reader: Callable[[str], Any] | None = None,
) -> DecodedBin:
    if reader is None:
        from pymavlink import mavutil  # type: ignore[import-not-found]

        active_reader: Callable[[str], Any] = mavutil.mavlink_connection
    else:
        active_reader = reader
    conn = active_reader(bin_path)
    series: dict[str, list[tuple[float, dict[str, Any]]]] = {
        name: [] for name in ("ARSP", "CTUN", "GPS", "TECS", "SIM2", "POS", "ATT", "AOA", "AETR")
    }
    wind_max: float | None = None
    ratio_param_events: list[tuple[float, float]] = []
    while True:
        msg = conn.recv_match(blocking=False)
        if msg is None:
            break
        kind = msg.get_type()
        data = msg.to_dict()
        if kind == "PARM":
            if data.get("Name") == "AHRS_WIND_MAX":
                wind_max = _float(data.get("Value"))
            elif data.get("Name") == "SIM_ARSPD_RATIO":
                timestamp = _message_timestamp(msg, data)
                value = _float(data.get("Value"))
                if timestamp is not None and value is not None:
                    if (
                        not ratio_param_events
                        or abs(timestamp - ratio_param_events[-1][0]) > 0.1
                        or abs(value - ratio_param_events[-1][1]) > 1e-7
                    ):
                        ratio_param_events.append((timestamp, value))
            continue
        if kind not in series:
            continue
        if kind in {"ARSP", "GPS"} and int(data.get("I") or 0) != 0:
            continue
        timestamp = _message_timestamp(msg, data)
        if timestamp is not None:
            series[kind].append((timestamp, data))

    return DecodedBin(series, wind_max, ratio_param_events)


def _extract_signals(
    decoded: DecodedBin,
    *,
    expected_cruise: float | None,
    start: float | None,
    end: float | None,
) -> RunSignals:
    all_times = [timestamp for rows in decoded.series.values() for timestamp, _ in rows]
    if start is None and all_times:
        earliest, latest = min(all_times), max(all_times)
        start = earliest + (latest - earliest) * (2.0 / 3.0)
    if end is None and all_times:
        end = max(all_times) + 1e-6
    series: dict[str, list[tuple[float, dict[str, Any]]]] = {}
    for name, rows in decoded.series.items():
        series[name] = [
            row for row in rows if (start is None or row[0] >= start) and (end is None or row[0] < end)
        ]

    aligned: list[dict[str, float]] = []
    series_times = {
        name: [timestamp for timestamp, _data in rows]
        for name, rows in series.items()
    }
    for timestamp, ctun in series["CTUN"]:
        arsp = _nearest(series["ARSP"], timestamp, times=series_times["ARSP"])
        gps = _nearest(series["GPS"], timestamp, times=series_times["GPS"])
        tecs = _nearest(series["TECS"], timestamp, times=series_times["TECS"])
        if arsp is None or gps is None or tecs is None:
            continue
        raw = _float(arsp.get("Airspeed")); believed = _float(ctun.get("As"))
        gnd = _float(gps.get("Spd")); target = _float(tecs.get("spdem")); e2t = _float(ctun.get("E2T"))
        if (
            raw is None
            or believed is None
            or gnd is None
            or target is None
            or e2t is None
            or e2t <= 0
        ):
            continue
        aligned.append(
            {
                "raw": raw,
                "believed": believed,
                "gnd": gnd,
                "target": target,
                "e2t": e2t,
                "use": float(arsp.get("U") or 0),
                "source_type": float(ctun.get("AsT") or 0),
                "health": float(arsp.get("H") or 0),
                "health_probability": float(arsp.get("Hp") or 0),
                "test_ratio": float(arsp.get("TR") or 0),
            }
        )

    u1 = [row for row in aligned if row["use"] == 1.0]
    sensor_rows = [row for row in aligned if row["source_type"] == 1.0]
    clamp_errors: list[float] = []
    tracking_errors: list[float] = []
    demand_errors: list[float] = []
    exercised = 0
    for row in sensor_rows:
        tracking_errors.append(abs(row["believed"] - row["raw"]))
        if expected_cruise is not None:
            demand_errors.append(row["target"] - expected_cruise * row["e2t"])
        if decoded.ahrs_wind_max is not None and decoded.ahrs_wind_max > 0:
            lower_tas = row["gnd"] - decoded.ahrs_wind_max
            upper_tas = row["gnd"] + decoded.ahrs_wind_max
            expected_eas = min(max(row["raw"] * row["e2t"], lower_tas), upper_tas) / row["e2t"]
            upper_eas = upper_tas / row["e2t"]
            if row["raw"] >= upper_eas + RAW_EXCESS_REQUIRED_MPS:
                exercised += 1
                clamp_errors.append(abs(row["believed"] - expected_eas))

    return RunSignals(
        ahrs_wind_max=decoded.ahrs_wind_max,
        raw_arsp_late=_mean(row["raw"] for row in sensor_rows),
        believed_as_late=_mean(row["believed"] for row in sensor_rows),
        gnd_speed_late=_mean(row["gnd"] for row in sensor_rows),
        tecs_target_late=_mean(row["target"] for row in sensor_rows),
        commanded_cruise_expected=expected_cruise,
        arsp_use_all_one=bool(aligned) and len(u1) == len(aligned),
        raw_arsp_max=max((row["raw"] for row in sensor_rows), default=None),
        eas2tas_late=_mean(row["e2t"] for row in sensor_rows),
        aligned_u1_sample_count=len(u1),
        aligned_sensor_sample_count=len(sensor_rows),
        clamp_exercised_sample_count=exercised,
        clamp_error_mean_mps=_mean(clamp_errors),
        tracking_error_mean_mps=_mean(tracking_errors),
        demand_error_mean_mps=_mean(demand_errors),
        sensor_disable_intervals=_disable_intervals(series["ARSP"]),
        sensor_source_rejection_intervals=_source_rejection_intervals(series["CTUN"]),
        sensor_source_all_one=bool(aligned) and len(sensor_rows) == len(aligned),
        airspeed_source_types_present=sorted(
            {int(row["source_type"]) for row in aligned}
        ),
        arsp_health_mean=_mean(row["health"] for row in aligned),
        arsp_health_probability_mean=_mean(row["health_probability"] for row in aligned),
        arsp_test_ratio_mean=_mean(row["test_ratio"] for row in aligned),
        true_airspeed_mean=_field_mean(series["SIM2"], "As"),
        altitude_mean=_field_mean(series["POS"], "RelHomeAlt"),
        throttle_mean=_field_mean(series["CTUN"], "ThO"),
        pitch_mean=_field_mean(series["ATT"], "Pitch"),
        aoa_mean=_field_mean(series["AOA"], "AOA"),
        elevator_mean=_field_mean(series["AETR"], "Elev"),
        window_start_s=start,
        window_end_s=end,
    )


def _nearest(
    rows: list[tuple[float, dict[str, Any]]],
    timestamp: float,
    *,
    times: list[float] | None = None,
) -> dict[str, Any] | None:
    if not rows:
        return None
    active_times = times if times is not None else [row[0] for row in rows]
    index = bisect_left(active_times, timestamp)
    candidates = rows[max(0, index - 1): min(len(rows), index + 1)]
    nearest = min(candidates, key=lambda row: abs(row[0] - timestamp))
    return nearest[1] if abs(nearest[0] - timestamp) <= MAX_ALIGNMENT_SKEW_S else None


def _disable_intervals(rows: list[tuple[float, dict[str, Any]]]) -> list[dict[str, float | None]]:
    intervals: list[dict[str, float | None]] = []
    start: float | None = None
    for timestamp, data in rows:
        use = int(data.get("U") or 0)
        if use == 0 and start is None:
            start = timestamp
        elif use == 1 and start is not None:
            intervals.append({"start_s": start, "end_s": timestamp, "duration_s": timestamp - start})
            start = None
    if start is not None:
        intervals.append({"start_s": start, "end_s": None, "duration_s": None})
    return intervals


def _source_rejection_intervals(
    rows: list[tuple[float, dict[str, Any]]],
) -> list[dict[str, float | None]]:
    intervals: list[dict[str, float | None]] = []
    start: float | None = None
    for timestamp, data in rows:
        source_type = int(data.get("AsT") or 0)
        if source_type != 1 and start is None:
            start = timestamp
        elif source_type == 1 and start is not None:
            intervals.append(
                {"start_s": start, "end_s": timestamp, "duration_s": timestamp - start}
            )
            start = None
    if start is not None:
        intervals.append({"start_s": start, "end_s": None, "duration_s": None})
    return intervals


def _match_schedule_ratio_windows(
    ratio_param_events: Sequence[tuple[float, float]],
    injection_events: Sequence[dict[str, Any]],
) -> tuple[
    list[tuple[dict[str, Any], float, float, float]],
    list[str],
]:
    """Match schedule events after the initial baseline to PARM transitions."""

    matched_starts: list[tuple[dict[str, Any], float, float]] = []
    errors: list[str] = []
    cursor = 0
    # Event 1 is an already-active baseline and can be indistinguishable from
    # boot parameter traffic.  Event 2 is the first actual ratio transition;
    # every later pulse/ramp event alternates or changes value and is matchable.
    for event in injection_events[1:]:
        expected = _event_ratio(event)
        step = event.get("step") if isinstance(event, dict) else None
        event_index = int(step.get("event_index") or 0) if isinstance(step, dict) else 0
        if expected is None:
            errors.append(f"event {event_index}: missing SIM_ARSPD_RATIO readback")
            continue
        while cursor < len(ratio_param_events):
            timestamp, observed = ratio_param_events[cursor]
            cursor += 1
            if abs(observed - expected) <= 1e-5:
                matched_starts.append((event, observed, timestamp))
                break
        else:
            errors.append(
                f"event {event_index}: no matching SIM_ARSPD_RATIO PARM transition for {expected}"
            )

    windows: list[tuple[dict[str, Any], float, float, float]] = []
    for index, (event, observed, start) in enumerate(matched_starts):
        if index + 1 < len(matched_starts):
            end = matched_starts[index + 1][2]
        else:
            step = event.get("step") if isinstance(event, dict) else None
            observe_s = float(step.get("observe_s") or 0.0) if isinstance(step, dict) else 0.0
            end = start + observe_s
        if end <= start:
            event_index = int(event.get("step", {}).get("event_index") or 0)
            errors.append(f"event {event_index}: non-positive BIN window")
            continue
        windows.append((event, observed, start, end))
    return windows, errors


def _event_ratio(event: dict[str, Any]) -> float | None:
    readback = event.get("readback_values")
    if isinstance(readback, dict):
        ratio = _float(readback.get("SIM_ARSPD_RATIO"))
        if ratio is not None:
            return ratio
    step = event.get("step")
    payload = step.get("payload") if isinstance(step, dict) else None
    if isinstance(payload, dict):
        return _float(payload.get("SIM_ARSPD_RATIO"))
    return None


def _message_timestamp(msg: Any, data: dict[str, Any]) -> float | None:
    timestamp = _float(getattr(msg, "_timestamp", None))
    if timestamp is not None:
        return timestamp
    time_us = _float(data.get("TimeUS"))
    return time_us / 1_000_000.0 if time_us is not None else None


def _parse_utc(value: str | None) -> float | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Sequence[float] | Any) -> float | None:
    materialized = [float(value) for value in values if value is not None]
    return sum(materialized) / len(materialized) if materialized else None


def _field_mean(rows: list[tuple[float, dict[str, Any]]], field: str) -> float | None:
    return _mean(value for _timestamp, data in rows if (value := _float(data.get(field))) is not None)


def _late_mean(series: Sequence[float]) -> float | None:
    """Compatibility helper retained for callers outside the aligned extractor."""
    values = [value for value in series if value is not None]
    if not values:
        return None
    third = max(1, len(values) // 3)
    return sum(values[-third:]) / third
