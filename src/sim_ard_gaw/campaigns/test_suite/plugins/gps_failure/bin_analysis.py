"""Decoded-BIN analysis helpers for gps_failure.

Input records are decoded dictionaries. The default decoder is a lazy pymavlink
DFReader boundary, and tests can inject a fake decoder to keep no-SITL coverage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import bisect
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .source_contract import pos_test_ratio_from_xkf4_sp

MAX_TRUTH_BELIEF_SKEW_S = 0.1
DecodedBinRecord = dict[str, Any]
BinDecoder = Callable[[Path], Iterable[Mapping[str, Any] | Any]]


@dataclass(frozen=True)
class BinMechanismResult:
    ok: bool
    reason: str
    primary_core: int | None = None
    samples: list[dict[str, Any]] = field(default_factory=list)
    reset_events: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "primary_core": self.primary_core,
            "samples": list(self.samples),
            "reset_events": list(self.reset_events),
            "source": "XKF4.SP/PI/TS/OFN/OFE",
        }


def extract_xkf4_mechanism(records: Iterable[Mapping[str, Any]]) -> BinMechanismResult:
    xkf4 = [_copy_record(record) for record in records if _record_type(record) == "XKF4"]
    if not xkf4:
        return BinMechanismResult(ok=False, reason="missing_xkf4_records")
    if any(record.get("PI") is None for record in xkf4):
        return BinMechanismResult(ok=False, reason="missing_xkf4_primary_index")
    primary_values = {_int(record.get("PI")) for record in xkf4}
    if None in primary_values or not primary_values:
        return BinMechanismResult(ok=False, reason="missing_xkf4_primary_index")
    if len(primary_values) != 1:
        return BinMechanismResult(ok=False, reason="primary_core_changed")
    primary_core = next(iter(primary_values))
    primary = [record for record in xkf4 if _int(record.get("C")) == primary_core]
    if not primary:
        return BinMechanismResult(ok=False, reason="missing_primary_core_xkf4")
    if any(record.get("TimeUS") is None or record.get("SP") is None for record in primary):
        return BinMechanismResult(ok=False, reason="malformed_primary_core_xkf4")
    try:
        primary.sort(key=lambda item: _float(item["TimeUS"]))
    except (TypeError, ValueError):
        return BinMechanismResult(ok=False, reason="malformed_primary_core_xkf4")

    samples: list[dict[str, Any]] = []
    reset_events: list[dict[str, Any]] = []
    previous_ofn: float | None = None
    previous_ofe: float | None = None
    previous_time: float | None = None
    for record in primary:
        try:
            time_us = _float(record["TimeUS"])
            ofn = _float(record.get("OFN", 0.0))
            ofe = _float(record.get("OFE", 0.0))
            ratio = pos_test_ratio_from_xkf4_sp(record.get("SP"))
        except (TypeError, ValueError):
            return BinMechanismResult(ok=False, reason="malformed_primary_core_xkf4")
        if previous_time is not None and time_us <= previous_time:
            return BinMechanismResult(ok=False, reason="xkf4_time_not_strictly_increasing")
        previous_time = time_us
        ts = _int(record.get("TS", 0)) or 0
        sample = {
            "time_us": time_us,
            "core": primary_core,
            "pos_test_ratio": ratio,
            "gps_position_rejected": ratio >= 1.0,
            "pos_timeout": bool(ts & 0x1),
            "gps_status": _int(record.get("GPS", 0)),
            "filter_status": _int(record.get("FS", 0)),
            "reset_north_m": ofn,
            "reset_east_m": ofe,
        }
        if previous_ofn is not None and (ofn != previous_ofn or ofe != previous_ofe):
            reset_events.append(
                {
                    "time_us": time_us,
                    "core": primary_core,
                    "ofn_m": ofn,
                    "ofe_m": ofe,
                    "delta_n_m": ofn - previous_ofn,
                    "delta_e_m": ofe - (previous_ofe or 0.0),
                }
            )
            sample["position_reset_event"] = True
        else:
            sample["position_reset_event"] = False
        samples.append(sample)
        previous_ofn = ofn
        previous_ofe = ofe
    return BinMechanismResult(
        ok=True,
        reason="ok",
        primary_core=primary_core,
        samples=samples,
        reset_events=reset_events,
    )


def decode_bin_records(
    bin_path: Path,
    *,
    decoder: BinDecoder | None = None,
) -> list[DecodedBinRecord]:
    """Decode a DataFlash BIN into JSON-safe records.

    The production path imports pymavlink only here, after a live attempt has
    produced a selected BIN. Unit tests pass ``decoder=`` and never require
    pymavlink or a real log file.
    """

    path = Path(bin_path)
    if decoder is not None:
        return [_decoded_record(item) for item in decoder(path)]
    try:
        from pymavlink import DFReader  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("pymavlink is required to decode GPS attempt BIN logs") from exc

    reader = DFReader.DFReader_binary(str(path))
    records: list[DecodedBinRecord] = []
    while True:
        msg = reader.recv_msg()
        if msg is None:
            break
        records.append(_decoded_record(msg))
    return records


def analyze_attempt_bin(
    bin_path: Path,
    *,
    decoder: BinDecoder | None = None,
    window_start_time_us: float | None = None,
    trigger_seq: int = 4,
    injection_payload: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Decode and analyze only the injection-window portion of an attempt BIN."""

    records = decode_bin_records(bin_path, decoder=decoder)
    try:
        anchor_us = (
            _float(window_start_time_us)
            if window_start_time_us is not None
            else _find_injection_window_start(
                records,
                trigger_seq=trigger_seq,
                injection_payload=injection_payload,
            )
        )
    except (TypeError, ValueError):
        anchor_us = None
    if anchor_us is None:
        return {
            "ok": False,
            "bin_path": str(Path(bin_path)),
            "record_count": len(records),
            "reason": "injection_window_not_anchored",
            "mechanism": BinMechanismResult(
                ok=False,
                reason="injection_window_not_anchored",
            ).as_dict(),
            "truth_vs_belief": {
                "ok": False,
                "reason": "injection_window_not_anchored",
                "samples": [],
            },
        }
    window_records = [
        record
        for record in records
        if (_record_time_us(record) is not None)
        and float(_record_time_us(record) or 0.0) >= anchor_us
    ]
    mechanism = extract_xkf4_mechanism(window_records)
    reset_times = [
        float(event["time_us"])
        for event in mechanism.reset_events
        if isinstance(event.get("time_us"), (int, float))
    ]
    truth_belief = truth_vs_belief_from_decoded_records(
        window_records,
        reset_event_times_us=reset_times,
    )
    return {
        "ok": mechanism.ok and bool(truth_belief.get("ok")),
        "bin_path": str(Path(bin_path)),
        "record_count": len(records),
        "window_record_count": len(window_records),
        "window_start_time_us": anchor_us,
        "window_anchor": "mission_seq_or_injection_parameter_transition",
        "mechanism": mechanism.as_dict(),
        "truth_vs_belief": truth_belief,
    }


