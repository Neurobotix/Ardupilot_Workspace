#!/usr/bin/env python3
"""Pure numerical helpers for the real-flight IMU analysis.

This module deliberately has no DataFlash or plotting dependency.  Keeping the
math separate makes the assumptions testable and lets a reviewer reason about
the engineering decisions without also reasoning about file parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class Interval:
    """Closed time interval in autopilot boot-time seconds."""

    start_s: float
    end_s: float

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_s - self.start_s)

    def contains(self, time_s: float) -> bool:
        return self.start_s <= time_s <= self.end_s


def finite_array(values: Iterable[float]) -> np.ndarray:
    """Return finite floating-point values only."""

    array = np.asarray(list(values), dtype=float)
    return array[np.isfinite(array)]


def describe(values: Iterable[float]) -> dict[str, float | int | None]:
    """Produce stable descriptive statistics used by every output table."""

    array = finite_array(values)
    if array.size == 0:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    return {
        "count": int(array.size),
        "mean": float(np.mean(array)),
        "std": float(np.std(array)),
        "p50": float(np.percentile(array, 50)),
        "p95": float(np.percentile(array, 95)),
        "p99": float(np.percentile(array, 99)),
        "max": float(np.max(array)),
    }


def threshold_fraction(values: Iterable[float], threshold: float) -> float | None:
    """Fraction of finite samples strictly above an engineering threshold."""

    array = finite_array(values)
    if array.size == 0:
        return None
    return float(np.mean(array > threshold))


def monotonic_increment(values: Iterable[float]) -> float | None:
    """Sum positive increments in a cumulative counter, tolerating resets."""

    array = finite_array(values)
    if array.size == 0:
        return None
    if array.size == 1:
        return 0.0
    differences = np.diff(array)
    return float(np.sum(differences[differences > 0.0]))


def effective_rate_hz(times_s: Iterable[float]) -> float | None:
    """Estimate message rate from the median positive inter-message interval."""

    times = finite_array(times_s)
    if times.size < 2:
        return None
    differences = np.diff(np.sort(times))
    differences = differences[differences > 0.0]
    if differences.size == 0:
        return None
    return float(1.0 / np.median(differences))


def select_airborne_interval(
    times_s: Sequence[float],
    speeds_mps: Sequence[float],
    *,
    minimum_speed_mps: float = 8.0,
    bridge_gap_s: float = 30.0,
    minimum_duration_s: float = 10.0,
    pad_s: float = 2.0,
) -> Interval | None:
    """Select the longest sustained fixed-wing movement interval.

    Only timestamps whose GPS speed meets ``minimum_speed_mps`` become anchor
    points.  Nearby anchor groups are bridged to tolerate turns, GPS dropouts,
    and short low-speed transients.  The longest group is the main flight.
    This avoids including long armed-on-ground sections in VIBE statistics.
    """

    times = np.asarray(times_s, dtype=float)
    speeds = np.asarray(speeds_mps, dtype=float)
    if times.size != speeds.size or times.size == 0:
        return None
    valid = np.isfinite(times) & np.isfinite(speeds) & (speeds >= minimum_speed_mps)
    anchors = np.sort(times[valid])
    if anchors.size < 2:
        return None

    groups: list[tuple[float, float]] = []
    group_start = float(anchors[0])
    previous = float(anchors[0])
    for current_value in anchors[1:]:
        current = float(current_value)
        if current - previous > bridge_gap_s:
            groups.append((group_start, previous))
            group_start = current
        previous = current
    groups.append((group_start, previous))

    eligible = [group for group in groups if group[1] - group[0] >= minimum_duration_s]
    if not eligible:
        return None
    start_s, end_s = max(eligible, key=lambda group: group[1] - group[0])
    return Interval(
        start_s=max(float(np.min(times)), start_s - pad_s),
        end_s=min(float(np.max(times)), end_s + pad_s),
    )


def phase_for_time(time_s: float, airborne: Interval) -> str:
    """Classify a timestamp relative to the main airborne interval."""

    if time_s < airborne.start_s:
        return "ground_before"
    if time_s > airborne.end_s:
        return "ground_after"
    return "airborne"


def hann_psd(
    samples: Sequence[float], sample_rate_hz: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return one-sided Hann-window power spectral density.

    The normalization matches pymavlink's ``mavfft_isb.py``: integrating the
    PSD over frequency approximates the mean-square signal after DC removal.
    """

    values = np.asarray(samples, dtype=float)
    if values.size < 8 or sample_rate_hz <= 0.0:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    values = values - np.mean(values)
    window = np.hanning(values.size)
    window_energy = float(np.inner(window, window))
    transformed = np.fft.rfft(values * window)
    psd = 2.0 * np.square(np.abs(transformed)) / (sample_rate_hz * window_energy)
    psd[0] = 0.0
    if psd.size > 1:
        psd[-1] = 0.0
    frequencies = np.fft.rfftfreq(values.size, d=1.0 / sample_rate_hz)
    return frequencies, psd


