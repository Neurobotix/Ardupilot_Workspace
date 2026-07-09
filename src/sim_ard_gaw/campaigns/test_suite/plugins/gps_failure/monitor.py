"""Monitor metadata for gps_failure."""
from __future__ import annotations

from dataclasses import dataclass
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
    for seq in sequences:
        if seq in required:
            seen_front_half.add(seq)
        if seq == defaults.INJECTION_TRIGGER["seq"]:
            return required.issubset(seen_front_half)
    return False


def first_seq4_edge_after_armed_auto_front_half(
    events: Iterable[dict[str, Any]],
) -> bool:
    """Validate ADR-0020 trigger preconditions from no-SITL event records."""
    seen_front_half: set[int] = set()
    required = set(defaults.INJECTION_TRIGGER["front_half_required_sequences"])
    trigger_seq = defaults.INJECTION_TRIGGER["seq"]
    trigger_mode = defaults.INJECTION_TRIGGER["mode"]
    for event in events:
        seq = event.get("seq")
        armed = event.get("armed") is True
        mode = event.get("mode") == trigger_mode
        if seq in required and armed and mode:
            seen_front_half.add(int(seq))
        if seq == trigger_seq:
            return required.issubset(seen_front_half) and armed and mode
    return False
