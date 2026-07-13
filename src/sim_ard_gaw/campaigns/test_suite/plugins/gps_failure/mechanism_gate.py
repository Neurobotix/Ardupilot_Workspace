"""No-SITL GPS EKF mechanism-gate evaluation for synthetic observations."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


GATE_BOUNDARY = 1.0
DEFAULT_SUSTAINED_REJECTION_MIN_SAMPLES = 2

MECHANISM_STATES = (
    "fused_below_gate",
    "rejected_above_gate",
    "reset_detected",
    "mechanism_unverified",
)

TIME_FIELD_ALIASES = (
    "timestamp_s",
    "time_s",
    "relative_time_s",
    "elapsed_s",
    "timestamp",
    "time",
    "t",
)
POS_TEST_RATIO_FIELD_ALIASES = (
    "posTestRatio",
    "pos_test_ratio",
    "pos_test_ratio_norm",
    "position_test_ratio",
    "normalized_pos_test_ratio",
    "test_ratio",
)
RESET_FIELD_ALIASES = (
    "reset_detected",
    "reset_event",
    "reset",
    "position_reset",
    "reset_position",
    "ResetPosition",
)
REJECT_FIELD_ALIASES = (
    "rejected",
    "reject",
    "reject_flag",
    "gps_rejected",
    "pos_rejected",
    "pos_test_ratio_rejected",
)
GLITCH_FIELD_ALIASES = ("glitch", "glitch_flag", "glitch_detected")
FAILSAFE_FIELD_ALIASES = ("failsafe", "fail_safe", "ekf_failsafe")


@dataclass(frozen=True)
class MechanismGateResult:
    mechanism_state: str
    accepted_evidence: bool
    incomplete: bool
    reason: str
    metrics: dict[str, Any] = field(default_factory=dict)
    source_fields: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "mechanism_state": self.mechanism_state,
            "mechanism_class": self.mechanism_state,
            "accepted_evidence": self.accepted_evidence,
            "mechanism_evidence_accepted": self.accepted_evidence,
            "incomplete": self.incomplete,
            "reason": self.reason,
            "metrics": _json_safe_dict(self.metrics),
            "source_fields": _json_safe_dict(self.source_fields),
        }


@dataclass(frozen=True)
class _Sample:
    timestamp_s: float
    pos_test_ratio: float
    reset_detected: bool
    reject_flag: bool
    glitch_flag: bool
    failsafe: bool


def evaluate(
    records: Iterable[Mapping[str, Any]],
    *,
    sustained_rejection_min_samples: int = DEFAULT_SUSTAINED_REJECTION_MIN_SAMPLES,
) -> MechanismGateResult:
    """Evaluate synthetic EKF mechanism observations.

    This intentionally does not parse DataFlash logs or invoke runtime tooling.
    Callers must provide already-decoded, EKF-like records.
    """

    if sustained_rejection_min_samples < 1:
        return _unverified(
            "invalid_sustained_rejection_min_samples",
            extra_metrics={"sustained_rejection_min_samples": sustained_rejection_min_samples},
        )

    try:
        record_list = list(records)
    except TypeError:
        return _unverified("records_not_iterable")

    if not record_list:
        return _unverified("empty_records")

    samples: list[_Sample] = []
    time_fields: set[str] = set()
    ratio_fields: set[str] = set()
    reset_fields: set[str] = set()
    reject_fields: set[str] = set()
    glitch_fields: set[str] = set()
    failsafe_fields: set[str] = set()
    previous_timestamp: float | None = None

    for index, record in enumerate(record_list):
        if not isinstance(record, Mapping):
            return _unverified("record_not_mapping", record_index=index)

        time_field, raw_time = _first_present(record, TIME_FIELD_ALIASES)
        if time_field is None:
            return _unverified("missing_timestamp", record_index=index)
        timestamp_s = _finite_float(raw_time)
        if timestamp_s is None:
            return _unverified("invalid_timestamp", record_index=index)
        if previous_timestamp is not None and timestamp_s < previous_timestamp:
            return _unverified(
                "out_of_order_timestamps",
                record_index=index,
                extra_metrics={
                    "previous_timestamp_s": previous_timestamp,
                    "timestamp_s": timestamp_s,
                },
            )
        previous_timestamp = timestamp_s
        time_fields.add(time_field)

        ratio_field, raw_ratio = _first_present(record, POS_TEST_RATIO_FIELD_ALIASES)
        if ratio_field is None:
            return _unverified("missing_pos_test_ratio", record_index=index)
        pos_test_ratio = _finite_float(raw_ratio)
        if pos_test_ratio is None:
            return _unverified("invalid_pos_test_ratio", record_index=index)
        ratio_fields.add(ratio_field)

        reset_detected, reset_field, reset_error = _optional_bool(
            record,
            RESET_FIELD_ALIASES,
        )
        if reset_error is not None:
            return _unverified(reset_error, record_index=index)
        if reset_field is not None:
            reset_fields.add(reset_field)

        reject_flag, reject_field, reject_error = _optional_bool(
            record,
            REJECT_FIELD_ALIASES,
        )
        if reject_error is not None:
            return _unverified(reject_error, record_index=index)
        if reject_field is not None:
            reject_fields.add(reject_field)

        glitch_flag, glitch_field, glitch_error = _optional_bool(
            record,
            GLITCH_FIELD_ALIASES,
        )
        if glitch_error is not None:
            return _unverified(glitch_error, record_index=index)
        if glitch_field is not None:
            glitch_fields.add(glitch_field)

        failsafe, failsafe_field, failsafe_error = _optional_bool(
            record,
            FAILSAFE_FIELD_ALIASES,
        )
        if failsafe_error is not None:
            return _unverified(failsafe_error, record_index=index)
        if failsafe_field is not None:
            failsafe_fields.add(failsafe_field)

        samples.append(
            _Sample(
                timestamp_s=timestamp_s,
                pos_test_ratio=pos_test_ratio,
                reset_detected=reset_detected,
                reject_flag=reject_flag,
                glitch_flag=glitch_flag,
                failsafe=failsafe,
            )
        )

    metrics = _metrics(samples, sustained_rejection_min_samples)
    source_fields = {
        "timestamp": sorted(time_fields),
        "pos_test_ratio": sorted(ratio_fields),
        "reset": sorted(reset_fields),
        "reject": sorted(reject_fields),
        "glitch": sorted(glitch_fields),
        "failsafe": sorted(failsafe_fields),
    }

    reset_detected = bool(metrics["reset_evidence"])
    crossed_gate = bool(metrics["crossed_gate"])
    if reset_detected:
        return MechanismGateResult(
            mechanism_state="reset_detected",
            accepted_evidence=True,
            incomplete=False,
            reason="reset_evidence_present",
            metrics=metrics,
            source_fields=source_fields,
        )
    if crossed_gate:
        return MechanismGateResult(
            mechanism_state="rejected_above_gate",
            accepted_evidence=True,
            incomplete=False,
            reason="pos_test_ratio_at_or_above_gate",
            metrics=metrics,
            source_fields=source_fields,
        )
    return MechanismGateResult(
        mechanism_state="fused_below_gate",
        accepted_evidence=True,
        incomplete=False,
        reason="all_pos_test_ratio_samples_below_gate",
        metrics=metrics,
        source_fields=source_fields,
    )


def evaluate_mechanism_records(
    records: Iterable[Mapping[str, Any]],
    *,
    sustained_rejection_min_samples: int = DEFAULT_SUSTAINED_REJECTION_MIN_SAMPLES,
) -> MechanismGateResult:
    """Named wrapper for callers that prefer an explicit GPS mechanism API."""

    return evaluate(
        records,
        sustained_rejection_min_samples=sustained_rejection_min_samples,
    )


def _metrics(
    samples: list[_Sample],
    sustained_rejection_min_samples: int,
) -> dict[str, Any]:
    ratios = [sample.pos_test_ratio for sample in samples]
    timestamps = [sample.timestamp_s for sample in samples]
    crossing_samples = [
        sample for sample in samples if sample.pos_test_ratio >= GATE_BOUNDARY
    ]
    explicit_rejection = any(
        sample.reject_flag or sample.glitch_flag or sample.failsafe for sample in samples
    )
    max_consecutive_rejections = _max_consecutive(
        sample.pos_test_ratio >= GATE_BOUNDARY for sample in samples
    )
    return {
        "sample_count": len(samples),
        "first_timestamp_s": timestamps[0],
        "last_timestamp_s": timestamps[-1],
        "observation_duration_s": timestamps[-1] - timestamps[0],
        "min_pos_test_ratio": min(ratios),
        "max_pos_test_ratio": max(ratios),
        "gate_boundary": GATE_BOUNDARY,
        "crossed_gate": bool(crossing_samples),
        "first_crossing_time_s": (
            crossing_samples[0].timestamp_s if crossing_samples else None
        ),
        "crossing_sample_count": len(crossing_samples),
        "sampled_rejection": bool(crossing_samples) or explicit_rejection,
        "sustained_rejection": max_consecutive_rejections
        >= sustained_rejection_min_samples,
        "sustained_rejection_min_samples": sustained_rejection_min_samples,
        "max_consecutive_rejection_samples": max_consecutive_rejections,
        "reset_evidence": any(sample.reset_detected for sample in samples),
        "explicit_reject_flag_evidence": any(sample.reject_flag for sample in samples),
        "glitch_flag_evidence": any(sample.glitch_flag for sample in samples),
        "failsafe_flag_evidence": any(sample.failsafe for sample in samples),
    }


def _max_consecutive(values: Iterable[bool]) -> int:
    best = 0
    current = 0
    for value in values:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _unverified(
    reason: str,
    *,
    record_index: int | None = None,
    extra_metrics: dict[str, Any] | None = None,
) -> MechanismGateResult:
    metrics: dict[str, Any] = {
        "sample_count": 0,
        "first_timestamp_s": None,
        "last_timestamp_s": None,
        "observation_duration_s": None,
        "min_pos_test_ratio": None,
        "max_pos_test_ratio": None,
        "gate_boundary": GATE_BOUNDARY,
        "crossed_gate": False,
        "first_crossing_time_s": None,
        "crossing_sample_count": 0,
        "sampled_rejection": False,
        "sustained_rejection": False,
        "sustained_rejection_min_samples": DEFAULT_SUSTAINED_REJECTION_MIN_SAMPLES,
        "max_consecutive_rejection_samples": 0,
        "reset_evidence": False,
        "explicit_reject_flag_evidence": False,
        "glitch_flag_evidence": False,
        "failsafe_flag_evidence": False,
    }
    if record_index is not None:
        metrics["invalid_record_index"] = record_index
    if extra_metrics:
        metrics.update(extra_metrics)
    return MechanismGateResult(
        mechanism_state="mechanism_unverified",
        accepted_evidence=False,
        incomplete=True,
        reason=reason,
        metrics=metrics,
        source_fields={},
    )


def _first_present(
    record: Mapping[str, Any],
    aliases: tuple[str, ...],
) -> tuple[str | None, Any]:
    for name in aliases:
        if name in record:
            return name, record[name]
    return None, None


def _finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _optional_bool(
    record: Mapping[str, Any],
    aliases: tuple[str, ...],
) -> tuple[bool, str | None, str | None]:
    field_name, raw_value = _first_present(record, aliases)
    if field_name is None:
        return False, None, None
    if isinstance(raw_value, bool):
        return raw_value, field_name, None
    if isinstance(raw_value, int) and raw_value in (0, 1):
        return bool(raw_value), field_name, None
    if isinstance(raw_value, float) and math.isfinite(raw_value) and raw_value in (0.0, 1.0):
        return bool(raw_value), field_name, None
    return False, field_name, f"invalid_{field_name}"


def _json_safe_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_safe_value(value) for key, value in data.items()}


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _json_safe_dict(value)
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("MechanismGateResult contains a non-finite float")
        return value
    return value
