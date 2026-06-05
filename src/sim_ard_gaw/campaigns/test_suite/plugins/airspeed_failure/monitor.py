"""Monitor interfaces and trigger helpers for airspeed_failure."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ...core.models import AttemptContext, MonitorResult, TestCase
from ...core.monitor import CompletionMonitor
from . import defaults
from .config import AirspeedFailureConfig


@dataclass
class AirspeedFailureMonitor(CompletionMonitor):
    config: AirspeedFailureConfig

    def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
        if not self.config.launch_stack:
            return MonitorResult(
                completed=False,
                reason="phase1_no_sitl_monitor_not_run",
                duration_s=0.0,
            )
        raise NotImplementedError("airspeed_failure live monitor is Phase 2 work")


def trigger_metadata() -> dict[str, object]:
    return dict(defaults.INJECTION_TRIGGER)


def first_seq4_edge_after_front_half(sequences: Iterable[int]) -> bool:
    seen_front_half = False
    for seq in sequences:
        if seq in defaults.INJECTION_TRIGGER["front_half_required_sequences"]:
            seen_front_half = True
        if seq == defaults.INJECTION_TRIGGER["seq"]:
            return seen_front_half
    return False
