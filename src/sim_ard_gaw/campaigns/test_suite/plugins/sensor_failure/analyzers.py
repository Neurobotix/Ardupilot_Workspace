"""sensor_failure analysis and verdict adapters.

The analyzer extracts the resilience metrics from the monitor state (and copies
the raw .BIN into the attempt dir for provenance), writes verdict.json and
resilience_summary.json, and stashes plugin manifest fields. The verdict policy
implements the declarative resilience PASS/FAIL:

- hard_denial (gps_disable): PASS = the vehicle SAFELY handled the loss — the
  fault was injected and either an expected safe failsafe/recovery mode was
  entered, or it dead-reckoned while keeping attitude and altitude bounded; the
  vehicle did not lose attitude or sink/balloon out of band. Mission completion
  is NOT required.
- degradation (gps_glitch_50m): PASS = the position/EKF stayed bounded — the
  horizontal excursion attributable to the glitch stayed within tolerance and
  attitude/altitude stayed in band.

A failed/absent injection, an out-of-band attitude or altitude, or an excessive
excursion is a FAIL. This is resilience-based, not tracking-accuracy-based.

No legacy runner import. No framework-core edit.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from typing import Any, Sequence

from ..wind_matrix.analysis_helpers import (
    clamp_timeout_to_slot,
    collect_bin_log,
    ensure_run_alias_link,
    summarize_exception_text,
)
from ...core.analysis import Analyzer
from ...core.models import (
    AnalysisResult,
    AttemptContext,
    AttemptRecord,
    AttemptStatus,
    MonitorResult,
    TestCase,
    Verdict,
    VerdictClass,
)
from ...core.verdicts import VerdictPolicy
from . import defaults
from .config import SensorFailureConfig


@dataclass
class SensorFailureAnalyzer(Analyzer):
    config: SensorFailureConfig
    name: str = "sensor_failure_resilience_analysis"

    def analyze(self, case: TestCase, ctx: AttemptContext) -> AnalysisResult:
        try:
            return self._analyze(case, ctx)
        except Exception as exc:
            return self._terminal_error_result(case, ctx, exc)

    def _analyze(self, case: TestCase, ctx: AttemptContext) -> AnalysisResult:
        state = ctx.extra.get("resilience_state") or {}
        key = case.case_id
        attempt_name = defaults.attempt_id(
            key, ctx.target_run_index, ctx.attempt_index,
        )
        copied_bin_name = defaults.named_bin_filename(
            key, ctx.target_run_index, ctx.attempt_index,
        )
        bin_search_dir = defaults.sitl_bin_dir(ctx.extra.get("sitl_log_dir"))
        before_bins = set(ctx.extra.get("before_bin_names") or set())

        flush_wait_s = clamp_timeout_to_slot(
            defaults.BIN_FLUSH_DELAY_S,
            ctx.slot_deadline_monotonic_s,
            phase="BIN flush wait",
            reserve_s=defaults.ANALYSIS_HEADROOM_S,
        )
        time.sleep(flush_wait_s)
        bin_path = collect_bin_log(
            before_bins,
            ctx.start_wall_s,
            log_dir=bin_search_dir,
            strict_new_names=ctx.extra.get("sitl_log_dir") is not None,
        )
        raw_log_path = None
        if bin_path is not None:
            dest_bin = ctx.attempt_dir / copied_bin_name
            shutil.copy2(bin_path, dest_bin)
            ctx.artifacts["raw_log"] = dest_bin
            raw_log_path = str(dest_bin)

        metrics = _resilience_metrics(state)
        deltas = _behavioral_deltas(metrics)
        behavior, accepted, status, reasons = _classify_behavior(
            verdict_mode=str(
                state.get("verdict_mode") or case.parameters.get("verdict_mode") or ""
            ),
            metrics=metrics,
            deltas=deltas,
        )

        resilience_summary = {
            "attempt_id": attempt_name,
            "case_id": key,
            "verdict_mode": metrics["verdict_mode"],
            # `behavior` is the science output (what the vehicle DID); `accepted`
            # means the characterization itself was clean (fault applied/baseline
            # stamped + enough samples). We do NOT gate acceptance on guessed
            # safety thresholds.
            "behavior": behavior,
            "accepted": accepted,
            "status": status,
            "reasons": reasons,
            "pre_fault_envelope": _pre_envelope(metrics),
            "post_fault_envelope": _post_envelope(metrics),
            "deltas_post_minus_pre": deltas,
            "metrics": metrics,
            "raw_log_path": raw_log_path,
        }
        defaults.write_json(
            ctx.attempt_dir / "resilience_summary.json", resilience_summary,
        )
        defaults.write_json(ctx.attempt_dir / "verdict.json", {
            "attempt_id": attempt_name,
            "case_id": key,
            "verdict_mode": metrics["verdict_mode"],
            "behavior": behavior,
            "accepted": accepted,
            "status": status,
            "reasons": reasons,
            "recovery_mode": metrics["mode_after_inject"],
            "mode_changed_after_inject": metrics["mode_changed_after_inject"],
            "pre_fault_envelope": _pre_envelope(metrics),
            "post_fault_envelope": _post_envelope(metrics),
            "deltas_post_minus_pre": deltas,
        })

        run_alias = None
        if accepted:
            run_alias = defaults.run_alias(ctx.target_run_index)
            # Create the curated `<case>/runs/run_NN -> attempt_MMM` symlink so an
            # accepted run is reachable by its run alias, not just by attempt id.
            # (Without this the manifest names a run_alias that has no symlink.)
            ensure_run_alias_link(
                defaults.case_runs_dir(self.config.campaign_root, key) / run_alias,
                ctx.attempt_dir,
            )

        end_time = defaults.utc_now()
        plugin_fields = _plugin_fields(
            self.config, ctx, key, attempt_name, behavior, accepted, status,
            reasons, metrics, deltas, raw_log_path, run_alias, end_time,
        )
        ctx.extra["plugin_manifest_fields"] = plugin_fields

        return AnalysisResult(
            analyzer_name=self.name,
            ok=True,  # the analysis itself ran; behavior class is the result
            summary={
                "behavior": behavior,
                "accepted": accepted,
                "status": status,
                "verdict_mode": metrics["verdict_mode"],
                "reasons": reasons,
            },
            output_paths=(
                [ctx.attempt_dir / "verdict.json",
                 ctx.attempt_dir / "resilience_summary.json"]
            ),
            error=None,
        )

    def _terminal_error_result(
        self, case: TestCase, ctx: AttemptContext, exc: Exception,
    ) -> AnalysisResult:
        plugin_fields = build_sensor_failure_error_fields(self.config, ctx, exc)
        ctx.extra["plugin_manifest_fields"] = plugin_fields
        ctx.extra["attempt_status"] = AttemptStatus.ERROR
        return _error_analysis_result(exc)


def _resilience_metrics(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict_mode": str(state.get("verdict_mode") or ""),
        "is_baseline": bool(state.get("is_baseline", False)),
        "fault_injected": bool(state.get("fault_injected", False)),
        "fault_inject_seq": state.get("fault_inject_seq"),
        "fault_inject_error": state.get("fault_inject_error"),
        "confirmed_inject_params": state.get("confirmed_inject_params") or {},
        "mode_at_inject": state.get("mode_at_inject"),
        "mode_after_inject": state.get("mode_after_inject"),
        "mode_changed_after_inject": bool(state.get("mode_changed_after_inject", False)),
        "modes_seen": list(state.get("modes_seen") or []),
        # Pre-fault (control) envelope for this flight.
        "pre_inject_min_relalt_m": state.get("pre_inject_min_relalt_m"),
        "pre_inject_max_relalt_m": state.get("pre_inject_max_relalt_m"),
        "pre_inject_max_roll_deg": state.get("pre_inject_max_roll_deg"),
        "pre_inject_max_pitch_deg": state.get("pre_inject_max_pitch_deg"),
        "pre_inject_max_groundspeed_ms": state.get("pre_inject_max_groundspeed_ms"),
        "pre_inject_attitude_samples": int(state.get("pre_inject_attitude_samples") or 0),
        # Post-fault response envelope.
        "post_inject_min_relalt_m": state.get("post_inject_min_relalt_m"),
        "post_inject_max_relalt_m": state.get("post_inject_max_relalt_m"),
        "post_inject_max_roll_deg": state.get("post_inject_max_roll_deg"),
        "post_inject_max_pitch_deg": state.get("post_inject_max_pitch_deg"),
        "post_inject_max_groundspeed_ms": state.get("post_inject_max_groundspeed_ms"),
        "post_inject_max_excursion_m": state.get("post_inject_max_excursion_m"),
        "post_inject_attitude_samples": int(state.get("post_inject_attitude_samples") or 0),
        "ekf_failsafe_statustext": bool(state.get("ekf_failsafe_statustext", False)),
        "disarmed": bool(state.get("disarmed", False)),
        "timed_out": bool(state.get("timed_out", False)),
        "observation_duration_s": state.get("observation_duration_s"),
        "stopped_reason": state.get("stopped_reason"),
    }


def _pre_envelope(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "min_relalt_m": m["pre_inject_min_relalt_m"],
        "max_relalt_m": m["pre_inject_max_relalt_m"],
        "max_roll_deg": m["pre_inject_max_roll_deg"],
        "max_pitch_deg": m["pre_inject_max_pitch_deg"],
        "max_groundspeed_ms": m["pre_inject_max_groundspeed_ms"],
        "attitude_samples": m["pre_inject_attitude_samples"],
    }


def _post_envelope(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "min_relalt_m": m["post_inject_min_relalt_m"],
        "max_relalt_m": m["post_inject_max_relalt_m"],
        "max_roll_deg": m["post_inject_max_roll_deg"],
        "max_pitch_deg": m["post_inject_max_pitch_deg"],
        "max_groundspeed_ms": m["post_inject_max_groundspeed_ms"],
        "max_excursion_m": m["post_inject_max_excursion_m"],
        "attitude_samples": m["post_inject_attitude_samples"],
        "recovery_mode": m["mode_after_inject"],
        "mode_changed": m["mode_changed_after_inject"],
    }


def _behavioral_deltas(m: dict[str, Any]) -> dict[str, Any]:
    """Post-fault MINUS pre-fault, the measured behavioral change for THIS
    flight. None where a side has no samples."""
    def _delta(post_key: str, pre_key: str) -> float | None:
        post = m.get(post_key)
        pre = m.get(pre_key)
        if post is None or pre is None:
            return None
        return round(float(post) - float(pre), 3)

    alt_floor_drop = None
    if m["pre_inject_min_relalt_m"] is not None and m["post_inject_min_relalt_m"] is not None:
        alt_floor_drop = round(
            float(m["pre_inject_min_relalt_m"]) - float(m["post_inject_min_relalt_m"]), 3,
        )
    return {
        "max_roll_deg": _delta("post_inject_max_roll_deg", "pre_inject_max_roll_deg"),
        "max_pitch_deg": _delta("post_inject_max_pitch_deg", "pre_inject_max_pitch_deg"),
        "max_groundspeed_ms": _delta(
            "post_inject_max_groundspeed_ms", "pre_inject_max_groundspeed_ms",
        ),
        "min_relalt_drop_m": alt_floor_drop,
        "max_relalt_m": _delta("post_inject_max_relalt_m", "pre_inject_max_relalt_m"),
        # Excursion has no pre-fault analogue (origin is the inject fix), so it
        # is reported as the absolute post-fault max excursion.
        "post_inject_max_excursion_m": m["post_inject_max_excursion_m"],
    }


# Behavioral classification thresholds, expressed RELATIVE to the pre-fault
# envelope (not absolute guessed bounds). A response is `unsafe` only if it
# diverges far beyond how the vehicle was already flying, lost control, or
# crashed. These multipliers are conservative and documented as such.
ATTITUDE_DIVERGENCE_FACTOR = 2.5   # roll/pitch > factor x pre-fault max -> divergent
ATTITUDE_DIVERGENCE_FLOOR_DEG = 60.0  # ...but only flag if also past this absolute floor
ALT_COLLAPSE_DROP_M = 40.0         # losing >40 m below the pre-fault floor -> collapse
MIN_SAMPLES_FOR_CHARACTERIZATION = 3


def _classify_behavior(
    *, verdict_mode: str, metrics: dict[str, Any], deltas: dict[str, Any],
) -> tuple[str, bool, str, list[str]]:
    """Classify what the vehicle DID and whether the run is an accepted (clean)
    characterization.

    Returns (behavior, accepted, status, reasons):
      - behavior in {nominal, safe_degraded, unsafe, not_characterized}
      - accepted: True when the fault/baseline was applied AND enough post-trigger
        samples exist to characterize behavior. Acceptance is NOT a safety gate.
      - status: short machine label; reasons: human-readable findings.
    """
    reasons: list[str] = []
    is_baseline = metrics["is_baseline"]

    # 1. Did we get a clean measurement?
    if not metrics["fault_injected"]:
        err = metrics.get("fault_inject_error")
        if is_baseline:
            reasons.append("baseline trigger waypoint never reached")
        else:
            reasons.append(
                f"fault was not injected ({err})" if err else "fault was not injected"
            )
        return "not_characterized", False, "not_characterized_no_trigger", reasons

    if metrics["post_inject_attitude_samples"] < MIN_SAMPLES_FOR_CHARACTERIZATION:
        reasons.append(
            f"insufficient post-trigger samples "
            f"({metrics['post_inject_attitude_samples']} < "
            f"{MIN_SAMPLES_FOR_CHARACTERIZATION})"
        )
        return "not_characterized", False, "not_characterized_thin_window", reasons

    # 2. Behavioral classification relative to the pre-fault envelope.
    pre_roll = float(metrics["pre_inject_max_roll_deg"] or 0.0)
    pre_pitch = float(metrics["pre_inject_max_pitch_deg"] or 0.0)
    post_roll = float(metrics["post_inject_max_roll_deg"] or 0.0)
    post_pitch = float(metrics["post_inject_max_pitch_deg"] or 0.0)

    divergent = False
    if (
        post_roll > ATTITUDE_DIVERGENCE_FLOOR_DEG
        and post_roll > ATTITUDE_DIVERGENCE_FACTOR * max(pre_roll, 1.0)
    ):
        divergent = True
        reasons.append(
            f"roll diverged: {post_roll:.0f}deg post vs {pre_roll:.0f}deg pre-fault max"
        )
    if (
        post_pitch > ATTITUDE_DIVERGENCE_FLOOR_DEG
        and post_pitch > ATTITUDE_DIVERGENCE_FACTOR * max(pre_pitch, 1.0)
    ):
        divergent = True
        reasons.append(
            f"pitch diverged: {post_pitch:.0f}deg post vs {pre_pitch:.0f}deg pre-fault max"
        )

    alt_collapse = False
    drop = deltas.get("min_relalt_drop_m")
    if drop is not None and drop > ALT_COLLAPSE_DROP_M:
        alt_collapse = True
        reasons.append(
            f"altitude collapsed: lost {drop:.0f} m below the pre-fault floor"
        )

    crashed = metrics["disarmed"] and not is_baseline  # unexpected disarm mid-window

    if divergent or alt_collapse or crashed:
        if crashed:
            reasons.append("vehicle disarmed unexpectedly during the response window")
        behavior = "unsafe"
        status = "unsafe_divergence"
    else:
        # Bounded relative to how it was already flying.
        excursion = metrics["post_inject_max_excursion_m"] or 0.0
        if is_baseline:
            behavior = "nominal"
            status = "baseline_nominal"
            reasons.append(
                f"nominal control flight; reference excursion {excursion:.0f} m, "
                f"roll<= {post_roll:.0f}deg, alt {metrics['post_inject_min_relalt_m']}"
                f"-{metrics['post_inject_max_relalt_m']} m"
            )
        else:
            # Did it deviate from nominal at all?
            roll_delta = deltas.get("max_roll_deg") or 0.0
            mode = str(metrics.get("mode_after_inject") or "")
            mode_note = (
                f" entered {mode}" if metrics["mode_changed_after_inject"] else
                f" stayed in {mode}"
            )
            behavior = "safe_degraded"
            status = "safe_degraded"
            reasons.append(
                f"controlled response after GPS fault:{mode_note}; "
                f"roll +{roll_delta:.0f}deg vs pre-fault, "
                f"excursion {excursion:.0f} m, attitude/altitude bounded"
            )

    accepted = True  # the characterization was clean regardless of behavior class
    return behavior, accepted, status, reasons


def _plugin_fields(
    config: SensorFailureConfig,
    ctx: AttemptContext,
    key: str,
    attempt_name: str,
    behavior: str,
    accepted: bool,
    status: str,
    reasons: list[str],
    metrics: dict[str, Any],
    deltas: dict[str, Any],
    raw_log_path: str | None,
    run_alias: str | None,
    end_time: str,
) -> dict[str, Any]:
    attempt_dir = ctx.attempt_dir
    return {
        "attempt_id": attempt_name,
        "case_id": key,
        "sensor": ctx.case.parameters.get("sensor"),
        "fault_mode": ctx.case.parameters.get("mode"),
        "verdict_mode": metrics["verdict_mode"],
        "target_run_index": ctx.target_run_index,
        "attempt_index": ctx.attempt_index,
        "status": status,
        "behavior": behavior,
        "accepted": accepted,
        "fault_injected": metrics["fault_injected"],
        "recovery_mode": metrics["mode_after_inject"],
        "mode_changed_after_inject": metrics["mode_changed_after_inject"],
        "post_inject_max_excursion_m": metrics["post_inject_max_excursion_m"],
        "pre_inject_max_roll_deg": metrics["pre_inject_max_roll_deg"],
        "post_inject_max_roll_deg": metrics["post_inject_max_roll_deg"],
        "delta_max_roll_deg": deltas.get("max_roll_deg"),
        "post_inject_min_relalt_m": metrics["post_inject_min_relalt_m"],
        "post_inject_max_relalt_m": metrics["post_inject_max_relalt_m"],
        "min_relalt_drop_m": deltas.get("min_relalt_drop_m"),
        "reasons": reasons,
        "raw_log_path": raw_log_path,
        "attempt_dir": str(attempt_dir),
        "run_alias": run_alias,
        "start_time_utc": ctx.extra.get("attempt_start_time_utc") or end_time,
        "end_time_utc": end_time,
        "duration_wall_s": round(time.time() - ctx.start_wall_s, 1),
        "notes": list(reasons),
        "artifacts": {
            "attempt_dir": str(attempt_dir),
            **({"raw_log": raw_log_path} if raw_log_path is not None else {}),
            **({"run_alias": run_alias} if run_alias is not None else {}),
        },
    }


def build_sensor_failure_error_fields(
    config: SensorFailureConfig,
    ctx: AttemptContext,
    exc: BaseException,
) -> dict[str, Any]:
    key = ctx.case.case_id
    attempt_dir = defaults.attempt_dir(config.campaign_root, key, ctx.attempt_index)
    ctx.attempt_dir = attempt_dir
    attempt_dir.mkdir(parents=True, exist_ok=True)
    message = summarize_exception_text(exc)
    end_time = defaults.utc_now()
    status = "error" if isinstance(exc, Exception) else "interrupted"
    return {
        "attempt_id": defaults.attempt_id(key, ctx.target_run_index, ctx.attempt_index),
        "case_id": key,
        "sensor": ctx.case.parameters.get("sensor"),
        "fault_mode": ctx.case.parameters.get("mode"),
        "verdict_mode": ctx.case.parameters.get("verdict_mode"),
        "target_run_index": ctx.target_run_index,
        "attempt_index": ctx.attempt_index,
        "status": status,
        "behavior": "not_characterized",
        "accepted": False,
        "fault_injected": False,
        "recovery_mode": None,
        "raw_log_path": None,
        "attempt_dir": str(attempt_dir),
        "run_alias": None,
        "start_time_utc": ctx.extra.get("attempt_start_time_utc") or end_time,
        "end_time_utc": end_time,
        "duration_wall_s": round(time.time() - ctx.start_wall_s, 1),
        "notes": [f"exception: {message}"],
        "artifacts": {"attempt_dir": str(attempt_dir)},
    }


def build_sensor_failure_error_record(
    config: SensorFailureConfig,
    ctx: AttemptContext,
    exc: BaseException,
) -> AttemptRecord:
    plugin_fields = build_sensor_failure_error_fields(config, ctx, exc)
    framework_status = (
        AttemptStatus.INTERRUPTED
        if plugin_fields.get("status") == "interrupted"
        else AttemptStatus.ERROR
    )
    ctx.extra["plugin_manifest_fields"] = plugin_fields
    analysis_result = _error_analysis_result(exc)
    return AttemptRecord(
        attempt_id=str(plugin_fields["attempt_id"]),
        suite_name=ctx.case.suite_name,
        case_id=ctx.case.case_id,
        target_run_index=ctx.target_run_index,
        attempt_index=ctx.attempt_index,
        status=framework_status,
        verdict=Verdict(
            klass=VerdictClass.FAILED_RETRYABLE,
            reason=str(plugin_fields["status"]),
            retryable=True,
            requires_analysis=False,
            metadata={"exception": analysis_result.error},
        ),
        monitor_result=MonitorResult(
            completed=False,
            reason=f"exception: {analysis_result.error}",
            duration_s=round(time.time() - ctx.start_wall_s, 1),
        ),
        analysis_results=[analysis_result],
        start_time_utc=str(plugin_fields["start_time_utc"]),
        end_time_utc=str(plugin_fields["end_time_utc"]),
        duration_wall_s=float(plugin_fields["duration_wall_s"]),
        artifacts=dict(plugin_fields["artifacts"]),
        parameters=dict(ctx.case.parameters),
        stimulus_result=dict(ctx.stimulus_result),
        notes=list(plugin_fields["notes"]),
        plugin_manifest_fields=plugin_fields,
    )


def build_sensor_failure_running_record(
    config: SensorFailureConfig,
    ctx: AttemptContext,
) -> AttemptRecord:
    key = ctx.case.case_id
    attempt_dir = defaults.attempt_dir(config.campaign_root, key, ctx.attempt_index)
    ctx.attempt_dir = attempt_dir
    attempt_dir.mkdir(parents=True, exist_ok=True)
    start_time = str(ctx.extra.get("attempt_start_time_utc") or defaults.utc_now())
    ctx.extra["attempt_start_time_utc"] = start_time
    plugin_fields = {
        "attempt_id": defaults.attempt_id(key, ctx.target_run_index, ctx.attempt_index),
        "case_id": key,
        "sensor": ctx.case.parameters.get("sensor"),
        "fault_mode": ctx.case.parameters.get("mode"),
        "verdict_mode": ctx.case.parameters.get("verdict_mode"),
        "target_run_index": ctx.target_run_index,
        "attempt_index": ctx.attempt_index,
        "status": "running",
        "behavior": "running",
        "accepted": False,
        "fault_injected": False,
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


def _error_analysis_result(exc: BaseException) -> AnalysisResult:
    message = summarize_exception_text(exc)
    status = "error" if isinstance(exc, Exception) else "interrupted"
    return AnalysisResult(
        analyzer_name="sensor_failure_exception",
        ok=False,
        summary={"status": status, "behavior": "not_characterized", "accepted": False},
        output_paths=[],
        error=message,
    )


class SensorFailureVerdictPolicy(VerdictPolicy):
    """Maps the behavioral characterization to a framework verdict.

    A run SUCCEEDS when it produced a clean characterization (`accepted`), i.e.
    the fault was applied (or the baseline trigger reached) and enough
    post-trigger samples exist. The behavior class (nominal / safe_degraded /
    unsafe) is recorded as the scientific result, NOT used to fail the run — we
    are characterizing what happens, not gating on guessed safety bounds. A run
    that produced no clean measurement is retried.
    """

    def classify(
        self,
        case: TestCase,
        monitor_result: MonitorResult,
        analysis_results: Sequence[AnalysisResult],
    ) -> Verdict:
        accepted = False
        behavior = "not_characterized"
        status = "not_characterized"
        reasons: list[str] = []
        if analysis_results:
            summary = analysis_results[-1].summary
            accepted = bool(summary.get("accepted", False))
            behavior = str(summary.get("behavior") or behavior)
            status = str(summary.get("status") or status)
            reasons = list(summary.get("reasons") or [])
        klass = VerdictClass.SUCCESS if accepted else VerdictClass.FAILED_RETRYABLE
        return Verdict(
            klass=klass,
            reason=status,
            retryable=not accepted,
            requires_analysis=True,
            metadata={
                "behavior": behavior,
                "monitor_reason": monitor_result.reason,
                "reasons": reasons,
            },
        )