def truth_vs_belief_from_decoded_records(
    records: Iterable[Mapping[str, Any]],
    *,
    max_skew_s: float = MAX_TRUTH_BELIEF_SKEW_S,
    reset_event_times_us: Iterable[float] = (),
) -> dict[str, Any]:
    try:
        reset_times = sorted(_float(value) for value in reset_event_times_us)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "malformed_reset_event_times", "samples": []}
    try:
        all_records = list(records)
        truth = sorted(
            (
                _position_sample(record, "truth")
                for record in all_records
                if _record_type(record) == "SIM"
            ),
            key=lambda item: item["time_us"],
        )
        belief = sorted(
            (
                _position_sample(record, "belief")
                for record in all_records
                if _record_type(record) == "POS"
            ),
            key=lambda item: item["time_us"],
        )
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "reason": "malformed_position_records", "samples": []}
    if not truth:
        return {"ok": False, "reason": "missing_sim_truth_records", "samples": []}
    if not belief:
        return {"ok": False, "reason": "missing_pos_belief_records", "samples": []}

    truth_times = [item["time_us"] for item in truth]
    pairs: list[dict[str, Any]] = []
    for belief_sample in belief:
        index = bisect.bisect_left(truth_times, belief_sample["time_us"])
        candidates = []
        if index < len(truth):
            candidates.append(truth[index])
        if index > 0:
            candidates.append(truth[index - 1])
        if not candidates:
            continue
        nearest = min(
            candidates,
            key=lambda item: abs(item["time_us"] - belief_sample["time_us"]),
        )
        skew_s = abs(nearest["time_us"] - belief_sample["time_us"]) / 1_000_000.0
        if skew_s > max_skew_s:
            continue
        gap_m = horizontal_gap_m(
            nearest["lat_deg_e7"],
            nearest["lon_deg_e7"],
            belief_sample["lat_deg_e7"],
            belief_sample["lon_deg_e7"],
        )
        pairs.append(
            {
                "time_us": belief_sample["time_us"],
                "truth_time_us": nearest["time_us"],
                "belief_time_us": belief_sample["time_us"],
                "skew_s": skew_s,
                "truth_lat_deg_e7": nearest["lat_deg_e7"],
                "truth_lon_deg_e7": nearest["lon_deg_e7"],
                "belief_lat_deg_e7": belief_sample["lat_deg_e7"],
                "belief_lon_deg_e7": belief_sample["lon_deg_e7"],
                "horizontal_gap_m": gap_m,
                "segment_index": bisect.bisect_right(
                    reset_times,
                    belief_sample["time_us"],
                ),
            }
        )
    if not pairs:
        return {"ok": False, "reason": "no_truth_belief_pairs_within_skew", "samples": []}
    active_segment = max(int(sample["segment_index"]) for sample in pairs)
    active_pairs = [
        sample for sample in pairs if sample["segment_index"] == active_segment
    ]
    return {
        "ok": True,
        "reason": "ok",
        "samples": active_pairs,
        "all_sample_count": len(pairs),
        "active_segment_index": active_segment,
        "reset_event_times_us": reset_times,
        "source": "SIM Lat/Lng truth paired with POS Lat/Lng canonical belief",
        "max_skew_s": max_skew_s,
    }


