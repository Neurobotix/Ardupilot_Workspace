"""Wind-matrix campaign configuration.

Pulls defaults from the legacy `run_one` constants so the plugin can't
silently drift from the existing campaign. When Phase 3 lands, these
defaults move here and `run_one` reads from this module instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from ...core import _legacy


@dataclass
class WindMatrixConfig:
    x_values: tuple[int, ...] = (0, 4, 8, 12)
    y_values: tuple[int, ...] = (0, 4, 8, 12)
    runs_per_combo: int = 5
    campaign_root: Path = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_CAMPAIGN_ROOT)
    mission_file: Path = field(default_factory=lambda: _legacy.run_one_module().MISSION_FILE)
    mavlink_addr: str = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_MAVLINK)
    heartbeat_timeout_s: float = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_HEARTBEAT_TIMEOUT)
    mission_timeout_s: float = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_MISSION_TIMEOUT)
    ready_timeout_s: float = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_READY_TIMEOUT)
    upload_timeout_s: float = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_UPLOAD_TIMEOUT)
    arm_timeout_s: float = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_ARM_TIMEOUT)
    mode_timeout_s: float = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_MODE_TIMEOUT)
    accept_square_only: bool = False
    force_arm: bool = True
    auto_control: bool = True
    launch_stack: bool = True
    rebuild: bool = False
    wipe_eeprom: bool = False
    stack_settle_s: float = field(default_factory=lambda: _legacy.run_matrix_module().DEFAULT_STACK_SETTLE)
    retry_delay_s: float = field(default_factory=lambda: _legacy.run_matrix_module().DEFAULT_RETRY_DELAY)
    auto_wind_phase: str = field(default_factory=lambda: _legacy.run_one_module().DEFAULT_AUTO_WIND_PHASE)
    wind_world_mode: str = "calm-runtime"
    preloaded_wind_world: Path | None = None
    preloaded_wind_refresh: bool = True
    require_analysis: bool = False
    param_file_stack: Sequence[Path] | None = None
    stack_log_subdir: str = "orchestrator_logs"
    isolated_sitl_state: bool = True
    slot_deadline_margin_s: float = 0.0
    attempt_strategy: str = "legacy"
