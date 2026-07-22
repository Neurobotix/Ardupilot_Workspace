"""Monitor metadata for gps_failure."""
from __future__ import annotations

from dataclasses import dataclass, replace
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
                reason="no_sitl_monitor_not_run",
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
        self.trigger_event: dict[str, Any] | None = None
        self.normalized_messages: list[dict[str, Any]] = []
        self.injection_attempted = False
        self.triggered = False
        self.injection_monotonic_s: float | None = None
        self.injection_vehicle_time_boot_ms: float | None = None
        self.injection_result: dict[str, Any] | None = None
        self.restore_results: list[dict[str, Any]] = []
        self.ramp_update_results: list[dict[str, Any]] = []
        self.next_ramp_update_s = defaults.SLOW_DRIFT_UPDATE_PERIOD_S
        self.latest_vehicle_time_boot_ms: float | None = None
        self.latest_vehicle_time_arrival_s: float | None = None
        self.latest_vehicle_time_source: str | None = None
        self.stop_reason = "trigger_not_observed"
        self.operation_failure_reason: str | None = None
        self.observation_end_monotonic_s = self.started_monotonic
        self.current_mode: str | None = None
        self.current_armed = False
        self.max_seq_reached: int | None = None
        self.reached: list[int] = []
        self.auto_to_rtl_transition_seq: int | None = None
        self.rtl_transition_monotonic_s: float | None = None
        self.terminal_state_reached = False
        self.loss_of_control = False
        self.timeout = False
        self.pre_injection_estimator_flags: int | None = None
        self._operator_status_period_s = 15.0
        self._last_operator_status_s = self.started_monotonic
        self._logged_clean_trigger_sequences: set[int] = set()
        self._logged_stale_trigger_sequences: set[int] = set()
        self._logged_mission_current_sequences: set[int] = set()
        self._logged_reached_sequences: set[int] = set()

    def run(self) -> MonitorResult:
        self.ctx.extra["gps_telemetry_stream_request"] = (
            telemetry.request_live_streams(self.master)
        )
        self._read_source_contract_parameters()
        defaults.log(
            f"[gps_monitor] {self.case.case_id}: monitoring live mission; "
            f"trigger=clean armed/AUTO seq {defaults.INJECTION_TRIGGER['seq']} "
            f"after seqs {defaults.INJECTION_TRIGGER['front_half_required_sequences']}; "
            f"timeout={self.config.mission_timeout_s:.0f}s"
        )

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
            self._record_vehicle_clock_sample(normalized)
            self._record_pre_injection_source_sample(normalized)
            self._record_flight_progress(normalized, arrival)
            self._maybe_record_trigger_event(normalized)
            self._log_periodic_operator_status(arrival)
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
                if self._should_stop(arrival):
                    break
        else:
            self.stop_reason = "monitor_timeout"
            self.timeout = True
            defaults.log(
                f"[gps_monitor] {self.case.case_id}: monitor timeout; "
                f"triggered={self.triggered} max_seq={self.max_seq_reached} "
                f"reached={self.reached} mode={self.current_mode}"
            )

        self._write_artifacts()
        return self._monitor_result()

    def _execute_initial_injection(self, now_s: float) -> None:
        from .runtime import build_authorized_injection_plan, execute_injection_plan

        if self.injection_attempted:
            raise RuntimeError("GPS injection is one-shot and was already attempted")
        self.injection_attempted = True
        plan = build_authorized_injection_plan(self.case, self.trigger_trace)
        self.trigger_event = dict(plan.trigger_event)
        self.ctx.extra["gps_trigger_event"] = dict(self.trigger_event)
        if self._physical_schedule_requires_vehicle_time(plan):
            trigger_boot_ms = _finite_nonnegative(
                plan.trigger_event.get("trigger_vehicle_time_boot_ms")
            )
            if trigger_boot_ms is None:
                reason = "vehicle_time_unavailable_for_physical_scheduling"
                failed_plan = replace(
                    plan,
                    ready_to_inject=False,
                    failures=[
                        *plan.failures,
                        {
                            "reason": reason,
                            "detail": (
                                "trigger event lacks fresh finite "
                                "trigger_vehicle_time_boot_ms"
                            ),
                        },
                    ],
                )
                from .runtime import InjectionExecutionResult

                result = InjectionExecutionResult(
                    success=False,
                    reason=reason,
                    plan=failed_plan,
                )
                self.injection_result = result.as_dict()
                self.ctx.extra["gps_injection_execution"] = self.injection_result
                self.triggered = False
                self.stop_reason = reason
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: refusing physical "
                    "GPS fault write because fresh vehicle boot time is missing."
                )
                return

        result = execute_injection_plan(plan, self.master)
        self.injection_result = result.as_dict()
        self.ctx.extra["gps_injection_execution"] = self.injection_result
        self.triggered = result.success or (
            plan.execution_authorized and not plan.injection_payload
        )
        if self.triggered:
            self.injection_monotonic_s = now_s
            self.injection_vehicle_time_boot_ms = _finite_nonnegative(
                self.trigger_event.get("trigger_vehicle_time_boot_ms")
            )
            self.stop_reason = "observing_post_injection"
            defaults.log(
                f"GPS injection trigger latched at seq 4 for {self.case.case_id}; "
                "continuing through the mission terminal state."
            )
        else:
            self.stop_reason = result.reason
            defaults.log(
                f"[gps_monitor] {self.case.case_id}: trigger authorization/injection "
                f"failed: {result.reason}; stopping attempt."
            )

    def _maybe_execute_scheduled_steps(self, now_s: float) -> None:
        if self.injection_monotonic_s is None:
            return
        clock = self._post_injection_clock(now_s)
        if clock is None:
            if self._has_pending_physical_scheduled_operations():
                self.operation_failure_reason = (
                    "vehicle_time_unavailable_for_physical_scheduling"
                )
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: stopping physical "
                    "GPS scheduling because no fresh vehicle boot time is available."
                )
            return
        self._maybe_execute_restore(
            clock["vehicle_elapsed_s"],
            wall_elapsed_s=clock["wall_elapsed_s"],
            clock_ratio=clock["clock_ratio"],
            clock_source=clock["clock_source"],
        )
        self._maybe_execute_slow_drift_update(
            clock["vehicle_elapsed_s"],
            wall_elapsed_s=clock["wall_elapsed_s"],
            clock_ratio=clock["clock_ratio"],
            clock_source=clock["clock_source"],
        )

    def _maybe_execute_restore(
        self,
        vehicle_elapsed_s: float,
        *,
        wall_elapsed_s: float | None = None,
        clock_ratio: float | None = None,
        clock_source: str = "vehicle_time_boot_ms",
    ) -> None:
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
            if vehicle_elapsed_s < due_s:
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
            defaults.log(
                f"[gps_monitor] {self.case.case_id}: executing restore step "
                f"{index} at vehicle +{vehicle_elapsed_s:.1f}s: {payload}"
            )
            result = execute_restore_step(step, self.master)
            result_dict = result.as_dict() if result is not None else None
            self.restore_results.append({
                "restore_index": index,
                "elapsed_since_trigger_s": vehicle_elapsed_s,
                "vehicle_elapsed_s": vehicle_elapsed_s,
                "wall_elapsed_s": wall_elapsed_s,
                "clock_ratio": clock_ratio,
                "clock_source": clock_source,
                "result": result_dict,
            })
            if not isinstance(result_dict, dict) or result_dict.get("success") is not True:
                self.operation_failure_reason = f"restore_failed:{index}"
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: restore step {index} "
                    f"failed readback; stopping attempt."
                )
                return
            defaults.log(
                f"[gps_monitor] {self.case.case_id}: restore step {index} "
                "readback verified."
            )

    def _maybe_execute_slow_drift_update(
        self,
        vehicle_elapsed_s: float,
        *,
        wall_elapsed_s: float | None = None,
        clock_ratio: float | None = None,
        clock_source: str = "vehicle_time_boot_ms",
    ) -> None:
        if self.case.parameters.get("fault_type") != "slow_drift":
            return
        if vehicle_elapsed_s < self.next_ramp_update_s:
            return
        from .runtime import build_authorized_injection_plan, execute_injection_plan

        trace = [dict(event) for event in self.trigger_trace]
        for event in trace:
            if event.get("seq") == defaults.INJECTION_TRIGGER["seq"]:
                event["elapsed_since_trigger_s"] = vehicle_elapsed_s
                event["vehicle_elapsed_s"] = vehicle_elapsed_s
                event["wall_elapsed_s"] = wall_elapsed_s
                event["clock_ratio"] = clock_ratio
                event["payload_clock_source"] = clock_source
                break
        plan = build_authorized_injection_plan(self.case, trace)
        defaults.log(
            f"[gps_monitor] {self.case.case_id}: slow-drift update due at "
            f"vehicle +{vehicle_elapsed_s:.1f}s; payload={plan.injection_payload}"
        )
        result = execute_injection_plan(plan, self.master)
        self.ramp_update_results.append(
            {
                "elapsed_since_trigger_s": vehicle_elapsed_s,
                "vehicle_elapsed_s": vehicle_elapsed_s,
                "wall_elapsed_s": wall_elapsed_s,
                "clock_ratio": clock_ratio,
                "clock_source": clock_source,
                "resolved_payload": dict(plan.injection_payload),
                "result": result.as_dict(),
            }
        )
        if result.success is not True:
            self.operation_failure_reason = "slow_drift_update_failed"
            defaults.log(
                f"[gps_monitor] {self.case.case_id}: slow-drift update "
                f"failed readback ({result.reason}); stopping attempt."
            )
            return
        defaults.log(
            f"[gps_monitor] {self.case.case_id}: slow-drift update readback "
            "verified."
        )
        self.next_ramp_update_s += defaults.SLOW_DRIFT_UPDATE_PERIOD_S

    def _post_injection_s(self, now_s: float) -> float:
        if self.injection_monotonic_s is None:
            return 0.0
        return max(0.0, now_s - self.injection_monotonic_s)

    def _post_injection_clock(self, now_s: float) -> dict[str, Any] | None:
        wall_elapsed_s = self._post_injection_s(now_s)
        trigger_boot_ms = _finite_nonnegative(self.injection_vehicle_time_boot_ms)
        latest_boot_ms = _finite_nonnegative(self.latest_vehicle_time_boot_ms)
        latest_arrival_s = _finite_nonnegative(self.latest_vehicle_time_arrival_s)
        if (
            trigger_boot_ms is None
            or latest_boot_ms is None
            or latest_arrival_s is None
        ):
            return None
        sample_age_s = _sample_age(now_s, latest_arrival_s)
        if (
            sample_age_s is None
            or sample_age_s > defaults.TRIGGER_BOOT_TIME_MAX_AGE_S
            or latest_boot_ms < trigger_boot_ms
        ):
            return None
        vehicle_elapsed_s = (latest_boot_ms - trigger_boot_ms) / 1000.0
        clock_ratio = (
            wall_elapsed_s / vehicle_elapsed_s
            if wall_elapsed_s > 0.0 and vehicle_elapsed_s > 0.0
            else None
        )
        return {
            "wall_elapsed_s": wall_elapsed_s,
            "vehicle_elapsed_s": vehicle_elapsed_s,
            "clock_ratio": clock_ratio,
            "clock_source": "vehicle_time_boot_ms",
            "latest_vehicle_time_boot_ms": latest_boot_ms,
            "latest_vehicle_time_arrival_s": latest_arrival_s,
            "latest_vehicle_time_source": self.latest_vehicle_time_source,
            "trigger_vehicle_time_boot_ms": trigger_boot_ms,
        }

    def _record_vehicle_clock_sample(self, sample: dict[str, Any]) -> None:
        boot_ms = _finite_nonnegative(sample.get("time_boot_ms"))
        arrival_s = _finite_nonnegative(sample.get("arrival_monotonic_s"))
        if boot_ms is None or arrival_s is None:
            return
        self.latest_vehicle_time_boot_ms = boot_ms
        self.latest_vehicle_time_arrival_s = arrival_s
        self.latest_vehicle_time_source = str(sample.get("type"))

    def _physical_schedule_requires_vehicle_time(self, plan: Any) -> bool:
        if self.case.parameters.get("fault_type") == "slow_drift":
            return True
        restore_plan = getattr(plan, "restore_plan", [])
        return bool(restore_plan)

    def _has_pending_physical_scheduled_operations(self) -> bool:
        if self.case.parameters.get("fault_type") == "slow_drift":
            return True
        plan = self.injection_result.get("plan") if isinstance(self.injection_result, dict) else None
        restore_plan = plan.get("restore_plan") if isinstance(plan, dict) else []
        return isinstance(restore_plan, list) and any(
            not any(item.get("restore_index") == index for item in self.restore_results)
            for index, _step in enumerate(restore_plan)
        )

    def _required_post_injection_s(self) -> float:
        requirements = self.case.parameters.get("acceptance_requirements")
        if isinstance(requirements, dict):
            value = requirements.get("min_post_injection_s")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                parsed = float(value)
                if math.isfinite(parsed) and parsed > 0.0:
                    return parsed
        raise RuntimeError("case is missing a valid min_post_injection_s contract")

    def _record_flight_progress(
        self,
        sample: dict[str, Any],
        arrival_s: float,
    ) -> None:
        message_type = sample.get("type")
        if message_type == "HEARTBEAT":
            previous_mode = self.current_mode
            mode = sample.get("mode")
            self.current_mode = mode if isinstance(mode, str) else None
            self.current_armed = sample.get("armed") is True
            if (
                self.current_mode is not None
                and self.current_mode != previous_mode
            ):
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: mode={self.current_mode} "
                    f"armed={self.current_armed} max_seq={self.max_seq_reached}"
                )
            if (
                previous_mode == "AUTO"
                and self.current_mode == "RTL"
                and self.rtl_transition_monotonic_s is None
            ):
                self.auto_to_rtl_transition_seq = self.max_seq_reached
                self.rtl_transition_monotonic_s = arrival_s
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: RTL observed at "
                    f"seq={self.auto_to_rtl_transition_seq}; waiting "
                    f"{defaults.RTL_STABILIZE_S:.0f}s for terminal confirmation."
                )
            if self.triggered and sample.get("armed") is False:
                self.loss_of_control = True
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: unexpected disarm "
                    "after trigger; marking loss_of_control."
                )
            return
        if message_type in {"MISSION_CURRENT", "MISSION_ITEM_REACHED"}:
            seq = _coerce_seq(sample.get("seq"))
            if seq is None:
                return
            if (
                message_type == "MISSION_CURRENT"
                and seq not in self._logged_mission_current_sequences
            ):
                self._logged_mission_current_sequences.add(seq)
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: mission current seq={seq} "
                    f"(trigger seq={defaults.INJECTION_TRIGGER['seq']})"
                )
            self.max_seq_reached = (
                seq if self.max_seq_reached is None else max(self.max_seq_reached, seq)
            )
            if message_type == "MISSION_ITEM_REACHED" and seq not in self.reached:
                self.reached.append(seq)
                if seq not in self._logged_reached_sequences:
                    self._logged_reached_sequences.add(seq)
                    defaults.log(
                        f"[gps_monitor] {self.case.case_id}: waypoint reached "
                        f"seq={seq}; reached={self.reached}"
                    )
            return
        if message_type == "STATUSTEXT":
            text = str(sample.get("text") or "").lower()
            if any(token in text for token in ("crash", "terrain", "loss of control")):
                self.loss_of_control = True
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: STATUSTEXT indicates "
                    f"loss-of-control condition: {sample.get('text')}"
                )
            return
        if message_type == "GLOBAL_POSITION_INT" and self.triggered:
            relative_alt_mm = sample.get("relative_alt_mm")
            if isinstance(relative_alt_mm, (int, float)) and not isinstance(
                relative_alt_mm, bool
            ):
                relative_alt_m = float(relative_alt_mm) / 1000.0
                if relative_alt_m < defaults.LOW_ALTITUDE_ABORT_M:
                    self.loss_of_control = True
                    defaults.log(
                        f"[gps_monitor] {self.case.case_id}: low altitude after "
                        f"trigger ({relative_alt_m:.1f}m < "
                        f"{defaults.LOW_ALTITUDE_ABORT_M:.1f}m); stopping."
                    )

    def _should_stop(self, now_s: float) -> bool:
        if self.loss_of_control:
            self.terminal_state_reached = True
            self.stop_reason = "loss_of_control"
            defaults.log(
                f"[gps_monitor] {self.case.case_id}: terminal stop: "
                "loss_of_control."
            )
            return True
        if self.rtl_transition_monotonic_s is None:
            return False
        if now_s - self.rtl_transition_monotonic_s < defaults.RTL_STABILIZE_S:
            return False
        self.terminal_state_reached = True
        if self._planned_rtl_reached():
            self.stop_reason = "planned_rtl_stabilized"
        else:
            self.stop_reason = "early_rtl_stabilized"
        defaults.log(
            f"[gps_monitor] {self.case.case_id}: terminal stop: "
            f"{self.stop_reason} (rtl_seq={self.auto_to_rtl_transition_seq}, "
            f"max_seq={self.max_seq_reached}, reached={self.reached})."
        )
        return True

    def _planned_rtl_reached(self) -> bool:
        return bool(
            self.auto_to_rtl_transition_seq is not None
            and self.auto_to_rtl_transition_seq >= defaults.PLANNED_RTL_MIN_SEQ
        )

    def _mission_complete(self) -> bool:
        return bool(self.terminal_state_reached and self._planned_rtl_reached())

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
        from .analyzers import _summary_with_terminal_context

        summary = _summary_with_terminal_context(
            classify_observation(observation), observation, case=self.case
        )
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
            "behavior_status": (
                "accepted"
                if summary.get("accepted_observation") is True
                else "incomplete"
            ),
            "accepted_observation": False,
            "accepted_repetition": False,
            "scientific_behavior_label": summary.get("scientific_behavior_label"),
            "scientific_behavior_components": summary.get(
                "scientific_behavior_components"
            ),
            "stimulus_fidelity_status": observation.get("stimulus_fidelity_status"),
            "stimulus_fidelity_reason": observation.get("stimulus_fidelity_reason"),
            "lifecycle_windows_status": observation.get("lifecycle_windows_status"),
            "lifecycle_windows_reason": observation.get("lifecycle_windows_reason"),
            "terminal_state_reached": observation.get("terminal_state_reached"),
            "mission_complete": observation.get("mission_complete"),
            "stop_reason": observation.get("stop_reason"),
            "max_seq_reached": observation.get("max_seq_reached"),
            "auto_to_rtl_transition_seq": observation.get(
                "auto_to_rtl_transition_seq"
            ),
            "artifacts": {name: str(path) for name, path in self.ctx.artifacts.items()},
            "parameters": dict(self.case.parameters),
            "notes": [summary["reason"], self.stop_reason],
            "workflow_status": (
                "pre_cleanup_complete"
                if self._pre_cleanup_workflow_complete(observation)
                else "pre_cleanup_incomplete"
            ),
        }

    def _monitor_result(self) -> MonitorResult:
        summary = self.ctx.extra.get("plugin_manifest_fields") or {}
        return MonitorResult(
            completed=summary.get("workflow_status") == "pre_cleanup_complete",
            reason=str(self.stop_reason or summary.get("behavior_class")),
            duration_s=time.monotonic() - self.started_monotonic,
            waypoints_seen=list(self.reached),
            monitor_log_path=self.ctx.attempt_dir / "mode_timeline.json",
        )

    def _pre_cleanup_workflow_complete(self, observation: dict[str, Any]) -> bool:
        return bool(
            observation.get("injection_triggered") is True
            and observation.get("injection_readback_ok") is True
            and observation.get("terminal_state_reached") is True
            and observation.get("telemetry_delivery_ok") is True
        )

    def _artifact_payloads(self) -> dict[str, dict[str, Any]]:
        from .bin_analysis import (
            lifecycle_windows_pending_artifact,
            stimulus_fidelity_pending_artifact,
        )

        artifacts = {
            "ekf_innovation_metrics.json": self._ekf_metrics_artifact(),
            "truth_vs_belief.json": self._truth_vs_belief_artifact(),
            "mode_timeline.json": self._mode_timeline_artifact(),
            "attitude_altitude_envelope.json": self._attitude_altitude_artifact(),
            "source_contract.json": self._source_contract_artifact(),
            "stimulus_fidelity.json": stimulus_fidelity_pending_artifact(
                case_id=self.case.case_id,
                fault_type=str(self.case.parameters.get("fault_type", "")),
                fault_recipe=(
                    self.case.parameters.get("fault_recipe")
                    if isinstance(self.case.parameters.get("fault_recipe"), dict)
                    else None
                ),
            ),
            "gps_lifecycle_windows.json": lifecycle_windows_pending_artifact(
                case_id=self.case.case_id,
                fault_type=str(self.case.parameters.get("fault_type", "")),
            ),
        }
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
            "telemetry_stream_request": self.ctx.extra.get(
                "gps_telemetry_stream_request"
            ),
            "telemetry_delivery": self._telemetry_delivery_status(),
            "stop_reason": self.stop_reason,
            "required_post_injection_s": self._required_post_injection_s(),
            "terminal_state_reached": self.terminal_state_reached,
            "mission_complete": self._mission_complete(),
            "max_seq_reached": self.max_seq_reached,
            "reached_sequences": list(self.reached),
            "auto_to_rtl_transition_seq": self.auto_to_rtl_transition_seq,
            "planned_rtl_min_seq": defaults.PLANNED_RTL_MIN_SEQ,
            "rtl_stabilize_s": defaults.RTL_STABILIZE_S,
        }

    def _telemetry_delivery_status(self) -> dict[str, Any]:
        observed = sorted(
            {
                str(sample["type"])
                for sample in self.normalized_messages
                if isinstance(sample.get("type"), str)
            }
        )
        required = list(telemetry.DELIVERY_REQUIRED_MESSAGE_TYPES)
        missing = [
            message_type for message_type in required if message_type not in observed
        ]
        return {
            "ok": not missing,
            "required_message_types": required,
            "observed_message_types": observed,
            "missing_message_types": missing,
            "event_driven_optional_message_types": list(
                telemetry.EVENT_DRIVEN_OPTIONAL_MESSAGE_TYPES
            ),
        }

    def _attitude_altitude_artifact(self) -> dict[str, Any]:
        post_messages = self._post_injection_messages()
        altitude_samples = [
            {
                "arrival_monotonic_s": sample["arrival_monotonic_s"],
                "relative_alt_m": float(sample["relative_alt_mm"]) / 1000.0,
                "source": "GLOBAL_POSITION_INT.relative_alt_mm",
            }
            for sample in post_messages
            if sample["type"] == "GLOBAL_POSITION_INT"
            and isinstance(sample.get("relative_alt_mm"), (int, float))
        ]
        attitudes = []
        for sample in post_messages:
            if (
                sample["type"] != "ATTITUDE"
                or not isinstance(sample.get("roll_rad"), (int, float))
                or not isinstance(sample.get("pitch_rad"), (int, float))
            ):
                continue
            roll_deg = math.degrees(float(sample["roll_rad"]))
            pitch_deg = math.degrees(float(sample["pitch_rad"]))
            attitudes.append({
                **sample,
                "roll_deg": roll_deg,
                "pitch_deg": pitch_deg,
                "source": "ATTITUDE.roll_rad/pitch_rad",
            })
        altitudes = [sample["relative_alt_m"] for sample in altitude_samples]
        min_alt = min(altitudes) if altitudes else None
        max_drawdown = 0.0
        running_max: float | None = None
        for altitude in altitudes:
            running_max = altitude if running_max is None else max(running_max, altitude)
            max_drawdown = max(max_drawdown, running_max - altitude)
        threshold_crossings: list[dict[str, Any]] = []
        for sample in attitudes:
            roll_deg = float(sample["roll_deg"])
            pitch_deg = float(sample["pitch_deg"])
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
        missing = []
        if not altitude_samples:
            missing.append("live_telemetry.GLOBAL_POSITION_INT.relative_alt_mm")
        if not attitudes:
            missing.append("live_telemetry.ATTITUDE.roll_rad/pitch_rad")
        return {
            "status": "pass" if not missing else "fail",
            "reason": "ok" if not missing else "missing_live_envelope_samples",
            "source": "live_telemetry",
            "altitude_source": "live_telemetry:GLOBAL_POSITION_INT.relative_alt_mm",
            "attitude_source": "live_telemetry:ATTITUDE.roll_rad/pitch_rad",
            "sampling_limits": {
                "post_injection_only": True,
                "clock": "arrival_monotonic_s",
                "start_arrival_monotonic_s": self.injection_monotonic_s,
                "max_abs_roll_deg": defaults.MAX_ABS_ROLL_DEG,
                "max_abs_pitch_deg": defaults.MAX_ABS_PITCH_DEG,
                "max_altitude_loss_m": defaults.MAX_ALTITUDE_LOSS_M,
                "bin_live_altitude_tolerance_m": defaults.BIN_LIVE_ALTITUDE_TOLERANCE_M,
                "bin_live_attitude_tolerance_deg": defaults.BIN_LIVE_ATTITUDE_TOLERANCE_DEG,
            },
            "evidence_quality": "runtime_guard",
            "final_evidence_quality": False,
            "runtime_guard_quality": bool(not missing),
            "post_injection_min_alt_m": min_alt,
            "altitude_loss_m": max_drawdown,
            "altitude_samples": altitude_samples,
            "attitude_excursions": attitudes,
            "threshold_crossings": threshold_crossings,
            "unexpected_disarm": unexpected_disarm,
            "samples_complete": bool(attitudes and altitude_samples),
            "missing_evidence": missing,
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

    def _record_pre_injection_source_sample(self, sample: dict[str, Any]) -> None:
        if self.triggered or sample.get("type") != "EKF_STATUS_REPORT":
            return
        flags = sample.get("flags")
        if isinstance(flags, bool):
            return
        if isinstance(flags, int):
            self.pre_injection_estimator_flags = flags
            return
        if isinstance(flags, float) and flags.is_integer():
            self.pre_injection_estimator_flags = int(flags)

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
            estimator_flags=self.pre_injection_estimator_flags,
        )
        payload = contract.as_dict()
        payload["proof_stage"] = "pre_injection"
        payload["pre_injection_estimator_flags"] = self.pre_injection_estimator_flags
        payload["post_injection_estimator_flags"] = self._latest_estimator_flags()
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

    def _observation(self, artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
        wall_post_s = (
            self._post_injection_s(self.observation_end_monotonic_s)
            if self.triggered
            else 0.0
        )
        clock = (
            self._post_injection_clock(self.observation_end_monotonic_s)
            if self.triggered
            else None
        )
        vehicle_post_s = (
            float(clock["vehicle_elapsed_s"])
            if isinstance(clock, dict)
            else None
        )
        observation_post_s = (
            vehicle_post_s
            if vehicle_post_s is not None
            else wall_post_s
        )
        operation_status = self._scheduled_operation_status(vehicle_post_s or 0.0)
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
        telemetry_delivery = artifacts["mode_timeline.json"]["telemetry_delivery"]
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
            and not (
                sample.get("mode") == "RTL" and self._planned_rtl_reached()
            )
            for sample in heartbeat_samples
        )
        reset_events = artifacts["ekf_innovation_metrics.json"].get("reset_events")
        behavior_measurements_complete = bool(
            telemetry_delivery.get("ok") is True
            and len(gaps) >= 2
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
            "case_id": self.case.case_id,
            "fault_type": self.case.parameters.get("fault_type"),
            "injection_triggered": self.triggered,
            "injection_readback_ok": injection_ok,
            "post_injection_s": observation_post_s,
            "post_injection_vehicle_elapsed_s": vehicle_post_s,
            "post_injection_wall_elapsed_s": wall_post_s,
            "post_injection_elapsed_clock_source": (
                "vehicle_time_boot_ms"
                if vehicle_post_s is not None
                else "wall_monotonic_diagnostic"
            ),
            "required_post_injection_s": self._required_post_injection_s(),
            "required_artifacts_present": required_present,
            "mechanism_evidence": bool(ratios) and source_contract_ok,
            "source_contract_ok": source_contract_ok,
            "source_contract": source_contract,
            "scheduled_operations": operation_status,
            "behavior_measurements_complete": behavior_measurements_complete,
            "telemetry_delivery_ok": telemetry_delivery.get("ok") is True,
            "telemetry_delivery": telemetry_delivery,
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
                self.loss_of_control
                or attitude_artifact["unexpected_disarm"]
                or attitude_artifact["threshold_crossings"]
            ),
            "terminal_state_reached": self.terminal_state_reached,
            "mission_complete": self._mission_complete(),
            "max_seq_reached": self.max_seq_reached,
            "reached_sequences": list(self.reached),
            "auto_to_rtl_transition_seq": self.auto_to_rtl_transition_seq,
            "planned_rtl_min_seq": defaults.PLANNED_RTL_MIN_SEQ,
            "stop_reason": self.stop_reason,
            "timeout": self.timeout,
            "stimulus_fidelity_status": artifacts["stimulus_fidelity.json"].get("status"),
            "stimulus_fidelity_reason": artifacts["stimulus_fidelity.json"].get("reason"),
            "lifecycle_windows_status": artifacts["gps_lifecycle_windows.json"].get("status"),
            "lifecycle_windows_reason": artifacts["gps_lifecycle_windows.json"].get("reason"),
        }
        self.ctx.stimulus_result["verify"] = {
            "phase": "phase2_live_terminal_verification",
            "live_readback_performed": bool(self.injection_result),
            "terminal_verification_pending": False,
            "injection_readback_ok": injection_ok,
            "scheduled_operations": operation_status,
        }
        return observation

    def _scheduled_operation_status(self, vehicle_post_s: float) -> dict[str, Any]:
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
                min(vehicle_post_s, defaults.MIN_POST_INJECTION_S)
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
        wall_post_s = (
            self._post_injection_s(self.observation_end_monotonic_s)
            if self.triggered
            else 0.0
        )
        clock = (
            self._post_injection_clock(self.observation_end_monotonic_s)
            if self.triggered
            else None
        )
        vehicle_post_s = (
            float(clock["vehicle_elapsed_s"])
            if isinstance(clock, dict)
            else None
        )
        operation_status = self._scheduled_operation_status(vehicle_post_s or 0.0)
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
        payload["scheduling"] = {
            "physical_payload_clock_source": "vehicle_time_boot_ms",
            "restore_clock_source": "vehicle_time_boot_ms",
            "trigger_wall_monotonic_s": (
                self.trigger_event.get("trigger_wall_monotonic_s")
                if isinstance(self.trigger_event, dict)
                else None
            ),
            "trigger_vehicle_time_boot_ms": (
                self.trigger_event.get("trigger_vehicle_time_boot_ms")
                if isinstance(self.trigger_event, dict)
                else None
            ),
            "wall_elapsed_s": wall_post_s,
            "vehicle_elapsed_s": vehicle_post_s,
            "clock_ratio": (
                clock.get("clock_ratio") if isinstance(clock, dict) else None
            ),
            "latest_vehicle_time": clock if isinstance(clock, dict) else None,
            "missing_vehicle_time_fails_closed": True,
        }
        defaults.write_json(path, payload)
        self.ctx.artifacts["gps_injection.json"] = path
        self.ctx.stimulus_result.clear()
        self.ctx.stimulus_result.update(payload)

    def _maybe_record_trigger_event(self, sample: dict[str, Any]) -> None:
        if sample["type"] == "HEARTBEAT":
            self.ctx.extra["gps_last_heartbeat"] = dict(sample)
            return
        if sample["type"] != "MISSION_CURRENT":
            return
        seq = sample.get("seq")
        if seq is None:
            return
        if (
            not self.trigger_trace
            and seq in defaults.INJECTION_TRIGGER["pre_trigger_ignored_sequences"]
        ):
            # MISSION_CURRENT reports the home row before navigation begins.
            # It is not trigger evidence. Once seq 1 is recorded, a later seq 0
            # is retained so the validator rejects that regression.
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
        boot_time_fields = self._trigger_boot_time_fields(float(mission_arrival))
        event = {
            "seq": seq,
            "armed": isinstance(heartbeat, dict) and heartbeat.get("armed") is True,
            "mode": heartbeat.get("mode") if isinstance(heartbeat, dict) else None,
            "mission_arrival_monotonic_s": float(mission_arrival),
            "trigger_wall_monotonic_s": float(mission_arrival),
            "trigger_wall_time_utc": defaults.utc_now(),
            "heartbeat_age_s": heartbeat_age,
            "heartbeat_fresh": bool(
                heartbeat_age is not None
                and heartbeat_age <= defaults.TRIGGER_HEARTBEAT_MAX_AGE_S
            ),
            "trigger_time_s": sample["arrival_monotonic_s"] - self.started_monotonic,
            "elapsed_since_trigger_s": 0.0,
            "vehicle_elapsed_s": 0.0,
            "wall_elapsed_s": 0.0,
            "payload_clock_source": "vehicle_time_boot_ms",
            **latitude_fields,
            **boot_time_fields,
        }
        self.trigger_trace.append(event)
        self._log_trigger_evidence_event(event)

    def _log_trigger_evidence_event(self, event: dict[str, Any]) -> None:
        seq = _coerce_seq(event.get("seq"))
        if seq is None:
            return
        required = set(defaults.INJECTION_TRIGGER["front_half_required_sequences"])
        trigger_seq = int(defaults.INJECTION_TRIGGER["seq"])
        optional = set(defaults.INJECTION_TRIGGER["front_half_optional_sequences"])
        if seq not in required and seq != trigger_seq and seq not in optional:
            return
        fresh = bool(
            event.get("heartbeat_fresh") is True
            and event.get("simstate_fresh") is True
            and event.get("armed") is True
            and event.get("mode") == defaults.INJECTION_TRIGGER["mode"]
        )
        if fresh:
            if seq in self._logged_clean_trigger_sequences:
                return
            self._logged_clean_trigger_sequences.add(seq)
            if seq == trigger_seq:
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: clean seq-{seq} "
                    "trigger edge observed; authorizing injection/no-op."
                )
            else:
                defaults.log(
                    f"[gps_monitor] {self.case.case_id}: clean trigger progress "
                    f"seq={seq}; waiting for seq {trigger_seq}."
                )
            return
        if seq in self._logged_stale_trigger_sequences:
            return
        self._logged_stale_trigger_sequences.add(seq)
        defaults.log(
            f"[gps_monitor] {self.case.case_id}: ignoring stale/incomplete "
            f"trigger evidence seq={seq} "
            f"(armed={event.get('armed')}, mode={event.get('mode')}, "
            f"heartbeat_fresh={event.get('heartbeat_fresh')}, "
            f"heartbeat_age={_format_optional_seconds(event.get('heartbeat_age_s'))}, "
            f"simstate_fresh={event.get('simstate_fresh')}, "
            f"simstate_age={_format_optional_seconds(event.get('simstate_age_s'))}); "
            "waiting for a fresh sample."
        )

    def _log_periodic_operator_status(self, now_s: float) -> None:
        if now_s - self._last_operator_status_s < self._operator_status_period_s:
            return
        self._last_operator_status_s = now_s
        remaining_s = max(0.0, self.deadline - now_s)
        if not self.triggered:
            defaults.log(
                f"[gps_monitor] {self.case.case_id}: still waiting for clean "
                f"seq-{defaults.INJECTION_TRIGGER['seq']} trigger; "
                f"max_seq={self.max_seq_reached}, reached={self.reached}, "
                f"mode={self.current_mode}, deadline_in={remaining_s:.0f}s"
            )
            return
        post_s = self._post_injection_s(now_s)
        rtl_wait = ""
        if self.rtl_transition_monotonic_s is not None:
            rtl_wait_s = max(
                0.0,
                defaults.RTL_STABILIZE_S
                - (now_s - self.rtl_transition_monotonic_s),
            )
            rtl_wait = f", rtl_stabilize_remaining={rtl_wait_s:.0f}s"
        defaults.log(
            f"[gps_monitor] {self.case.case_id}: observing post-trigger "
            f"+{post_s:.1f}s/{self._required_post_injection_s():.1f}s; "
            f"mode={self.current_mode}, max_seq={self.max_seq_reached}, "
            f"reached={self.reached}{rtl_wait}, deadline_in={remaining_s:.0f}s"
        )

    def _trigger_latitude_field(self, mission_arrival_s: float) -> dict[str, Any]:
        for sample in reversed(self.normalized_messages):
            if sample["type"] == "SIMSTATE" and sample.get("lat_deg_e7") is not None:
                age = _sample_age(mission_arrival_s, sample.get("arrival_monotonic_s"))
                fresh = bool(
                    age is not None and age <= defaults.TRIGGER_SIMSTATE_MAX_AGE_S
                )
                payload = {
                    "trigger_latitude_deg": float(sample["lat_deg_e7"]) / 1e7,
                    "simstate_age_s": age,
                    "simstate_fresh": fresh,
                }
                if sample.get("lon_deg_e7") is not None:
                    payload["trigger_longitude_deg"] = (
                        float(sample["lon_deg_e7"]) / 1e7
                    )
                return payload
        return {"simstate_age_s": None, "simstate_fresh": False}

    def _trigger_boot_time_fields(self, mission_arrival_s: float) -> dict[str, Any]:
        preferred_types = {"ATTITUDE", "GLOBAL_POSITION_INT"}
        candidates = [
            sample
            for sample in reversed(self.normalized_messages)
            if sample.get("type") in preferred_types
            and isinstance(sample.get("time_boot_ms"), (int, float))
        ]
        for sample in candidates:
            age = _sample_age(
                mission_arrival_s,
                sample.get("arrival_monotonic_s"),
            )
            if age is None or age > defaults.TRIGGER_BOOT_TIME_MAX_AGE_S:
                continue
            boot_ms = float(sample["time_boot_ms"])
            if not math.isfinite(boot_ms) or boot_ms < 0.0:
                continue
            return {
                "trigger_time_boot_ms": boot_ms,
                "trigger_vehicle_time_boot_ms": boot_ms,
                "trigger_time_us": boot_ms * 1000.0,
                "trigger_time_source": str(sample.get("type")),
                "trigger_vehicle_time_source": str(sample.get("type")),
                "trigger_boot_sample_age_s": age,
                "trigger_boot_time_fresh": True,
            }
        return {
            "trigger_boot_sample_age_s": None,
            "trigger_boot_time_fresh": False,
        }


