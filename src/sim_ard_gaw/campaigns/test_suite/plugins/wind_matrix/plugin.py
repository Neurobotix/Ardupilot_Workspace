"""Wind-matrix plugin assembly.

This module is the only public surface of the plugin. It wires the
plugin's adapters together and exposes `build_plugin(config)` for the
CLI.

Phase-3 design:
- `legacy` remains the default strategy and delegates to
  `run_one.run_one(...)`.
- `staged` is an explicit opt-in strategy that wires wind stimulus,
  MAVLink control, monitoring, analysis, and verdict adapters through
  the framework. It is not the campaign default until live parity
  evidence exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sim_ard_gaw.campaigns.status import legacy_analysis_succeeded

from ...core import _legacy
from ...core.analysis import AnalyzerChain
from ...core.attempt_runner import (
    AttemptRunner,
    AttemptStrategy,
    LegacyDelegateStrategy,
    StagedStrategy,
)
from ...core.case_generator import CaseGenerator
from ...core.control import ManualMissionControl, MavlinkAutoMissionControl
from ...core.environment import EnvironmentAdapter
from ...core.manifest import LegacyManifest, Manifest
from ...core.models import (
    AnalysisResult,
    AttemptContext,
    AttemptRecord,
    AttemptStatus,
    MonitorResult,
    Verdict,
    VerdictClass,
)
from ...core.monitor import DisarmCompletionMonitor
from .case_generator import WindMatrixCaseGenerator
from .config import WindMatrixConfig
from .environment import WindMatrixEnvironment
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
    legacy_body: Callable[[AttemptContext], AttemptRecord]
    staged_strategy: AttemptStrategy | None = None

    def attempt_runner(self) -> AttemptRunner:
        strategy: AttemptStrategy
        if self.config.attempt_strategy == "staged":
            if self.staged_strategy is None:
                raise RuntimeError("staged attempt strategy was not configured")
            strategy = self.staged_strategy
        elif self.config.attempt_strategy == "legacy":
            strategy = LegacyDelegateStrategy(body=self.legacy_body)
        else:
            raise ValueError(
                "attempt_strategy must be 'legacy' or 'staged', got "
                f"{self.config.attempt_strategy!r}"
            )
        return AttemptRunner(
            environment=self.environment,
            strategy=strategy,
            manifest=self.manifest,
            artifact_root=self.config.campaign_root,
        )

    def attempt_dir_factory(self):
        run_one = _legacy.run_one_module()

        def _factory(manifest: Manifest, case) -> Path:
            # Match the legacy layout exactly; the legacy run_one will
            # also create/own its own attempt directory under
            # `combo_runs_dir(...)`. We return a stable per-case path
            # so the framework can still reason about it.
            return run_one.combo_runs_dir(self.config.campaign_root, case.case_id)

        return _factory


def _legacy_run_one_body(config: WindMatrixConfig) -> Callable[[AttemptContext], AttemptRecord]:
    """Build the Phase-1 LegacyDelegateStrategy body.

    The body calls `run_one.run_one(...)` and translates its returned
    record dict into a framework `AttemptRecord`.
    """
    run_one = _legacy.run_one_module()

    def body(ctx: AttemptContext) -> AttemptRecord:
        x = ctx.case.parameters["wind_x_mps"]
        y = ctx.case.parameters["wind_y_mps"]
        slot_deadline = ctx.slot_deadline_monotonic_s
        if slot_deadline is not None and config.slot_deadline_margin_s:
            slot_deadline = slot_deadline - config.slot_deadline_margin_s
        record_dict = run_one.run_one(
            x_wind=x,
            y_wind=y,
            rep=ctx.target_run_index,
            campaign_root=config.campaign_root,
            mavlink_addr=config.mavlink_addr,
            mission_file=config.mission_file,
            heartbeat_timeout=config.heartbeat_timeout_s,
            mission_timeout=config.mission_timeout_s,
            ready_timeout=config.ready_timeout_s,
            upload_timeout=config.upload_timeout_s,
            arm_timeout=config.arm_timeout_s,
            mode_timeout=config.mode_timeout_s,
            accept_square_only=config.accept_square_only,
            manual_control=not config.auto_control,
            force_arm=config.force_arm,
            wipe_eeprom=config.wipe_eeprom,
            require_analysis=config.require_analysis,
            before_bin_names=ctx.extra.get("before_bin_names"),
            sitl_log_dir=ctx.extra.get("sitl_log_dir"),
            slot_deadline_monotonic=slot_deadline,
            preloaded_wind_world=ctx.extra.get(
                "preloaded_wind_world", config.preloaded_wind_world,
            ),
            preloaded_wind_refresh=ctx.extra.get(
                "preloaded_wind_refresh", config.preloaded_wind_refresh,
            ),
            auto_wind_phase=config.auto_wind_phase,
            param_file_stack=(
                list(config.param_file_stack)
                if config.param_file_stack is not None else None
            ),
        )
        return _record_from_legacy(ctx, record_dict)

    return body


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
    if config.attempt_strategy not in {"legacy", "staged"}:
        raise ValueError(
            "attempt_strategy must be 'legacy' or 'staged', got "
            f"{config.attempt_strategy!r}"
        )
    if (
        config.attempt_strategy == "staged"
        and config.auto_control
        and config.auto_wind_phase == "after-takeoff"
    ):
        raise ValueError(
            "staged wind_matrix attempts do not support "
            "auto_wind_phase='after-takeoff'. Use attempt_strategy='legacy' "
            "or auto_wind_phase='before-arm'."
        )
    return WindMatrixPlugin(
        config=config,
        case_generator=WindMatrixCaseGenerator(config),
        environment=WindMatrixEnvironment(config),
        manifest=LegacyManifest(
            config.campaign_root,
            require_analysis=config.require_analysis,
            accept_square_only=config.accept_square_only,
        ),
        legacy_body=_legacy_run_one_body(config),
        staged_strategy=(
            _staged_strategy(config)
            if config.attempt_strategy == "staged" else None
        ),
    )


def _staged_strategy(config: WindMatrixConfig) -> StagedStrategy:
    run_one = _legacy.run_one_module()
    control = (
        MavlinkAutoMissionControl(
            mission_file=config.mission_file,
            upload_timeout_s=config.upload_timeout_s,
            arm_timeout_s=config.arm_timeout_s,
            mode_timeout_s=config.mode_timeout_s,
            settle_s=run_one.AUTO_ARM_TO_AUTO_SETTLE_S,
            force_arm=config.force_arm,
            upload_mission=run_one.upload_mission,
            verify_mission=run_one.verify_mission,
            arm_vehicle=run_one.arm_vehicle,
            settle_after_arm_before_auto=run_one.settle_after_arm_before_auto,
            set_auto_mode=run_one.set_auto_mode,
            clamp_timeout_to_slot=run_one.clamp_timeout_to_slot,
            bin_flush_delay_s=run_one.BIN_FLUSH_DELAY_S,
            analysis_headroom_s=run_one.ANALYSIS_HEADROOM_S,
            log=run_one.log,
        )
        if config.auto_control
        else ManualMissionControl(config.mission_file, log=run_one.log)
    )
    return StagedStrategy(
        stimulus=WindMatrixStimulus(config),
        control=control,
        monitor=DisarmCompletionMonitor(
            mission_timeout_s=config.mission_timeout_s,
            monitor_until_disarm=run_one.monitor_until_disarm,
            clamp_timeout_to_slot=run_one.clamp_timeout_to_slot,
            mission_pre_loaded=config.auto_control,
            stop_on_square_loiter=config.accept_square_only,
            bin_flush_delay_s=run_one.BIN_FLUSH_DELAY_S,
            analysis_headroom_s=run_one.ANALYSIS_HEADROOM_S,
        ),
        analyzers=AnalyzerChain([WindMatrixAnalyzer(config)]),
        verdict_policy=WindMatrixVerdictPolicy(),
        on_exception=lambda ctx, exc: build_wind_matrix_error_record(
            config, ctx, exc,
        ),
    )
