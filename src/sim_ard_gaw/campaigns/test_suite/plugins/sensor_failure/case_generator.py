"""sensor_failure case generator.

Yields one TestCase per selected GPS fault case. `acceptance_target_runs` is the
repeat count; the scheduler/manifest drive repeats exactly as they do for
wind_matrix, with no plugin-specific scheduling logic.
"""
from __future__ import annotations

from typing import Iterable

from ...core.case_generator import CaseGenerator
from ...core.models import TestCase
from . import cases
from .config import SensorFailureConfig


class SensorFailureCaseGenerator(CaseGenerator):
    def __init__(self, config: SensorFailureConfig) -> None:
        self._config = config

    def iter_cases(self) -> Iterable[TestCase]:
        for case in cases.select_cases(self._config.case_ids):
            yield TestCase(
                suite_name="sensor_failure",
                case_id=case.case_id,
                parameters={
                    "sensor": case.sensor,
                    "mode": case.mode,
                    "verdict_mode": case.verdict_mode,
                    "severity": case.severity,
                    "inject_params": dict(case.inject),
                    "baseline_params": dict(case.baseline),
                    "injection_waypoint": self._config.injection_waypoint,
                    "post_inject_window_s": self._config.post_inject_window_s,
                },
                scenario_name="square_500m_five_laps_loiter5_land",
                stimulus_name=f"sim_gps1_{case.mode}",
                mission_file=self._config.mission_file,
                acceptance_target_runs=self._config.repeats,
                tags=case.tags,
            )
