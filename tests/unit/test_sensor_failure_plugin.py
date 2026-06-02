from __future__ import annotations

# pyright: reportMissingImports=false

import os
import subprocess
import sys
import tempfile
import time
import unittest
from collections import deque
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCRIPTS = SRC / "sim_ard_gaw" / "compat_scripts"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))

from test_suite.core.models import (  # noqa: E402
    AttemptContext,
    MonitorResult,
    TestCase,
    VerdictClass,
)
from test_suite.plugins.sensor_failure import build_plugin  # noqa: E402
from test_suite.plugins.sensor_failure import cases as gps_cases  # noqa: E402
from test_suite.plugins.sensor_failure import defaults  # noqa: E402
from test_suite.plugins.sensor_failure.analyzers import (  # noqa: E402
    SensorFailureVerdictPolicy,
    _behavioral_deltas,
    _classify_behavior,
    _resilience_metrics,
)


def _classify(state: dict) -> tuple:
    """Helper: run the behavioral classifier on a monitor state dict.
    Returns (behavior, accepted, status, reasons)."""
    m = _resilience_metrics(state)
    d = _behavioral_deltas(m)
    return _classify_behavior(verdict_mode=m["verdict_mode"], metrics=m, deltas=d)
from test_suite.plugins.sensor_failure.config import SensorFailureConfig  # noqa: E402
from test_suite.plugins.sensor_failure.manifest import SensorFailureManifest  # noqa: E402
from test_suite.plugins.sensor_failure.monitor import (  # noqa: E402
    SensorFailureResilienceMonitor,
)


# --- fakes -----------------------------------------------------------------
class _FakeMessage:
    def __init__(self, msg_type: str, **fields: Any) -> None:
        self._msg_type = msg_type
        for key, value in fields.items():
            setattr(self, key, value)

    def get_type(self) -> str:
        return self._msg_type

    def to_dict(self) -> dict[str, Any]:
        return {
            **{k: v for k, v in self.__dict__.items() if k != "_msg_type"},
            "mavpackettype": self._msg_type,
        }



class _FakeMaster:
    """Scripted MAVLink master that mirrors pymavlink semantics closely enough
    for the resilience monitor + fault injector:

    - `recv_match(type=...)` honors the type filter and only consumes a matching
      message, leaving non-matching telemetry in the buffer (real pymavlink does
      not discard non-matching messages). This is what keeps a PARAM_VALUE
      readback from eating the GLOBAL_POSITION_INT/ATTITUDE stream.
    - `param_set_send` records the call and queues a confirming PARAM_VALUE so
      the readback loop succeeds.
    """

    def __init__(self, messages: list[_FakeMessage]) -> None:
        self._messages: deque[_FakeMessage] = deque(messages)
        self.target_system = 1
        self.target_component = 1
        self.param_sets: list[tuple[str, float]] = []
        # The SITL-side stored param values. A PARAM_REQUEST_READ echoes the
        # CURRENT stored value (= the last set value), never a stale default.
        self._stored: dict[str, float] = {}
        self.mav = self  # so master.mav.param_set_send works

    def recv_match(self, type=None, blocking=False, timeout=None):  # noqa: ANN001
        wanted = None
        if type is not None:
            wanted = {type} if isinstance(type, str) else set(type)
        for i, msg in enumerate(self._messages):
            if wanted is None or msg.get_type() in wanted:
                del self._messages[i]
                return msg
        return None

    # mav.* surface used by mavlink_fault
    def param_set_send(self, tgt, comp, pid, value, ptype):  # noqa: ANN001
        name = pid.decode("ascii") if isinstance(pid, bytes) else str(pid)
        self.param_sets.append((name, float(value)))
        self._stored[name] = float(value)
        # Echo a confirming PARAM_VALUE so the readback succeeds.
        self._messages.append(
            _FakeMessage("PARAM_VALUE", param_id=name, param_value=float(value))
        )

    def param_request_read_send(self, tgt, comp, pid, idx):  # noqa: ANN001
        # Mirror SITL: echo the CURRENT stored value (default 0.0 if never set)
        # so provenance snapshots/readbacks resolve and never disagree with a
        # value we just set.
        name = pid.decode("ascii") if isinstance(pid, bytes) else str(pid)
        self._messages.append(
            _FakeMessage("PARAM_VALUE", param_id=name,
                         param_value=self._stored.get(name, 0.0))
        )


