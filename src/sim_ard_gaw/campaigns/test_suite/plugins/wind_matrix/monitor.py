"""Wind-matrix completion monitor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ...core.models import AttemptContext, MonitorResult, TestCase
from ...core.monitor import CompletionMonitor


def _commanded_wind_mps(case: TestCase) -> tuple[float, float] | None:
    """The cell's commanded wind vector: this lane's independent variable.

    Returns None rather than a default when either component is missing, so
    the heartbeat prints `?` instead of implying a wind that was never
    commanded.
    """
    x = case.parameters.get("wind_x_mps")
    y = case.parameters.get("wind_y_mps")
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
    return float(x), float(y)  # type: ignore[arg-type]


@dataclass
class WindMatrixDisarmCompletionMonitor(CompletionMonitor):
    """Completion monitor for the square wind mission ending in disarm."""

    mission_timeout_s: float
    monitor_until_disarm: Callable[..., dict[str, Any]]
    clamp_timeout_to_slot: Callable[..., float]
    mission_pre_loaded: bool
    stop_on_square_loiter: bool = False
    master_key: str = "mavlink_master"
    bin_flush_delay_s: float = 0.0
    analysis_headroom_s: float = 0.0

    def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
        master = ctx.extra.get(self.master_key)
        if master is None:
            raise RuntimeError("MAVLink master is missing from attempt context.")

        monitor_log = ctx.attempt_dir / "monitor.log"
        state = self.monitor_until_disarm(
            master,
            monitor_log,
            self.clamp_timeout_to_slot(
                self.mission_timeout_s,
                ctx.slot_deadline_monotonic_s,
                phase="mission monitor",
                reserve_s=self.bin_flush_delay_s + self.analysis_headroom_s,
            ),
            mission_pre_loaded=self.mission_pre_loaded,
            stop_on_square_loiter=self.stop_on_square_loiter,
            case_id=case.case_id,
            commanded_wind_mps=_commanded_wind_mps(case),
        )
        ctx.extra["wind_monitor_state"] = state
        completed = bool(
            state.get("mission_completed_full")
            or state.get("completed_square_loiter_early")
            or (
                state.get("square_completed")
                and state.get("loiter_completed")
                and self.stop_on_square_loiter
            )
        )
        reason = "completed" if completed else "failed_or_timed_out"
        if state.get("invalid_start_reason"):
            reason = f"invalid_start: {state['invalid_start_reason']}"
        elif state.get("timed_out"):
            reason = "timed_out"
        return MonitorResult(
            completed=completed,
            reason=reason,
            duration_s=0.0,
            waypoints_seen=[
                int(seq) for seq in state.get("reached", [])
                if isinstance(seq, int)
            ],
            notes=[
                str(note) for note in (
                    state.get("statustext", [])[-3:]
                    if isinstance(state.get("statustext"), list) else []
                )
            ],
            monitor_log_path=monitor_log,
        )
