"""Monitor metadata for gps_failure."""
from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Iterable

from ...core.models import AttemptContext, MonitorResult, TestCase
from ...core.monitor import CompletionMonitor
from . import defaults
from .config import GpsFailureConfig
from . import telemetry
from .analyzers import classify_observation


@dataclass
class GpsFailureMonitor(CompletionMonitor):
    config: GpsFailureConfig

    def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
        if not self.config.launch_stack:
            return MonitorResult(
                completed=False,
                reason="phase1_no_sitl_monitor_not_run",
                duration_s=0.0,
            )
        master = ctx.extra.get("mavlink_master")
        if master is None:
            raise RuntimeError("MAVLink master is missing from attempt context.")
        live = _LiveGpsMonitor(self.config, case, ctx, master)
        return live.run()


class _LiveGpsMonitor:
    def __init__(
        self,
        config: GpsFailureConfig,
        case: TestCase,
        ctx: AttemptContext,
        master: Any,
    ) -> None:
        self.config = config
        self.case = case
        self.ctx = ctx
        self.master = master
        self.started_monotonic = time.monotonic()
        self.deadline = self.started_monotonic + config.mission_timeout_s
        self.trigger_trace: list[dict[str, Any]] = []
        self.normalized_messages: list[dict[str, Any]] = []
        self.injection_attempted = False
        self.triggered = False
        self.injection_monotonic_s: float | None = None
        self.injection_result: dict[str, Any] | None = None
        self.restore_results: list[dict[str, Any]] = []
        self.ramp_update_results: list[dict[str, Any]] = []
        self.next_ramp_update_s = defaults.SLOW_DRIFT_UPDATE_PERIOD_S
        self.stop_reason = "trigger_not_observed"
        self.operation_failure_reason: str | None = None
        self.observation_end_monotonic_s = self.started_monotonic

    def run(self) -> MonitorResult:
        rate_results = telemetry.request_telemetry_rates(self.master)
        self.ctx.extra["gps_telemetry_rate_requests"] = [
            result.as_dict() for result in rate_results
        ]
        if not all(result.ok for result in rate_results):
            self.stop_reason = "telemetry_rate_request_failed"
            self._write_artifacts()
            return self._monitor_result()
        self._read_source_contract_parameters()

        while time.monotonic() < self.deadline:
            msg = self.master.recv_match(
                type=list(defaults.TELEMETRY_MESSAGE_TYPES),
                blocking=True,
                timeout=0.5,
            )
            if msg is None:
                continue
            arrival = time.monotonic()
            self.observation_end_monotonic_s = arrival
            normalized = telemetry.normalize_message(msg, arrival_monotonic_s=arrival)
            self.normalized_messages.append(normalized)
            self._maybe_record_trigger_event(normalized)
            if not self.injection_attempted and first_seq4_edge_after_armed_auto_front_half(
                self.trigger_trace
            ):
                self._execute_initial_injection(arrival)
                if not self.triggered:
                    break
            if self.triggered:
                self._maybe_execute_scheduled_steps(arrival)
                if self.operation_failure_reason is not None:
                    self.stop_reason = self.operation_failure_reason
                    break
                if self._post_injection_s(arrival) >= defaults.MIN_POST_INJECTION_S:
                    self.stop_reason = "post_injection_observation_complete"
                    break
        else:
            self.stop_reason = "monitor_timeout"

        self._write_artifacts()
        return self._monitor_result()

    def _execute_initial_injection(self, now_s: float) -> None:
        from .runtime import build_authorized_injection_plan, execute_injection_plan

        if self.injection_attempted:
            raise RuntimeError("GPS injection is one-shot and was already attempted")
        self.injection_attempted = True
        plan = build_authorized_injection_plan(self.case, self.trigger_trace)
        result = execute_injection_plan(plan, self.master)
        self.injection_result = result.as_dict()
        self.ctx.extra["gps_injection_execution"] = self.injection_result
        self.triggered = result.success or (
            plan.execution_authorized and not plan.injection_payload
        )
        if self.triggered:
            self.injection_monotonic_s = now_s
            self.stop_reason = "observing_post_injection"
        else:
            self.stop_reason = result.reason

    def _maybe_execute_scheduled_steps(self, now_s: float) -> None:
        if self.injection_monotonic_s is None:
            return
        elapsed_s = self._post_injection_s(now_s)
        self._maybe_execute_restore(elapsed_s)
        self._maybe_execute_slow_drift_update(elapsed_s)

    def _maybe_execute_restore(self, elapsed_s: float) -> None:
        if self.injection_result is None:
            return
        plan = self.injection_result.get("plan") or {}
        restore_plan = plan.get("restore_plan") or []
        from .runtime import RestoreStep, execute_restore_step
        from .mavlink import normalize_readback_rules

        for index, step_dict in enumerate(restore_plan):
            if any(item.get("restore_index") == index for item in self.restore_results):
                continue
            due_s = float(step_dict.get("elapsed_since_trigger_s", 0.0))
            if elapsed_s < due_s:
                continue
            payload = {
                str(name): float(value)
                for name, value in dict(step_dict.get("payload") or {}).items()
            }
            rules = normalize_readback_rules(step_dict.get("readback_rules") or {})
            step = RestoreStep(
                elapsed_since_trigger_s=due_s,
                payload=payload,
                readback_rules=rules,
                reason=str(step_dict.get("reason") or "restore"),
            )
            result = execute_restore_step(step, self.master)
            result_dict = result.as_dict() if result is not None else None
            self.restore_results.append({
                "restore_index": index,
                "elapsed_since_trigger_s": elapsed_s,
                "result": result_dict,
            })
            if not isinstance(result_dict, dict) or result_dict.get("success") is not True:
                self.operation_failure_reason = f"restore_failed:{index}"
                return

    def _maybe_execute_slow_drift_update(self, elapsed_s: float) -> None:
        if self.case.parameters.get("fault_type") != "slow_drift":
            return
        if elapsed_s < self.next_ramp_update_s:
            return
        from .runtime import build_authorized_injection_plan, execute_injection_plan

        trace = [dict(event) for event in self.trigger_trace]
        for event in trace:
            if event.get("seq") == defaults.INJECTION_TRIGGER["seq"]:
                event["elapsed_since_trigger_s"] = elapsed_s
                break
        plan = build_authorized_injection_plan(self.case, trace)
        result = execute_injection_plan(plan, self.master)
        self.ramp_update_results.append(
            {
                "elapsed_since_trigger_s": elapsed_s,
                "result": result.as_dict(),
            }
        )
        if result.success is not True:
            self.operation_failure_reason = "slow_drift_update_failed"
            return
        self.next_ramp_update_s += defaults.SLOW_DRIFT_UPDATE_PERIOD_S

    def _post_injection_s(self, now_s: float) -> float:
        if self.injection_monotonic_s is None:
            return 0.0
        return max(0.0, now_s - self.injection_monotonic_s)

    def _write_artifacts(self) -> None:
        self.ctx.extra["gps_trigger_trace"] = list(self.trigger_trace)
        self.ctx.extra["gps_telemetry_messages"] = list(self.normalized_messages)
        self._update_injection_artifact()
        artifacts = self._artifact_payloads()
        for name, payload in artifacts.items():
            path = self.ctx.attempt_dir / name
            defaults.write_json(path, payload)
            self.ctx.artifacts[name] = path
        observation = self._observation(artifacts)
        summary = classify_observation(observation)
        summary_path = self.ctx.attempt_dir / "gps_behavior_summary.json"
        defaults.write_json(summary_path, summary)
        self.ctx.artifacts["gps_behavior_summary.json"] = summary_path
        self.ctx.extra["gps_observation"] = observation
        self.ctx.extra["plugin_manifest_fields"] = {
            "attempt_id": defaults.case_attempt_id(
                self.case.case_id,
                self.ctx.target_run_index,
                self.ctx.attempt_index,
            ),
            "behavior_class": summary["behavior_class"],
            "observation_quality_class": summary["observation_quality_class"],
            "accepted_observation": summary["accepted_observation"],
            "artifacts": {name: str(path) for name, path in self.ctx.artifacts.items()},
            "parameters": dict(self.case.parameters),
            "notes": [summary["reason"], self.stop_reason],
        }

    def _monitor_result(self) -> MonitorResult:
        summary = self.ctx.extra.get("plugin_manifest_fields") or {}
        return MonitorResult(
            completed=bool(summary.get("accepted_observation")),
            reason=str(summary.get("behavior_class") or self.stop_reason),
            duration_s=time.monotonic() - self.started_monotonic,
            waypoints_seen=[
                int(event["seq"]) for event in self.trigger_trace if "seq" in event
            ],
            monitor_log_path=self.ctx.attempt_dir / "mode_timeline.json",
        )

    def _artifact_payloads(self) -> dict[str, dict[str, Any]]:
        artifacts = {
            "ekf_innovation_metrics.json": self._ekf_metrics_artifact(),
            "truth_vs_belief.json": self._truth_vs_belief_artifact(),
            "mode_timeline.json": self._mode_timeline_artifact(),
            "attitude_altitude_envelope.json": self._attitude_altitude_artifact(),
            "source_contract.json": self._source_contract_artifact(),
        }
        self._maybe_overlay_bin_analysis(artifacts)
        return artifacts

    def _ekf_metrics_artifact(self) -> dict[str, Any]:
        samples = [
            sample for sample in self._post_injection_messages()
            if sample["type"] == "EKF_STATUS_REPORT"
        ]
        ratios: list[float] = []
        for sample in samples:
            ratio = sample.get("pos_test_ratio")
            if isinstance(ratio, (int, float)):
                ratios.append(float(ratio))
        return {
            "pos_test_ratio": ratios,
            "reject_flags": [ratio >= 1.0 for ratio in ratios],
            "reset_events": [],
            "variance": [sample.get("pos_horiz_variance") for sample in samples],
            "samples": samples,
        }

    def _truth_vs_belief_artifact(self) -> dict[str, Any]:
        paired = _pair_live_truth_belief(self._post_injection_messages())
        gaps = [sample["horizontal_gap_m"] for sample in paired]
        growth = 0.0
        if len(paired) >= 2:
            dt = paired[-1]["arrival_monotonic_s"] - paired[0]["arrival_monotonic_s"]
            if dt > 0:
                growth = (gaps[-1] - gaps[0]) / dt
        return {
            "horizontal_gap_m": gaps,
            "gap_growth_rate_mps": growth,
            "truth_source": "SIMSTATE",
            "belief_source": "GLOBAL_POSITION_INT",
            "samples": paired,
        }

    def _mode_timeline_artifact(self) -> dict[str, Any]:
        return {
            "mode_timeline": [
                sample for sample in self._post_injection_messages()
                if sample["type"] in {"HEARTBEAT", "MISSION_CURRENT", "STATUSTEXT"}
            ],
            "trigger_trace": list(self.trigger_trace),
            "stop_reason": self.stop_reason,
        }

    def _attitude_altitude_artifact(self) -> dict[str, Any]:
        post_messages = self._post_injection_messages()
        altitude_samples = [
            {
                "arrival_monotonic_s": sample["arrival_monotonic_s"],
                "relative_alt_m": float(sample["relative_alt_mm"]) / 1000.0,
            }
            for sample in post_messages
            if sample["type"] == "GLOBAL_POSITION_INT"
            and isinstance(sample.get("relative_alt_mm"), (int, float))
        ]
        attitudes = [
            sample for sample in post_messages
            if sample["type"] == "ATTITUDE"
            and isinstance(sample.get("roll_rad"), (int, float))
            and isinstance(sample.get("pitch_rad"), (int, float))
        ]
        altitudes = [sample["relative_alt_m"] for sample in altitude_samples]
        min_alt = min(altitudes) if altitudes else None
        max_drawdown = 0.0
        running_max: float | None = None
        for altitude in altitudes:
            running_max = altitude if running_max is None else max(running_max, altitude)
            max_drawdown = max(max_drawdown, running_max - altitude)
        threshold_crossings: list[dict[str, Any]] = []
        for sample in attitudes:
            roll_deg = math.degrees(float(sample["roll_rad"]))
            pitch_deg = math.degrees(float(sample["pitch_rad"]))
            if abs(roll_deg) > defaults.MAX_ABS_ROLL_DEG:
                threshold_crossings.append({
                    "type": "roll",
                    "arrival_monotonic_s": sample.get("arrival_monotonic_s"),
                    "value_deg": roll_deg,
                    "limit_deg": defaults.MAX_ABS_ROLL_DEG,
                })
            if abs(pitch_deg) > defaults.MAX_ABS_PITCH_DEG:
                threshold_crossings.append({
                    "type": "pitch",
                    "arrival_monotonic_s": sample.get("arrival_monotonic_s"),
                    "value_deg": pitch_deg,
                    "limit_deg": defaults.MAX_ABS_PITCH_DEG,
                })
        if max_drawdown > defaults.MAX_ALTITUDE_LOSS_M:
            threshold_crossings.append({
                "type": "altitude_loss",
                "value_m": max_drawdown,
                "limit_m": defaults.MAX_ALTITUDE_LOSS_M,
            })
        unexpected_disarm = any(
            sample["type"] == "HEARTBEAT" and sample.get("armed") is False
            for sample in post_messages
        )
        return {
            "post_injection_min_alt_m": min_alt,
            "altitude_loss_m": max_drawdown,
            "altitude_samples": altitude_samples,
            "attitude_excursions": attitudes,
            "threshold_crossings": threshold_crossings,
            "unexpected_disarm": unexpected_disarm,
            "samples_complete": bool(attitudes and altitude_samples),
            "limits": {
                "max_abs_roll_deg": defaults.MAX_ABS_ROLL_DEG,
                "max_abs_pitch_deg": defaults.MAX_ABS_PITCH_DEG,
                "max_altitude_loss_m": defaults.MAX_ALTITUDE_LOSS_M,
            },
        }

    def _post_injection_messages(self) -> list[dict[str, Any]]:
        if self.injection_monotonic_s is None:
            return []
        return [
            sample
            for sample in self.normalized_messages
            if isinstance(sample.get("arrival_monotonic_s"), (int, float))
            and float(sample["arrival_monotonic_s"]) >= self.injection_monotonic_s
        ]

    def _read_source_contract_parameters(self) -> None:
        from .mavlink import read_live_contract_parameters

        results = read_live_contract_parameters(self.master)
        self.ctx.extra["gps_live_contract_readbacks"] = {
            name: result.as_dict() for name, result in results.items()
        }

    def _source_contract_artifact(self) -> dict[str, Any]:
        from .source_contract import validate_source_contract

        raw_readbacks = self.ctx.extra.get("gps_live_contract_readbacks")
        readbacks: dict[str, Any] = {}
        if isinstance(raw_readbacks, dict):
            for name, result in raw_readbacks.items():
                if (
                    isinstance(name, str)
                    and isinstance(result, dict)
                    and result.get("ok") is True
                ):
                    readbacks[name] = result.get("value")
        contract = validate_source_contract(
            readbacks,
            estimator_flags=self._latest_estimator_flags(),
        )
        payload = contract.as_dict()
        payload["readback_results"] = raw_readbacks if isinstance(raw_readbacks, dict) else {}
        self.ctx.extra["gps_source_contract"] = payload
        return payload

    def _latest_estimator_flags(self) -> int | None:
        for sample in reversed(self._post_injection_messages()):
            if sample["type"] != "EKF_STATUS_REPORT":
                continue
            flags = sample.get("flags")
            if isinstance(flags, bool):
                continue
            if isinstance(flags, int):
                return flags
            if isinstance(flags, float) and flags.is_integer():
                return int(flags)
        return None

    def _maybe_overlay_bin_analysis(
        self,
        artifacts: dict[str, dict[str, Any]],
    ) -> None:
        from .environment import identify_attempt_bin
        from .bin_analysis import analyze_attempt_bin

        bin_path = identify_attempt_bin(self.ctx)
        if bin_path is None:
            status = {
                "ok": False,
                "reason": "single_current_attempt_bin_not_available",
            }
            artifacts["ekf_innovation_metrics.json"]["bin_analysis"] = status
            artifacts["truth_vs_belief.json"]["bin_analysis"] = status
            return
        decoder = self.ctx.extra.get("gps_bin_decoder")
        injection_plan = (
            self.injection_result.get("plan")
            if isinstance(self.injection_result, dict)
            else None
        )
        injection_payload = (
            injection_plan.get("injection_payload")
            if isinstance(injection_plan, dict)
            else None
        )
        try:
            analysis = analyze_attempt_bin(
                bin_path,
                decoder=decoder,
                trigger_seq=int(defaults.INJECTION_TRIGGER["seq"]),
                injection_payload=(
                    injection_payload
                    if isinstance(injection_payload, dict)
                    else None
                ),
            )
        except Exception as exc:
            analysis = {
                "ok": False,
                "bin_path": str(bin_path),
                "reason": f"{type(exc).__name__}: {exc}",
            }
        self.ctx.extra["gps_bin_analysis"] = analysis
        mechanism = analysis.get("mechanism") if isinstance(analysis, dict) else None
        if isinstance(mechanism, dict) and mechanism.get("ok") is True:
            artifacts["ekf_innovation_metrics.json"] = _ekf_metrics_from_bin(
                mechanism,
                fallback=artifacts["ekf_innovation_metrics.json"],
            )
        truth_belief = (
            analysis.get("truth_vs_belief")
            if isinstance(analysis, dict)
            else None
        )
        if isinstance(truth_belief, dict) and truth_belief.get("ok") is True:
            artifacts["truth_vs_belief.json"] = _truth_belief_from_bin(
                truth_belief,
                fallback=artifacts["truth_vs_belief.json"],
            )
        artifacts["ekf_innovation_metrics.json"]["bin_analysis"] = analysis
        artifacts["truth_vs_belief.json"]["bin_analysis"] = analysis

    def _observation(self, artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
        post_s = (
            self._post_injection_s(self.observation_end_monotonic_s)
            if self.triggered
            else 0.0
        )
        operation_status = self._scheduled_operation_status(post_s)
        injection_ok = bool(
            self.injection_result
            and self.injection_result.get("success") is True
            and operation_status["ok"] is True
        )
        gaps = artifacts["truth_vs_belief.json"]["horizontal_gap_m"]
        ratios = artifacts["ekf_innovation_metrics.json"]["pos_test_ratio"]
        source_contract = artifacts["source_contract.json"]
        source_contract_ok = source_contract.get("ok") is True
        attitude_artifact = artifacts["attitude_altitude_envelope.json"]
        mode_samples = artifacts["mode_timeline.json"]["mode_timeline"]
        heartbeat_samples = [
            sample for sample in mode_samples if sample.get("type") == "HEARTBEAT"
        ]
        trigger_mode = next(
            (
                event.get("mode")
                for event in self.trigger_trace
                if event.get("seq") == defaults.INJECTION_TRIGGER["seq"]
            ),
            defaults.INJECTION_TRIGGER["mode"],
        )
        mode_change = any(
            sample.get("mode") not in (None, trigger_mode)
            for sample in heartbeat_samples
        )
        reset_events = artifacts["ekf_innovation_metrics.json"].get("reset_events")
        behavior_measurements_complete = bool(
            len(gaps) >= 2
            and ratios
            and attitude_artifact.get("samples_complete") is True
            and heartbeat_samples
        )
        required_present = all(
            (self.ctx.attempt_dir / name).exists()
            for name in defaults.REQUIRED_ATTEMPT_ARTIFACTS
            if name != "gps_behavior_summary.json"
        )
        observation = {
            "injection_triggered": self.triggered,
            "injection_readback_ok": injection_ok,
            "post_injection_s": post_s,
            "required_artifacts_present": required_present,
            "mechanism_evidence": bool(ratios) and source_contract_ok,
            "source_contract_ok": source_contract_ok,
            "source_contract": source_contract,
            "scheduled_operations": operation_status,
            "behavior_measurements_complete": behavior_measurements_complete,
            "horizontal_gap_m": gaps[-1] if gaps else 0.0,
            "gap_growing": bool(
                len(gaps) >= 2
                and gaps[-1] > 5.0
                and gaps[-1] - gaps[0] > 1.0
                and artifacts["truth_vs_belief.json"].get("gap_growth_rate_mps", 0.0) > 0.0
            ),
            "gap_within_nominal_band": bool((gaps[-1] if gaps else 0.0) <= 5.0),
            "attitude_in_band": bool(
                attitude_artifact.get("samples_complete") is True
                and not attitude_artifact["threshold_crossings"]
            ),
            "fused": bool(ratios and max(ratios) < 1.0),
            "pos_test_ratio_rejected": bool(ratios and max(ratios) >= 1.0),
            "reset_event": bool(reset_events),
            "failsafe": any(
                sample["type"] == "STATUSTEXT" and "failsafe" in str(sample.get("text", "")).lower()
                for sample in self._post_injection_messages()
            ),
            "mode_change": mode_change,
            "loss_of_control": bool(
                attitude_artifact["unexpected_disarm"]
                or attitude_artifact["threshold_crossings"]
            ),
        }
        self.ctx.stimulus_result["verify"] = {
            "phase": "phase2_live_terminal_verification",
            "live_readback_performed": bool(self.injection_result),
            "terminal_verification_pending": False,
            "injection_readback_ok": injection_ok,
            "scheduled_operations": operation_status,
        }
        return observation

    def _scheduled_operation_status(self, post_s: float) -> dict[str, Any]:
        plan = (
            self.injection_result.get("plan")
            if isinstance(self.injection_result, dict)
            else None
        )
        restore_plan = plan.get("restore_plan") if isinstance(plan, dict) else []
        expected_restore_count = len(restore_plan) if isinstance(restore_plan, list) else 0
        restore_ok = (
            len(self.restore_results) == expected_restore_count
            and all(
                isinstance(item.get("result"), dict)
                and item["result"].get("success") is True
                for item in self.restore_results
            )
        )
        expected_ramp_count = 0
        if self.case.parameters.get("fault_type") == "slow_drift":
            expected_ramp_count = int(
                min(post_s, defaults.MIN_POST_INJECTION_S)
                // defaults.SLOW_DRIFT_UPDATE_PERIOD_S
            )
        ramp_ok = (
            len(self.ramp_update_results) >= expected_ramp_count
            and all(
                isinstance(item.get("result"), dict)
                and item["result"].get("success") is True
                for item in self.ramp_update_results
            )
        )
        ok = bool(
            self.operation_failure_reason is None
            and restore_ok
            and ramp_ok
        )
        return {
            "ok": ok,
            "failure_reason": self.operation_failure_reason,
            "expected_restore_count": expected_restore_count,
            "completed_restore_count": len(self.restore_results),
            "expected_ramp_update_count": expected_ramp_count,
            "completed_ramp_update_count": len(self.ramp_update_results),
        }

    def _update_injection_artifact(self) -> None:
        if self.injection_result is None:
            return
        path = self.ctx.attempt_dir / "gps_injection.json"
        if path.exists():
            raw_payload = defaults.read_json(path)
            payload: dict[str, Any] = (
                raw_payload if isinstance(raw_payload, dict) else {}
            )
        else:
            payload = {"case_id": self.case.case_id}
        payload["live_execution"] = self.injection_result
        payload["restore_results"] = list(self.restore_results)
        payload["ramp_update_results"] = list(self.ramp_update_results)
        post_s = (
            self._post_injection_s(self.observation_end_monotonic_s)
            if self.triggered
            else 0.0
        )
        operation_status = self._scheduled_operation_status(post_s)
        plan = self.injection_result.get("plan")
        restore_plan = plan.get("restore_plan") if isinstance(plan, dict) else []
        payload["readback_status_shape"] = {
            "injection": (
                "verified"
                if self.injection_result.get("success") is True
                else "failed"
            ),
            "reset": (
                "not_required"
                if not restore_plan
                else "verified"
                if operation_status["completed_restore_count"]
                == operation_status["expected_restore_count"]
                and operation_status["ok"] is True
                else "failed_or_incomplete"
            ),
            "missing_params_are_pre_injection_failure": True,
        }
        live_contract = payload.get("live_plan_contract")
        if isinstance(live_contract, dict):
            live_contract.update({
                "plan_only": False,
                "live_readback_performed": True,
                "terminal_verification_pending": False,
            })
        defaults.write_json(path, payload)

    def _maybe_record_trigger_event(self, sample: dict[str, Any]) -> None:
        if sample["type"] == "HEARTBEAT":
            self.ctx.extra["gps_last_heartbeat"] = dict(sample)
            return
        if sample["type"] != "MISSION_CURRENT":
            return
        seq = sample.get("seq")
        if seq is None:
            return
        mission_arrival = sample.get("arrival_monotonic_s")
        if not isinstance(mission_arrival, (int, float)):
            return
        heartbeat = self.ctx.extra.get("gps_last_heartbeat")
        heartbeat_arrival = (
            heartbeat.get("arrival_monotonic_s")
            if isinstance(heartbeat, dict)
            else None
        )
        heartbeat_age = _sample_age(mission_arrival, heartbeat_arrival)
        latitude_fields = self._trigger_latitude_field(float(mission_arrival))
        self.trigger_trace.append(
            {
                "seq": seq,
                "armed": isinstance(heartbeat, dict) and heartbeat.get("armed") is True,
                "mode": heartbeat.get("mode") if isinstance(heartbeat, dict) else None,
                "mission_arrival_monotonic_s": float(mission_arrival),
                "heartbeat_age_s": heartbeat_age,
                "heartbeat_fresh": bool(
                    heartbeat_age is not None
                    and heartbeat_age <= defaults.TRIGGER_HEARTBEAT_MAX_AGE_S
                ),
                "trigger_time_s": sample["arrival_monotonic_s"] - self.started_monotonic,
                "elapsed_since_trigger_s": 0.0,
                **latitude_fields,
            }
        )

    def _trigger_latitude_field(self, mission_arrival_s: float) -> dict[str, Any]:
        for sample in reversed(self.normalized_messages):
            if sample["type"] == "SIMSTATE" and sample.get("lat_deg_e7") is not None:
                age = _sample_age(mission_arrival_s, sample.get("arrival_monotonic_s"))
                fresh = bool(
                    age is not None and age <= defaults.TRIGGER_SIMSTATE_MAX_AGE_S
                )
                return {
                    "trigger_latitude_deg": float(sample["lat_deg_e7"]) / 1e7,
                    "simstate_age_s": age,
                    "simstate_fresh": fresh,
                }
        return {"simstate_age_s": None, "simstate_fresh": False}


def trigger_metadata() -> dict[str, object]:
    return dict(defaults.INJECTION_TRIGGER)


def first_seq4_edge_after_front_half(sequences: Iterable[int]) -> bool:
    """Schema-level helper requiring seq 1, 2, and 3 before first seq 4."""
    seen_front_half: set[int] = set()
    required = set(defaults.INJECTION_TRIGGER["front_half_required_sequences"])
    trigger_seq = int(defaults.INJECTION_TRIGGER["seq"])
    for raw_seq in sequences:
        seq = _coerce_seq(raw_seq)
        if seq is None:
            return False
        if seq in required:
            seen_front_half.add(seq)
        if seq == trigger_seq:
            return required.issubset(seen_front_half)
    return False


def first_seq4_edge_after_armed_auto_front_half(
    events: Iterable[Any],
) -> bool:
    """Validate ADR-0020 trigger preconditions from no-SITL event records.

    Fails closed for malformed events and for any mission-current evidence that
    is not a clean, monotonic seq 1->2->3->4 progression. A regression to a lower
    seq or a skipped front-half seq is rejected. Repeated ``MISSION_CURRENT``
    events for the *current* seq are benign telemetry and allowed (the stream
    reports the same seq repeatedly), but every front-half seq must be observed
    in order, armed and in AUTO, before the first seq-4 edge.
    """
    expected_order = list(
        defaults.INJECTION_TRIGGER["front_half_required_sequences"]
    )
    trigger_seq = int(defaults.INJECTION_TRIGGER["seq"])
    trigger_mode = defaults.INJECTION_TRIGGER["mode"]
    next_required_index = 0
    last_seq: int | None = None

    for event in events:
        if not isinstance(event, dict):
            return False
        seq = _coerce_seq(event.get("seq"))
        if seq is None:
            return False
        armed = event.get("armed") is True
        mode = event.get("mode") == trigger_mode
        heartbeat_age = _finite_nonnegative(event.get("heartbeat_age_s"))
        simstate_age = _finite_nonnegative(event.get("simstate_age_s"))
        if (
            event.get("heartbeat_fresh") is not True
            or heartbeat_age is None
            or heartbeat_age > defaults.TRIGGER_HEARTBEAT_MAX_AGE_S
            or event.get("simstate_fresh") is not True
            or simstate_age is None
            or simstate_age > defaults.TRIGGER_SIMSTATE_MAX_AGE_S
        ):
            return False

        if last_seq is not None and seq < last_seq:
            # Any regression to a lower mission-current seq is invalid evidence.
            return False

        if seq == last_seq:
            # A repeat of the current seq is benign telemetry, not progression.
            continue

        if seq == trigger_seq:
            # The seq-4 edge is valid only once the full ordered front half has
            # been observed and this event is itself armed and in AUTO.
            return next_required_index == len(expected_order) and armed and mode

        if (
            next_required_index < len(expected_order)
            and seq == expected_order[next_required_index]
        ):
            if not (armed and mode):
                return False
            next_required_index += 1
            last_seq = seq
            continue

        # Any other seq (a skip ahead, an out-of-contract value, or a jump past
        # the next required front-half seq) invalidates the trace.
        return False

    return False


def _coerce_seq(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _finite_nonnegative(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0:
        return None
    return parsed


def _sample_age(newer: object, older: object) -> float | None:
    newer_value = _finite_nonnegative(newer)
    older_value = _finite_nonnegative(older)
    if newer_value is None or older_value is None or newer_value < older_value:
        return None
    return newer_value - older_value


def _pair_live_truth_belief(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    truth = [
        sample for sample in samples
        if sample["type"] == "SIMSTATE"
        and isinstance(sample.get("lat_deg_e7"), (int, float))
        and isinstance(sample.get("lon_deg_e7"), (int, float))
    ]
    belief = [
        sample for sample in samples
        if sample["type"] == "GLOBAL_POSITION_INT"
        and isinstance(sample.get("lat_deg_e7"), (int, float))
        and isinstance(sample.get("lon_deg_e7"), (int, float))
    ]
    paired: list[dict[str, Any]] = []
    for belief_sample in belief:
        nearest = min(
            truth,
            key=lambda item: abs(item["arrival_monotonic_s"] - belief_sample["arrival_monotonic_s"]),
            default=None,
        )
        if nearest is None:
            continue
        skew_s = abs(
            nearest["arrival_monotonic_s"] - belief_sample["arrival_monotonic_s"]
        )
        if skew_s > 0.1:
            continue
        gap = _horizontal_gap_m(
            nearest["lat_deg_e7"],
            nearest["lon_deg_e7"],
            belief_sample["lat_deg_e7"],
            belief_sample["lon_deg_e7"],
        )
        paired.append(
            {
                "arrival_monotonic_s": belief_sample["arrival_monotonic_s"],
                "skew_s": skew_s,
                "truth_lat_deg_e7": nearest["lat_deg_e7"],
                "truth_lon_deg_e7": nearest["lon_deg_e7"],
                "belief_lat_deg_e7": belief_sample["lat_deg_e7"],
                "belief_lon_deg_e7": belief_sample["lon_deg_e7"],
                "horizontal_gap_m": gap,
            }
        )
    return paired


def _ekf_metrics_from_bin(
    mechanism: dict[str, Any],
    *,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    samples = [
        sample for sample in mechanism.get("samples", [])
        if isinstance(sample, dict)
    ]
    ratios = [
        sample.get("pos_test_ratio")
        for sample in samples
        if isinstance(sample.get("pos_test_ratio"), (int, float))
    ]
    return {
        "pos_test_ratio": ratios,
        "reject_flags": [
            bool(sample.get("gps_position_rejected")) for sample in samples
        ],
        "reset_events": list(mechanism.get("reset_events") or []),
        "variance": list(fallback.get("variance") or []),
        "samples": samples,
        "source": mechanism.get("source", "XKF4"),
    }


def _truth_belief_from_bin(
    truth_belief: dict[str, Any],
    *,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    samples = [
        sample for sample in truth_belief.get("samples", [])
        if isinstance(sample, dict)
    ]
    gaps: list[float] = []
    for sample in samples:
        gap = sample.get("horizontal_gap_m")
        if isinstance(gap, (int, float)):
            gaps.append(float(gap))
    growth = 0.0
    if len(samples) >= 2 and len(gaps) >= 2:
        first_time = samples[0].get("time_us")
        last_time = samples[-1].get("time_us")
        if isinstance(first_time, (int, float)) and isinstance(last_time, (int, float)):
            dt = (last_time - first_time) / 1_000_000.0
            if dt > 0:
                growth = (gaps[-1] - gaps[0]) / dt
    return {
        "horizontal_gap_m": gaps,
        "gap_growth_rate_mps": growth,
        "truth_source": "SIM",
        "belief_source": "POS",
        "samples": samples,
        "live_fallback_source": {
            "truth_source": fallback.get("truth_source"),
            "belief_source": fallback.get("belief_source"),
        },
        "source": truth_belief.get("source", "SIM/POS"),
    }


def _horizontal_gap_m(
    truth_lat_e7: Any,
    truth_lon_e7: Any,
    belief_lat_e7: Any,
    belief_lon_e7: Any,
) -> float:
    truth_lat = float(truth_lat_e7) / 1e7
    truth_lon = float(truth_lon_e7) / 1e7
    belief_lat = float(belief_lat_e7) / 1e7
    belief_lon = float(belief_lon_e7) / 1e7
    ref_lat = math.radians((truth_lat + belief_lat) / 2.0)
    dn = (belief_lat - truth_lat) * 111_320.0
    de = (belief_lon - truth_lon) * 111_320.0 * math.cos(ref_lat)
    return math.hypot(dn, de)