class _FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _hb(armed: bool, mode: str = "AUTO") -> _FakeMessage:
    base_mode = 128 if armed else 0  # MAV_MODE_FLAG_SAFETY_ARMED = 128
    return _FakeMessage("HEARTBEAT", base_mode=base_mode, mode_name=mode,
                        custom_mode=0)


def _attitudes(n: int, *, roll: float, pitch: float) -> list[_FakeMessage]:
    """N ATTITUDE messages (radians) so the classifier has enough samples."""
    return [_FakeMessage("ATTITUDE", roll=roll, pitch=pitch, yaw=0.0) for _ in range(n)]


def _gpi(lat_e7: int, lon_e7: int, relalt_mm: int, *, vx=2000, vy=0) -> _FakeMessage:
    """A GLOBAL_POSITION_INT (lat/lon 1e7 deg, relalt mm, vel cm/s)."""
    return _FakeMessage("GLOBAL_POSITION_INT", lat=lat_e7, lon=lon_e7,
                        relative_alt=relalt_mm, vx=vx, vy=vy)


def _ctx(case: TestCase, root: Path, master: _FakeMaster) -> AttemptContext:
    attempt_dir = defaults.attempt_dir(root, case.case_id, 1)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    ctx = AttemptContext(
        case=case,
        campaign_root=root,
        attempt_dir=attempt_dir,
        attempt_index=1,
        target_run_index=1,
        start_wall_s=0.0,
        start_monotonic_s=0.0,
    )
    ctx.extra["mavlink_master"] = master
    ctx.extra["fault_case"] = gps_cases.CASES_BY_ID[case.case_id]
    return ctx


def _gps_case(case_id: str, *, inject_wp: int = 6, window_s: float = 10.0) -> TestCase:
    fc = gps_cases.CASES_BY_ID[case_id]
    return TestCase(
        suite_name="sensor_failure",
        case_id=case_id,
        parameters={
            "sensor": fc.sensor, "mode": fc.mode, "verdict_mode": fc.verdict_mode,
            "inject_params": dict(fc.inject), "baseline_params": dict(fc.baseline),
            "injection_waypoint": inject_wp, "post_inject_window_s": window_s,
        },
        acceptance_target_runs=3,
    )


def _mode_string(msg):  # noqa: ANN001
    return getattr(msg, "mode_name", "UNKNOWN")


# --- case generation -------------------------------------------------------
class CaseGenerationTests(unittest.TestCase):
    def test_three_cases_times_repeats(self) -> None:
        # baseline (control) first, then the two GPS faults.
        cfg = SensorFailureConfig(repeats=3)
        plugin = build_plugin(cfg)
        cases = list(plugin.case_generator.iter_cases())
        self.assertEqual(
            ["gps_baseline", "gps_disable", "gps_glitch_50m"],
            [c.case_id for c in cases],
        )
        for c in cases:
            self.assertEqual(3, c.acceptance_target_runs)
            self.assertEqual("sensor_failure", c.suite_name)

    def test_baseline_injects_no_fault(self) -> None:
        self.assertEqual({}, gps_cases.CASES_BY_ID["gps_baseline"].inject)
        self.assertEqual("baseline", gps_cases.CASES_BY_ID["gps_baseline"].verdict_mode)

    def test_case_selection_subset(self) -> None:
        cfg = SensorFailureConfig(case_ids=("gps_glitch_50m",), repeats=2)
        plugin = build_plugin(cfg)
        cases = list(plugin.case_generator.iter_cases())
        self.assertEqual(["gps_glitch_50m"], [c.case_id for c in cases])

    def test_glitch_offsets_are_degrees_not_metres(self) -> None:
        # 50 m must convert to a small fraction of a degree, NOT 50.0 (the old
        # 021 design's wrong example). Latitude offset ~0.000449 deg.
        inject = gps_cases.CASES_BY_ID["gps_glitch_50m"].inject
        self.assertAlmostEqual(inject[defaults.SIM_GPS1_GLTCH_X], 50.0 / 111320.0, places=7)
        self.assertLess(inject[defaults.SIM_GPS1_GLTCH_X], 0.001)
        self.assertEqual(inject[defaults.SIM_GPS1_GLTCH_Z], 0.0)

    def test_disable_sets_enable_zero(self) -> None:
        inject = gps_cases.CASES_BY_ID["gps_disable"].inject
        self.assertEqual({defaults.SIM_GPS1_ENABLE: 0.0}, inject)


