"""sensor_failure resilience monitor.

A passive MAVLink listener that ALSO performs the mid-flight fault injection,
then records the vehicle's resilience response. It is modeled on the wind
plugin's `monitor_until_disarm` shape (recv loop over HEARTBEAT /
MISSION_CURRENT / STATUSTEXT / GLOBAL_POSITION_INT / ATTITUDE / EKF_STATUS_REPORT)
but its success condition is SAFE HANDLING, not full mission completion.

Lifecycle inside `run()`:
  1. Wait until the trigger waypoint (`injection_waypoint`) is reached.
  2. Inject the fault via plugin-owned MAVLink PARAM_SET (confirmed by readback),
     stamp t=0 for the response window, snapshot the injected params.
  3. For `post_inject_window_s`, record: mode changes (failsafe), EKF status
     flags, altitude band (min/max AGL), attitude extremes (roll/pitch), the
     horizontal position excursion from the pre-fault fix, and disarm/RTL/land.
  4. Return a MonitorResult and stash a rich resilience-state dict in
     `ctx.extra["resilience_state"]` for the analyzer/verdict.

The monitor never forces "mission completed full" as the success condition.

No legacy runner import. No framework-core edit. The fault-injection callable
and a clock are injected so the monitor can be unit-tested with a scripted fake
MAVLink master and a fake clock (no SITL).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable

from pymavlink import mavutil

from ...core.models import AttemptContext, MonitorResult, TestCase
from ...core.monitor import CompletionMonitor
from . import defaults


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lon degree pairs."""
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


