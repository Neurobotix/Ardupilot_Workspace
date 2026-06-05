"""Mission control interfaces for airspeed_failure."""
from __future__ import annotations

from dataclasses import dataclass

from ...core.control import ControlMode, ControlStrategy
from ...core.models import AttemptContext, TestCase
from .config import AirspeedFailureConfig


@dataclass
class AirspeedFailureMissionControl(ControlStrategy):
    config: AirspeedFailureConfig
    mode: ControlMode = ControlMode.PASSIVE

    def execute(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self.config.launch_stack:
            return None
        raise NotImplementedError("airspeed_failure mission control is Phase 2 work")