# --- stimulus provenance ---------------------------------------------------
class StimulusProvenanceTests(unittest.TestCase):
    def test_apply_writes_run_config_and_fault_injection(self) -> None:
        from test_suite.plugins.sensor_failure.stimulus import SensorFailureStimulus
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = SensorFailureConfig(campaign_root=root)
            case = _gps_case("gps_disable")
            master = _FakeMaster([])
            ctx = _ctx(case, root, master)
            result = SensorFailureStimulus(cfg).apply(case, ctx)
            self.assertEqual("sim_gps_param_fault", result["kind"])
            self.assertEqual("monitor_stage", result["applied_at"])
            # Provenance artifacts exist.
            self.assertTrue((ctx.attempt_dir / "run_config.json").exists())
            self.assertTrue((ctx.attempt_dir / "fault_injection.json").exists())
            # Baseline was asserted via param_set (SIM_GPS1_ENABLE=1).
            self.assertIn((defaults.SIM_GPS1_ENABLE, 1.0), master.param_sets)
            # The mission file was copied for reproducibility.
            self.assertTrue((ctx.attempt_dir / case.mission_file.name).exists()
                            if case.mission_file else True)


# --- mavlink fault injector resilience -------------------------------------
class _ScriptedParamMaster:
    """A param master with a fake clock and controllable echo behavior, so the
    injector's resilience (retry, bounded best-effort) is tested without real
    time or a live SITL."""

    def __init__(self, *, clock, drop_first_n_sets=0, echo_value=True,
                 echo_reads=True):
        self.clock = clock
        self.target_system = 1
        self.target_component = 1
        self.mav = self
        self._q = deque()
        self.set_calls = 0
        self._drop_first_n_sets = drop_first_n_sets
        self._echo_value = echo_value
        self._echo_reads = echo_reads
        self._stored: dict[str, float] = {}

    def param_set_send(self, t, c, pid, value, ptype):  # noqa: ANN001
        self.set_calls += 1
        name = pid.decode("ascii") if isinstance(pid, bytes) else str(pid)
        if self.set_calls <= self._drop_first_n_sets:
            return  # simulate a dropped PARAM_SET (no echo, value not stored)
        self._stored[name] = float(value)
        if self._echo_value:
            self._q.append(("PARAM_VALUE", name, float(value)))

    def param_request_read_send(self, t, c, pid, idx):  # noqa: ANN001
        name = pid.decode("ascii") if isinstance(pid, bytes) else str(pid)
        if self._echo_reads:
            # Echo the current "stored" value: the last successfully-set value,
            # else the unset default (None -> not echoed). This mirrors SITL
            # where a dropped PARAM_SET leaves the old value in place.
            stored = getattr(self, "_stored", {}).get(name)
            if stored is not None:
                self._q.append(("PARAM_VALUE", name, stored))

    def recv_match(self, type=None, blocking=False, timeout=None):  # noqa: ANN001
        wanted = ({type} if isinstance(type, str) else set(type)) if type else None
        for i, (mt, name, val) in enumerate(self._q):
            if wanted is None or mt in wanted:
                del self._q[i]
                m = _FakeMessage(mt, param_id=name, param_value=val)
                return m
        # No matching message: advance the fake clock so bounded loops terminate.
        if timeout:
            self.clock.advance(float(timeout))
        return None


