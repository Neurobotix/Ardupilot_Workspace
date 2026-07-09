"""Configuration for the gps_failure plugin."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from . import defaults


@dataclass
class GpsFailureConfig:
    drift_rates_mps: tuple[float, ...] = defaults.DRIFT_RATES_MPS
    glitch_magnitudes_m: tuple[int, ...] = defaults.GLITCH_MAGNITUDES_M
    denial_durations_s: tuple[int, ...] = defaults.DENIAL_DURATIONS_S
    jamming_repeats: int = defaults.JAMMING_REPEAT_COUNT
    jamming_duration_s: float = defaults.JAMMING_DURATION_S
    runs_per_case: int = 1
    campaign_root: Path = field(default_factory=defaults.default_campaign_root)
    mission_file: Path = field(default_factory=lambda: defaults.MISSION_FILE)
    param_file_stack: Sequence[Path] | None = None
    mavlink_addr: str = "udpin:0.0.0.0:14551"
    launch_stack: bool = False

    def __post_init__(self) -> None:
        if self.runs_per_case < 1:
            raise ValueError("runs_per_case must be >= 1")
        if self.jamming_repeats < 1:
            raise ValueError("jamming_repeats must be >= 1")
        if self.jamming_duration_s <= 0:
            raise ValueError("jamming_duration_s must be > 0")
        for rate in self.drift_rates_mps:
            if rate <= 0:
                raise ValueError("drift_rates_mps values must be > 0")
        for magnitude in self.glitch_magnitudes_m:
            if magnitude <= 0:
                raise ValueError("glitch_magnitudes_m values must be > 0")
        for duration in self.denial_durations_s:
            if duration <= 0:
                raise ValueError("denial_durations_s values must be > 0")

    @property
    def effective_param_stack(self) -> list[Path]:
        if self.param_file_stack is None:
            return defaults.phase1_param_files()
        return [Path(path) for path in self.param_file_stack]
