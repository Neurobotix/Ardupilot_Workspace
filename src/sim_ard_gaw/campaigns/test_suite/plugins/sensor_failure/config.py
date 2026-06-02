"""sensor_failure campaign configuration (GPS scope, Phase 4)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from . import defaults


@dataclass
class SensorFailureConfig:
    # Case selection: None selects all GPS cases. Otherwise a subset of
    # cases.ALL_CASE_IDS.
    case_ids: tuple[str, ...] | None = None
    repeats: int = defaults.DEFAULT_REPEATS

    campaign_root: Path = field(default_factory=lambda: defaults.DEFAULT_CAMPAIGN_ROOT)
    mission_file: Path = field(default_factory=lambda: defaults.MISSION_FILE)
    mavlink_addr: str = defaults.DEFAULT_MAVLINK

    heartbeat_timeout_s: float = defaults.DEFAULT_HEARTBEAT_TIMEOUT
    mission_timeout_s: float = defaults.DEFAULT_MISSION_TIMEOUT
    ready_timeout_s: float = defaults.DEFAULT_READY_TIMEOUT
    upload_timeout_s: float = defaults.DEFAULT_UPLOAD_TIMEOUT
    arm_timeout_s: float = defaults.DEFAULT_ARM_TIMEOUT
    mode_timeout_s: float = defaults.DEFAULT_MODE_TIMEOUT

    # Mid-flight fault trigger and observation window.
    injection_waypoint: int = defaults.DEFAULT_INJECTION_WAYPOINT
    post_inject_window_s: float = defaults.DEFAULT_POST_INJECT_WINDOW_S

    force_arm: bool = True
    auto_control: bool = True
    launch_stack: bool = True
    rebuild: bool = False
    wipe_eeprom: bool = True
    stack_settle_s: float = defaults.DEFAULT_STACK_SETTLE
    retry_delay_s: float = defaults.DEFAULT_RETRY_DELAY

    param_file_stack: Sequence[Path] | None = None
    stack_log_subdir: str = "orchestrator_logs"
    isolated_sitl_state: bool = True
    slot_deadline_margin_s: float = 0.0

    # The sensor_failure plugin is staged-only. There is no legacy delegate to
    # fall back to (this is a brand-new second plugin), but we keep the field so
    # the CLI surface and framework wiring mirror wind_matrix.
    attempt_strategy: str = "staged"

    def __post_init__(self) -> None:
        if self.repeats < 1:
            raise ValueError(f"repeats must be >= 1, got {self.repeats}")
        if self.attempt_strategy != "staged":
            raise ValueError(
                "sensor_failure supports only attempt_strategy='staged'; got "
                f"{self.attempt_strategy!r}. There is no legacy delegate for "
                "this second plugin."
            )