class MavlinkFaultResilienceTests(unittest.TestCase):
    def test_set_param_retries_after_dropped_set(self) -> None:
        from test_suite.plugins.sensor_failure import mavlink_fault
        clock = _FakeClock()
        # First PARAM_SET is dropped (no echo); the retry must confirm.
        master = _ScriptedParamMaster(clock=clock, drop_first_n_sets=1)
        # Use a non-zero target so a stale/default read cannot accidentally
        # confirm: only the retried, stored set value can match.
        confirmed = mavlink_fault.set_param(
            master, "SIM_GPS1_NUMSATS", 4.0, clock=clock,
        )
        self.assertEqual(4.0, confirmed)
        self.assertGreaterEqual(master.set_calls, 2)  # retried at least once

    def test_set_param_raises_when_never_confirmed(self) -> None:
        from test_suite.plugins.sensor_failure import mavlink_fault
        clock = _FakeClock()
        # Never echo the set value: confirmation must fail (not hang forever).
        master = _ScriptedParamMaster(clock=clock, echo_value=False, echo_reads=False)
        with self.assertRaises(TimeoutError):
            mavlink_fault.set_param(
                master, "SIM_GPS1_ENABLE", 0.0, clock=clock, max_attempts=2,
            )
        # Bounded: 2 attempts x 5 s readback budget, on the FAKE clock only.
        self.assertLessEqual(clock.t - 1000.0, 2 * 5.0 + 1.0)

    def test_snapshot_params_is_bounded_when_params_missing(self) -> None:
        from test_suite.plugins.sensor_failure import mavlink_fault
        clock = _FakeClock()
        master = _ScriptedParamMaster(clock=clock, echo_reads=False)
        snap = mavlink_fault.snapshot_params(
            master, ("A", "B", "C", "D", "E"), total_budget_s=4.0, clock=clock,
        )
        # All missing -> None, and the TOTAL fake-clock cost is the shared budget,
        # NOT 5 x per-param timeout.
        self.assertEqual({"A": None, "B": None, "C": None, "D": None, "E": None}, snap)
        self.assertLessEqual(clock.t - 1000.0, 4.0 + 1.0)

    def test_set_param_ignores_interleaved_telemetry(self) -> None:
        from test_suite.plugins.sensor_failure import mavlink_fault
        clock = _FakeClock()
        master = _ScriptedParamMaster(clock=clock)
        # Inject unrelated telemetry into the queue; it must NOT be consumed or
        # block the PARAM_VALUE match.
        master._q.append(("HEARTBEAT", "", 0.0))
        master._q.append(("GLOBAL_POSITION_INT", "", 0.0))
        confirmed = mavlink_fault.set_param(
            master, "SIM_GPS1_ENABLE", 0.0, clock=clock,
        )
        self.assertEqual(0.0, confirmed)
        # The non-PARAM_VALUE telemetry is still in the buffer (not dropped).
        remaining = {mt for mt, _, _ in master._q}
        self.assertIn("HEARTBEAT", remaining)
        self.assertIn("GLOBAL_POSITION_INT", remaining)


