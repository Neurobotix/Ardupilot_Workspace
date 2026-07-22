"""Decoded-BIN analysis helpers for gps_failure.

Input records are decoded dictionaries. The default decoder is a lazy pymavlink
DFReader boundary, and tests can inject a fake decoder to keep no-SITL coverage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import bisect
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, cast

from sim_ard_gaw.campaigns.provenance import file_provenance

from . import defaults, glitch
from .source_contract import pos_test_ratio_from_xkf4_sp

MAX_TRUTH_BELIEF_SKEW_S = 0.1
NOMINAL_MAX_TRUTH_BELIEF_GAP_M = 5.0
HEALTHY_GPS_STATUS_MIN = 3
HEALTHY_GPS_SATS_MIN = 6
DENIED_GPS_STATUS_MAX = 2
DENIED_GPS_SATS_MAX = 4
SLOW_DRIFT_ABS_TOLERANCE_MPS = 0.03
SLOW_DRIFT_REL_TOLERANCE = 0.075
SLOW_DRIFT_OFFSET_ABS_TOLERANCE_M = 0.5
STEP_GLITCH_OFFSET_ABS_TOLERANCE_M = 0.5
HARD_DENIAL_DURATION_TOLERANCE_S = 0.8
LIFECYCLE_WINDOW_NAMES = (
    "pre_trigger_baseline",
    "trigger",
    "injection",
    "fault_active",
    "ekf_response",
    "recovery_or_continuation",
    "terminal",
)
DecodedBinRecord = dict[str, Any]
BinDecoder = Callable[[Path], Iterable[Mapping[str, Any] | Any]]


@dataclass(frozen=True)
class BinMechanismResult:
    ok: bool
    reason: str
    primary_core: int | None = None
    samples: list[dict[str, Any]] = field(default_factory=list)
    reset_events: list[dict[str, Any]] = field(default_factory=list)
    primary_core_changes: list[dict[str, Any]] = field(default_factory=list)
    missing_bin_observable_fields: list[str] = field(default_factory=list)
    malformed_optional_context: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        bin_observable_proof = (
            self.ok
            and not self.missing_bin_observable_fields
            and not self.malformed_optional_context
        )
        return {
            "ok": self.ok,
            "reason": self.reason,
            "primary_core": self.primary_core,
            "samples": list(self.samples),
            "reset_events": list(self.reset_events),
            "primary_core_changes": list(self.primary_core_changes),
            "primary_core_changed": bool(self.primary_core_changes),
            "exact_internal_proof": False,
            "bin_observable_proof": bin_observable_proof,
            "validated_proxy_proof": False,
            "proof_level": (
                "bin_observable_proof"
                if bin_observable_proof
                else "partial_bin_observable_context"
                if self.ok
                else "incomplete"
            ),
            "missing_bin_observable_fields": list(self.missing_bin_observable_fields),
            "malformed_optional_context": list(self.malformed_optional_context),
            "source": (
                "XKF4.SP/PI/GPS/TS/OFN/OFE with GPS.Status/NSats reported "
                "only when decoded GPS rows are present"
            ),
            "source_fields": {
                "primary_core": ["XKF4.PI", "XKF4.C"],
                "pos_test_ratio": ["XKF4.SP"],
                "gps_status": ["XKF4.GPS"],
                "decoded_gps_quality_optional": ["GPS.Status", "GPS.NSats"],
                "timeout": ["XKF4.TS"],
                "position_reset": ["XKF4.OFN", "XKF4.OFE"],
            },
            "source_field_availability": _mechanism_source_field_availability(
                self.samples,
                missing_fields=self.missing_bin_observable_fields,
                malformed_optional_context=self.malformed_optional_context,
            ),
        }


def extract_xkf4_mechanism(records: Iterable[Mapping[str, Any]]) -> BinMechanismResult:
    all_records = [_copy_record(record) for record in records]
    xkf4 = [record for record in all_records if _record_type(record) == "XKF4"]
    if not xkf4:
        return BinMechanismResult(ok=False, reason="missing_xkf4_records")
    if any(record.get("PI") is None for record in xkf4):
        return BinMechanismResult(ok=False, reason="missing_xkf4_primary_index")
    primary_values = {_int(record.get("PI")) for record in xkf4}
    if None in primary_values or not primary_values:
        return BinMechanismResult(ok=False, reason="missing_xkf4_primary_index")
    if any(record.get("C") is None for record in xkf4):
        return BinMechanismResult(ok=False, reason="missing_primary_core_xkf4")
    try:
        xkf4.sort(key=lambda item: _float(item["TimeUS"]))
    except (KeyError, TypeError, ValueError):
        return BinMechanismResult(ok=False, reason="malformed_primary_core_xkf4")

    primary = [
        record for record in xkf4
        if _int(record.get("C")) == _int(record.get("PI"))
    ]
    if not primary:
        return BinMechanismResult(ok=False, reason="missing_primary_core_xkf4")
    if any(record.get("TimeUS") is None or record.get("SP") is None for record in primary):
        return BinMechanismResult(ok=False, reason="malformed_primary_core_xkf4")
    primary_core = _int(primary[-1].get("PI"))
    if primary_core is None:
        return BinMechanismResult(ok=False, reason="missing_xkf4_primary_index")

    samples: list[dict[str, Any]] = []
    reset_events: list[dict[str, Any]] = []
    primary_core_changes: list[dict[str, Any]] = []
    try:
        gps_quality_samples = _gps_quality_samples(all_records)
    except ValueError:
        gps_quality_samples = []
        malformed_optional_context = ["GPS.Status/NSats"]
    else:
        malformed_optional_context = []
    gps_quality_index = _gps_quality_index(gps_quality_samples)
    missing_fields: set[str] = set()
    previous_ofn: float | None = None
    previous_ofe: float | None = None
    previous_time: float | None = None
    previous_core: int | None = None
    for record in primary:
        try:
            time_us = _float(record["TimeUS"])
            ratio = pos_test_ratio_from_xkf4_sp(record.get("SP"))
            sample_core = _int(record.get("C"))
        except (TypeError, ValueError):
            return BinMechanismResult(ok=False, reason="malformed_primary_core_xkf4")
        if sample_core is None:
            return BinMechanismResult(ok=False, reason="malformed_primary_core_xkf4")
        try:
            ofn = _optional_float_field(record, "OFN", missing_fields)
            ofe = _optional_float_field(record, "OFE", missing_fields)
            ts = _optional_int_field(record, "TS", missing_fields)
            gps_status = _optional_int_field(record, "GPS", missing_fields)
            filter_status = _optional_int_field(
                record,
                "FS",
                missing_fields,
                required=False,
            )
        except ValueError:
            return BinMechanismResult(ok=False, reason="malformed_primary_core_xkf4")
        if previous_time is not None and time_us <= previous_time:
            return BinMechanismResult(ok=False, reason="xkf4_time_not_strictly_increasing")
        previous_time = time_us
        core_changed = previous_core is not None and sample_core != previous_core
        if core_changed:
            primary_core_changes.append(
                {
                    "time_us": time_us,
                    "from_core": previous_core,
                    "to_core": sample_core,
                    "source": "XKF4.PI/C",
                }
            )
        sample = {
            "time_us": time_us,
            "core": sample_core,
            "primary_core_source": "XKF4.PI",
            "primary_core_changed": core_changed,
            "pos_test_ratio": ratio,
            "pos_test_ratio_source": "XKF4.SP",
            "gps_position_rejected": ratio >= 1.0,
            "pos_timeout": bool(ts & 0x1) if ts is not None else None,
            "pos_timeout_source": "XKF4.TS",
            "gps_status": gps_status,
            "gps_status_source": "XKF4.GPS",
            "gps_quality": _nearest_gps_quality(gps_quality_index, time_us),
            "filter_status": filter_status,
            "reset_north_m": ofn,
            "reset_east_m": ofe,
            "position_reset_source": "XKF4.OFN/OFE",
        }
        if (
            previous_ofn is not None
            and previous_ofe is not None
            and ofn is not None
            and ofe is not None
            and not core_changed
            and (ofn != previous_ofn or ofe != previous_ofe)
        ):
            reset_events.append(
                {
                    "time_us": time_us,
                    "core": sample_core,
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
        if ofn is not None and ofe is not None:
            previous_ofn = ofn
            previous_ofe = ofe
        previous_core = sample_core
    return BinMechanismResult(
        ok=True,
        reason="ok",
        primary_core=primary_core,
        samples=samples,
        reset_events=reset_events,
        primary_core_changes=primary_core_changes,
        missing_bin_observable_fields=sorted(missing_fields),
        malformed_optional_context=malformed_optional_context,
    )


def _mechanism_source_field_availability(
    samples: Iterable[Mapping[str, Any]],
    *,
    missing_fields: Iterable[str],
    malformed_optional_context: Iterable[str],
) -> dict[str, Any]:
    sample_list = list(samples)
    missing = sorted(set(missing_fields))
    malformed = sorted(set(malformed_optional_context))
    return {
        "required_xkf4_fields_complete": not missing,
        "missing_required_xkf4_fields": missing,
        "malformed_optional_context": malformed,
        "decoded_gps_quality_available": any(
            isinstance(sample.get("gps_quality"), Mapping)
            for sample in sample_list
        ),
        "sample_count": len(sample_list),
        "notes": {
            "decoded_gps_quality": (
                "GPS.Status/NSats are optional context because GPS rows can be "
                "absent from a decoded window; malformed decoded GPS rows are "
                "reported separately."
            ),
        },
    }


def _optional_float_field(
    record: Mapping[str, Any],
    name: str,
    missing_fields: set[str],
) -> float | None:
    if name not in record:
        missing_fields.add(f"XKF4.{name}")
        return None
    return _float(record[name])


def _optional_int_field(
    record: Mapping[str, Any],
    name: str,
    missing_fields: set[str],
    *,
    required: bool = True,
) -> int | None:
    if name not in record:
        if required:
            missing_fields.add(f"XKF4.{name}")
        return None
    parsed = _int(record.get(name))
    if parsed is None:
        raise ValueError(f"XKF4.{name} must be an integer")
    return parsed


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
    case_id: str | None = None,
    fault_type: str | None = None,
    fault_recipe: Mapping[str, Any] | None = None,
    trigger_event: Mapping[str, Any] | None = None,
    injection_execution: Mapping[str, Any] | None = None,
    source_contract: Mapping[str, Any] | None = None,
    terminal_context: Mapping[str, Any] | None = None,
    wall_elapsed_s: float | None = None,
    clock_ratio: float | None = None,
    live_attitude_altitude_envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Decode and analyze only the injection-window portion of an attempt BIN."""

    records = decode_bin_records(bin_path, decoder=decoder)
    anchor_kind = (
        "live_trigger_boot_time"
        if window_start_time_us is not None
        else "injection_parameter_transition"
    )
    try:
        if window_start_time_us is not None:
            anchor_us = _float(window_start_time_us)
        else:
            anchor_us = _find_injection_window_start(
                records,
                trigger_seq=trigger_seq,
                injection_payload=injection_payload,
            )
    except (TypeError, ValueError):
        anchor_us = None
    if anchor_us is None:
        stimulus_fidelity = stimulus_fidelity_from_decoded_records(
            records,
            case_id=case_id,
            fault_type=fault_type,
            fault_recipe=fault_recipe,
            window_start_time_us=None,
            trigger_event=trigger_event,
            wall_elapsed_s=wall_elapsed_s,
            clock_ratio=clock_ratio,
        )
        lifecycle_windows = lifecycle_windows_from_decoded_records(
            records,
            case_id=case_id,
            fault_type=fault_type,
            fault_recipe=fault_recipe,
            window_start_time_us=None,
            trigger_event=trigger_event,
            injection_execution=injection_execution,
            source_contract=source_contract,
            terminal_context=terminal_context,
            stimulus_fidelity=stimulus_fidelity,
            mechanism=None,
            truth_vs_belief=None,
        )
        envelope = attitude_altitude_envelope_from_decoded_records(
            records,
            window_start_time_us=None,
            live_artifact=live_attitude_altitude_envelope,
            reason="injection_window_not_anchored",
        )
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
            "stimulus_fidelity": stimulus_fidelity,
            "lifecycle_windows": lifecycle_windows,
            "attitude_altitude_envelope": envelope,
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
    stimulus_fidelity = stimulus_fidelity_from_decoded_records(
        records,
        case_id=case_id,
        fault_type=fault_type,
        fault_recipe=fault_recipe,
        window_start_time_us=anchor_us,
        trigger_event=trigger_event,
        truth_vs_belief=truth_belief,
        mechanism=mechanism.as_dict(),
        wall_elapsed_s=wall_elapsed_s,
        clock_ratio=clock_ratio,
    )
    lifecycle_windows = lifecycle_windows_from_decoded_records(
        records,
        case_id=case_id,
        fault_type=fault_type,
        fault_recipe=fault_recipe,
        window_start_time_us=anchor_us,
        trigger_event=trigger_event,
        injection_execution=injection_execution,
        source_contract=source_contract,
        terminal_context=terminal_context,
        stimulus_fidelity=stimulus_fidelity,
        mechanism=mechanism.as_dict(),
        truth_vs_belief=truth_belief,
    )
    envelope = attitude_altitude_envelope_from_decoded_records(
        records,
        window_start_time_us=anchor_us,
        live_artifact=live_attitude_altitude_envelope,
    )
    return {
        "ok": mechanism.ok and bool(truth_belief.get("ok")) and envelope.get("status") == "pass",
        "bin_path": str(Path(bin_path)),
        "record_count": len(records),
        "window_record_count": len(window_records),
        "window_start_time_us": anchor_us,
        "window_anchor": anchor_kind,
        "bin_provenance": (
            file_provenance(bin_path) if Path(bin_path).is_file() else None
        ),
        "mechanism": mechanism.as_dict(),
        "truth_vs_belief": truth_belief,
        "stimulus_fidelity": stimulus_fidelity,
        "lifecycle_windows": lifecycle_windows,
        "attitude_altitude_envelope": envelope,
    }


