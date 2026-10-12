#!/usr/bin/env python3
"""Unit tests for the numerical decisions in real_flight/analysis_core.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.analysis.real_flight.analysis_core import (  # noqa: E402
    describe,
    dominant_frequency,
    effective_rate_hz,
    hann_psd,
    integrate_band_rms,
    monotonic_increment,
    phase_for_time,
    select_airborne_interval,
    threshold_fraction,
)


class AnalysisCoreTests(unittest.TestCase):
    def test_selects_longest_sustained_airborne_group(self) -> None:
        times = list(np.arange(0.0, 121.0, 1.0))
        speeds = [10.0 if 20.0 <= time <= 80.0 else 0.0 for time in times]
        interval = select_airborne_interval(times, speeds)
        self.assertIsNotNone(interval)
        assert interval is not None
        self.assertEqual(18.0, interval.start_s)
        self.assertEqual(82.0, interval.end_s)
        self.assertEqual("ground_before", phase_for_time(10.0, interval))
        self.assertEqual("airborne", phase_for_time(50.0, interval))
        self.assertEqual("ground_after", phase_for_time(90.0, interval))

    def test_rejects_short_speed_excursion(self) -> None:
        self.assertIsNone(select_airborne_interval([0.0, 1.0, 2.0], [0.0, 9.0, 9.0]))

    def test_padding_does_not_extend_beyond_observed_data(self) -> None:
        interval = select_airborne_interval(
            list(np.arange(0.0, 21.0)),
            [0.0] * 5 + [10.0] * 16,
        )
        self.assertIsNotNone(interval)
        assert interval is not None
        self.assertEqual(20.0, interval.end_s)

    def test_counter_increment_tolerates_reset(self) -> None:
        self.assertEqual(5.0, monotonic_increment([10, 12, 12, 1, 4]))

    def test_describe_and_threshold_fraction_ignore_nonfinite(self) -> None:
        summary = describe([1.0, 2.0, np.nan, np.inf, 3.0])
        self.assertEqual(3, summary["count"])
        self.assertEqual(2.0, summary["mean"])
        self.assertAlmostEqual(1.0 / 3.0, threshold_fraction([1, 2, 3], 2.0))

    def test_effective_rate_uses_median_interval(self) -> None:
        self.assertAlmostEqual(10.0, effective_rate_hz([0.0, 0.1, 0.2, 0.3]))

    def test_psd_finds_known_sine_frequency(self) -> None:
        rate_hz = 1000.0
        times = np.arange(1024) / rate_hz
        samples = 2.0 * np.sin(2.0 * np.pi * 123.0 * times)
        frequencies, psd = hann_psd(samples, rate_hz)
        peak_hz, _ = dominant_frequency(frequencies, psd)
        self.assertIsNotNone(peak_hz)
        assert peak_hz is not None
        self.assertLess(abs(peak_hz - 123.0), 1.5)
        band_rms = integrate_band_rms(frequencies, psd, 115.0, 130.0)
        self.assertIsNotNone(band_rms)
        assert band_rms is not None
        self.assertGreater(band_rms, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
