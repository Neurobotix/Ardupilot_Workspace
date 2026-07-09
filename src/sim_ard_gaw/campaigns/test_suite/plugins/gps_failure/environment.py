"""Environment adapter for gps_failure.

Phase 1 Chunk 1 intentionally does not launch SITL or Gazebo.
"""
from __future__ import annotations

from ...core.environment import EnvironmentAdapter
from ...core.models import AttemptContext, TestCase
from .config import GpsFailureConfig


class GpsFailureEnvironment(EnvironmentAdapter):
    def __init__(self, config: GpsFailureConfig) -> None:
        self._config = config

    def prepare_case(self, case: TestCase) -> None:
        return None

    def launch(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return None
        raise RuntimeError("gps_failure live launch is out of scope for Phase 1 Chunk 1")

    def assert_ready(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return None
        raise RuntimeError("gps_failure live readiness is out of scope for Phase 1 Chunk 1")

    def cleanup(self, case: TestCase, ctx: AttemptContext) -> None:
        return None
