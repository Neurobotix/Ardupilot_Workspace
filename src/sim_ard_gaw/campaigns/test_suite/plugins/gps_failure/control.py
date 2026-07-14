"""Mission control interfaces for gps_failure."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ...core.control import ControlMode, ControlStrategy
from ...core.models import AttemptContext, TestCase
from .config import GpsFailureConfig
from . import defaults


class MissionAdapter(Protocol):
    def upload_mission(self, mission_file: str) -> Any:
        ...

    def verify_mission(self, mission_file: str) -> Any:
        ...

    def arm(self) -> Any:
        ...

    def set_mode(self, mode: str) -> Any:
        ...


class MavlinkGpsMissionAdapter:
    """Production mission adapter around the live MAVLink master.

    The actual mission protocol helpers are imported only when the adapter
    methods run, preserving the GPS plugin's import-time no-connection contract.
    """

    def __init__(self, master: Any, config: GpsFailureConfig) -> None:
        self._master = master
        self._config = config
        self._uploaded_items: list[Any] | None = None

    def upload_mission(self, mission_file: str) -> list[Any]:
        from ..airspeed_failure import mavlink as mission_mavlink

        self._uploaded_items = mission_mavlink.upload_mission(
            self._master,
            Path(mission_file),
            self._config.upload_timeout_s,
        )
        return list(self._uploaded_items)

    def verify_mission(self, mission_file: str) -> None:
        from ..airspeed_failure import mavlink as mission_mavlink

        if self._uploaded_items is None:
            raise RuntimeError(
                f"mission must be uploaded before verification: {mission_file}"
            )
        mission_mavlink.verify_mission(
            self._master,
            self._uploaded_items,
            self._config.upload_timeout_s,
        )

    def arm(self) -> None:
        from ..airspeed_failure import mavlink as mission_mavlink

        mission_mavlink.arm_vehicle(
            self._master,
            self._config.arm_timeout_s,
            self._config.force_arm,
        )
        mission_mavlink.settle_after_arm_before_auto(
            self._master,
            defaults.AUTO_ARM_TO_AUTO_SETTLE_S,
        )

    def set_mode(self, mode: str) -> None:
        from ..airspeed_failure import mavlink as mission_mavlink

        if mode != ControlMode.AUTO.name:
            raise ValueError(f"gps_failure live smoke only supports AUTO mode: {mode}")
        mission_mavlink.set_auto_mode(
            self._master,
            self._config.mode_timeout_s,
        )


def build_mission_adapter(master: Any, config: GpsFailureConfig) -> MissionAdapter:
    return MavlinkGpsMissionAdapter(master, config)


@dataclass
class GpsFailureMissionControl(ControlStrategy):
    config: GpsFailureConfig
    mode: ControlMode = ControlMode.AUTO

    def execute(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self.config.launch_stack:
            return None
        adapter = ctx.extra.get("mission_adapter")
        if adapter is None:
            master = ctx.extra.get("mavlink_master")
            if master is not None:
                adapter = build_mission_adapter(master, self.config)
                ctx.extra["mission_adapter"] = adapter
        if adapter is None:
            raise RuntimeError("GPS mission control requires an explicit adapter")
        mission_file = str(case.mission_file or defaults.MISSION_FILE)
        for method_name, args in (
            ("upload_mission", (mission_file,)),
            ("verify_mission", (mission_file,)),
            ("arm", ()),
            ("set_mode", (self.mode.name,)),
        ):
            method = getattr(adapter, method_name, None)
            if not callable(method):
                raise RuntimeError(f"mission adapter missing {method_name}")
            method(*args)
        ctx.extra["gps_mission_control"] = {
            "mission_file": mission_file,
            "armed": True,
            "mode": self.mode.name,
            "trigger_contract": dict(defaults.INJECTION_TRIGGER),
        }