def integrate_band_rms(
    frequencies_hz: Sequence[float],
    psd: Sequence[float],
    low_hz: float,
    high_hz: float,
) -> float | None:
    """Integrate PSD within a frequency band and return RMS amplitude."""

    frequencies = np.asarray(frequencies_hz, dtype=float)
    power = np.asarray(psd, dtype=float)
    mask = (
        np.isfinite(frequencies)
        & np.isfinite(power)
        & (frequencies >= low_hz)
        & (frequencies < high_hz)
    )
    if np.count_nonzero(mask) < 2:
        return None
    band_frequency = frequencies[mask]
    band_power = np.maximum(power[mask], 0.0)
    return float(np.sqrt(np.trapezoid(band_power, band_frequency)))


def dominant_frequency(
    frequencies_hz: Sequence[float],
    psd: Sequence[float],
    *,
    low_hz: float = 30.0,
    high_hz: float = 500.0,
) -> tuple[float | None, float | None]:
    """Find the strongest PSD bin in a bounded engineering band."""

    frequencies = np.asarray(frequencies_hz, dtype=float)
    power = np.asarray(psd, dtype=float)
    mask = (
        np.isfinite(frequencies)
        & np.isfinite(power)
        & (frequencies >= low_hz)
        & (frequencies <= high_hz)
    )
    if not np.any(mask):
        return None, None
    indices = np.flatnonzero(mask)
    peak_index = int(indices[np.argmax(power[indices])])
    return float(frequencies[peak_index]), float(power[peak_index])


def separated_peaks(
    frequencies_hz: Sequence[float],
    psd: Sequence[float],
    *,
    low_hz: float = 30.0,
    high_hz: float = 500.0,
    count: int = 5,
    separation_hz: float = 8.0,
) -> list[tuple[float, float]]:
    """Return strongest local PSD maxima separated in frequency."""

    frequencies = np.asarray(frequencies_hz, dtype=float)
    power = np.asarray(psd, dtype=float)
    if frequencies.size < 3 or frequencies.size != power.size:
        return []
    candidates: list[int] = []
    for index in range(1, power.size - 1):
        if not (low_hz <= frequencies[index] <= high_hz):
            continue
        if power[index] >= power[index - 1] and power[index] > power[index + 1]:
            candidates.append(index)
    candidates.sort(key=lambda index: power[index], reverse=True)
    selected: list[int] = []
    for candidate in candidates:
        if all(
            abs(float(frequencies[candidate] - frequencies[chosen])) >= separation_hz
            for chosen in selected
        ):
            selected.append(candidate)
        if len(selected) == count:
            break
    return [(float(frequencies[index]), float(power[index])) for index in selected]


def pearson_correlation(x_values: Iterable[float], y_values: Iterable[float]) -> float | None:
    """Return Pearson r when two finite, non-constant vectors are available."""

    x_array = np.asarray(list(x_values), dtype=float)
    y_array = np.asarray(list(y_values), dtype=float)
    if x_array.size != y_array.size or x_array.size < 3:
        return None
    mask = np.isfinite(x_array) & np.isfinite(y_array)
    x_array = x_array[mask]
    y_array = y_array[mask]
    if x_array.size < 3 or np.std(x_array) == 0.0 or np.std(y_array) == 0.0:
        return None
    return float(np.corrcoef(x_array, y_array)[0, 1])