# --- resilience monitor (fake master) --------------------------------------
class ResilienceMonitorTests(unittest.TestCase):
    def _build_monitor(self, window_s: float, clock: _FakeClock):
        from test_suite.plugins.sensor_failure import mavlink_fault
        return SensorFailureResilienceMonitor(
            injection_waypoint=6,
            post_inject_window_s=window_s,
            mission_timeout_s=600.0,
            inject_fault=mavlink_fault.set_params,
            clamp_timeout_to_slot=lambda req, dl, **kw: req,
            clock=clock,
        )

    def test_injects_fault_at_trigger_waypoint(self) -> None:
        messages = [
            _hb(True), _FakeMessage("MISSION_CURRENT", seq=3),
            _FakeMessage("MISSION_CURRENT", seq=6),  # trigger
            _FakeMessage("GLOBAL_POSITION_INT", lat=-353632620, lon=1491652370,
                         relative_alt=100000),
            _FakeMessage("ATTITUDE", roll=0.05, pitch=0.02),
        ]
        state, result, master = self._drive("gps_disable", messages)
        self.assertTrue(state["fault_injected"])
        self.assertIn((defaults.SIM_GPS1_ENABLE, 0.0), master.param_sets)
        self.assertTrue(result.completed)
        # Fault must NOT be injected before the trigger waypoint (seq 3 < 6).
        self.assertEqual(6, state["fault_inject_seq"])

    def _drive(self, case_id, messages, window_s=5.0):
        clock = _FakeClock()
        master = _FakeMaster(list(messages))
        real_recv = master.recv_match

        def recv(type=None, blocking=False, timeout=None):  # noqa: ANN001
            msg = real_recv(type=type, blocking=blocking, timeout=timeout)
            if msg is None:
                # Telemetry exhausted: advance past the observation window so the
                # monitor stops cleanly instead of spinning.
                clock.advance(window_s * 2)
            return msg
        master.recv_match = recv  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = _gps_case(case_id, window_s=window_s)
            ctx = _ctx(case, root, master)
            with mock.patch(
                "test_suite.plugins.sensor_failure.monitor.mavutil.mode_string_v10",
                side_effect=_mode_string,
            ):
                monitor = self._build_monitor(window_s=window_s, clock=clock)
                result = monitor.run(case, ctx)
            return ctx.extra["resilience_state"], result, master

    def test_disable_safe_degraded_is_accepted_and_classified(self) -> None:
        # After GPS denial the vehicle keeps flying under control (attitude near
        # its pre-fault range) but dead-reckons / drifts. Behavior = safe_degraded,
        # accepted = True. This is the real result type for ArduPlane GPS loss.
        messages = (
            [_hb(True, "AUTO")]
            # pre-fault: established flight, normal attitude
            + _attitudes(8, roll=0.4, pitch=0.15)
            + [_gpi(-353632620, 1491652370, 100000)] * 3
            + [_FakeMessage("MISSION_CURRENT", seq=6)]  # trigger
            # post-fault: still controlled, slightly higher roll, large drift
            # (~0.012 deg latitude ~= 1.3 km from the inject fix)
            + _attitudes(8, roll=0.55, pitch=0.2)
            + [_gpi(-352734620, 1491652370, 98000)] * 3  # ~1 km lat offset
        )
        state, result, master = self._drive("gps_disable", messages)
        self.assertTrue(state["fault_injected"])
        behavior, accepted, status, reasons = _classify(state)
        self.assertTrue(accepted, msg=reasons)
        self.assertEqual("safe_degraded", behavior)
        # Dead-reckoning drift is recorded but NOT a failure for total GPS loss.
        self.assertGreater(state["post_inject_max_excursion_m"], 1000.0)

    def test_disable_tumble_is_unsafe(self) -> None:
        # Attitude diverges far beyond the pre-fault envelope -> unsafe.
        messages = (
            [_hb(True, "AUTO")]
            + _attitudes(8, roll=0.3, pitch=0.1)
            + [_gpi(-353632620, 1491652370, 100000)] * 3
            + [_FakeMessage("MISSION_CURRENT", seq=6)]
            + _attitudes(8, roll=2.6, pitch=1.4)  # ~149deg roll tumble
            + [_gpi(-353632620, 1491652370, 90000)] * 3
        )
        state, result, master = self._drive("gps_disable", messages)
        behavior, accepted, status, reasons = _classify(state)
        self.assertTrue(accepted)  # still a clean measurement
        self.assertEqual("unsafe", behavior)
        self.assertEqual("unsafe_divergence", status)

    def test_disable_altitude_collapse_is_unsafe(self) -> None:
        # Altitude collapses far below the pre-fault floor -> unsafe.
        messages = (
            [_hb(True, "AUTO")]
            + _attitudes(8, roll=0.3, pitch=0.1)
            + [_gpi(-353632620, 1491652370, 100000)] * 3  # pre-fault ~100 m
            + [_FakeMessage("MISSION_CURRENT", seq=6)]
            + _attitudes(8, roll=0.4, pitch=0.15)
            + [_gpi(-353632620, 1491652370, 40000)] * 3  # sank to 40 m (-60 m)
        )
        state, result, master = self._drive("gps_disable", messages)
        behavior, accepted, status, reasons = _classify(state)
        self.assertEqual("unsafe", behavior)

    def test_glitch_bounded_is_safe_degraded(self) -> None:
        messages = (
            [_hb(True, "AUTO")]
            + _attitudes(8, roll=0.3, pitch=0.1)
            + [_gpi(-353632620, 1491652370, 100000)] * 3  # pre-fault fix
            + [_FakeMessage("MISSION_CURRENT", seq=6)]
            + _attitudes(8, roll=0.45, pitch=0.15)
            + [_gpi(-353632800, 1491652500, 99000)] * 3  # ~25 m excursion
        )
        state, result, master = self._drive("gps_glitch_50m", messages)
        behavior, accepted, status, reasons = _classify(state)
        self.assertTrue(accepted, msg=reasons)
        self.assertIn(behavior, ("safe_degraded", "nominal"))
        self.assertLess(state["post_inject_max_excursion_m"], 100.0)

    def test_baseline_is_nominal_and_accepted(self) -> None:
        # No fault injected; the trigger still stamps t=0 and the control envelope
        # is captured. Behavior = nominal, accepted = True, no param_set issued.
        messages = (
            [_hb(True, "AUTO")]
            + _attitudes(8, roll=0.3, pitch=0.1)
            + [_gpi(-353632620, 1491652370, 100000)] * 3
            + [_FakeMessage("MISSION_CURRENT", seq=6)]
            + _attitudes(8, roll=0.35, pitch=0.12)
            + [_gpi(-353632700, 1491652400, 100500)] * 3
        )
        state, result, master = self._drive("gps_baseline", messages)
        self.assertTrue(state["is_baseline"])
        self.assertTrue(state["fault_injected"])  # trigger stamped
        self.assertEqual([], master.param_sets)   # NO fault param set
        behavior, accepted, status, reasons = _classify(state)
        self.assertTrue(accepted, msg=reasons)
        self.assertEqual("nominal", behavior)

    def test_no_injection_is_not_characterized(self) -> None:
        # Vehicle never reaches the trigger waypoint -> no clean measurement.
        messages = [
            _hb(True, "AUTO"),
            _FakeMessage("MISSION_CURRENT", seq=3),
            _FakeMessage("MISSION_CURRENT", seq=4),
        ]
        state, result, master = self._drive("gps_disable", messages, window_s=2.0)
        self.assertFalse(state["fault_injected"])
        self.assertFalse(result.completed)
        behavior, accepted, status, reasons = _classify(state)
        self.assertFalse(accepted)
        self.assertEqual("not_characterized", behavior)