def _find_injection_window_start(
    records: Iterable[Mapping[str, Any]],
    *,
    trigger_seq: int,
    injection_payload: Mapping[str, float] | None,
) -> float | None:
    mission_candidates: list[float] = []
    parameter_candidates: list[float] = []
    expected_payload = dict(injection_payload or {})
    for record in records:
        time_us = _record_time_us(record)
        if time_us is None:
            continue
        record_type = _record_type(record)
        if record_type in {"CMD", "MISSION_CURRENT"}:
            seq = _int(
                record.get("CNum", record.get("Seq", record.get("seq")))
            )
            if seq == trigger_seq:
                mission_candidates.append(time_us)
        if record_type == "PARM" and expected_payload:
            name = str(record.get("Name", record.get("name", ""))).rstrip("\x00")
            if name not in expected_payload:
                continue
            try:
                observed = _float(record.get("Value", record.get("value")))
                expected = _float(expected_payload[name])
            except (TypeError, ValueError):
                continue
            if math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-6):
                parameter_candidates.append(time_us)
    if mission_candidates:
        return min(mission_candidates)
    if parameter_candidates:
        return min(parameter_candidates)
    return None


def _record_time_us(record: Mapping[str, Any]) -> float | None:
    value = record.get("TimeUS")
    if value is None:
        return None
    try:
        return _float(value)
    except (TypeError, ValueError):
        return None


def horizontal_gap_m(
    truth_lat_e7: object,
    truth_lon_e7: object,
    belief_lat_e7: object,
    belief_lon_e7: object,
) -> float:
    truth_lat = _float(truth_lat_e7) / 1e7
    truth_lon = _float(truth_lon_e7) / 1e7
    belief_lat = _float(belief_lat_e7) / 1e7
    belief_lon = _float(belief_lon_e7) / 1e7
    ref_lat_rad = math.radians((truth_lat + belief_lat) / 2.0)
    dn = (belief_lat - truth_lat) * 111_320.0
    de = (belief_lon - truth_lon) * 111_320.0 * math.cos(ref_lat_rad)
    return math.hypot(dn, de)


def _position_sample(record: Mapping[str, Any], kind: str) -> dict[str, Any]:
    lat_name = "Lat" if "Lat" in record else "lat"
    lng_name = "Lng" if "Lng" in record else "lng"
    return {
        "kind": kind,  # type: ignore[dict-item]
        "time_us": _float(record["TimeUS"]),
        "lat_deg_e7": _float(record[lat_name]),
        "lon_deg_e7": _float(record[lng_name]),
    }


def _record_type(record: Mapping[str, Any]) -> str:
    return str(record.get("type") or record.get("name") or record.get("mavpackettype") or "")


def _copy_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in record.items()}


def _decoded_record(item: Mapping[str, Any] | Any) -> DecodedBinRecord:
    if isinstance(item, Mapping):
        record = _copy_record(item)
    else:
        to_dict = getattr(item, "to_dict", None)
        if callable(to_dict):
            raw = to_dict()
            record = _copy_record(raw) if isinstance(raw, Mapping) else {}
        else:
            names = getattr(item, "_fieldnames", ())
            record = {
                str(name): getattr(item, str(name))
                for name in names
                if hasattr(item, str(name))
            }
    msg_type = _decoded_type(item, record)
    if msg_type and not _record_type(record):
        record["type"] = msg_type
    return record


def _decoded_type(item: Mapping[str, Any] | Any, record: Mapping[str, Any]) -> str | None:
    if isinstance(item, Mapping):
        value = _record_type(item)
        return value or None
    get_type = getattr(item, "get_type", None)
    if callable(get_type):
        return str(get_type())
    value = _record_type(record)
    return value or None


def _float(value: object) -> float:
    parsed = float(value)  # type: ignore[arg-type]
    if not math.isfinite(parsed):
        raise ValueError("decoded BIN value must be finite")
    return parsed


def _int(value: object) -> int | None:
    if value is None:
        return None
    parsed = _float(value)
    if not parsed.is_integer():
        return None
    return int(parsed)