@dataclass
class SensorFailureResilienceMonitor(CompletionMonitor):
    """Inject a GPS fault at the trigger waypoint and capture the response."""

    injection_waypoint: int
    post_inject_window_s: float
    mission_timeout_s: float
    inject_fault: Callable[[Any, dict[str, float]], dict[str, float]]
    clamp_timeout_to_slot: Callable[..., float]
    master_key: str = "mavlink_master"
    bin_flush_delay_s: float = 0.0
    analysis_headroom_s: float = 0.0
    # Injected for testability.
    clock: Callable[[], float] = time.time

    def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
        master = ctx.extra.get(self.master_key)
        if master is None:
            raise RuntimeError("MAVLink master is missing from attempt context.")
        fault_case = ctx.extra.get("fault_case")
        inject_params: dict[str, float] = (
            dict(fault_case.inject) if fault_case is not None
            else dict(case.parameters.get("inject_params") or {})
        )
        verdict_mode = (
            fault_case.verdict_mode if fault_case is not None
            else str(case.parameters.get("verdict_mode") or "")
        )

        monitor_log = ctx.attempt_dir / "monitor.log"
        overall_timeout_s = self.clamp_timeout_to_slot(
            self.mission_timeout_s,
            ctx.slot_deadline_monotonic_s,
            phase="resilience monitor",
            reserve_s=self.bin_flush_delay_s + self.analysis_headroom_s,
        )

        state = self._fresh_state(verdict_mode, inject_params)
        deadline = self.clock() + overall_timeout_s

        defaults.log(
            f"Resilience monitor started: inject at wp "
            f"{self.injection_waypoint}, then observe "
            f"{self.post_inject_window_s:.0f}s (overall budget "
            f"{overall_timeout_s/60:.1f} min)."
        )

        with monitor_log.open("a", encoding="utf-8") as fh:
            while self.clock() < deadline:
                msg = master.recv_match(
                    type=[
                        "HEARTBEAT", "MISSION_CURRENT", "MISSION_ITEM_REACHED",
                        "STATUSTEXT", "GLOBAL_POSITION_INT", "ATTITUDE",
                        "EKF_STATUS_REPORT",
                    ],
                    blocking=True,
                    timeout=1.0,
                )
                if msg is None:
                    if self._post_window_elapsed(state):
                        state["stopped_reason"] = "post_inject_window_complete"
                        break
                    continue

                mt = msg.get_type()
                fh.write(f"{defaults.utc_now()} {mt} {msg.to_dict()}\n")
                fh.flush()

                self._observe(mt, msg, state)

                # Trigger the injection once we reach the trigger waypoint.
                if (
                    not state["fault_injected"]
                    and state["mission_seq"] is not None
                    and int(state["mission_seq"]) >= self.injection_waypoint
                    and state["armed_now"]
                ):
                    self._inject(master, inject_params, state)

                if self._post_window_elapsed(state):
                    state["stopped_reason"] = "post_inject_window_complete"
                    break

                if state["disarmed"]:
                    state["stopped_reason"] = "vehicle_disarmed"
                    break
            else:
                state["timed_out"] = True
                state["stopped_reason"] = (
                    "overall_timeout_before_injection"
                    if not state["fault_injected"] else "overall_timeout_after_injection"
                )

        self._finalize(state)
        ctx.extra["resilience_state"] = state

        completed = bool(state["fault_injected"])
        reason = state.get("stopped_reason") or (
            "fault_injected" if completed else "fault_not_injected"
        )
        return MonitorResult(
            completed=completed,
            reason=reason,
            duration_s=float(state.get("observation_duration_s") or 0.0),
            waypoints_seen=[int(s) for s in state["reached"] if isinstance(s, int)],
            notes=[str(n) for n in state["notes"][-5:]],
            monitor_log_path=monitor_log,
        )

    # --- helpers -----------------------------------------------------------
    def _fresh_state(
        self, verdict_mode: str, inject_params: dict[str, float],
    ) -> dict[str, Any]:
        return {
            "verdict_mode": verdict_mode,
            "intended_inject_params": dict(inject_params),
            "confirmed_inject_params": {},
            # A baseline (no-fault) case has empty inject_params: we still stamp
            # t=0 at the trigger waypoint so the same before/after split and the
            # same observation window apply, giving a true control envelope.
            "is_baseline": not bool(inject_params),
            "armed_ever": False,
            "armed_now": False,
            "disarmed": False,
            "mission_seq": None,
            "reached": [],
            "fault_injected": False,
            "fault_inject_time": None,
            "fault_inject_seq": None,
            "fault_inject_error": None,
            "fault_inject_lat": None,
            "fault_inject_lon": None,
            # Pre-fault envelope (the self-referencing baseline for THIS flight):
            # how the vehicle was behaving in the window before the trigger.
            "pre_fault_lat": None,
            "pre_fault_lon": None,
            "pre_fault_relalt_m": None,
            "pre_inject_min_relalt_m": None,
            "pre_inject_max_relalt_m": None,
            "pre_inject_max_roll_deg": 0.0,
            "pre_inject_max_pitch_deg": 0.0,
            "pre_inject_max_groundspeed_ms": 0.0,
            "pre_inject_attitude_samples": 0,
            # Post-injection response capture.
            "modes_seen": [],
            "mode_at_inject": None,
            "mode_after_inject": None,
            "mode_changed_after_inject": False,
            "post_inject_min_relalt_m": None,
            "post_inject_max_relalt_m": None,
            "post_inject_max_roll_deg": 0.0,
            "post_inject_max_pitch_deg": 0.0,
            "post_inject_max_groundspeed_ms": 0.0,
            "post_inject_max_excursion_m": 0.0,
            "post_inject_attitude_samples": 0,
            "ekf_flags_after_inject": None,
            "ekf_failsafe_statustext": False,
            "last_mode": None,
            "statustext": [],
            "notes": [],
            "timed_out": False,
            "stopped_reason": None,
            "observation_duration_s": None,
        }

    def _inject(
        self, master: Any, inject_params: dict[str, float], state: dict[str, Any],
    ) -> None:
        seq = state["mission_seq"]

        def _stamp_trigger() -> None:
            state["fault_injected"] = True
            state["fault_inject_time"] = self.clock()
            state["fault_inject_seq"] = int(seq) if seq is not None else None
            state["mode_at_inject"] = state["last_mode"]
            state["mode_after_inject"] = state["last_mode"]
            state["fault_inject_lat"] = state["pre_fault_lat"]
            state["fault_inject_lon"] = state["pre_fault_lon"]

        if state["is_baseline"]:
            # Control run: no fault. Stamp the trigger so the post-window is the
            # SAME shape/duration as a fault run, giving a clean reference for the
            # behavioral deltas.
            defaults.log(
                f"Trigger waypoint {self.injection_waypoint} reached (seq={seq}); "
                "BASELINE (no fault injected) — capturing control envelope."
            )
            _stamp_trigger()
            state["notes"].append(f"baseline_trigger seq={seq} (no fault)")
            return

        defaults.log(
            f"Trigger waypoint {self.injection_waypoint} reached (seq={seq}); "
            f"injecting fault: {inject_params}"
        )
        try:
            confirmed = self.inject_fault(master, inject_params)
            state["confirmed_inject_params"] = confirmed
            _stamp_trigger()
            state["notes"].append(f"fault_injected seq={seq} params={confirmed}")
        except Exception as exc:  # injection failure is a hard monitor failure
            state["fault_inject_error"] = f"{type(exc).__name__}: {exc}"
            state["notes"].append(f"fault_inject_error: {state['fault_inject_error']}")
            defaults.log(f"WARNING: fault injection failed: {state['fault_inject_error']}")

    def _observe(self, mt: str, msg: Any, state: dict[str, Any]) -> None:
        injected = state["fault_injected"]
        if mt == "HEARTBEAT":
            mode = mavutil.mode_string_v10(msg)
            state["last_mode"] = mode
            if mode not in state["modes_seen"]:
                state["modes_seen"].append(mode)
            armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            if armed and not state["armed_ever"]:
                state["armed_ever"] = True
                state["armed_now"] = True
                defaults.log(f"Vehicle ARMED mode={mode}")
            if not armed and state["armed_ever"] and state["armed_now"]:
                state["armed_now"] = False
                state["disarmed"] = True
                defaults.log(f"Vehicle DISARMED mode={mode}")
            if injected:
                if (
                    state["mode_after_inject"] is not None
                    and mode != state["mode_after_inject"]
                ):
                    if not state["mode_changed_after_inject"]:
                        state["notes"].append(
                            f"mode_change_after_inject -> {mode}"
                        )
                    state["mode_changed_after_inject"] = True

        elif mt == "MISSION_CURRENT":
            state["mission_seq"] = int(msg.seq)

        elif mt == "MISSION_ITEM_REACHED":
            seq = int(msg.seq)
            state["reached"].append(seq)
            if state["mission_seq"] is None or seq > int(state["mission_seq"]):
                state["mission_seq"] = seq

        elif mt == "GLOBAL_POSITION_INT":
            lat = float(getattr(msg, "lat", 0)) / 1e7
            lon = float(getattr(msg, "lon", 0)) / 1e7
            relalt_m = float(getattr(msg, "relative_alt", 0)) / 1000.0
            vx = float(getattr(msg, "vx", 0)) / 100.0  # cm/s -> m/s (N)
            vy = float(getattr(msg, "vy", 0)) / 100.0  # cm/s -> m/s (E)
            groundspeed = math.hypot(vx, vy)
            if not injected:
                # Pre-fault envelope: the most recent healthy fix (excursion
                # origin) plus the normal altitude/groundspeed range before the
                # trigger. This is the self-referencing control for THIS flight.
                if lat != 0.0 or lon != 0.0:
                    state["pre_fault_lat"] = lat
                    state["pre_fault_lon"] = lon
                    state["pre_fault_relalt_m"] = relalt_m
                self._update_band(state, "pre_inject_min_relalt_m", relalt_m, min)
                self._update_band(state, "pre_inject_max_relalt_m", relalt_m, max)
                state["pre_inject_max_groundspeed_ms"] = max(
                    state["pre_inject_max_groundspeed_ms"], groundspeed,
                )
            else:
                self._update_band(state, "post_inject_min_relalt_m", relalt_m, min)
                self._update_band(state, "post_inject_max_relalt_m", relalt_m, max)
                state["post_inject_max_groundspeed_ms"] = max(
                    state["post_inject_max_groundspeed_ms"], groundspeed,
                )
                # Excursion is measured from the fix at the moment of injection.
                origin_lat = state.get("fault_inject_lat") or state["pre_fault_lat"]
                origin_lon = state.get("fault_inject_lon") or state["pre_fault_lon"]
                if origin_lat is not None and (lat != 0.0 or lon != 0.0):
                    excursion = _haversine_m(origin_lat, origin_lon, lat, lon)
                    state["post_inject_max_excursion_m"] = max(
                        state["post_inject_max_excursion_m"], excursion,
                    )

        elif mt == "ATTITUDE":
            roll = abs(math.degrees(float(getattr(msg, "roll", 0.0))))
            pitch = abs(math.degrees(float(getattr(msg, "pitch", 0.0))))
            if not injected:
                state["pre_inject_max_roll_deg"] = max(
                    state["pre_inject_max_roll_deg"], roll,
                )
                state["pre_inject_max_pitch_deg"] = max(
                    state["pre_inject_max_pitch_deg"], pitch,
                )
                state["pre_inject_attitude_samples"] += 1
            else:
                state["post_inject_max_roll_deg"] = max(
                    state["post_inject_max_roll_deg"], roll,
                )
                state["post_inject_max_pitch_deg"] = max(
                    state["post_inject_max_pitch_deg"], pitch,
                )
                state["post_inject_attitude_samples"] += 1

        elif mt == "EKF_STATUS_REPORT":
            if injected:
                flags = getattr(msg, "flags", None)
                if flags is not None:
                    state["ekf_flags_after_inject"] = int(flags)

        elif mt == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text:
                state["statustext"].append(text)
                lower = text.lower()
                if any(
                    token in lower
                    for token in ("ekf", "gps", "failsafe", "rtl", "dead reckoning",
                                  "glitch", "variance")
                ):
                    defaults.log(f"  STATUSTEXT: {text}")
                if injected and any(
                    token in lower
                    for token in ("ekf failsafe", "ekf variance", "gps glitch",
                                  "dead reckoning", "long failsafe")
                ):
                    state["ekf_failsafe_statustext"] = True

    @staticmethod
    def _update_band(
        state: dict[str, Any], key: str, value: float, fn: Callable[[float, float], float],
    ) -> None:
        cur = state[key]
        state[key] = value if cur is None else fn(cur, value)

    def _post_window_elapsed(self, state: dict[str, Any]) -> bool:
        if not state["fault_injected"] or state["fault_inject_time"] is None:
            return False
        return (self.clock() - state["fault_inject_time"]) >= self.post_inject_window_s

    def _finalize(self, state: dict[str, Any]) -> None:
        if state["fault_inject_time"] is not None:
            state["observation_duration_s"] = round(
                self.clock() - state["fault_inject_time"], 1,
            )
        if state["fault_injected"]:
            state["mode_after_inject"] = state["mode_after_inject"] or state["last_mode"]
