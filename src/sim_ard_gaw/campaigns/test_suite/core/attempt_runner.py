"""AttemptRunner: orchestrates one attempt's lifecycle.

Phase 1 supports two strategies:

- `LegacyDelegateStrategy` — calls `run_one.run_one(...)` as a single
  body for stages 4-10. Used by the wind_matrix plugin to preserve
  exact current behavior.
- `StagedStrategy` — walks each stage adapter explicitly. Used by new
  plugins that don't have legacy delegates to lean on, and by the
  Phase-3 split-up wind_matrix plugin.

Both strategies share stages 1-3 (env prepare/launch/ready) and stage
12 (cleanup) — those are framework-owned in every case.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .analysis import AnalyzerChain
from .control import ControlStrategy
from .environment import EnvironmentAdapter
from .manifest import Manifest
from .models import (
    AttemptContext,
    AttemptRecord,
    AttemptStatus,
    MonitorResult,
    TestCase,
    Verdict,
)
from .monitor import CompletionMonitor
from .stimulus import StimulusAdapter
from .verdicts import VerdictPolicy


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AttemptStrategy(ABC):
    """The plugin-overridable body of one attempt (stages 4-10).

    Stages 1-3 (env prepare/launch/ready) and stage 12 (cleanup) are
    always run by the framework regardless of strategy.
    """

    @abstractmethod
    def execute(self, ctx: AttemptContext) -> AttemptRecord:
        ...


@dataclass
class StagedStrategy(AttemptStrategy):
    """Canonical staged execution: stim → control → monitor → analyze →
    verdict. Use this for any new plugin."""
    stimulus: StimulusAdapter
    control: ControlStrategy
    monitor: CompletionMonitor
    analyzers: AnalyzerChain
    verdict_policy: VerdictPolicy

    def execute(self, ctx: AttemptContext) -> AttemptRecord:
        ctx.stimulus_result = self.stimulus.apply(ctx.case, ctx)
        verify_payload = self.stimulus.verify(ctx.case, ctx)
        if verify_payload:
            ctx.stimulus_result.setdefault("verify", verify_payload)

        self.control.execute(ctx.case, ctx)
        monitor_result: MonitorResult = self.monitor.run(ctx.case, ctx)
        analysis_results = self.analyzers.run(ctx.case, ctx)
        verdict: Verdict = self.verdict_policy.classify(
            ctx.case, monitor_result, analysis_results,
        )

        return AttemptRecord(
            attempt_id=f"{ctx.case.case_id}__attempt_{ctx.attempt_index:03d}",
            suite_name=ctx.case.suite_name,
            case_id=ctx.case.case_id,
            target_run_index=ctx.target_run_index,
            attempt_index=ctx.attempt_index,
            status=_status_from_verdict(verdict),
            verdict=verdict,
            monitor_result=monitor_result,
            analysis_results=list(analysis_results),
            start_time_utc=_utc_now_iso(),  # filled in by runner end-of-run
            duration_wall_s=time.time() - ctx.start_wall_s,
            parameters=dict(ctx.case.parameters),
            stimulus_result=dict(ctx.stimulus_result),
        )


def _status_from_verdict(v: Verdict) -> AttemptStatus:
    from .models import VerdictClass
    return {
        VerdictClass.SUCCESS: AttemptStatus.SUCCESS,
        VerdictClass.PARTIAL: AttemptStatus.PARTIAL,
        VerdictClass.FAILED: AttemptStatus.FAILED,
        VerdictClass.FAILED_RETRYABLE: AttemptStatus.FAILED,
        VerdictClass.ANALYSIS_FAILED: AttemptStatus.ANALYSIS_FAILED,
    }[v.klass]


@dataclass
class LegacyDelegateStrategy(AttemptStrategy):
    """Phase-1 escape hatch: hand stages 4-10 to a single callable.

    The wind_matrix plugin uses this to call `run_one.run_one(...)` as
    one block, preserving exact behavior of the existing campaign.
    """
    body: Callable[[AttemptContext], AttemptRecord]

    def execute(self, ctx: AttemptContext) -> AttemptRecord:
        return self.body(ctx)


class AttemptRunner:
    def __init__(
        self,
        environment: EnvironmentAdapter,
        strategy: AttemptStrategy,
        manifest: Manifest,
        artifact_root: Path,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._env = environment
        self._strategy = strategy
        self._manifest = manifest
        self._artifact_root = artifact_root
        self._log = log or (lambda msg: print(msg))

    def run(
        self,
        case: TestCase,
        target_run_index: int,
        attempt_index: int,
        attempt_dir: Path,
        slot_deadline_monotonic_s: float | None = None,
        attempt_metadata: dict | None = None,
    ) -> AttemptRecord:
        ctx = AttemptContext(
            case=case,
            campaign_root=self._artifact_root,
            attempt_dir=attempt_dir,
            attempt_index=attempt_index,
            target_run_index=target_run_index,
            start_wall_s=time.time(),
            start_monotonic_s=time.monotonic(),
            slot_deadline_monotonic_s=slot_deadline_monotonic_s,
        )
        if attempt_metadata:
            ctx.extra.update(attempt_metadata)

        try:
            self._env.prepare_case(case)
            self._env.launch(case, ctx)
            self._env.assert_ready(case, ctx)
            record = self._strategy.execute(ctx)
            if not record.end_time_utc:
                record.end_time_utc = _utc_now_iso()
            record.duration_wall_s = time.time() - ctx.start_wall_s
            self._manifest.append_attempt(record)
            return record
        except Exception as exc:
            self._log(f"[attempt_runner] error in {case.case_id}: "
                      f"{type(exc).__name__}: {exc}")
            raise
        finally:
            try:
                self._env.cleanup(case, ctx)
            except Exception as cleanup_exc:
                self._log(f"[attempt_runner] cleanup error: "
                          f"{type(cleanup_exc).__name__}: {cleanup_exc}")