# --- verdict policy --------------------------------------------------------
class VerdictPolicyTests(unittest.TestCase):
    def _verdict(self, *, accepted, behavior, status):
        from test_suite.core.models import AnalysisResult
        ar = AnalysisResult(
            analyzer_name="sensor_failure_resilience_analysis",
            ok=True,
            summary={"accepted": accepted, "behavior": behavior, "status": status,
                     "reasons": []},
        )
        mr = MonitorResult(completed=True, reason="fault_injected", duration_s=10.0)
        return SensorFailureVerdictPolicy().classify(
            _gps_case("gps_disable"), mr, [ar],
        )

    def test_accepted_characterization_maps_to_success(self) -> None:
        # A clean characterization succeeds regardless of behavior class — even
        # 'unsafe' is a valid measurement of what the vehicle did.
        for behavior in ("nominal", "safe_degraded", "unsafe"):
            v = self._verdict(accepted=True, behavior=behavior, status=behavior)
            self.assertEqual(VerdictClass.SUCCESS, v.klass, msg=behavior)
            self.assertEqual(behavior, v.metadata["behavior"])

    def test_not_characterized_is_retryable(self) -> None:
        v = self._verdict(accepted=False, behavior="not_characterized",
                          status="not_characterized_no_trigger")
        self.assertEqual(VerdictClass.FAILED_RETRYABLE, v.klass)
        self.assertTrue(v.retryable)


