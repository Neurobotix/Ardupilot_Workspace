"""Monitor metadata for gps_failure."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable

from ...core.models import AttemptContext, MonitorResult, TestCase
from ...core.monitor import CompletionMonitor
from . import defaults
from .config import GpsFailureConfig


@dataclass
class GpsFailureMonitor(CompletionMonitor):
    config: GpsFailureConfig

    def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
        if not self.config.launch_stack:
            return MonitorResult(
                completed=False,
                reason="phase1_no_sitl_monitor_not_run",
                duration_s=0.0,
            )
        raise RuntimeError("gps_failure live monitor is out of scope for Phase 1 Chunk 1")


def trigger_metadata() -> dict[str, object]:
    return dict(defaults.INJECTION_TRIGGER)


def first_seq4_edge_after_front_half(sequences: Iterable[int]) -> bool:
    """Schema-level helper requiring seq 1, 2, and 3 before first seq 4."""
    seen_front_half: set[int] = set()
    required = set(defaults.INJECTION_TRIGGER["front_half_required_sequences"])
    trigger_seq = int(defaults.INJECTION_TRIGGER["seq"])
    for raw_seq in sequences:
        seq = _coerce_seq(raw_seq)
        if seq is None:
            return False
        if seq in required:
            seen_front_half.add(seq)
        if seq == trigger_seq:
            return required.issubset(seen_front_half)
    return False


def first_seq4_edge_after_armed_auto_front_half(
    events: Iterable[Any],
) -> bool:
    """Validate ADR-0020 trigger preconditions from no-SITL event records.

    Fails closed for malformed events and for any mission-current evidence that
    is not a clean, monotonic seq 1->2->3->4 progression. A regression to a lower
    seq or a skipped front-half seq is rejected. Repeated ``MISSION_CURRENT``
    events for the *current* seq are benign telemetry and allowed (the stream
    reports the same seq repeatedly), but every front-half seq must be observed
    in order, armed and in AUTO, before the first seq-4 edge.
    """
    expected_order = list(
        defaults.INJECTION_TRIGGER["front_half_required_sequences"]
    )
    trigger_seq = int(defaults.INJECTION_TRIGGER["seq"])
    trigger_mode = defaults.INJECTION_TRIGGER["mode"]
    next_required_index = 0
    last_seq: int | None = None

    for event in events:
        if not isinstance(event, dict):
            return False
        seq = _coerce_seq(event.get("seq"))
        if seq is None:
            return False
        armed = event.get("armed") is True
        mode = event.get("mode") == trigger_mode

        if last_seq is not None and seq < last_seq:
            # Any regression to a lower mission-current seq is invalid evidence.
            return False

        if seq == last_seq:
            # A repeat of the current seq is benign telemetry, not progression.
            continue

        if seq == trigger_seq:
            # The seq-4 edge is valid only once the full ordered front half has
            # been observed and this event is itself armed and in AUTO.
            return next_required_index == len(expected_order) and armed and mode

        if (
            next_required_index < len(expected_order)
            and seq == expected_order[next_required_index]
        ):
            if not (armed and mode):
                return False
            next_required_index += 1
            last_seq = seq
            continue

        # Any other seq (a skip ahead, an out-of-contract value, or a jump past
        # the next required front-half seq) invalidates the trace.
        return False

    return False


def _coerce_seq(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
