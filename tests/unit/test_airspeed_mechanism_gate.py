from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.mechanism_gate import (  # noqa: E402
    RunSignals,
    evaluate,
    extract_signals_from_bin,
)

# A real protected-stack run from the ADR-0015 investigation. Present in dev
# trees; tests that need it are skipped if the BIN is absent (e.g. clean CI).
MAX28_BIN = (
    ROOT
    / "var/runs/envelope_matrix_max28_n3/_sitl_state"
    / "ratio_bias_ramp_p10_to_p200_headwind/attempt_001/logs/00000001.BIN"
)


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
    )
    for key, value in over.items():
        setattr(sig, key, value)
    return sig


class MechanismGateLogicTests(unittest.TestCase):
    def test_protected_run_is_interpretable(self) -> None:
        res = evaluate(_protected_signals(), tier="protected", expected_wind_max=15.0)
        self.assertTrue(res.interpretable, res.as_dict())
        self.assertEqual("mechanism_verified", res.as_dict()["observation_quality_class"])

    def test_protected_run_judged_as_diagnostic_FAILS(self) -> None:
        # This is the ADR-0015 guard: the same clamped run must NOT pass as a
        # diagnostic (clamp-off) run, because believed (22) != raw (37).
        res = evaluate(_protected_signals(), tier="diagnostic", expected_wind_max=0.0)
        self.assertFalse(res.interpretable)
        believed = next(c for c in res.checks if c.name == "believed_behaviour")
        self.assertFalse(believed.ok)

    def test_wrong_wind_max_readback_fails(self) -> None:
        # Intended diagnostic (0) but the vehicle booted with 15 -> must fail.
        res = evaluate(_protected_signals(), tier="diagnostic", expected_wind_max=0.0)
        c1 = next(c for c in res.checks if c.name == "ahrs_wind_max_readback")
        self.assertFalse(c1.ok)

    def test_diagnostic_run_tracking_raw_is_interpretable(self) -> None:
        sig = _protected_signals(ahrs_wind_max=0.0, believed_as_late=36.5)
        res = evaluate(sig, tier="diagnostic", expected_wind_max=0.0)
        self.assertTrue(res.interpretable, res.as_dict())

    def test_clamp_not_exercised_is_not_interpretable(self) -> None:
        # If raw never pushed past gnd+wind_max, the protected mechanism was not
        # exercised, so the run cannot confirm clamp behaviour.
        sig = _protected_signals(raw_arsp_late=18.0, raw_arsp_max=18.0, believed_as_late=18.0)
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        self.assertFalse(res.interpretable)

    def test_do_change_speed_override_is_flagged(self) -> None:
        # Intended cruise 18, but TECS target stuck at 15.5 (stale DO_CHANGE_SPEED)
        # -> gap 2.5 m/s exceeds the 1.5 tolerance, so override is detected.
        sig = _protected_signals(commanded_cruise_expected=18.0, tecs_target_late=15.5)
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        cc = next(c for c in res.checks if c.name == "commanded_cruise")
        self.assertFalse(cc.ok)

    def test_matching_cruise_passes(self) -> None:
        # No override: intended 14, target ~14.5 (small TECS compensation) -> ok.
        sig = _protected_signals(commanded_cruise_expected=14.0, tecs_target_late=14.6)
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        cc = next(c for c in res.checks if c.name == "commanded_cruise")
        self.assertTrue(cc.ok)

    def test_missing_third_signal_fails(self) -> None:
        sig = _protected_signals(tecs_target_late=None)
        res = evaluate(sig, tier="protected", expected_wind_max=15.0)
        present = next(c for c in res.checks if c.name == "three_signals_present")
        self.assertFalse(present.ok)


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