# --- analyzer run-alias symlink --------------------------------------------
class AnalyzerRunAliasTests(unittest.TestCase):
    """An accepted run must create the curated `runs/run_NN -> attempt_MMM`
    symlink, not just name it in the manifest. (Regression: the symlink creation
    was missing while the manifest claimed a run_alias.)"""

    def _run_analyzer(self, root: Path, *, target_run_index: int):
        from test_suite.plugins.sensor_failure.analyzers import SensorFailureAnalyzer
        cfg = SensorFailureConfig(campaign_root=root)
        case = _gps_case("gps_disable")
        attempt_dir = defaults.attempt_dir(root, case.case_id, target_run_index)
        attempt_dir.mkdir(parents=True, exist_ok=True)
        ctx = AttemptContext(
            case=case, campaign_root=root, attempt_dir=attempt_dir,
            attempt_index=target_run_index, target_run_index=target_run_index,
            start_wall_s=0.0, start_monotonic_s=0.0,
        )
        # A clean, accepted safe_degraded state (enough samples, bounded).
        ctx.extra["resilience_state"] = {
            "verdict_mode": "hard_denial", "is_baseline": False,
            "fault_injected": True, "fault_inject_seq": 6,
            "confirmed_inject_params": {"SIM_GPS1_ENABLE": 0.0},
            "mode_at_inject": "AUTO", "mode_after_inject": "AUTO",
            "mode_changed_after_inject": False, "modes_seen": ["AUTO"],
            "pre_inject_min_relalt_m": 98.0, "pre_inject_max_relalt_m": 102.0,
            "pre_inject_max_roll_deg": 25.0, "pre_inject_max_pitch_deg": 10.0,
            "pre_inject_max_groundspeed_ms": 22.0, "pre_inject_attitude_samples": 12,
            "post_inject_min_relalt_m": 95.0, "post_inject_max_relalt_m": 101.0,
            "post_inject_max_roll_deg": 30.0, "post_inject_max_pitch_deg": 12.0,
            "post_inject_max_groundspeed_ms": 23.0, "post_inject_attitude_samples": 12,
            "post_inject_max_excursion_m": 120.0, "disarmed": False,
            "timed_out": False, "observation_duration_s": 90.0, "notes": [],
        }
        with mock.patch(
            "test_suite.plugins.sensor_failure.analyzers.collect_bin_log",
            return_value=None,
        ), mock.patch(
            "test_suite.plugins.sensor_failure.analyzers.time.sleep",
        ):
            SensorFailureAnalyzer(cfg).analyze(case, ctx)
        return case, attempt_dir

    def test_accepted_run_creates_run_alias_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case, attempt_dir = self._run_analyzer(root, target_run_index=1)
            alias = defaults.case_runs_dir(root, case.case_id) / defaults.run_alias(1)
            self.assertTrue(alias.is_symlink(), "run_01 symlink was not created")
            self.assertEqual(attempt_dir.resolve(), alias.resolve())

    def test_run_alias_is_idempotent_across_attempts(self) -> None:
        # A second accepted run for the next rep must create its own alias and
        # not clobber the first.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run_analyzer(root, target_run_index=1)
            self._run_analyzer(root, target_run_index=2)
            runs = defaults.case_runs_dir(root, "gps_disable")
            self.assertTrue((runs / "run_01").is_symlink())
            self.assertTrue((runs / "run_02").is_symlink())


