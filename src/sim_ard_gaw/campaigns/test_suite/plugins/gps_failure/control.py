"""Mission control interfaces for gps_failure."""
from __future__ import annotations

from dataclasses import dataclass

from ...core.control import ControlMode, ControlStrategy
from ...core.models import AttemptContext, TestCase
from .config import GpsFailureConfig


@dataclass
class GpsFailureMissionControl(ControlStrategy):
    config: GpsFailureConfig
    mode: ControlMode = ControlMode.AUTO

    def execute(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self.config.launch_stack:
            return None
        raise RuntimeError("gps_failure live mission control is out of scope for Phase 1 Chunk 1")
