from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.mechanism_gate import (  # noqa: E402
    RunSignals,
    evaluate,
    extract_schedule_signals_from_bin,
    extract_signals_from_bin,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.analyzers import (  # noqa: E402
    analyze_mechanism_bin,
)

# A real protected-stack run from the ADR-0015 investigation. Present in dev
# trees; tests that need it are skipped if the BIN is absent (e.g. clean CI).
MAX28_BIN = (
    ROOT
    / "var/runs/envelope_matrix_max28_n3/_sitl_state"
    / "ratio_bias_ramp_p10_to_p200_headwind/attempt_001/logs/00000001.BIN"
)


class _FakeMessage:
    def __init__(self, kind: str, timestamp: float, **data: object) -> None:
        self._kind = kind
        self._timestamp = timestamp
        self._data = {"mavpackettype": kind, **data}

    def get_type(self) -> str:
        return self._kind

    def to_dict(self) -> dict[str, object]:
        return dict(self._data)


class _FakeReader:
    def __init__(self, messages: list[_FakeMessage]) -> None:
        self._messages = iter(messages)

    def recv_match(self, **_kwargs: Any) -> _FakeMessage | None:
        return next(self._messages, None)


def _protected_signals(**over: object) -> RunSignals:
    sig = RunSignals(
        ahrs_wind_max=15.0,
        raw_arsp_late=37.0,
        believed_as_late=22.1,
        gnd_speed_late=7.9,
        tecs_target_late=15.5,
        commanded_cruise_expected=15.0,
        arsp_use_all_one=True,
        raw_arsp_max=37.2,
        eas2tas_late=1.0,
        aligned_u1_sample_count=100,
        clamp_exercised_sample_count=100,
        clamp_error_mean_mps=0.8,
        tracking_error_mean_mps=14.9,
        demand_error_mean_mps=0.5,
    )
    for key, value in over.items():
        setattr(sig, key, value)
    return sig


class MechanismGateLogicTests(unittest.TestCase):
    def test_protected_run_is_interpretable(self) -> None:
        res = evaluate(_protected_signals(), tier="protected", expected_wind_max=15.0)
        self.assertTrue(res.interpretable, res.as_dict())
        self.assertEqual("clamp_verified", res.as_dict()["observation_quality_class"])

    def test_protected_run_judged_as_diagnostic_FAILS(self) -> None:
        # This is the ADR-0015 guard: the same clamped run must NOT pass as a
        # diagnostic (clamp-off) run, because believed (22) != raw (37).
        res = evaluate(_protected_signals(), tier="diagnostic", expected_wind_max=0.0)
        self.assertFalse(res.interpretable)
        believed = next(c for c in res.checks if c.name == "unclamped_tracking")
        self.assertFalse(believed.ok)

    def test_wrong_wind_max_readback_fails(self) -> None:
        # Intended diagnostic (0) but the vehicle booted with 15 -> must fail.
        res = evaluate(_protected_signals(), tier="diagnostic", expected_wind_max=0.0)
        c1 = next(c for c in res.checks if c.name == "ahrs_wind_max_readback")
        self.assertFalse(c1.ok)

    def test_diagnostic_run_tracking_raw_is_interpretable(self) -> None:
        sig = _protected_signals(
            ahrs_wind_max=0.0,
            believed_as_late=36.5,
            tracking_error_mean_mps=0.5,
        )
        res = evaluate(sig, tier="diagnostic", expected_wind_max=0.0)
        self.assertTrue(res.interpretable, res.as_dict())

    def test_clamp_not_exercised_is_not_interpretable(self) -> None:
        # If raw never pushed past gnd+wind_max, the protected mechanism was not
        # exercised, so the run cannot confirm clamp behaviour.
        sig = _protected_signals(
            raw_arsp_late=18.0,
            raw_arsp_max=18.0,
            believed_as_late=18.0,
            clamp_exercised_sample_count=0,
            clamp_error_mean_mps=None,
        )
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        self.assertFalse(res.interpretable)

    def test_do_change_speed_override_is_flagged(self) -> None:
        # Intended cruise 18, but TECS target stuck at 15.5 (stale DO_CHANGE_SPEED)
        # -> gap 2.5 m/s exceeds the 1.5 tolerance, so override is detected.
        sig = _protected_signals(
            commanded_cruise_expected=18.0,
            tecs_target_late=15.5,
            demand_error_mean_mps=-2.5,
        )
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        cc = next(c for c in res.checks if c.name == "commanded_cruise")
        self.assertFalse(cc.ok)

    def test_matching_cruise_passes(self) -> None:
        # No override: intended 14, target ~14.5 (small TECS compensation) -> ok.
        sig = _protected_signals(commanded_cruise_expected=14.0, tecs_target_late=14.6)
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        cc = next(c for c in res.checks if c.name == "commanded_cruise")
        self.assertTrue(cc.ok)

    def test_source_arithmetic_uses_eas2tas(self) -> None:
        # gnd=8, WIND_MAX=15 and E2T=1.05 gives an upper EAS bound of 21.90.
        sig = _protected_signals(
            gnd_speed_late=8.0,
            eas2tas_late=1.05,
            believed_as_late=21.9,
            clamp_error_mean_mps=0.1,
        )
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        self.assertEqual("clamp_verified", res.mechanism_status)
        self.assertTrue(res.interpretable, res.as_dict())

    def test_sensor_rejected_before_verification_is_distinct(self) -> None:
        sig = _protected_signals(
            aligned_u1_sample_count=0,
            clamp_exercised_sample_count=0,
            clamp_error_mean_mps=None,
            sensor_disable_intervals=[{"start_s": 1.0, "end_s": None, "duration_s": None}],
        )
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        self.assertEqual("sensor_rejected_before_verification", res.mechanism_status)
        mechanism = next(c for c in res.checks if c.name == "protected_clamp")
        self.assertIn("did not exercise", mechanism.detail)

    def test_missing_third_signal_fails(self) -> None:
        sig = _protected_signals(tecs_target_late=None)
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        present = next(c for c in res.checks if c.name == "time_aligned_signals_present")
        self.assertFalse(present.ok)


class MechanismGateScheduleExtractionTests(unittest.TestCase):
    def test_parm_clock_anchor_and_ctun_source_type_control_clamp_rows(self) -> None:
        messages = [
            _FakeMessage("PARM", 1.0, Name="AHRS_WIND_MAX", Value=15.0),
            _FakeMessage("PARM", 2.0, Name="SIM_ARSPD_RATIO", Value=1.99),
            _FakeMessage("PARM", 100.0, Name="SIM_ARSPD_RATIO", Value=0.5),
            _FakeMessage("PARM", 160.0, Name="SIM_ARSPD_RATIO", Value=1.99),
        ]
        # Twelve genuine sensor-source rows verify the upper clamp exactly.
        for index in range(12):
            timestamp = 101.0 + index
            messages.extend(
                [
                    _FakeMessage(
                        "ARSP", timestamp, I=0, Airspeed=40.0, U=1, H=1, Hp=0.5, TR=8.0
                    ),
                    _FakeMessage("GPS", timestamp, I=0, Spd=20.0),
                    _FakeMessage("TECS", timestamp, spdem=15.0),
                    _FakeMessage("CTUN", timestamp, As=35.0, AsT=1, E2T=1.0, ThO=40.0),
                ]
            )
        # AHRS then switches to synthetic airspeed while ARSP.U still says the
        # sensor parameter is enabled.  These rows must not contaminate the
        # raw-to-believed clamp calculation.
        for index in range(12):
            timestamp = 121.0 + index
            messages.extend(
                [
                    _FakeMessage(
                        "ARSP", timestamp, I=0, Airspeed=40.0, U=1, H=1, Hp=0.2, TR=9.0
                    ),
                    _FakeMessage("GPS", timestamp, I=0, Spd=20.0),
                    _FakeMessage("TECS", timestamp, spdem=15.0),
                    _FakeMessage("CTUN", timestamp, As=14.0, AsT=3, E2T=1.0, ThO=60.0),
                ]
            )
        messages.sort(key=lambda message: message._timestamp)
        events = [
            {
                "timestamp_utc": "2026-01-01T00:00:00+00:00",
                "readback_values": {"SIM_ARSPD_RATIO": 1.99},
                "step": {"event_index": 1, "phase": "baseline_settle", "bias_percent": 0},
            },
            {
                # Deliberately unrelated wall time: the BIN PARM at t=100 is authoritative.
                "timestamp_utc": "2026-01-01T00:20:00+00:00",
                "readback_values": {"SIM_ARSPD_RATIO": 0.5},
                "step": {
                    "event_index": 2,
                    "phase": "fault_observe",
                    "bias_percent": 100,
                    "observe_s": 60.0,
                },
            },
            {
                "timestamp_utc": "2026-01-01T00:21:00+00:00",
                "readback_values": {"SIM_ARSPD_RATIO": 1.99},
                "step": {
                    "event_index": 3,
                    "phase": "baseline_settle",
                    "bias_percent": 0,
                    "observe_s": 60.0,
                },
            },
        ]

        windows, errors = extract_schedule_signals_from_bin(
            "unused.BIN",
            expected_cruise=15.0,
            injection_events=events,
            reader=lambda _path: _FakeReader(messages),
        )

        self.assertEqual([], errors)
        fault = next(window for window in windows if window.phase == "fault_observe")
        self.assertEqual(100.0, fault.window_start_s)
        self.assertEqual(160.0, fault.window_end_s)
        self.assertEqual(12, fault.signals.aligned_sensor_sample_count)
        self.assertEqual(24, fault.signals.aligned_u1_sample_count)
        self.assertEqual([1, 3], fault.signals.airspeed_source_types_present)
        self.assertTrue(fault.signals.sensor_source_rejection_intervals)
        self.assertEqual(12, fault.signals.clamp_exercised_sample_count)
        self.assertAlmostEqual(0.0, fault.signals.clamp_error_mean_mps or 0.0)
        result = evaluate(fault.signals, tier="protected", expected_wind_max=15.0)
        self.assertTrue(result.interpretable, result.as_dict())
        self.assertEqual("clamp_verified", result.mechanism_status)

        aggregate = analyze_mechanism_bin(
            "unused.BIN",
            injection_events=events,
            expected_cruise=15.0,
            tier="protected",
            expected_wind_max=15.0,
            schedule_kind="pulse_ladder",
            reader=lambda _path: _FakeReader(messages),
        )
        self.assertTrue(aggregate["interpretable"], aggregate)
        schedule = aggregate["schedule_analysis"]
        self.assertEqual(1, schedule["fault_window_count"])
        self.assertEqual(100.0, schedule["first_ahrs_source_rejection_bias_percent"])
        self.assertIsNone(schedule["first_arsp_parameter_disable_bias_percent"])
        self.assertEqual([], schedule["matching_errors"])

    def test_ramp_verified_window_not_erased_by_later_rejection(self) -> None:
        # Regression for the Chunk-3 tailwind ramp defect: a ramp attempt that
        # verifies the protected clamp in an earlier fault window and is then
        # pushed into AHRS source rejection in a later, higher-bias window must
        # still report clamp_verified/interpretable.  Previously only
        # schedule_kind="pulse_ladder" got the last-interpretable representative;
        # ramps fell through to evaluated[-1], so the final rejected window
        # erased the earlier verified clamp.
        messages = [
            _FakeMessage("PARM", 1.0, Name="AHRS_WIND_MAX", Value=15.0),
            _FakeMessage("PARM", 2.0, Name="SIM_ARSPD_RATIO", Value=1.99),
            _FakeMessage("PARM", 100.0, Name="SIM_ARSPD_RATIO", Value=0.5),
            _FakeMessage("PARM", 160.0, Name="SIM_ARSPD_RATIO", Value=0.4),
            _FakeMessage("PARM", 220.0, Name="SIM_ARSPD_RATIO", Value=1.99),
        ]
        # First fault window (+100): genuine sensor-source rows verify the clamp.
        for index in range(12):
            timestamp = 101.0 + index
            messages.extend(
                [
                    _FakeMessage("ARSP", timestamp, I=0, Airspeed=40.0, U=1, H=1, Hp=0.5, TR=8.0),
                    _FakeMessage("GPS", timestamp, I=0, Spd=20.0),
                    _FakeMessage("TECS", timestamp, spdem=15.0),
                    _FakeMessage("CTUN", timestamp, As=35.0, AsT=1, E2T=1.0, ThO=40.0),
                ]
            )
        # Second fault window (+120): AHRS rejects the sensor (AsT=3); no clamp rows.
        for index in range(12):
            timestamp = 161.0 + index
            messages.extend(
                [
                    _FakeMessage("ARSP", timestamp, I=0, Airspeed=45.0, U=0, H=0, Hp=0.1, TR=9.0),
                    _FakeMessage("GPS", timestamp, I=0, Spd=20.0),
                    _FakeMessage("TECS", timestamp, spdem=15.0),
                    _FakeMessage("CTUN", timestamp, As=14.0, AsT=3, E2T=1.0, ThO=60.0),
                ]
            )
        messages.sort(key=lambda message: message._timestamp)
        events = [
            {
                "readback_values": {"SIM_ARSPD_RATIO": 1.99},
                "step": {"event_index": 1, "phase": "baseline_settle", "bias_percent": 0},
            },
            {
                "readback_values": {"SIM_ARSPD_RATIO": 0.5},
                "step": {
                    "event_index": 2,
                    "phase": "fault_observe",
                    "bias_percent": 100,
                    "observe_s": 60.0,
                },
            },
            {
                "readback_values": {"SIM_ARSPD_RATIO": 0.4},
                "step": {
                    "event_index": 3,
                    "phase": "fault_observe",
                    "bias_percent": 120,
                    "observe_s": 60.0,
                },
            },
            {
                "readback_values": {"SIM_ARSPD_RATIO": 1.99},
                "step": {
                    "event_index": 4,
                    "phase": "baseline_settle",
                    "bias_percent": 0,
                    "observe_s": 60.0,
                },
            },
        ]

        aggregate = analyze_mechanism_bin(
            "unused.BIN",
            injection_events=events,
            expected_cruise=15.0,
            tier="protected",
            expected_wind_max=15.0,
            schedule_kind="ramp",
            reader=lambda _path: _FakeReader(messages),
        )
        schedule = aggregate["schedule_analysis"]
        self.assertEqual(2, schedule["fault_window_count"])
        # The earlier +100 window verified the clamp and must not be erased.
        self.assertTrue(aggregate["interpretable"], aggregate)
        self.assertEqual("clamp_verified", aggregate["mechanism_status"])
        # The separate AHRS source-rejection threshold is still reported.
        self.assertEqual(120.0, schedule["first_ahrs_source_rejection_bias_percent"])


class MechanismGateRealBinTests(unittest.TestCase):
    @unittest.skipUnless(MAX28_BIN.exists(), "real max28 BIN not present")
    def test_real_max28_bin_is_protected_not_diagnostic(self) -> None:
        sig = extract_signals_from_bin(str(MAX28_BIN), expected_cruise=15.0)
        # mechanism facts confirmed in ADR-0015
        assert sig.ahrs_wind_max is not None
        assert sig.raw_arsp_max is not None
        assert sig.believed_as_late is not None
        self.assertAlmostEqual(sig.ahrs_wind_max, 15.0, places=2)
        self.assertGreater(sig.raw_arsp_max, 30.0)
        self.assertLess(sig.believed_as_late, 25.0)
        self.assertTrue(sig.arsp_use_all_one)

        # passes as protected ...
        prot = evaluate(sig, tier="protected", expected_wind_max=15.0)
        self.assertTrue(prot.interpretable, prot.as_dict())
        # ... and is correctly REJECTED if mislabelled diagnostic
        diag = evaluate(sig, tier="diagnostic", expected_wind_max=0.0)
        self.assertFalse(diag.interpretable)


if __name__ == "__main__":
    unittest.main()