# --- manifest acceptance ---------------------------------------------------
class ManifestAcceptanceTests(unittest.TestCase):
    def test_accepted_rows_count_regardless_of_behavior(self) -> None:
        # A clean characterization counts as accepted even when behavior=unsafe;
        # a not-characterized row does not.
        from test_suite.core.models import AttemptRecord, AttemptStatus
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = SensorFailureManifest(root)
            case = _gps_case("gps_disable")
            attempt_dir = defaults.attempt_dir(root, case.case_id, 1)
            attempt_dir.mkdir(parents=True, exist_ok=True)
            man.append_attempt(AttemptRecord(
                attempt_id="gps_disable__rep_01__attempt_001",
                suite_name="sensor_failure",
                case_id="gps_disable",
                target_run_index=1,
                attempt_index=1,
                status=AttemptStatus.SUCCESS,
                plugin_manifest_fields={
                    "attempt_id": "gps_disable__rep_01__attempt_001",
                    "case_id": "gps_disable", "status": "unsafe_divergence",
                    "behavior": "unsafe", "accepted": True,
                    "attempt_index": 1, "target_run_index": 1,
                    "attempt_dir": str(attempt_dir),
                },
            ))
            self.assertEqual(1, man.accepted_count(case))  # unsafe is still measured
            man.append_attempt(AttemptRecord(
                attempt_id="gps_disable__rep_02__attempt_002",
                suite_name="sensor_failure", case_id="gps_disable",
                target_run_index=2, attempt_index=2,
                status=AttemptStatus.FAILED,
                plugin_manifest_fields={
                    "attempt_id": "gps_disable__rep_02__attempt_002",
                    "case_id": "gps_disable", "status": "not_characterized_no_trigger",
                    "behavior": "not_characterized", "accepted": False,
                    "attempt_index": 2, "target_run_index": 2,
                },
            ))
            self.assertEqual(1, man.accepted_count(case))  # not-characterized excluded

    def test_stale_running_recovered_as_interrupted(self) -> None:
        from test_suite.core.models import AttemptRecord, AttemptStatus
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = SensorFailureManifest(root)
            case = _gps_case("gps_disable")
            man.append_attempt(AttemptRecord(
                attempt_id="gps_disable__rep_01__attempt_001",
                suite_name="sensor_failure", case_id="gps_disable",
                target_run_index=1, attempt_index=1,
                status=AttemptStatus.RUNNING,
                plugin_manifest_fields={
                    "attempt_id": "gps_disable__rep_01__attempt_001",
                    "case_id": "gps_disable", "status": "running",
                    "accepted": False, "attempt_index": 1, "target_run_index": 1,
                },
            ))
            # Reconcile by reading accepted_count -> running becomes interrupted.
            self.assertEqual(0, man.accepted_count(case))
            data = man.load()
            statuses = [a["status"] for a in data["attempts"]]
            self.assertIn("interrupted", statuses)


# --- stack cleanup / orphan reaping ----------------------------------------
class StackCleanupTests(unittest.TestCase):
    """The known orphan gap: sim_vehicle.py spawns mavproxy in its own session,
    and launch.sh `pkill -x mavproxy` never matches the real process name, so
    mavproxy orphans and corrupts the next attempt's telemetry. The plugin
    cleanup must reap the whole process GROUP of each launched child."""

    def test_reap_process_group_kills_all_descendants(self) -> None:
        from test_suite.plugins.sensor_failure.environment import (
            SensorFailureEnvironment,
        )
        # A session leader with two grandchildren (mirrors sim_vehicle ->
        # arduplane + mavproxy).
        proc = subprocess.Popen(
            ["bash", "-c", "sleep 60 & sleep 60 & wait"],
            start_new_session=True,
        )
        try:
            time.sleep(0.4)
            pgid = os.getpgid(proc.pid)
            before = subprocess.run(
                ["pgrep", "-g", str(pgid)], capture_output=True, text=True,
            ).stdout.split()
            self.assertGreaterEqual(len(before), 2)

            SensorFailureEnvironment._reap_process_group(proc)
            time.sleep(0.4)
            after = subprocess.run(
                ["pgrep", "-g", str(pgid)], capture_output=True, text=True,
            ).stdout.split()
            self.assertEqual([], after, msg=f"orphans left: {after}")
        finally:
            try:
                os.killpg(os.getpgid(proc.pid), 9)
            except Exception:
                pass

    def test_reap_process_group_tolerates_none_and_dead(self) -> None:
        from test_suite.plugins.sensor_failure.environment import (
            SensorFailureEnvironment,
        )
        # None handle and an already-dead process must not raise.
        SensorFailureEnvironment._reap_process_group(None)
        proc = subprocess.Popen(["bash", "-c", "true"], start_new_session=True)
        proc.wait()
        SensorFailureEnvironment._reap_process_group(proc)  # should be a no-op


if __name__ == "__main__":
    unittest.main()