def stimulus_fidelity_from_decoded_records(
    records: Iterable[Mapping[str, Any]],
    *,
    case_id: str | None,
    fault_type: str | None,
    fault_recipe: Mapping[str, Any] | None = None,
    window_start_time_us: float | None,
    trigger_event: Mapping[str, Any] | None = None,
    truth_vs_belief: Mapping[str, Any] | None = None,
    mechanism: Mapping[str, Any] | None = None,
    wall_elapsed_s: float | None = None,
    clock_ratio: float | None = None,
) -> dict[str, Any]:
    """Evaluate whether the decoded BIN proves the requested GPS stimulus.

    This is deliberately separate from behavior analysis. A run can contain
    useful behavior samples while failing the requested physical dose.
    """

    fault = str(fault_type or "")
    base = _stimulus_base(
        case_id=case_id,
        fault_type=fault,
        requested=_stimulus_requested(fault, fault_recipe),
        tolerances=_stimulus_tolerances(fault),
    )
    try:
        all_records = [_copy_record(record) for record in records]
        anchor_us = _float(window_start_time_us)
    except (TypeError, ValueError):
        return _stimulus_fail(base, "injection_window_not_anchored", ["window_start_time_us"])
    if anchor_us < 0:
        return _stimulus_fail(base, "injection_window_not_anchored", ["window_start_time_us"])

    if fault == "nominal":
        return _nominal_stimulus_fidelity(
            all_records,
            anchor_us=anchor_us,
            base=base,
            truth_vs_belief=truth_vs_belief,
            mechanism=mechanism,
        )
    if fault == "slow_drift":
        return _slow_drift_stimulus_fidelity(
            all_records,
            anchor_us=anchor_us,
            base=base,
            fault_recipe=fault_recipe,
            trigger_event=trigger_event,
            wall_elapsed_s=wall_elapsed_s,
            clock_ratio=clock_ratio,
        )
    if fault == "step_glitch":
        return _step_glitch_stimulus_fidelity(
            all_records,
            anchor_us=anchor_us,
            base=base,
            fault_recipe=fault_recipe,
            trigger_event=trigger_event,
        )
    if fault == "hard_denial":
        return _hard_denial_stimulus_fidelity(
            all_records,
            anchor_us=anchor_us,
            base=base,
            fault_recipe=fault_recipe,
        )
    base.update({
        "status": "not_applicable",
        "reason": "stimulus_fidelity_not_implemented_for_fault_type",
    })
    return base


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
            nearest["lat_deg"],
            nearest["lon_deg"],
            belief_sample["lat_deg"],
            belief_sample["lon_deg"],
        )
        pairs.append(
            {
                "time_us": belief_sample["time_us"],
                "truth_time_us": nearest["time_us"],
                "belief_time_us": belief_sample["time_us"],
                "skew_s": skew_s,
                "truth_lat_deg": nearest["lat_deg"],
                "truth_lon_deg": nearest["lon_deg"],
                "belief_lat_deg": belief_sample["lat_deg"],
                "belief_lon_deg": belief_sample["lon_deg"],
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
    full_terminal = pairs[-1] if pairs else None
    active_terminal = active_pairs[-1] if active_pairs else None
    max_gap_sample = max(pairs, key=lambda item: item["horizontal_gap_m"])
    mission_terminal_event = _mission_terminal_event(all_records)
    mission_terminal_sample = (
        min(
            pairs,
            key=lambda item: abs(
                item["time_us"] - mission_terminal_event["time_us"]
            ),
        )
        if mission_terminal_event is not None
        else None
    )
    return {
        "ok": True,
        "reason": "ok",
        "samples": active_pairs,
        "sample_scope": "active_segment_post_last_reset",
        "mission_terminal_event": mission_terminal_event,
        "mission_terminal_sample": (
            dict(mission_terminal_sample) if mission_terminal_sample else None
        ),
        "full_window_terminal_sample": dict(full_terminal) if full_terminal else None,
        "active_segment_terminal_sample": (
            dict(active_terminal) if active_terminal else None
        ),
        "full_window_max_gap_sample": dict(max_gap_sample),
        "all_sample_count": len(pairs),
        "active_segment_index": active_segment,
        "reset_event_times_us": reset_times,
        "full_window_gap_summary": _gap_summary(
            pairs,
            sample_scope="full_post_trigger_window",
        ),
        "active_segment_gap_summary": _gap_summary(
            active_pairs,
            sample_scope="active_segment_post_last_reset",
        ),
        "sample_scope_labels": {
            "samples": "active_segment_post_last_reset",
            "mission_terminal_sample": "sample_nearest_mission_terminal_event",
            "full_window_gap_summary": "full_post_trigger_window",
            "active_segment_gap_summary": "active_segment_post_last_reset",
        },
        "source": "SIM Lat/Lng truth paired with POS Lat/Lng canonical belief",
        "max_skew_s": max_skew_s,
    }


def _mission_terminal_event(records: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    events: list[dict[str, Any]] = []
    for record in records:
        if _record_type(record) != "MSG":
            continue
        time_us = _record_time_us(record)
        if time_us is None:
            continue
        message = str(record.get("Message") or record.get("message") or "")
        if message.startswith("Mission: 9 RTL"):
            events.append({
                "time_us": time_us,
                "message": message,
                "source": "MSG.Message",
            })
    return min(events, key=lambda item: item["time_us"]) if events else None


def attitude_altitude_envelope_from_decoded_records(
    records: Iterable[Mapping[str, Any]],
    *,
    window_start_time_us: float | None,
    live_artifact: Mapping[str, Any] | None = None,
    reason: str = "ok",
) -> dict[str, Any]:
    """Build the post-cleanup altitude/attitude envelope from decoded BIN rows.

    BIN-derived values are final-evidence quality only when both altitude and
    attitude are available from decoded records and any live guard values agree
    within the declared tolerance.
    """

    try:
        anchor_us = _float(window_start_time_us)
    except (TypeError, ValueError):
        return _attitude_altitude_artifact(
            source="hybrid",
            altitude_source=None,
            attitude_source=None,
            altitude_samples=[],
            attitude_samples=[],
            evidence_quality="incomplete",
            final_evidence_quality=False,
            runtime_guard_quality=False,
            reason=reason if reason != "ok" else "injection_window_not_anchored",
            missing_evidence=["window_start_time_us"],
            unexpected_disarm=_live_unexpected_disarm(live_artifact),
            comparison=_live_bin_comparison(None, None, live_artifact),
        )
    all_records = [_copy_record(record) for record in records]
    post_records = [
        record
        for record in all_records
        if (_record_time_us(record) is not None)
        and float(_record_time_us(record) or 0.0) >= anchor_us
    ]
    altitude_samples = _bin_altitude_samples(post_records)
    attitude_samples = _bin_attitude_samples(post_records)
    missing: list[str] = []
    if not altitude_samples:
        missing.append("BIN.altitude")
        altitude_samples = _live_altitude_samples(live_artifact)
    if not attitude_samples:
        missing.append("BIN.attitude")
        attitude_samples = _live_attitude_samples(live_artifact)
    altitude_source = _sample_source(altitude_samples)
    attitude_source = _sample_source(attitude_samples)
    comparison = _live_bin_comparison(altitude_samples, attitude_samples, live_artifact)
    if comparison.get("status") == "mismatch":
        missing.extend(str(item) for item in comparison.get("mismatches", []))
    source = "BIN"
    evidence_quality = "final_evidence"
    final_quality = True
    if missing:
        source = "hybrid" if _live_has_envelope_samples(live_artifact) else "BIN"
        evidence_quality = "incomplete"
        final_quality = False
    artifact = _attitude_altitude_artifact(
        source=source,
        altitude_source=altitude_source,
        attitude_source=attitude_source,
        altitude_samples=altitude_samples,
        attitude_samples=attitude_samples,
        evidence_quality=evidence_quality,
        final_evidence_quality=final_quality,
        runtime_guard_quality=False,
        reason="ok" if not missing else "bin_live_mismatch_or_missing_source",
        missing_evidence=missing,
        unexpected_disarm=_live_unexpected_disarm(live_artifact),
        comparison=comparison,
    )
    if reason != "ok" and artifact["status"] == "fail":
        artifact["reason"] = reason
    return artifact


def stimulus_fidelity_pending_artifact(
    *,
    case_id: str,
    fault_type: str | None,
    fault_recipe: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = _stimulus_base(
        case_id=case_id,
        fault_type=str(fault_type or ""),
        requested=_stimulus_requested(str(fault_type or ""), fault_recipe),
        tolerances=_stimulus_tolerances(str(fault_type or "")),
    )
    artifact.update({
        "status": "fail",
        "reason": "pending_post_cleanup_bin_analysis",
        "missing_evidence": ["finalized_bin_analysis"],
    })
    return artifact


def stimulus_fidelity_missing_bin_artifact(
    *,
    case_id: str | None,
    fault_type: str | None,
    fault_recipe: Mapping[str, Any] | None = None,
    reason: str = "bin_not_available",
) -> dict[str, Any]:
    artifact = _stimulus_base(
        case_id=case_id,
        fault_type=str(fault_type or ""),
        requested=_stimulus_requested(str(fault_type or ""), fault_recipe),
        tolerances=_stimulus_tolerances(str(fault_type or "")),
    )
    return _stimulus_fail(artifact, reason, ["BIN"])


def lifecycle_windows_pending_artifact(
    *,
    case_id: str,
    fault_type: str | None,
) -> dict[str, Any]:
    return _lifecycle_unavailable_artifact(
        case_id=case_id,
        fault_type=fault_type,
        reason="pending_post_cleanup_bin_analysis",
        missing_evidence=["finalized_bin_analysis"],
    )


def lifecycle_windows_missing_bin_artifact(
    *,
    case_id: str | None,
    fault_type: str | None,
    reason: str = "bin_not_available",
) -> dict[str, Any]:
    return _lifecycle_unavailable_artifact(
        case_id=case_id,
        fault_type=fault_type,
        reason=reason,
        missing_evidence=["BIN"],
    )


def lifecycle_windows_from_decoded_records(
    records: Iterable[Mapping[str, Any]],
    *,
    case_id: str | None,
    fault_type: str | None,
    fault_recipe: Mapping[str, Any] | None = None,
    window_start_time_us: float | None,
    trigger_event: Mapping[str, Any] | None = None,
    injection_execution: Mapping[str, Any] | None = None,
    source_contract: Mapping[str, Any] | None = None,
    terminal_context: Mapping[str, Any] | None = None,
    stimulus_fidelity: Mapping[str, Any] | None = None,
    mechanism: Mapping[str, Any] | None = None,
    truth_vs_belief: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        all_records = [_copy_record(record) for record in records]
        anchor_us = _float(window_start_time_us)
    except (TypeError, ValueError):
        return _lifecycle_unavailable_artifact(
            case_id=case_id,
            fault_type=fault_type,
            reason="injection_window_not_anchored",
            missing_evidence=["window_start_time_us"],
        )
    if anchor_us < 0.0:
        return _lifecycle_unavailable_artifact(
            case_id=case_id,
            fault_type=fault_type,
            reason="injection_window_not_anchored",
            missing_evidence=["window_start_time_us"],
        )

    fault = str(fault_type or "")
    windows = [
        _baseline_window(all_records, anchor_us, source_contract=source_contract),
        _trigger_window(anchor_us, trigger_event=trigger_event),
        _injection_window(
            anchor_us,
            records=all_records,
            injection_execution=injection_execution,
        ),
        _fault_active_window(
            all_records,
            anchor_us,
            fault_type=fault,
            fault_recipe=fault_recipe,
            trigger_event=trigger_event,
            stimulus_fidelity=stimulus_fidelity,
        ),
        _ekf_response_window(
            anchor_us,
            mechanism=mechanism,
            terminal_context=terminal_context,
        ),
        _recovery_or_continuation_window(
            all_records,
            anchor_us,
            fault_type=fault,
            stimulus_fidelity=stimulus_fidelity,
            mechanism=mechanism,
            truth_vs_belief=truth_vs_belief,
        ),
        _terminal_window(all_records, anchor_us, terminal_context=terminal_context),
    ]
    failing = [window for window in windows if window["status"] == "fail"]
    transient = _hard_denial_transient_summary(
        fault_type=fault,
        stimulus_fidelity=stimulus_fidelity,
        mechanism=mechanism,
        truth_vs_belief=truth_vs_belief,
    )
    if transient.get("status") == "fail":
        failing.append({"status": "fail", "metrics": transient})
    return {
        "case_id": case_id,
        "fault_type": fault,
        "status": "fail" if failing else "pass",
        "reason": "lifecycle_window_failure" if failing else "ok",
        "source": "hybrid",
        "required_order": list(LIFECYCLE_WINDOW_NAMES),
        "windows": windows,
        "hard_denial_transient": transient,
        "missing_evidence": [
            item
            for window in failing
            for item in window["metrics"].get("missing_evidence", [])
        ],
    }


def _lifecycle_unavailable_artifact(
    *,
    case_id: str | None,
    fault_type: str | None,
    reason: str,
    missing_evidence: list[str],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "fault_type": str(fault_type or ""),
        "status": "fail",
        "reason": reason,
        "source": "hybrid",
        "required_order": list(LIFECYCLE_WINDOW_NAMES),
        "windows": [
            _window(
                name=name,
                start_time_us=None,
                end_time_us=None,
                source="hybrid",
                status="fail",
                summary=reason,
                metrics={"missing_evidence": list(missing_evidence)},
                evidence_refs=[],
            )
            for name in LIFECYCLE_WINDOW_NAMES
        ],
        "hard_denial_transient": {
            "status": "fail",
            "reason": reason,
            "fault_type": str(fault_type or ""),
            "sample_scope": "unavailable",
            "missing_evidence": list(missing_evidence),
        },
        "missing_evidence": list(missing_evidence),
    }


def _hard_denial_transient_summary(
    *,
    fault_type: str,
    stimulus_fidelity: Mapping[str, Any] | None,
    mechanism: Mapping[str, Any] | None,
    truth_vs_belief: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if fault_type != "hard_denial":
        return {
            "status": "not_applicable",
            "reason": "not_hard_denial_case",
            "fault_type": fault_type,
            "sample_scope": "not_applicable",
            "missing_evidence": [],
        }

    realized: Mapping[str, Any] = {}
    if isinstance(stimulus_fidelity, Mapping):
        realized_obj = stimulus_fidelity.get("realized")
        if isinstance(realized_obj, Mapping):
            realized = cast(Mapping[str, Any], realized_obj)
    reset_events: list[Any] = []
    if isinstance(mechanism, Mapping):
        reset_obj = mechanism.get("reset_events")
        if isinstance(reset_obj, list):
            reset_events = reset_obj
    missing: list[str] = []
    for key in ("disable_time_us", "restore_time_us"):
        if _safe_float(realized.get(key)) is None:
            missing.append(f"hard_denial.{key}")
    for key in (
        "gps_status_before",
        "gps_status_during",
        "gps_status_after",
        "satellites_before",
        "satellites_during",
        "satellites_after",
    ):
        if _safe_float(realized.get(key)) is None:
            missing.append(f"hard_denial.{key}")
    reset_summary, reset_missing = _reset_event_summary(reset_events)
    missing.extend(reset_missing)

    if not isinstance(truth_vs_belief, Mapping) or truth_vs_belief.get("ok") is not True:
        full_gap = _empty_gap_summary("full_post_trigger_window")
        active_gap = _empty_gap_summary("active_segment_post_last_reset")
        missing.append("SIM/POS.truth_vs_belief")
    else:
        full_gap = _coerced_gap_summary(
            truth_vs_belief.get("full_window_gap_summary"),
            sample_scope="full_post_trigger_window",
        )
        active_gap = _coerced_gap_summary(
            truth_vs_belief.get("active_segment_gap_summary"),
            sample_scope="active_segment_post_last_reset",
        )
        if full_gap["sample_count"] == 0:
            missing.append("SIM/POS.full_window_gap_samples")
        if active_gap["sample_count"] == 0:
            missing.append("SIM/POS.active_segment_gap_samples")

    restore_time = _safe_float(realized.get("restore_time_us"))
    return {
        "status": "fail" if missing else "pass",
        "reason": "hard_denial_transient_incomplete" if missing else "ok",
        "fault_type": fault_type,
        "sample_scope": "full_post_trigger_window_and_active_segment",
        "denial": {
            "start_time_us": _safe_float(realized.get("disable_time_us")),
            "end_time_us": _safe_float(realized.get("restore_time_us")),
            "requested_duration_s": _safe_float(realized.get("requested_denial_duration_s")),
            "realized_duration_s": _safe_float(realized.get("realized_denial_duration_s")),
        },
        "restore_event": {
            "present": restore_time is not None,
            "time_us": restore_time,
        },
        "gps_quality": {
            "before": {
                "status": _safe_float(realized.get("gps_status_before")),
                "satellites": _safe_float(realized.get("satellites_before")),
            },
            "during": {
                "status": _safe_float(realized.get("gps_status_during")),
                "satellites": _safe_float(realized.get("satellites_during")),
            },
            "after": {
                "status": _safe_float(realized.get("gps_status_after")),
                "satellites": _safe_float(realized.get("satellites_after")),
            },
        },
        "reset_events": reset_summary,
        "full_window_gap_summary": full_gap,
        "active_segment_gap_summary": active_gap,
        "top_level_sample_labels": {
            "full_window_gap_summary": "full_post_trigger_window",
            "active_segment_gap_summary": "active_segment_post_last_reset",
            "classifier_truth_vs_belief_samples": "active_segment_post_last_reset",
        },
        "missing_evidence": missing,
    }


def _reset_event_summary(events: object) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(events, list) or not events:
        return (
            {
                "count": 0,
                "times_us": [],
                "north_offsets_m": [],
                "east_offsets_m": [],
                "delta_north_m": [],
                "delta_east_m": [],
                "details_complete": True,
            },
            [],
        )
    times: list[float] = []
    north: list[float] = []
    east: list[float] = []
    delta_north: list[float] = []
    delta_east: list[float] = []
    missing: list[str] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            missing.append(f"XKF4.reset_events[{index}]")
            continue
        time_us = _safe_float(event.get("time_us"))
        ofn = _safe_float(event.get("ofn_m"))
        ofe = _safe_float(event.get("ofe_m"))
        delta_n = _safe_float(event.get("delta_n_m"))
        delta_e = _safe_float(event.get("delta_e_m"))
        if time_us is None:
            missing.append(f"XKF4.reset_events[{index}].time_us")
        else:
            times.append(time_us)
        if ofn is None:
            missing.append(f"XKF4.reset_events[{index}].ofn_m")
        else:
            north.append(ofn)
        if ofe is None:
            missing.append(f"XKF4.reset_events[{index}].ofe_m")
        else:
            east.append(ofe)
        if delta_n is None:
            missing.append(f"XKF4.reset_events[{index}].delta_n_m")
        else:
            delta_north.append(delta_n)
        if delta_e is None:
            missing.append(f"XKF4.reset_events[{index}].delta_e_m")
        else:
            delta_east.append(delta_e)
    return (
        {
            "count": len(events),
            "times_us": times,
            "north_offsets_m": north,
            "east_offsets_m": east,
            "delta_north_m": delta_north,
            "delta_east_m": delta_east,
            "details_complete": not missing,
        },
        missing,
    )


def _gap_summary(samples: list[dict[str, Any]], *, sample_scope: str) -> dict[str, Any]:
    gaps = [
        _safe_float(sample.get("horizontal_gap_m"))
        for sample in samples
        if isinstance(sample, Mapping)
    ]
    times = [
        _safe_float(sample.get("time_us"))
        for sample in samples
        if isinstance(sample, Mapping)
    ]
    paired = [
        (gap, time)
        for gap, time in zip(gaps, times)
        if gap is not None and time is not None
    ]
    if not paired:
        return _empty_gap_summary(sample_scope)
    max_gap, max_time = max(paired, key=lambda item: item[0])
    first_gap, first_time = paired[0]
    last_gap, last_time = paired[-1]
    growth = None
    span_s = (last_time - first_time) / 1_000_000.0
    if span_s > 0.0:
        growth = (last_gap - first_gap) / span_s
    return {
        "sample_scope": sample_scope,
        "sample_count": len(paired),
        "max_horizontal_gap_m": max_gap,
        "max_gap_time_us": max_time,
        "start_gap_m": first_gap,
        "end_gap_m": last_gap,
        "gap_delta_m": last_gap - first_gap,
        "gap_growth_rate_mps": growth,
    }


def _coerced_gap_summary(value: object, *, sample_scope: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _empty_gap_summary(sample_scope)
    return {
        "sample_scope": str(value.get("sample_scope") or sample_scope),
        "sample_count": _safe_int(value.get("sample_count")) or 0,
        "max_horizontal_gap_m": _safe_float(value.get("max_horizontal_gap_m")),
        "max_gap_time_us": _safe_float(value.get("max_gap_time_us")),
        "start_gap_m": _safe_float(value.get("start_gap_m")),
        "end_gap_m": _safe_float(value.get("end_gap_m")),
        "gap_delta_m": _safe_float(value.get("gap_delta_m")),
        "gap_growth_rate_mps": _safe_float(value.get("gap_growth_rate_mps")),
    }


def _empty_gap_summary(sample_scope: str) -> dict[str, Any]:
    return {
        "sample_scope": sample_scope,
        "sample_count": 0,
        "max_horizontal_gap_m": None,
        "max_gap_time_us": None,
        "start_gap_m": None,
        "end_gap_m": None,
        "gap_delta_m": None,
        "gap_growth_rate_mps": None,
    }


def _attitude_altitude_artifact(
    *,
    source: str,
    altitude_source: str | None,
    attitude_source: str | None,
    altitude_samples: list[dict[str, Any]],
    attitude_samples: list[dict[str, Any]],
    evidence_quality: str,
    final_evidence_quality: bool,
    runtime_guard_quality: bool,
    reason: str,
    missing_evidence: list[str],
    unexpected_disarm: bool,
    comparison: dict[str, Any],
) -> dict[str, Any]:
    altitudes = [
        value
        for sample in altitude_samples
        if (value := _safe_float(sample.get("relative_alt_m"))) is not None
    ]
    min_alt = min(altitudes) if altitudes else None
    max_drawdown = 0.0
    running_max: float | None = None
    for altitude in altitudes:
        running_max = altitude if running_max is None else max(running_max, altitude)
        max_drawdown = max(max_drawdown, running_max - altitude)
    crossings = _attitude_altitude_crossings(
        altitude_loss_m=max_drawdown,
        attitude_samples=attitude_samples,
    )
    samples_complete = bool(altitude_samples and attitude_samples)
    status = "pass" if samples_complete and not missing_evidence else "fail"
    return {
        "status": status,
        "reason": reason if status == "fail" else "ok",
        "source": source,
        "altitude_source": altitude_source,
        "attitude_source": attitude_source,
        "sampling_limits": {
            "post_injection_only": True,
            "clock": (
                "TimeUS"
                if source == "BIN"
                else "mixed:TimeUS/arrival_monotonic_s"
                if source == "hybrid"
                else "arrival_monotonic_s"
            ),
            "max_abs_roll_deg": defaults.MAX_ABS_ROLL_DEG,
            "max_abs_pitch_deg": defaults.MAX_ABS_PITCH_DEG,
            "max_altitude_loss_m": defaults.MAX_ALTITUDE_LOSS_M,
            "bin_live_altitude_tolerance_m": defaults.BIN_LIVE_ALTITUDE_TOLERANCE_M,
            "bin_live_attitude_tolerance_deg": defaults.BIN_LIVE_ATTITUDE_TOLERANCE_DEG,
        },
        "evidence_quality": evidence_quality,
        "final_evidence_quality": final_evidence_quality and status == "pass",
        "runtime_guard_quality": runtime_guard_quality,
        "post_injection_min_alt_m": min_alt,
        "altitude_loss_m": max_drawdown,
        "altitude_samples": altitude_samples,
        "attitude_excursions": attitude_samples,
        "threshold_crossings": crossings,
        "unexpected_disarm": unexpected_disarm,
        "samples_complete": samples_complete,
        "missing_evidence": list(missing_evidence),
        "source_authority": {
            "altitude": altitude_source,
            "attitude": attitude_source,
            "comparison_to_live_guard": comparison,
        },
        "limits": {
            "max_abs_roll_deg": defaults.MAX_ABS_ROLL_DEG,
            "max_abs_pitch_deg": defaults.MAX_ABS_PITCH_DEG,
            "max_altitude_loss_m": defaults.MAX_ALTITUDE_LOSS_M,
        },
    }


def _attitude_altitude_crossings(
    *,
    altitude_loss_m: float,
    attitude_samples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    crossings: list[dict[str, Any]] = []
    for sample in attitude_samples:
        time_us = _safe_float(sample.get("time_us"))
        roll_deg = _safe_float(sample.get("roll_deg"))
        pitch_deg = _safe_float(sample.get("pitch_deg"))
        if roll_deg is not None and abs(roll_deg) > defaults.MAX_ABS_ROLL_DEG:
            crossings.append({
                "type": "roll",
                "time_us": time_us,
                "value_deg": roll_deg,
                "limit_deg": defaults.MAX_ABS_ROLL_DEG,
            })
        if pitch_deg is not None and abs(pitch_deg) > defaults.MAX_ABS_PITCH_DEG:
            crossings.append({
                "type": "pitch",
                "time_us": time_us,
                "value_deg": pitch_deg,
                "limit_deg": defaults.MAX_ABS_PITCH_DEG,
            })
    if altitude_loss_m > defaults.MAX_ALTITUDE_LOSS_M:
        crossings.append({
            "type": "altitude_loss",
            "value_m": altitude_loss_m,
            "limit_m": defaults.MAX_ALTITUDE_LOSS_M,
        })
    return crossings


def _bin_altitude_samples(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for record in records:
        record_type = _record_type(record)
        source_field: str | None = None
        value: float | None = None
        if record_type == "POS":
            value = _safe_float(record.get("RelHomeAlt"))
            if value is not None:
                source_field = "POS.RelHomeAlt"
        elif record_type == "CTUN":
            value = _safe_float(record.get("Alt"))
            if value is not None:
                source_field = "CTUN.Alt"
        if value is None or source_field is None:
            continue
        time_us = _record_time_us(record)
        if time_us is None:
            continue
        samples.append({
            "time_us": time_us,
            "relative_alt_m": value,
            "source": source_field,
        })
    samples.sort(key=lambda item: item["time_us"])
    return samples


def _bin_attitude_samples(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for record in records:
        if _record_type(record) != "ATT":
            continue
        time_us = _record_time_us(record)
        if time_us is None:
            continue
        roll_deg = _safe_float(record.get("Roll"))
        pitch_deg = _safe_float(record.get("Pitch"))
        source = "ATT.Roll/Pitch"
        if roll_deg is None:
            roll_rad = _safe_float(record.get("roll_rad"))
            if roll_rad is not None:
                roll_deg = math.degrees(roll_rad)
                source = "ATT.roll_rad/pitch_rad"
        if pitch_deg is None:
            pitch_rad = _safe_float(record.get("pitch_rad"))
            if pitch_rad is not None:
                pitch_deg = math.degrees(pitch_rad)
                source = "ATT.roll_rad/pitch_rad"
        if roll_deg is None or pitch_deg is None:
            continue
        samples.append({
            "time_us": time_us,
            "roll_deg": roll_deg,
            "pitch_deg": pitch_deg,
            "source": source,
        })
    samples.sort(key=lambda item: item["time_us"])
    return samples


def _sample_source(samples: list[dict[str, Any]]) -> str | None:
    sources = sorted(
        {
            str(sample.get("source"))
            for sample in samples
            if isinstance(sample.get("source"), str)
        }
    )
    if not sources:
        return None
    if all(source.startswith("live_telemetry:") for source in sources):
        return ",".join(sources)
    if any(source.startswith("live_telemetry:") for source in sources):
        return "hybrid:" + ",".join(sources)
    return "BIN:" + ",".join(sources)


def _live_altitude_samples(
    live_artifact: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(live_artifact, Mapping):
        return []
    raw = live_artifact.get("altitude_samples")
    if not isinstance(raw, list):
        return []
    samples: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        altitude = _safe_float(item.get("relative_alt_m"))
        if altitude is None:
            continue
        samples.append({
            "arrival_monotonic_s": _safe_float(item.get("arrival_monotonic_s")),
            "relative_alt_m": altitude,
            "source": "live_telemetry:GLOBAL_POSITION_INT.relative_alt_mm",
        })
    return samples


def _live_attitude_samples(
    live_artifact: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(live_artifact, Mapping):
        return []
    raw = live_artifact.get("attitude_excursions")
    if not isinstance(raw, list):
        return []
    samples: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        roll_deg = _safe_float(item.get("roll_deg"))
        pitch_deg = _safe_float(item.get("pitch_deg"))
        if roll_deg is None and (roll_rad := _safe_float(item.get("roll_rad"))) is not None:
            roll_deg = math.degrees(roll_rad)
        if pitch_deg is None and (pitch_rad := _safe_float(item.get("pitch_rad"))) is not None:
            pitch_deg = math.degrees(pitch_rad)
        if roll_deg is None or pitch_deg is None:
            continue
        samples.append({
            "arrival_monotonic_s": _safe_float(item.get("arrival_monotonic_s")),
            "roll_deg": roll_deg,
            "pitch_deg": pitch_deg,
            "source": "live_telemetry:ATTITUDE.roll_rad/pitch_rad",
        })
    return samples


def _live_bin_comparison(
    altitude_samples: list[dict[str, Any]] | None,
    attitude_samples: list[dict[str, Any]] | None,
    live_artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(live_artifact, Mapping) or not _live_has_envelope_samples(live_artifact):
        return {
            "status": "not_available",
            "reason": "live_runtime_guard_not_available",
            "mismatches": [],
        }
    mismatches: list[str] = []
    live_min_alt = _safe_float(live_artifact.get("post_injection_min_alt_m"))
    live_alt_loss = _safe_float(live_artifact.get("altitude_loss_m"))
    bin_min_alt = _min_altitude(altitude_samples or [])
    bin_alt_loss = _altitude_loss(altitude_samples or [])
    live_attitude = _max_abs_attitude_from_live(live_artifact)
    bin_attitude = _max_abs_attitude(attitude_samples or [])
    if (
        live_min_alt is not None
        and bin_min_alt is not None
        and abs(live_min_alt - bin_min_alt) > defaults.BIN_LIVE_ALTITUDE_TOLERANCE_M
    ):
        mismatches.append("altitude_min_live_bin_mismatch")
    if (
        live_alt_loss is not None
        and bin_alt_loss is not None
        and abs(live_alt_loss - bin_alt_loss) > defaults.BIN_LIVE_ALTITUDE_TOLERANCE_M
    ):
        mismatches.append("altitude_loss_live_bin_mismatch")
    for axis in ("roll", "pitch"):
        live_value = live_attitude.get(axis)
        bin_value = bin_attitude.get(axis)
        if (
            live_value is not None
            and bin_value is not None
            and abs(live_value - bin_value) > defaults.BIN_LIVE_ATTITUDE_TOLERANCE_DEG
        ):
            mismatches.append(f"{axis}_live_bin_mismatch")
    return {
        "status": "mismatch" if mismatches else "consistent",
        "reason": "live_bin_mismatch" if mismatches else "within_tolerance",
        "mismatches": mismatches,
        "tolerances": {
            "altitude_m": defaults.BIN_LIVE_ALTITUDE_TOLERANCE_M,
            "attitude_deg": defaults.BIN_LIVE_ATTITUDE_TOLERANCE_DEG,
        },
        "live": {
            "min_alt_m": live_min_alt,
            "altitude_loss_m": live_alt_loss,
            "max_abs_roll_deg": live_attitude.get("roll"),
            "max_abs_pitch_deg": live_attitude.get("pitch"),
        },
        "bin": {
            "min_alt_m": bin_min_alt,
            "altitude_loss_m": bin_alt_loss,
            "max_abs_roll_deg": bin_attitude.get("roll"),
            "max_abs_pitch_deg": bin_attitude.get("pitch"),
        },
    }


def _live_has_envelope_samples(live_artifact: Mapping[str, Any] | None) -> bool:
    return bool(
        isinstance(live_artifact, Mapping)
        and live_artifact.get("samples_complete") is True
    )


def _live_unexpected_disarm(live_artifact: Mapping[str, Any] | None) -> bool:
    return bool(
        isinstance(live_artifact, Mapping)
        and live_artifact.get("unexpected_disarm") is True
    )


def _min_altitude(samples: list[dict[str, Any]]) -> float | None:
    values = [
        value
        for sample in samples
        if (value := _safe_float(sample.get("relative_alt_m"))) is not None
    ]
    return min(values) if values else None


def _altitude_loss(samples: list[dict[str, Any]]) -> float | None:
    values = [
        value
        for sample in samples
        if (value := _safe_float(sample.get("relative_alt_m"))) is not None
    ]
    if not values:
        return None
    running_max: float | None = None
    loss = 0.0
    for value in values:
        running_max = value if running_max is None else max(running_max, value)
        loss = max(loss, running_max - value)
    return loss


def _max_abs_attitude(samples: list[dict[str, Any]]) -> dict[str, float | None]:
    rolls = [
        abs(value)
        for sample in samples
        if (value := _safe_float(sample.get("roll_deg"))) is not None
    ]
    pitches = [
        abs(value)
        for sample in samples
        if (value := _safe_float(sample.get("pitch_deg"))) is not None
    ]
    return {
        "roll": max(rolls) if rolls else None,
        "pitch": max(pitches) if pitches else None,
    }


def _max_abs_attitude_from_live(
    live_artifact: Mapping[str, Any],
) -> dict[str, float | None]:
    samples = live_artifact.get("attitude_excursions")
    if not isinstance(samples, list):
        return {"roll": None, "pitch": None}
    normalized: list[dict[str, Any]] = []
    for sample in samples:
        if not isinstance(sample, Mapping):
            continue
        roll_deg = _safe_float(sample.get("roll_deg"))
        pitch_deg = _safe_float(sample.get("pitch_deg"))
        if roll_deg is None and (roll_rad := _safe_float(sample.get("roll_rad"))) is not None:
            roll_deg = math.degrees(roll_rad)
        if pitch_deg is None and (pitch_rad := _safe_float(sample.get("pitch_rad"))) is not None:
            pitch_deg = math.degrees(pitch_rad)
        normalized.append({"roll_deg": roll_deg, "pitch_deg": pitch_deg})
    return _max_abs_attitude(normalized)


def _baseline_window(
    records: list[dict[str, Any]],
    anchor_us: float,
    *,
    source_contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    baseline = [
        record for record in records
        if (_record_time_us(record) is not None)
        and float(_record_time_us(record) or 0.0) < anchor_us
    ]
    times = _record_times(baseline)
    missing: list[str] = []
    try:
        gps_samples = _gps_quality_samples(baseline)
    except ValueError:
        return _window_fail("pre_trigger_baseline", "malformed_gps_record", ["GPS"])
    mechanism = extract_xkf4_mechanism(baseline)
    truth = truth_vs_belief_from_decoded_records(baseline)
    healthy_gps = bool(gps_samples and _gps_quality_healthy(_best_gps_sample(gps_samples) or {}))
    ratios = [
        _safe_float(sample.get("pos_test_ratio"))
        for sample in mechanism.samples
        if isinstance(sample, Mapping)
    ]
    ratios = [ratio for ratio in ratios if ratio is not None]
    gaps = [
        _safe_float(sample.get("horizontal_gap_m"))
        for sample in truth.get("samples", [])
        if isinstance(sample, Mapping)
    ]
    gaps = [gap for gap in gaps if gap is not None]
    source_ok = isinstance(source_contract, Mapping) and source_contract.get("ok") is True
    if not gps_samples or not healthy_gps:
        missing.append("GPS.pre_trigger_healthy")
    if not mechanism.ok or not ratios:
        missing.append("XKF4.pre_trigger_primary_core")
    if not truth.get("ok") or not gaps:
        missing.append("SIM/POS.pre_trigger_truth_belief")
    if not source_ok:
        missing.append("source_contract.pre_injection")
    metrics = {
        "gps_sample_count": len(gps_samples),
        "healthy_gps": healthy_gps,
        "max_pos_test_ratio": max(ratios) if ratios else None,
        "max_truth_belief_gap_m": max(gaps) if gaps else None,
        "source_contract_ok": source_ok,
        "missing_evidence": missing,
    }
    if missing:
        return _window(
            name="pre_trigger_baseline",
            start_time_us=times[0] if times else None,
            end_time_us=times[-1] if times else None,
            source="hybrid",
            status="fail",
            summary="missing pre-trigger normal-state evidence",
            metrics=metrics,
            evidence_refs=["GPS", "XKF4", "SIM", "POS", "source_contract.json"],
        )
    status = "pass" if max(ratios) < 1.0 and max(gaps) <= NOMINAL_MAX_TRUTH_BELIEF_GAP_M else "fail"
    if status == "fail":
        metrics["missing_evidence"] = ["pre_trigger_normal_state"]
    return _window(
        name="pre_trigger_baseline",
        start_time_us=times[0],
        end_time_us=times[-1],
        source="hybrid",
        status=status,
        summary=(
            "aircraft GPS/EKF baseline is normal before trigger"
            if status == "pass"
            else "pre-trigger GPS/EKF baseline is outside nominal bounds"
        ),
        metrics=metrics,
        evidence_refs=["GPS.Status/NSats", "XKF4.SP/PI", "SIM/POS", "source_contract.json"],
    )


def _trigger_window(
    anchor_us: float,
    *,
    trigger_event: Mapping[str, Any] | None,
) -> dict[str, Any]:
    event = trigger_event if isinstance(trigger_event, Mapping) else {}
    missing: list[str] = []
    warnings: list[str] = []
    seq = _safe_int(event.get("seq"))
    if seq != 4:
        missing.append("trigger.seq4")
    if event.get("mode") != "AUTO":
        missing.append("trigger.mode_AUTO")
    if event.get("armed") is not True:
        missing.append("trigger.armed")
    if event.get("heartbeat_fresh") is not True:
        if seq == 4 and event.get("mode") == "AUTO" and event.get("armed") is True:
            warnings.append("trigger.heartbeat_fresh")
        else:
            missing.append("trigger.heartbeat_fresh")
    if event.get("simstate_fresh") is not True:
        missing.append("trigger.simstate_fresh")
    for key in ("trigger_vehicle_time_boot_ms", "trigger_wall_monotonic_s", "trigger_latitude_deg"):
        if _safe_float(event.get(key)) is None:
            missing.append(f"trigger.{key}")
    if not _non_empty_string(event.get("trigger_wall_time_utc")):
        missing.append("trigger.trigger_wall_time_utc")
    metrics = {
        "seq": seq,
        "mode": event.get("mode"),
        "armed": event.get("armed"),
        "heartbeat_age_s": _safe_float(event.get("heartbeat_age_s")),
        "heartbeat_fresh": event.get("heartbeat_fresh"),
        "simstate_age_s": _safe_float(event.get("simstate_age_s")),
        "simstate_fresh": event.get("simstate_fresh"),
        "trigger_vehicle_time_boot_ms": _safe_float(event.get("trigger_vehicle_time_boot_ms")),
        "trigger_wall_monotonic_s": _safe_float(event.get("trigger_wall_monotonic_s")),
        "trigger_wall_time_utc": event.get("trigger_wall_time_utc"),
        "trigger_position": {
            "latitude_deg": _safe_float(event.get("trigger_latitude_deg")),
            "longitude_deg": _safe_float(event.get("trigger_longitude_deg")),
        },
        "nearest_mission_sequence": seq,
        "mission_leg": "seq4_outbound_measurement_start",
        "missing_evidence": missing,
        "warnings": warnings,
    }
    return _window(
        name="trigger",
        start_time_us=anchor_us,
        end_time_us=anchor_us,
        source="live_telemetry",
        status="fail" if missing else "pass",
        summary=(
            "authorized fresh armed/AUTO seq-4 trigger"
            if not missing and not warnings
            else "authorized armed/AUTO seq-4 trigger with stale heartbeat warning"
            if not missing
            else "trigger authorization evidence is incomplete"
        ),
        metrics=metrics,
        evidence_refs=["MISSION_CURRENT", "HEARTBEAT", "SIMSTATE", "time_boot_ms"],
    )


def _injection_window(
    anchor_us: float,
    *,
    records: list[dict[str, Any]],
    injection_execution: Mapping[str, Any] | None,
) -> dict[str, Any]:
    execution: Mapping[str, Any] = (
        injection_execution if isinstance(injection_execution, Mapping) else {}
    )
    plan_obj = execution.get("plan")
    plan: Mapping[str, Any] = (
        cast(Mapping[str, Any], plan_obj) if isinstance(plan_obj, Mapping) else {}
    )
    payload_obj = plan.get("injection_payload")
    payload: Mapping[str, Any] = (
        cast(Mapping[str, Any], payload_obj)
        if isinstance(payload_obj, Mapping)
        else {}
    )
    result_obj = execution.get("parameter_result")
    result: Mapping[str, Any] | None = (
        cast(Mapping[str, Any], result_obj)
        if isinstance(result_obj, Mapping)
        else None
    )
    transitions = _matching_payload_transitions(records, anchor_us, payload)
    authorized = plan.get("execution_authorized") is True
    success = execution.get("success") is True
    zero_write_authorization_failure = bool(
        plan.get("requires_trigger_authorization") is True
        and not authorized
        and not result
    )
    missing: list[str] = []
    if not execution:
        missing.append("gps_injection.live_execution")
    elif zero_write_authorization_failure:
        pass
    elif not success:
        missing.append("gps_injection.success")
    elif payload and not transitions:
        missing.append("PARM.injection_readback_transition")
    elif payload and result is None:
        missing.append("gps_injection.parameter_result")
    metrics = {
        "requested_payload": dict(payload),
        "execution_authorized": authorized,
        "execution_success": success,
        "reason": execution.get("reason"),
        "observed_readbacks": result,
        "observed_parameter_transitions": transitions,
        "zero_writes": bool(not payload or zero_write_authorization_failure),
        "zero_writes_reason": (
            "trigger_authorization_failed"
            if zero_write_authorization_failure
            else ("nominal_no_write_case" if not payload else None)
        ),
        "missing_evidence": missing,
    }
    end_us = max([anchor_us, *[item["time_us"] for item in transitions]])
    return _window(
        name="injection",
        start_time_us=anchor_us,
        end_time_us=end_us,
        source="hybrid",
        status="fail" if missing else "pass",
        summary=(
            "injection/no-write execution and readback are accounted for"
            if not missing
            else "injection evidence is incomplete"
        ),
        metrics=metrics,
        evidence_refs=["gps_injection.json", "PARM"],
    )


def _fault_active_window(
    records: list[dict[str, Any]],
    anchor_us: float,
    *,
    fault_type: str,
    fault_recipe: Mapping[str, Any] | None,
    trigger_event: Mapping[str, Any] | None,
    stimulus_fidelity: Mapping[str, Any] | None,
) -> dict[str, Any]:
    realized: Mapping[str, Any] = {}
    if isinstance(stimulus_fidelity, Mapping):
        realized_obj = stimulus_fidelity.get("realized")
        if isinstance(realized_obj, Mapping):
            realized = cast(Mapping[str, Any], realized_obj)
    missing: list[str] = []
    metrics: dict[str, Any] = {
        "stimulus_fidelity_status": (
            stimulus_fidelity.get("status")
            if isinstance(stimulus_fidelity, Mapping)
            else None
        ),
        "stimulus_fidelity_reason": (
            stimulus_fidelity.get("reason")
            if isinstance(stimulus_fidelity, Mapping)
            else None
        ),
        "missing_evidence": missing,
    }
    start_us = anchor_us
    end_us = _max_record_time(records, min_time_us=anchor_us) or anchor_us
    evidence_refs = ["stimulus_fidelity.json"]
    if fault_type == "slow_drift":
        samples = realized.get("offset_samples")
        if not isinstance(samples, list) or len(samples) < 2:
            missing.append("PARM.SIM_GPS1_GLTCH_X/Y.offset_samples")
        else:
            offsets = [
                _safe_float(sample.get("axis_offset_m"))
                for sample in samples
                if isinstance(sample, Mapping)
            ]
            offsets = [value for value in offsets if value is not None]
            if len(offsets) < 2:
                missing.append("slow_drift.offset_values")
            metrics.update({
                "requested_drift_rate_mps": realized.get("requested_drift_rate_mps"),
                "realized_drift_rate_mps": realized.get("realized_drift_rate_mps"),
                "monotonic_drift_growth": _monotonic_values(offsets),
                "start_offset_m": offsets[0] if offsets else None,
                "end_offset_m": offsets[-1] if offsets else None,
                "offset_sample_count": len(offsets),
            })
            if offsets and not metrics["monotonic_drift_growth"]:
                missing.append("slow_drift.monotonic_growth")
        evidence_refs.append("PARM.SIM_GPS1_GLTCH_X/Y")
    elif fault_type == "step_glitch":
        requested_offset_m = _safe_float(realized.get("requested_offset_m"))
        realized_offset_m = _safe_float(realized.get("realized_offset_m"))
        offset_error_m = _safe_float(realized.get("offset_error_m"))
        metrics.update({
            "requested_offset_m": requested_offset_m,
            "realized_offset_m": realized_offset_m,
            "offset_error_m": offset_error_m,
            "axis": realized.get("axis"),
            "transition_time_us": realized.get("transition_time_us"),
        })
        if realized_offset_m is None:
            missing.append("step_glitch.realized_offset_m")
        if requested_offset_m is None:
            missing.append("step_glitch.requested_offset_m")
        evidence_refs.append("PARM.SIM_GPS1_GLTCH_X/Y")
    elif fault_type == "hard_denial":
        required = ("disable_time_us", "restore_time_us", "gps_status_during", "gps_status_after")
        for key in required:
            if _safe_float(realized.get(key)) is None:
                missing.append(f"hard_denial.{key}")
        start_us = _safe_float(realized.get("disable_time_us")) or anchor_us
        end_us = _safe_float(realized.get("restore_time_us")) or end_us
        metrics.update({
            "requested_denial_duration_s": realized.get("requested_denial_duration_s"),
            "realized_denial_duration_s": realized.get("realized_denial_duration_s"),
            "gps_status_before": realized.get("gps_status_before"),
            "gps_status_during": realized.get("gps_status_during"),
            "gps_status_after": realized.get("gps_status_after"),
            "satellites_during": realized.get("satellites_during"),
        })
        evidence_refs.extend(["PARM.SIM_GPS1_ENABLE", "GPS.Status", "GPS.NSats"])
    elif fault_type == "nominal":
        metrics.update({
            "no_fault_transition": (
                realized.get("post_trigger_fault_parameter_transitions") == []
            ),
            "max_truth_belief_gap_m": realized.get("max_truth_belief_gap_m"),
            "unhealthy_gps_sample_count": realized.get("unhealthy_gps_sample_count"),
        })
        if metrics["no_fault_transition"] is not True:
            missing.append("nominal.no_fault_transition")
        evidence_refs.extend(["PARM", "GPS", "SIM/POS"])
    else:
        missing.append("fault_type.supported")
    if not isinstance(stimulus_fidelity, Mapping):
        missing.append("stimulus_fidelity.artifact")
    elif stimulus_fidelity.get("status") != "pass":
        reason = str(stimulus_fidelity.get("reason") or "unknown")
        missing.append(f"stimulus_fidelity.{reason}")
        for item in stimulus_fidelity.get("missing_evidence", []):
            missing.append(str(item))
    return _window(
        name="fault_active",
        start_time_us=start_us,
        end_time_us=end_us,
        source="BIN",
        status="fail" if missing else "pass",
        summary=(
            "case-specific physical fault evidence is active"
            if not missing
            else "case-specific physical fault evidence is incomplete"
        ),
        metrics=metrics,
        evidence_refs=evidence_refs,
    )


def _ekf_response_window(
    anchor_us: float,
    *,
    mechanism: Mapping[str, Any] | None,
    terminal_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    mech: Mapping[str, Any] = mechanism if isinstance(mechanism, Mapping) else {}
    samples_obj = mech.get("samples")
    samples: list[Any] = samples_obj if isinstance(samples_obj, list) else []
    reset_obj = mech.get("reset_events")
    reset_events: list[Any] = reset_obj if isinstance(reset_obj, list) else []
    ratios = [
        _safe_float(sample.get("pos_test_ratio"))
        for sample in samples
        if isinstance(sample, Mapping)
    ]
    ratios = [ratio for ratio in ratios if ratio is not None]
    times = [
        _safe_float(sample.get("time_us"))
        for sample in samples
        if isinstance(sample, Mapping)
    ]
    times = [value for value in times if value is not None]
    missing: list[str] = []
    if mech.get("ok") is not True:
        missing.append("XKF4.primary_core")
    if not ratios:
        missing.append("XKF4.posTestRatio")
    metrics = {
        "primary_core": mech.get("primary_core"),
        "sample_count": len(samples),
        "max_pos_test_ratio": max(ratios) if ratios else None,
        "gps_position_rejected": bool(ratios and max(ratios) >= 1.0),
        "pos_timeout": any(
            sample.get("pos_timeout") is True
            for sample in samples
            if isinstance(sample, Mapping)
        ),
        "reset_events": list(reset_events),
        "reset_event_count": len(reset_events),
        "mode_or_failsafe_context": {
            "stop_reason": (
                terminal_context.get("stop_reason")
                if isinstance(terminal_context, Mapping)
                else None
            ),
            "auto_to_rtl_transition_seq": (
                terminal_context.get("auto_to_rtl_transition_seq")
                if isinstance(terminal_context, Mapping)
                else None
            ),
        },
        "missing_evidence": missing,
    }
    return _window(
        name="ekf_response",
        start_time_us=min(times) if times else anchor_us,
        end_time_us=max(times) if times else anchor_us,
        source="BIN",
        status="fail" if missing else "pass",
        summary=(
            "EKF primary-core response is captured"
            if not missing
            else "EKF response evidence is incomplete"
        ),
        metrics=metrics,
        evidence_refs=["XKF4.SP/PI/TS/OFN/OFE", "mode_timeline.json"],
    )


def _recovery_or_continuation_window(
    records: list[dict[str, Any]],
    anchor_us: float,
    *,
    fault_type: str,
    stimulus_fidelity: Mapping[str, Any] | None,
    mechanism: Mapping[str, Any] | None,
    truth_vs_belief: Mapping[str, Any] | None,
) -> dict[str, Any]:
    realized: Mapping[str, Any] = {}
    if isinstance(stimulus_fidelity, Mapping):
        realized_obj = stimulus_fidelity.get("realized")
        if isinstance(realized_obj, Mapping):
            realized = cast(Mapping[str, Any], realized_obj)
    reset_events: list[Any] = []
    if isinstance(mechanism, Mapping):
        reset_obj = mechanism.get("reset_events")
        if isinstance(reset_obj, list):
            reset_events = reset_obj
    truth_samples: list[Any] = []
    full_gap_summary = _empty_gap_summary("full_post_trigger_window")
    active_gap_summary = _empty_gap_summary("active_segment_post_last_reset")
    if isinstance(truth_vs_belief, Mapping):
        truth_obj = truth_vs_belief.get("samples")
        if isinstance(truth_obj, list):
            truth_samples = truth_obj
        full_gap_summary = _coerced_gap_summary(
            truth_vs_belief.get("full_window_gap_summary"),
            sample_scope="full_post_trigger_window",
        )
        active_gap_summary = _coerced_gap_summary(
            truth_vs_belief.get("active_segment_gap_summary"),
            sample_scope="active_segment_post_last_reset",
        )
    gaps = [
        _safe_float(sample.get("horizontal_gap_m"))
        for sample in truth_samples
        if isinstance(sample, Mapping)
    ]
    gaps = [gap for gap in gaps if gap is not None]
    missing: list[str] = []
    if len(gaps) < 2:
        missing.append("SIM/POS.continuation_gap_samples")
    mode = "nominal_stable_behavior"
    if fault_type == "hard_denial":
        mode = "hard_denial_recovery"
        if _safe_float(realized.get("restore_time_us")) is None:
            missing.append("hard_denial.restore_event")
    elif fault_type == "slow_drift":
        mode = "slow_drift_continuation"
        full_sample_count = _safe_int(full_gap_summary.get("sample_count")) or 0
        start_gap = _safe_float(full_gap_summary.get("start_gap_m"))
        max_gap = _safe_float(full_gap_summary.get("max_horizontal_gap_m"))
        full_window_growth = (
            (max_gap - start_gap)
            if max_gap is not None and start_gap is not None
            else None
        )
        if full_sample_count >= 2:
            if full_window_growth is None or full_window_growth <= 0.0:
                missing.append("slow_drift.continued_gap_growth")
        elif len(gaps) >= 2 and gaps[-1] <= gaps[0]:
            missing.append("slow_drift.continued_gap_growth")
    elif fault_type == "step_glitch":
        mode = "step_glitch_continuation"
        if len(gaps) < 2:
            missing.append("SIM/POS.step_glitch_gap_samples")
    elif fault_type == "nominal":
        if gaps and max(gaps) > NOMINAL_MAX_TRUTH_BELIEF_GAP_M:
            missing.append("nominal.stable_gap")
        if reset_events:
            missing.append("nominal.no_reset_event")
    else:
        missing.append("fault_type.supported")
    metrics = {
        "mode": mode,
        "start_gap_m": gaps[0] if gaps else None,
        "end_gap_m": gaps[-1] if gaps else None,
        "gap_delta_m": (gaps[-1] - gaps[0]) if len(gaps) >= 2 else None,
        "active_segment_gap_summary": active_gap_summary,
        "full_window_gap_summary": full_gap_summary,
        "reset_events": list(reset_events),
        "restore_time_us": realized.get("restore_time_us"),
        "missing_evidence": missing,
    }
    start_us = anchor_us
    if fault_type == "hard_denial":
        start_us = _safe_float(realized.get("restore_time_us")) or anchor_us
    end_us = _max_record_time(records, min_time_us=start_us) or start_us
    return _window(
        name="recovery_or_continuation",
        start_time_us=start_us,
        end_time_us=end_us,
        source="BIN",
        status="fail" if missing else "pass",
        summary=(
            "post-fault recovery/continuation behavior is distinguished"
            if not missing
            else "post-fault recovery/continuation evidence is incomplete"
        ),
        metrics=metrics,
        evidence_refs=["SIM/POS", "XKF4", "PARM/GPS"],
    )


def _terminal_window(
    records: list[dict[str, Any]],
    anchor_us: float,
    *,
    terminal_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    context: Mapping[str, Any] = (
        terminal_context if isinstance(terminal_context, Mapping) else {}
    )
    missing: list[str] = []
    cleanup_obj = context.get("cleanup_result")
    cleanup: Mapping[str, Any] = (
        cast(Mapping[str, Any], cleanup_obj)
        if isinstance(cleanup_obj, Mapping)
        else {}
    )
    if context.get("terminal_state_reached") is not True:
        missing.append("terminal_state_reached")
    if cleanup.get("ok") is not True:
        missing.append("cleanup.ok")
    if context.get("raw_bin_archived") is not True:
        missing.append("raw_log.archived_bin")
    if context.get("required_json_artifacts_present") is not True:
        missing.append("required_json_artifacts")
    metrics = {
        "mission_complete": context.get("mission_complete"),
        "stop_reason": context.get("stop_reason"),
        "max_seq_reached": context.get("max_seq_reached"),
        "auto_to_rtl_transition_seq": context.get("auto_to_rtl_transition_seq"),
        "cleanup_ok": cleanup.get("ok"),
        "raw_log_path": context.get("raw_log_path"),
        "raw_bin_archived": context.get("raw_bin_archived"),
        "required_json_artifacts": context.get("required_json_artifacts", []),
        "required_json_artifacts_present": context.get("required_json_artifacts_present"),
        "missing_evidence": missing,
    }
    end_us = _max_record_time(records, min_time_us=anchor_us) or anchor_us
    return _window(
        name="terminal",
        start_time_us=end_us,
        end_time_us=end_us,
        source="hybrid",
        status="fail" if missing else "pass",
        summary=(
            "terminal mission, cleanup, raw BIN, and artifact state are reviewable"
            if not missing
            else "terminal state evidence is incomplete"
        ),
        metrics=metrics,
        evidence_refs=["mode_timeline.json", "cleanup_result", "raw_log", "required_artifacts"],
    )


def _window_fail(name: str, reason: str, missing_evidence: list[str]) -> dict[str, Any]:
    return _window(
        name=name,
        start_time_us=None,
        end_time_us=None,
        source="BIN",
        status="fail",
        summary=reason,
        metrics={"missing_evidence": list(missing_evidence)},
        evidence_refs=[],
    )


def _window(
    *,
    name: str,
    start_time_us: float | None,
    end_time_us: float | None,
    source: str,
    status: str,
    summary: str,
    metrics: dict[str, Any],
    evidence_refs: list[str],
) -> dict[str, Any]:
    start = _safe_float(start_time_us)
    end = _safe_float(end_time_us)
    duration = (
        max(0.0, (end - start) / 1_000_000.0)
        if start is not None and end is not None
        else None
    )
    return {
        "name": name,
        "start_time_us": start,
        "end_time_us": end,
        "duration_s": duration,
        "source": source,
        "status": status,
        "summary": summary,
        "metrics": metrics,
        "evidence_refs": list(evidence_refs),
    }


def _record_times(records: Iterable[Mapping[str, Any]]) -> list[float]:
    return sorted(
        time_us
        for record in records
        if (time_us := _record_time_us(record)) is not None
    )


def _max_record_time(
    records: Iterable[Mapping[str, Any]],
    *,
    min_time_us: float,
) -> float | None:
    times = [
        time_us
        for record in records
        if (time_us := _record_time_us(record)) is not None
        and time_us >= min_time_us
    ]
    return max(times) if times else None


def _matching_payload_transitions(
    records: Iterable[Mapping[str, Any]],
    anchor_us: float,
    payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    for record in records:
        if _record_type(record) != "PARM":
            continue
        time_us = _record_time_us(record)
        if time_us is None or time_us < anchor_us:
            continue
        name = str(record.get("Name", record.get("name", ""))).rstrip("\x00")
        if name not in payload:
            continue
        observed = _safe_float(record.get("Value", record.get("value")))
        expected = _safe_float(payload.get(name))
        if observed is None or expected is None:
            continue
        if math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-6):
            transitions.append({
                "time_us": time_us,
                "name": name,
                "value": observed,
            })
    transitions.sort(key=lambda item: (item["time_us"], item["name"]))
    return transitions


def _monotonic_values(values: Iterable[float]) -> bool:
    previous: float | None = None
    for value in values:
        if previous is not None and value + 1e-9 < previous:
            return False
        previous = value
    return previous is not None


def _nominal_stimulus_fidelity(
    records: list[dict[str, Any]],
    *,
    anchor_us: float,
    base: dict[str, Any],
    truth_vs_belief: Mapping[str, Any] | None,
    mechanism: Mapping[str, Any] | None,
) -> dict[str, Any]:
    try:
        post_fault_params = _fault_param_transitions(records, min_time_us=anchor_us)
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["PARM"])
    try:
        gps_samples = _gps_quality_samples(records, min_time_us=anchor_us)
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["GPS"])
    missing: list[str] = []
    if not gps_samples:
        missing.append("GPS")
    if not isinstance(truth_vs_belief, Mapping) or truth_vs_belief.get("ok") is not True:
        missing.append("truth_vs_belief")
    if not isinstance(mechanism, Mapping) or mechanism.get("ok") is not True:
        missing.append("XKF4")
    if missing:
        return _stimulus_fail(base, "missing_nominal_fidelity_evidence", missing)
    assert isinstance(truth_vs_belief, Mapping)
    assert isinstance(mechanism, Mapping)

    gaps = [
        _safe_float(sample.get("horizontal_gap_m"))
        for sample in truth_vs_belief.get("samples", [])
        if isinstance(sample, Mapping)
    ]
    gaps = [gap for gap in gaps if gap is not None]
    if not gaps:
        return _stimulus_fail(base, "missing_nominal_truth_belief_gap", ["truth_vs_belief.horizontal_gap_m"])

    unhealthy_gps = [
        sample for sample in gps_samples
        if not _gps_quality_healthy(sample)
    ]
    reset_events = mechanism.get("reset_events")
    if post_fault_params:
        return _stimulus_fail(
            _with_realized(
                base,
                {
                    "post_trigger_fault_parameter_transitions": post_fault_params,
                    "max_truth_belief_gap_m": max(gaps),
                    "gps_sample_count": len(gps_samples),
                    "unhealthy_gps_sample_count": len(unhealthy_gps),
                    "reset_event_count": len(reset_events) if isinstance(reset_events, list) else None,
                },
            ),
            "unexpected_post_trigger_fault_parameter_transition",
            [],
        )
    if unhealthy_gps:
        return _stimulus_fail(
            _with_realized(
                base,
                {
                    "post_trigger_fault_parameter_transitions": [],
                    "max_truth_belief_gap_m": max(gaps),
                    "gps_sample_count": len(gps_samples),
                    "unhealthy_gps_sample_count": len(unhealthy_gps),
                    "worst_gps_sample": unhealthy_gps[0],
                },
            ),
            "unexpected_gps_degradation",
            [],
        )
    if max(gaps) > NOMINAL_MAX_TRUTH_BELIEF_GAP_M:
        return _stimulus_fail(
            _with_realized(
                base,
                {
                    "post_trigger_fault_parameter_transitions": [],
                    "max_truth_belief_gap_m": max(gaps),
                    "gps_sample_count": len(gps_samples),
                    "unhealthy_gps_sample_count": 0,
                },
            ),
            "nominal_truth_belief_gap_exceeded",
            [],
        )
    if isinstance(reset_events, list) and reset_events:
        return _stimulus_fail(
            _with_realized(
                base,
                {
                    "post_trigger_fault_parameter_transitions": [],
                    "max_truth_belief_gap_m": max(gaps),
                    "gps_sample_count": len(gps_samples),
                    "unhealthy_gps_sample_count": 0,
                    "reset_event_count": len(reset_events),
                },
            ),
            "unexpected_ekf_reset_event",
            [],
        )
    return _stimulus_pass(
        _with_realized(
            base,
            {
                "post_trigger_fault_parameter_transitions": [],
                "max_truth_belief_gap_m": max(gaps),
                "gps_sample_count": len(gps_samples),
                "unhealthy_gps_sample_count": 0,
                "reset_event_count": 0,
            },
        ),
        "nominal_no_fault_condition_preserved",
        evidence_refs=["PARM", "GPS", "XKF4", "SIM", "POS"],
    )


def _slow_drift_stimulus_fidelity(
    records: list[dict[str, Any]],
    *,
    anchor_us: float,
    base: dict[str, Any],
    fault_recipe: Mapping[str, Any] | None,
    trigger_event: Mapping[str, Any] | None,
    wall_elapsed_s: float | None,
    clock_ratio: float | None,
) -> dict[str, Any]:
    recipe = fault_recipe if isinstance(fault_recipe, Mapping) else {}
    requested_rate = _safe_float(recipe.get("drift_rate_mps"))
    if requested_rate is None:
        return _stimulus_fail(base, "missing_requested_drift_rate", ["fault_recipe.drift_rate_mps"])
    axis = str(recipe.get("axis", "east"))
    latitude = _trigger_latitude(trigger_event)
    if latitude is None:
        return _stimulus_fail(base, "missing_trigger_latitude_for_gltch_conversion", ["trigger_latitude_deg"])

    try:
        transitions = _fault_param_transitions(
            records,
            min_time_us=anchor_us,
            names={"SIM_GPS1_GLTCH_X", "SIM_GPS1_GLTCH_Y"},
        )
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["PARM.SIM_GPS1_GLTCH_X/Y"])
    if not transitions:
        return _stimulus_fail(base, "missing_slow_drift_parm_evidence", ["PARM.SIM_GPS1_GLTCH_X/Y"])
    try:
        samples = _glitch_offset_samples(
            transitions,
            latitude_deg=latitude,
            axis=axis,
        )
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["PARM.SIM_GPS1_GLTCH_X/Y"])
    if len(samples) < 2:
        return _stimulus_fail(base, "insufficient_slow_drift_offset_updates", ["PARM.SIM_GPS1_GLTCH_X/Y"])
    if not _monotonic_offsets(samples):
        return _stimulus_fail(
            _with_realized(base, {"offset_samples": samples}),
            "slow_drift_offset_not_monotonic",
            [],
        )

    start = samples[0]
    end = samples[-1]
    sample_span_vehicle_elapsed_s = (end["time_us"] - start["time_us"]) / 1_000_000.0
    if sample_span_vehicle_elapsed_s <= 0.0:
        return _stimulus_fail(base, "invalid_slow_drift_elapsed_time", ["PARM.TimeUS"])
    realized_rate = (
        (end["axis_offset_m"] - start["axis_offset_m"])
        / sample_span_vehicle_elapsed_s
    )
    rate_error = realized_rate - requested_rate
    percent_error = (
        abs(rate_error) / abs(requested_rate) * 100.0
        if requested_rate != 0.0
        else 0.0
    )
    tolerance = max(
        SLOW_DRIFT_ABS_TOLERANCE_MPS,
        abs(requested_rate) * SLOW_DRIFT_REL_TOLERANCE,
    )
    try:
        dose_samples = _slow_drift_dose_samples(
            samples,
            anchor_us=anchor_us,
            requested_rate_mps=requested_rate,
            rate_tolerance_mps=tolerance,
        )
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["PARM.SIM_GPS1_GLTCH_X/Y"])
    bad_dose_samples = [
        sample for sample in dose_samples
        if abs(sample["offset_error_m"]) > sample["offset_tolerance_m"]
    ]
    dose_end = dose_samples[-1]
    realized = {
        "requested_drift_rate_mps": requested_rate,
        "realized_drift_rate_mps": realized_rate,
        "rate_error_mps": rate_error,
        "rate_error_percent": percent_error,
        "vehicle_elapsed_s": dose_end["elapsed_since_trigger_s"],
        "sample_span_vehicle_elapsed_s": sample_span_vehicle_elapsed_s,
        "wall_elapsed_s": _safe_float(wall_elapsed_s),
        "clock_ratio": _safe_float(clock_ratio),
        "unique_offset_update_count": len(samples),
        "start_offset_m": start["axis_offset_m"],
        "end_offset_m": end["axis_offset_m"],
        "axis": axis,
        "trigger_latitude_deg": latitude,
        "offset_samples": dose_samples,
    }
    enriched = _with_realized(base, realized)
    if abs(rate_error) > tolerance:
        return _stimulus_fail(enriched, "slow_drift_rate_out_of_tolerance", [])
    if bad_dose_samples:
        return _stimulus_fail(enriched, "slow_drift_offset_out_of_tolerance", [])
    return _stimulus_pass(
        enriched,
        "slow_drift_rate_matches_requested_recipe",
        evidence_refs=["PARM.SIM_GPS1_GLTCH_X/Y", "PARM.TimeUS"],
    )


def _step_glitch_stimulus_fidelity(
    records: list[dict[str, Any]],
    *,
    anchor_us: float,
    base: dict[str, Any],
    fault_recipe: Mapping[str, Any] | None,
    trigger_event: Mapping[str, Any] | None,
) -> dict[str, Any]:
    recipe = fault_recipe if isinstance(fault_recipe, Mapping) else {}
    requested_offset = _safe_float(recipe.get("offset_magnitude_m"))
    if requested_offset is None:
        return _stimulus_fail(
            base,
            "missing_requested_step_glitch_offset",
            ["fault_recipe.offset_magnitude_m"],
        )
    axis = str(recipe.get("axis", "east"))
    latitude = _trigger_latitude(trigger_event)
    if latitude is None:
        return _stimulus_fail(
            base,
            "missing_trigger_latitude_for_gltch_conversion",
            ["trigger_latitude_deg"],
        )
    try:
        transitions = _fault_param_transitions(
            records,
            min_time_us=anchor_us,
            names={"SIM_GPS1_GLTCH_X", "SIM_GPS1_GLTCH_Y"},
        )
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["PARM.SIM_GPS1_GLTCH_X/Y"])
    if not transitions:
        return _stimulus_fail(
            base,
            "missing_step_glitch_parm_evidence",
            ["PARM.SIM_GPS1_GLTCH_X/Y"],
        )
    try:
        samples = _glitch_offset_samples(
            transitions,
            latitude_deg=latitude,
            axis=axis,
        )
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["PARM.SIM_GPS1_GLTCH_X/Y"])
    if not samples:
        return _stimulus_fail(
            base,
            "missing_step_glitch_offset_samples",
            ["PARM.SIM_GPS1_GLTCH_X/Y"],
        )
    realized_sample = max(
        samples,
        key=lambda sample: abs(float(sample["axis_offset_m"])),
    )
    realized_offset = float(realized_sample["axis_offset_m"])
    offset_error = realized_offset - requested_offset
    realized = {
        "requested_offset_m": requested_offset,
        "realized_offset_m": realized_offset,
        "offset_error_m": offset_error,
        "axis": axis,
        "trigger_latitude_deg": latitude,
        "transition_time_us": realized_sample["time_us"],
        "offset_samples": samples,
    }
    enriched = _with_realized(base, realized)
    if abs(offset_error) > STEP_GLITCH_OFFSET_ABS_TOLERANCE_M:
        return _stimulus_fail(enriched, "step_glitch_offset_out_of_tolerance", [])
    return _stimulus_pass(
        enriched,
        "step_glitch_offset_matches_requested_recipe",
        evidence_refs=["PARM.SIM_GPS1_GLTCH_X/Y", "PARM.TimeUS"],
    )


def _hard_denial_stimulus_fidelity(
    records: list[dict[str, Any]],
    *,
    anchor_us: float,
    base: dict[str, Any],
    fault_recipe: Mapping[str, Any] | None,
) -> dict[str, Any]:
    recipe = fault_recipe if isinstance(fault_recipe, Mapping) else {}
    requested_duration = _safe_float(recipe.get("denial_duration_s"))
    if requested_duration is None:
        return _stimulus_fail(base, "missing_requested_denial_duration", ["fault_recipe.denial_duration_s"])
    try:
        all_enable_transitions = _fault_param_transitions(
            records,
            min_time_us=-math.inf,
            names={"SIM_GPS1_ENABLE"},
        )
        transitions = _fault_param_transitions(
            records,
            min_time_us=anchor_us,
            names={"SIM_GPS1_ENABLE"},
        )
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["PARM.SIM_GPS1_ENABLE"])
    pre_enable = next(
        (
            item for item in reversed(all_enable_transitions)
            if item["time_us"] < anchor_us and item["value"] == 1.0
        ),
        None,
    )
    disable = next((item for item in transitions if item["value"] == 0.0), None)
    restore = next(
        (
            item for item in transitions
            if item["value"] == 1.0 and disable is not None and item["time_us"] > disable["time_us"]
        ),
        None,
    )
    missing: list[str] = []
    if pre_enable is None:
        missing.append("PARM.SIM_GPS1_ENABLE.pre_trigger_enabled")
    if disable is None:
        missing.append("PARM.SIM_GPS1_ENABLE.disable")
    if restore is None:
        missing.append("PARM.SIM_GPS1_ENABLE.restore")
    if missing:
        return _stimulus_fail(base, "missing_hard_denial_enable_transition", missing)
    assert pre_enable is not None
    assert disable is not None
    assert restore is not None

    try:
        gps_samples = _gps_quality_samples(records)
    except ValueError as exc:
        return _stimulus_fail(base, str(exc), ["GPS"])
    before = _best_gps_sample(
        sample for sample in gps_samples if sample["time_us"] <= disable["time_us"]
    )
    during = _worst_gps_sample(
        sample for sample in gps_samples
        if disable["time_us"] <= sample["time_us"] <= restore["time_us"]
    )
    after = _best_gps_sample(
        sample for sample in gps_samples if sample["time_us"] >= restore["time_us"]
    )
    missing = []
    if before is None:
        missing.append("GPS.before_disable")
    if during is None:
        missing.append("GPS.during_denial")
    if after is None:
        missing.append("GPS.after_restore")
    if missing:
        return _stimulus_fail(base, "missing_hard_denial_gps_quality_evidence", missing)
    assert before is not None
    assert during is not None
    assert after is not None

    realized_duration = (restore["time_us"] - disable["time_us"]) / 1_000_000.0
    realized = {
        "requested_denial_duration_s": requested_duration,
        "realized_denial_duration_s": realized_duration,
        "duration_error_s": realized_duration - requested_duration,
        "pre_enable_time_us": pre_enable["time_us"],
        "disable_time_us": disable["time_us"],
        "restore_time_us": restore["time_us"],
        "gps_status_before": before["status"],
        "gps_status_during": during["status"],
        "gps_status_after": after["status"],
        "satellites_before": before["satellites"],
        "satellites_during": during["satellites"],
        "satellites_after": after["satellites"],
    }
    enriched = _with_realized(base, realized)
    if not _gps_quality_healthy(before):
        return _stimulus_fail(enriched, "gps_not_healthy_before_denial", [])
    if not _gps_quality_denied(during):
        return _stimulus_fail(enriched, "gps_did_not_degrade_during_denial", [])
    if not _gps_quality_healthy(after):
        return _stimulus_fail(enriched, "gps_did_not_recover_after_restore", [])
    if abs(realized_duration - requested_duration) > HARD_DENIAL_DURATION_TOLERANCE_S:
        return _stimulus_fail(enriched, "hard_denial_duration_out_of_tolerance", [])
    return _stimulus_pass(
        enriched,
        "hard_denial_disable_restore_and_gps_recovery_verified",
        evidence_refs=["PARM.SIM_GPS1_ENABLE", "GPS.Status", "GPS.NSats"],
    )


def _stimulus_base(
    *,
    case_id: str | None,
    fault_type: str,
    requested: dict[str, Any],
    tolerances: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "fault_type": fault_type,
        "status": "fail",
        "reason": "not_evaluated",
        "source": "BIN",
        "requested": requested,
        "realized": {},
        "tolerances": tolerances,
        "evidence_refs": [],
        "missing_evidence": [],
    }


def _stimulus_requested(
    fault_type: str,
    fault_recipe: Mapping[str, Any] | None,
) -> dict[str, Any]:
    recipe = fault_recipe if isinstance(fault_recipe, Mapping) else {}
    if fault_type == "nominal":
        return {
            "no_post_trigger_fault_parameter_changes": True,
            "healthy_gps_required": True,
            "max_truth_belief_gap_m": NOMINAL_MAX_TRUTH_BELIEF_GAP_M,
        }
    if fault_type == "slow_drift":
        return {
            "drift_rate_mps": _safe_float(recipe.get("drift_rate_mps")),
            "axis": recipe.get("axis", "east"),
        }
    if fault_type == "step_glitch":
        return {
            "offset_magnitude_m": _safe_float(recipe.get("offset_magnitude_m")),
            "axis": recipe.get("axis", "east"),
        }
    if fault_type == "hard_denial":
        return {
            "denial_duration_s": _safe_float(recipe.get("denial_duration_s")),
            "restore_required": True,
        }
    return {}


def _stimulus_tolerances(fault_type: str) -> dict[str, Any]:
    if fault_type == "slow_drift":
        return {
            "rate_abs_tolerance_mps": SLOW_DRIFT_ABS_TOLERANCE_MPS,
            "rate_rel_tolerance": SLOW_DRIFT_REL_TOLERANCE,
            "rule": "max(abs_tolerance, requested_rate_mps * rel_tolerance)",
        }
    if fault_type == "hard_denial":
        return {"duration_tolerance_s": HARD_DENIAL_DURATION_TOLERANCE_S}
    if fault_type == "step_glitch":
        return {"offset_abs_tolerance_m": STEP_GLITCH_OFFSET_ABS_TOLERANCE_M}
    if fault_type == "nominal":
        return {
            "max_truth_belief_gap_m": NOMINAL_MAX_TRUTH_BELIEF_GAP_M,
            "healthy_gps_status_min": HEALTHY_GPS_STATUS_MIN,
            "healthy_gps_sats_min": HEALTHY_GPS_SATS_MIN,
        }
    return {}


def _stimulus_pass(
    artifact: dict[str, Any],
    reason: str,
    *,
    evidence_refs: list[str],
) -> dict[str, Any]:
    result = dict(artifact)
    result.update({
        "status": "pass",
        "reason": reason,
        "evidence_refs": list(evidence_refs),
        "missing_evidence": [],
    })
    return result


def _stimulus_fail(
    artifact: dict[str, Any],
    reason: str,
    missing_evidence: list[str],
) -> dict[str, Any]:
    result = dict(artifact)
    result.update({
        "status": "fail",
        "reason": reason,
        "missing_evidence": list(missing_evidence),
    })
    return result


def _with_realized(artifact: dict[str, Any], realized: dict[str, Any]) -> dict[str, Any]:
    result = dict(artifact)
    result["realized"] = realized
    return result


def _fault_param_transitions(
    records: Iterable[Mapping[str, Any]],
    *,
    min_time_us: float,
    names: set[str] | None = None,
) -> list[dict[str, Any]]:
    selected_names = names or set(glitch_params())
    transitions: list[dict[str, Any]] = []
    for record in records:
        if _record_type(record) != "PARM":
            continue
        name = str(record.get("Name", record.get("name", ""))).rstrip("\x00")
        if name not in selected_names:
            continue
        time_us = _record_time_us(record)
        if time_us is None:
            raise ValueError("malformed_parm_record")
        if time_us < min_time_us:
            continue
        try:
            value = _float(record.get("Value", record.get("value")))
        except (TypeError, ValueError):
            raise ValueError("malformed_parm_record") from None
        transitions.append({"time_us": time_us, "name": name, "value": value})
    transitions.sort(key=lambda item: (item["time_us"], item["name"]))
    return transitions


def glitch_params() -> tuple[str, ...]:
    return (
        "SIM_GPS1_ENABLE",
        "SIM_GPS1_GLTCH_X",
        "SIM_GPS1_GLTCH_Y",
        "SIM_GPS1_GLTCH_Z",
        "SIM_GPS1_JAM",
    )


def _glitch_offset_samples(
    transitions: Iterable[Mapping[str, Any]],
    *,
    latitude_deg: float,
    axis: str,
) -> list[dict[str, Any]]:
    current = {"SIM_GPS1_GLTCH_X": 0.0, "SIM_GPS1_GLTCH_Y": 0.0}
    samples: list[dict[str, Any]] = []
    last_axis_offset: float | None = None
    for transition in transitions:
        name = str(transition["name"])
        value = _float(transition["value"])
        current[name] = value
        north_m = current["SIM_GPS1_GLTCH_X"] * glitch.METRES_PER_LATITUDE_DEGREE
        east_m = (
            current["SIM_GPS1_GLTCH_Y"]
            * glitch.METRES_PER_LATITUDE_DEGREE
            * math.cos(math.radians(latitude_deg))
        )
        axis_offset = _axis_component(east_m=east_m, north_m=north_m, axis=axis)
        sample = {
            "time_us": _float(transition["time_us"]),
            "east_m": east_m,
            "north_m": north_m,
            "axis_offset_m": axis_offset,
            "source_param": name,
        }
        if last_axis_offset is None or not math.isclose(
            axis_offset,
            last_axis_offset,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            samples.append(sample)
            last_axis_offset = axis_offset
    return samples


def _slow_drift_dose_samples(
    samples: Iterable[Mapping[str, Any]],
    *,
    anchor_us: float,
    requested_rate_mps: float,
    rate_tolerance_mps: float,
) -> list[dict[str, Any]]:
    dose_samples: list[dict[str, Any]] = []
    for sample in samples:
        time_us = _float(sample.get("time_us"))
        axis_offset_m = _float(sample.get("axis_offset_m"))
        elapsed_since_trigger_s = (time_us - anchor_us) / 1_000_000.0
        if elapsed_since_trigger_s < 0.0:
            raise ValueError("slow_drift_offset_before_trigger")
        expected_offset_m = requested_rate_mps * elapsed_since_trigger_s
        offset_error_m = axis_offset_m - expected_offset_m
        offset_tolerance_m = max(
            SLOW_DRIFT_OFFSET_ABS_TOLERANCE_M,
            rate_tolerance_mps * elapsed_since_trigger_s,
        )
        within_startup_update_grace = (
            elapsed_since_trigger_s < defaults.SLOW_DRIFT_UPDATE_PERIOD_S
        )
        if within_startup_update_grace:
            offset_tolerance_m = max(
                offset_tolerance_m,
                abs(requested_rate_mps) * defaults.SLOW_DRIFT_UPDATE_PERIOD_S
                + SLOW_DRIFT_OFFSET_ABS_TOLERANCE_M,
            )
        enriched = dict(sample)
        enriched.update({
            "elapsed_since_trigger_s": elapsed_since_trigger_s,
            "expected_axis_offset_m": expected_offset_m,
            "offset_error_m": offset_error_m,
            "offset_tolerance_m": offset_tolerance_m,
            "within_startup_update_grace": within_startup_update_grace,
        })
        dose_samples.append(enriched)
    return dose_samples


def _axis_component(*, east_m: float, north_m: float, axis: str) -> float:
    axis_name = axis.lower()
    if axis_name == "east":
        return east_m
    if axis_name == "west":
        return -east_m
    if axis_name == "north":
        return north_m
    if axis_name == "south":
        return -north_m
    raise ValueError("unsupported_slow_drift_axis")


def _monotonic_offsets(samples: Iterable[Mapping[str, Any]]) -> bool:
    previous: float | None = None
    for sample in samples:
        value = _safe_float(sample.get("axis_offset_m"))
        if value is None:
            return False
        if previous is not None and value + 1e-9 < previous:
            return False
        previous = value
    return True


def _nearest_gps_quality(
    samples: Iterable[Mapping[str, Any]] | tuple[list[float], list[Mapping[str, Any]]],
    time_us: float,
) -> dict[str, Any] | None:
    if isinstance(samples, tuple):
        times = cast(list[float], samples[0])
        candidates = cast(list[Mapping[str, Any]], samples[1])
    else:
        indexed = _gps_quality_index(samples)
        times, candidates = indexed
    if not times:
        return None
    insert_at = bisect.bisect_left(times, time_us)
    candidate_indices = [
        index for index in (insert_at - 1, insert_at)
        if 0 <= index < len(candidates)
    ]
    nearest_index = min(
        candidate_indices,
        key=lambda index: abs(times[index] - time_us),
    )
    nearest = candidates[nearest_index]
    return {
        "source": "GPS.Status/NSats",
        "time_us": nearest.get("time_us"),
        "status": nearest.get("status"),
        "satellites": nearest.get("satellites"),
    }


def _gps_quality_index(
    samples: Iterable[Mapping[str, Any]],
) -> tuple[list[float], list[Mapping[str, Any]]]:
    candidates = [
        sample for sample in samples
        if isinstance(sample.get("time_us"), (int, float))
    ]
    candidates.sort(key=lambda sample: float(sample["time_us"]))
    return (
        [float(sample["time_us"]) for sample in candidates],
        candidates,
    )


def _gps_quality_samples(
    records: Iterable[Mapping[str, Any]],
    *,
    min_time_us: float | None = None,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for record in records:
        if _record_type(record) not in {"GPS", "GPS2"}:
            continue
        time_us = _record_time_us(record)
        if time_us is None:
            raise ValueError("malformed_gps_record")
        if min_time_us is not None and time_us < min_time_us:
            continue
        try:
            status = _gps_status(record)
            satellites = _gps_satellites(record)
        except (TypeError, ValueError):
            raise ValueError("malformed_gps_record") from None
        if status is None or satellites is None:
            raise ValueError("malformed_gps_record")
        samples.append({
            "time_us": time_us,
            "status": status,
            "satellites": satellites,
        })
    samples.sort(key=lambda item: item["time_us"])
    return samples


def _gps_status(record: Mapping[str, Any]) -> int | None:
    for key in ("Status", "status", "GPSStatus"):
        if key not in record:
            continue
        value = _int(record.get(key))
        if value is not None:
            return value
    return None


def _gps_satellites(record: Mapping[str, Any]) -> int | None:
    for key in ("NSats", "num_sats", "satellites_visible", "Sats", "Sat"):
        if key not in record:
            continue
        value = _int(record.get(key))
        if value is not None:
            return value
    return None


def _gps_quality_healthy(sample: Mapping[str, Any]) -> bool:
    status = _safe_float(sample.get("status"))
    sats = _safe_float(sample.get("satellites"))
    return bool(
        status is not None
        and sats is not None
        and status >= HEALTHY_GPS_STATUS_MIN
        and sats >= HEALTHY_GPS_SATS_MIN
    )


def _gps_quality_denied(sample: Mapping[str, Any]) -> bool:
    status = _safe_float(sample.get("status"))
    sats = _safe_float(sample.get("satellites"))
    return bool(
        status is not None
        and sats is not None
        and status <= DENIED_GPS_STATUS_MAX
        and sats <= DENIED_GPS_SATS_MAX
    )


def _best_gps_sample(samples: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    items = list(samples)
    if not items:
        return None
    return max(items, key=lambda item: (item["status"], item["satellites"]))


def _worst_gps_sample(samples: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    items = list(samples)
    if not items:
        return None
    return min(items, key=lambda item: (item["status"], item["satellites"]))


def _trigger_latitude(trigger_event: Mapping[str, Any] | None) -> float | None:
    if not isinstance(trigger_event, Mapping):
        return None
    for key in ("trigger_latitude_deg", "latitude_deg", "lat_deg"):
        if key in trigger_event:
            return _safe_float(trigger_event.get(key))
    return None


def _safe_float(value: object) -> float | None:
    try:
        return _float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    try:
        return _int(value)
    except (TypeError, ValueError):
        return None


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _find_injection_window_start(
    records: Iterable[Mapping[str, Any]],
    *,
    trigger_seq: int,
    injection_payload: Mapping[str, float] | None,
) -> float | None:
    # DataFlash CMD rows describe mission upload contents, not mission-current
    # execution. A live trigger boot timestamp is passed explicitly by the
    # monitor; parameter transitions are the only safe decoded-log fallback.
    _ = trigger_seq
    parameter_candidates: list[float] = []
    expected_payload = dict(injection_payload or {})
    for record in records:
        time_us = _record_time_us(record)
        if time_us is None:
            continue
        record_type = _record_type(record)
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
    truth_lat_deg: object,
    truth_lon_deg: object,
    belief_lat_deg: object,
    belief_lon_deg: object,
) -> float:
    truth_lat = _float(truth_lat_deg)
    truth_lon = _float(truth_lon_deg)
    belief_lat = _float(belief_lat_deg)
    belief_lon = _float(belief_lon_deg)
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
        "lat_deg": _float(record[lat_name]),
        "lon_deg": _float(record[lng_name]),
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
