"""Control strategies: how the vehicle/subject is driven.

Three named strategies map onto the modes the legacy stack already
supports:

- `ManualControl`  — print operator instructions, do not send commands
                     (matches `run_one.py` without `--auto`)
- `AutoControl`    — upload mission, arm, switch mode
                     (matches `run_one.py --auto` and `run_matrix.py`)
- `PassiveControl` — never command, only observe
                     (matches `run_one_og.py`)

A plugin selects the default strategy for its CLI but every strategy is
plugin-overridable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from .models import AttemptContext, TestCase


class ControlMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"
    PASSIVE = "passive"


class ControlStrategy(ABC):
    mode: ControlMode

    @abstractmethod
    def execute(self, case: TestCase, ctx: AttemptContext) -> None:
        """Perform whatever commanding is needed before monitoring."""


class ManualControl(ControlStrategy):
    mode = ControlMode.MANUAL

    def execute(self, case: TestCase, ctx: AttemptContext) -> None:
        # Default printer. Plugins typically subclass to print
        # family-specific instructions (which mission to load, which
        # mode to set, etc.).
        print(f"[manual] case={case.case_id} attempt_dir={ctx.attempt_dir}")
        print("[manual] perform the operator steps now; monitor will block "
              "until the completion policy fires.")


class AutoControl(ControlStrategy):
    mode = ControlMode.AUTO

    def execute(self, case: TestCase, ctx: AttemptContext) -> None:
        # Phase 1: legacy run_one.run_one performs upload+arm+mode
        # internally when called with manual_control=False. Phase 3
        # extracts that flow here and this method becomes the only auto
        # commanding path.
        return None


class PassiveControl(ControlStrategy):
    mode = ControlMode.PASSIVE

    def execute(self, case: TestCase, ctx: AttemptContext) -> None:
        return None
