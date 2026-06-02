"""sensor_failure plugin assembly (Phase 4 second plugin).

`build_plugin(config)` wires the staged framework path:
  stimulus (baseline + provenance)
    -> MavlinkAutoMissionControl (auto upload/arm/AUTO, the SAME core strategy
       wind_matrix uses, with injected mavlink_control helpers)
    -> SensorFailureResilienceMonitor (injects the fault mid-flight, captures
       the resilience response)
    -> SensorFailureAnalyzer (metrics + verdict.json)
    -> SensorFailureVerdictPolicy.

Every adapter is plugin-owned or core-owned. No framework-core edit is made by
this plugin; that is the Phase 4 thesis. There is no legacy strategy — this is a
brand-new plugin built directly on the staged path.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..wind_matrix import analysis_helpers as wm_analysis_helpers
from ..wind_matrix import mavlink_control as wm_mavlink_control
from ...core.analysis import AnalyzerChain
from ...core.attempt_runner import AttemptRunner, AttemptStrategy, StagedStrategy
from ...core.case_generator import CaseGenerator
from ...core.control import ControlMode, ControlStrategy, MavlinkAutoMissionControl
from ...core.environment import EnvironmentAdapter
from ...core.manifest import Manifest
from ...core.models import AttemptContext
from . import defaults, mavlink_fault
from .analyzers import (
    SensorFailureAnalyzer,
    SensorFailureVerdictPolicy,
    build_sensor_failure_error_record,
    build_sensor_failure_running_record,
)
from .case_generator import SensorFailureCaseGenerator
from .config import SensorFailureConfig
from .environment import SensorFailureEnvironment
from .manifest import SensorFailureManifest
from .monitor import SensorFailureResilienceMonitor
from .stimulus import SensorFailureStimulus


@dataclass
class SensorFailureAutoMissionControl(ControlStrategy):
    config: SensorFailureConfig
    mode: ControlMode = ControlMode.AUTO

    def execute(self, case, ctx: AttemptContext) -> None:
        return MavlinkAutoMissionControl(
            mission_file=self.config.mission_file,
            upload_timeout_s=self.config.upload_timeout_s,
            arm_timeout_s=self.config.arm_timeout_s,
            mode_timeout_s=self.config.mode_timeout_s,
            settle_s=defaults.AUTO_ARM_TO_AUTO_SETTLE_S,
            force_arm=self.config.force_arm,
            upload_mission=wm_mavlink_control.upload_mission,
            verify_mission=wm_mavlink_control.verify_mission,
            arm_vehicle=wm_mavlink_control.arm_vehicle,
            settle_after_arm_before_auto=wm_mavlink_control.settle_after_arm_before_auto,
            set_auto_mode=wm_mavlink_control.set_auto_mode,
            clamp_timeout_to_slot=wm_analysis_helpers.clamp_timeout_to_slot,
            bin_flush_delay_s=defaults.BIN_FLUSH_DELAY_S,
            analysis_headroom_s=defaults.ANALYSIS_HEADROOM_S,
            log=defaults.log,
        ).execute(case, ctx)


@dataclass
class SensorFailurePlugin:
    config: SensorFailureConfig
    case_generator: CaseGenerator
    environment: EnvironmentAdapter
    manifest: Manifest
    staged_strategy: AttemptStrategy

    def attempt_runner(self) -> AttemptRunner:
        return AttemptRunner(
            environment=self.environment,
            strategy=self.staged_strategy,
            manifest=self.manifest,
            artifact_root=self.config.campaign_root,
            prewrite_running_record=True,
            running_record_factory=lambda ctx: build_sensor_failure_running_record(
                self.config, ctx,
            ),
            exception_record_factory=lambda ctx, exc: build_sensor_failure_error_record(
                self.config, ctx, exc,
            ),
        )

    def attempt_dir_factory(self) -> Callable[..., Path]:
        def _factory(
            manifest: Manifest,
            case,
            attempt_index: int | None = None,
        ) -> Path:
            idx = (
                int(attempt_index)
                if attempt_index is not None
                else manifest.next_attempt_index(case)
            )
            return defaults.attempt_dir(self.config.campaign_root, case.case_id, idx)

        return _factory


def _staged_strategy(config: SensorFailureConfig) -> StagedStrategy:
    return StagedStrategy(
        stimulus=SensorFailureStimulus(config),
        control=SensorFailureAutoMissionControl(config),
        monitor=SensorFailureResilienceMonitor(
            injection_waypoint=config.injection_waypoint,
            post_inject_window_s=config.post_inject_window_s,
            mission_timeout_s=config.mission_timeout_s,
            inject_fault=mavlink_fault.set_params,
            clamp_timeout_to_slot=wm_analysis_helpers.clamp_timeout_to_slot,
            bin_flush_delay_s=defaults.BIN_FLUSH_DELAY_S,
            analysis_headroom_s=defaults.ANALYSIS_HEADROOM_S,
        ),
        analyzers=AnalyzerChain([SensorFailureAnalyzer(config)]),
        verdict_policy=SensorFailureVerdictPolicy(),
        on_exception=lambda ctx, exc: build_sensor_failure_error_record(config, ctx, exc),
    )


def build_plugin(config: SensorFailureConfig) -> SensorFailurePlugin:
    if config.attempt_strategy != "staged":
        raise ValueError(
            "sensor_failure supports only attempt_strategy='staged'; got "
            f"{config.attempt_strategy!r}"
        )
    return SensorFailurePlugin(
        config=config,
        case_generator=SensorFailureCaseGenerator(config),
        environment=SensorFailureEnvironment(config),
        manifest=SensorFailureManifest(config.campaign_root),
        staged_strategy=_staged_strategy(config),
    )
