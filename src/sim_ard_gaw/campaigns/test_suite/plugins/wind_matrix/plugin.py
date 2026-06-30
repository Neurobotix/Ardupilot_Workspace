"""Wind-matrix plugin assembly.

This module is the only public surface of the plugin. It wires the
plugin's adapters together and exposes `build_plugin(config)` for the
CLI.

Design:
- `staged` is the only supported strategy. It wires wind stimulus,
  MAVLink control, monitoring, analysis, and verdict adapters through
  the framework. The historical `legacy` strategy (which delegated to
  the `run_one` monolith) has been retired.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sim_ard_gaw.campaigns.status import legacy_analysis_succeeded

from ...core.analysis import AnalyzerChain
from ...core.attempt_runner import (
    AttemptRunner,
    AttemptStrategy,
    StagedStrategy,
)
from ...core.case_generator import CaseGenerator
from ...core.control import (
    ControlMode,
    ControlStrategy,
    ManualMissionControl,
    MavlinkAutoMissionControl,
)
from ...core.environment import EnvironmentAdapter
from ...core.manifest import Manifest
from ...core.monitor import CompletionMonitor
from ...core.models import (
    AnalysisResult,
    AttemptContext,
    AttemptRecord,
    AttemptStatus,
    MonitorResult,
    Verdict,
    VerdictClass,
)
from .case_generator import WindMatrixCaseGenerator
from .config import WindMatrixConfig
from .defaults import (
    ANALYSIS_HEADROOM_S,
    AUTO_ARM_TO_AUTO_SETTLE_S,
    BIN_FLUSH_DELAY_S,
    attempt_dir as attempt_dir_path,
    attempt_id,
    log,
    utc_now,
)
from .environment import WindMatrixEnvironment
from . import analysis_helpers
from . import mavlink_control
from .manifest import WindMatrixManifest
from .monitor import WindMatrixDisarmCompletionMonitor
from .analyzers import (
    WindMatrixAnalyzer,
    WindMatrixVerdictPolicy,
    build_wind_matrix_error_record,
)
from .stimulus import WindMatrixStimulus


@dataclass
class WindMatrixPlugin:
    config: WindMatrixConfig
    case_generator: CaseGenerator
    environment: EnvironmentAdapter
    manifest: Manifest
    staged_strategy: AttemptStrategy | None = None

    def attempt_runner(self) -> AttemptRunner:
        if self.config.attempt_strategy != "staged":
            raise ValueError(
                "wind_matrix supports only attempt_strategy='staged'; got "
                f"{self.config.attempt_strategy!r}. The legacy run_one delegate "
                "has been retired."
            )
        if self.staged_strategy is None:
            raise RuntimeError("staged attempt strategy was not configured")
        strategy: AttemptStrategy = self.staged_strategy
        prewrite_running = True
        running_record_factory: Callable[[AttemptContext], AttemptRecord] | None = None
        exception_record_factory: (
            Callable[[AttemptContext, BaseException], AttemptRecord] | None
        ) = None
        if prewrite_running:
            running_record_factory = lambda ctx: build_wind_matrix_running_record(
                self.config, ctx,
            )
            exception_record_factory = lambda ctx, exc: build_wind_matrix_error_record(
                self.config, ctx, exc,
            )
        return AttemptRunner(
            environment=self.environment,
            strategy=strategy,
            manifest=self.manifest,
            artifact_root=self.config.campaign_root,
            prewrite_running_record=prewrite_running,
            running_record_factory=running_record_factory,
            exception_record_factory=exception_record_factory,
        )

    def attempt_dir_factory(self):
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
            return attempt_dir_path(self.config.campaign_root, case.case_id, idx)

        return _factory


def build_wind_matrix_running_record(
    config: WindMatrixConfig,
    ctx: AttemptContext,
) -> AttemptRecord:
    key = ctx.case.case_id
    # Record the canonical attempt_NNN directory so the prewritten running row
    # matches the terminal row even if the runner was handed the combo runs/
    # parent before the stimulus stage normalized ctx.attempt_dir.
    attempt_dir = attempt_dir_path(config.campaign_root, key, ctx.attempt_index)
    ctx.attempt_dir = attempt_dir
    attempt_dir.mkdir(parents=True, exist_ok=True)
    start_time = str(
        ctx.extra.get("legacy_start_time_utc")
        or ctx.extra.get("attempt_start_time_utc")
        or utc_now()
    )
    ctx.extra["legacy_start_time_utc"] = start_time
    ctx.extra["attempt_start_time_utc"] = start_time
    plugin_fields = {
        "attempt_id": attempt_id(key, ctx.target_run_index, ctx.attempt_index),
        "combo_key": key,
        "x_wind_mps": ctx.case.parameters.get("wind_x_mps"),
        "y_wind_mps": ctx.case.parameters.get("wind_y_mps"),
        "target_run_index": ctx.target_run_index,
        "attempt_index": ctx.attempt_index,
        "status": "running",
        "success_class": None,
        "mission_completed_full": False,
        "square_completed": False,
        "loiter_completed": False,
        "analysis_status": "pending",
        "raw_log_path": None,
        "attempt_dir": str(attempt_dir),
        "run_alias": None,
        "start_time_utc": start_time,
        "end_time_utc": None,
        "duration_wall_s": None,
        "notes": [],
        "artifacts": {"attempt_dir": str(attempt_dir)},
    }
    return AttemptRecord(
        attempt_id=str(plugin_fields["attempt_id"]),
        suite_name=ctx.case.suite_name,
        case_id=ctx.case.case_id,
        target_run_index=ctx.target_run_index,
        attempt_index=ctx.attempt_index,
        status=AttemptStatus.RUNNING,
        start_time_utc=start_time,
        artifacts={"attempt_dir": str(attempt_dir)},
        parameters=dict(ctx.case.parameters),
        stimulus_result=dict(ctx.stimulus_result),
        plugin_manifest_fields=plugin_fields,
    )


@dataclass
class WindMatrixAutoMissionControl(ControlStrategy):
    config: WindMatrixConfig
    mode: ControlMode = ControlMode.AUTO

    def execute(self, case, ctx: AttemptContext) -> None:
        return MavlinkAutoMissionControl(
            mission_file=self.config.mission_file,
            upload_timeout_s=self.config.upload_timeout_s,
            arm_timeout_s=self.config.arm_timeout_s,
            mode_timeout_s=self.config.mode_timeout_s,
            settle_s=AUTO_ARM_TO_AUTO_SETTLE_S,
            force_arm=self.config.force_arm,
            upload_mission=mavlink_control.upload_mission,
            verify_mission=mavlink_control.verify_mission,
            arm_vehicle=mavlink_control.arm_vehicle,
            settle_after_arm_before_auto=mavlink_control.settle_after_arm_before_auto,
            set_auto_mode=mavlink_control.set_auto_mode,
            clamp_timeout_to_slot=analysis_helpers.clamp_timeout_to_slot,
            bin_flush_delay_s=BIN_FLUSH_DELAY_S,
            analysis_headroom_s=ANALYSIS_HEADROOM_S,
            log=log,
        ).execute(case, ctx)


@dataclass
class WindMatrixDisarmMonitor(CompletionMonitor):
    config: WindMatrixConfig

    def run(self, case, ctx: AttemptContext) -> MonitorResult:
        return WindMatrixDisarmCompletionMonitor(
            mission_timeout_s=self.config.mission_timeout_s,
            monitor_until_disarm=mavlink_control.monitor_until_disarm,
            clamp_timeout_to_slot=analysis_helpers.clamp_timeout_to_slot,
            mission_pre_loaded=self.config.auto_control,
            stop_on_square_loiter=self.config.accept_square_only,
            bin_flush_delay_s=BIN_FLUSH_DELAY_S,
            analysis_headroom_s=ANALYSIS_HEADROOM_S,
        ).run(case, ctx)


def _record_from_legacy(ctx: AttemptContext, rec: dict) -> AttemptRecord:
    status_raw = (rec or {}).get("status", "error")
    x = ctx.case.parameters.get("wind_x_mps")
    y = ctx.case.parameters.get("wind_y_mps")
    status = _LEGACY_STATUS_TO_FRAMEWORK.get(status_raw, AttemptStatus.ERROR)
    verdict_klass = _LEGACY_STATUS_TO_VERDICT.get(status_raw, VerdictClass.FAILED)
    verdict = Verdict(
        klass=verdict_klass,
        reason=status_raw,
        retryable=verdict_klass == VerdictClass.FAILED_RETRYABLE,
        requires_analysis=status_raw in ("success_full", "success_square_only"),
        metadata={k: v for k, v in (rec or {}).items()
                  if k not in {"status", "analysis_status"}},
    )
    monitor_result = MonitorResult(
        completed=status in {AttemptStatus.SUCCESS, AttemptStatus.PARTIAL},
        reason=status_raw,
        duration_s=float((rec or {}).get("duration_wall_s", 0.0) or 0.0),
    )
    analysis_status = (rec or {}).get("analysis_status")
    analysis_results: list[AnalysisResult] = []
    if analysis_status is not None:
        analysis_results.append(
            AnalysisResult(
                analyzer_name="legacy_run_analysis",
                ok=legacy_analysis_succeeded(analysis_status),
                summary={"legacy_status": analysis_status},
            )
        )
    return AttemptRecord(
        attempt_id=(rec or {}).get("attempt_id",
                                   f"{ctx.case.case_id}__attempt_{ctx.attempt_index:03d}"),
        suite_name=ctx.case.suite_name,
        case_id=ctx.case.case_id,
        target_run_index=ctx.target_run_index,
        attempt_index=ctx.attempt_index,
        status=status,
        verdict=verdict,
        monitor_result=monitor_result,
        analysis_results=analysis_results,
        start_time_utc=(rec or {}).get("start_time_utc") or "",
        end_time_utc=(rec or {}).get("end_time_utc") or "",
        duration_wall_s=float((rec or {}).get("duration_wall_s", 0.0) or 0.0),
        artifacts={
            key: value
            for key, value in {
                "raw_log": (rec or {}).get("raw_log_path"),
                "attempt_dir": (rec or {}).get("attempt_dir"),
                "run_alias": (rec or {}).get("run_alias"),
            }.items()
            if value is not None
        },
        parameters=dict(ctx.case.parameters),
        stimulus_result={
            "kind": ctx.case.stimulus_name or "wind_matrix",
            "wind_mps": {"x": x, "y": y, "z": 0.0},
        },
    )


_LEGACY_STATUS_TO_FRAMEWORK = {
    "success_full": AttemptStatus.SUCCESS,
    "success_square_only": AttemptStatus.PARTIAL,
    "failed": AttemptStatus.FAILED,
    "failed_analysis": AttemptStatus.ANALYSIS_FAILED,
    "error": AttemptStatus.ERROR,
    "interrupted": AttemptStatus.INTERRUPTED,
}

_LEGACY_STATUS_TO_VERDICT = {
    "success_full": VerdictClass.SUCCESS,
    "success_square_only": VerdictClass.PARTIAL,
    "failed": VerdictClass.FAILED_RETRYABLE,
    "failed_analysis": VerdictClass.ANALYSIS_FAILED,
    "error": VerdictClass.FAILED_RETRYABLE,
    "interrupted": VerdictClass.FAILED_RETRYABLE,
}


def build_plugin(config: WindMatrixConfig) -> WindMatrixPlugin:
    if config.attempt_strategy != "staged":
        raise ValueError(
            "wind_matrix supports only attempt_strategy='staged'; got "
            f"{config.attempt_strategy!r}. The legacy run_one delegate has "
            "been retired."
        )
    if config.auto_control and config.auto_wind_phase == "after-takeoff":
        raise ValueError(
            "staged wind_matrix attempts do not support "
            "auto_wind_phase='after-takeoff'. Use auto_wind_phase='before-arm'."
        )
    return WindMatrixPlugin(
        config=config,
        case_generator=WindMatrixCaseGenerator(config),
        environment=WindMatrixEnvironment(config),
        manifest=WindMatrixManifest(
            config.campaign_root,
            require_analysis=config.require_analysis,
            accept_square_only=config.accept_square_only,
        ),
        staged_strategy=_staged_strategy(config),
    )


def _staged_strategy(config: WindMatrixConfig) -> StagedStrategy:
    control = (
        WindMatrixAutoMissionControl(config)
        if config.auto_control
        else ManualMissionControl(config.mission_file, log=log)
    )
    return StagedStrategy(
        stimulus=WindMatrixStimulus(config),
        control=control,
        monitor=WindMatrixDisarmMonitor(config),
        analyzers=AnalyzerChain([WindMatrixAnalyzer(config)]),
        verdict_policy=WindMatrixVerdictPolicy(),
        on_exception=lambda ctx, exc: build_wind_matrix_error_record(
            config, ctx, exc,
        ),
    )