def trigger_metadata() -> dict[str, object]:
    return dict(defaults.INJECTION_TRIGGER)


def first_seq4_edge_after_armed_auto_front_half(
    events: Iterable[Any],
) -> bool:
    """Validate ADR-0020 trigger preconditions from no-SITL event records.

    Fails closed for malformed events and for any mission-current evidence that
    is not a clean, monotonic navigation progression from seq 1 through seq 3
    to seq 4. Seq 2 is an optional ``DO_CHANGE_SPEED`` current report. A
    regression to a lower seq or a skipped required navigation seq is rejected.
    Repeated ``MISSION_CURRENT`` events for the *current* seq are benign
    telemetry and allowed, but every required navigation seq must be observed
    in order, armed and in AUTO, before the first seq-4 edge.
    """
    expected_order = list(
        defaults.INJECTION_TRIGGER["front_half_required_sequences"]
    )
    optional_sequences = set(
        defaults.INJECTION_TRIGGER["front_half_optional_sequences"]
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
        if last_seq is not None and seq < last_seq:
            # Any regression to a lower mission-current seq is invalid evidence.
            return False
        if seq == last_seq:
            # A repeat of the current seq is benign telemetry, not progression.
            # It does not need to carry fresh co-temporal HEARTBEAT/SIMSTATE.
            continue
        is_next_required = (
            next_required_index < len(expected_order)
            and seq == expected_order[next_required_index]
        )
        is_context_valid_optional = (
            seq in optional_sequences
            and next_required_index == 1
        )
        is_candidate_progress = (
            is_next_required
            or is_context_valid_optional
            or seq == trigger_seq
        )
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
            if is_candidate_progress:
                # During live runs ArduPlane can publish the next
                # MISSION_CURRENT value before fresh co-temporal HEARTBEAT and
                # SIMSTATE samples arrive. That sample is not valid progress
                # evidence, but it must not poison the whole trace; wait for a
                # clean sample at the same progression point. Out-of-contract
                # jumps still fail closed below.
                continue
            return False

        if seq == trigger_seq:
            # The seq-4 edge is valid only once the full ordered front half has
            # been observed and this event is itself armed and in AUTO.
            return next_required_index == len(expected_order) and armed and mode

        if is_next_required:
            if not (armed and mode):
                return False
            next_required_index += 1
            last_seq = seq
            continue

        if seq in optional_sequences:
            # The optional DO command is valid only after the first required
            # navigation item and must carry the same fresh armed/AUTO state.
            if next_required_index != 1 or not (armed and mode):
                return False
            last_seq = seq
            continue

        # Any other seq (a skip ahead, an out-of-contract value, or a jump past
        # the next required navigation seq) invalidates the trace.
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


def _format_optional_seconds(value: object) -> str:
    parsed = _finite_nonnegative(value)
    if parsed is None:
        return "n/a"
    return f"{parsed:.2f}s"


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
