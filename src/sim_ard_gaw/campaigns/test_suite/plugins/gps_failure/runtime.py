"""No-SITL-testable GPS injection planning and parameter execution contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ...core.models import TestCase
from . import defaults, glitch
from .mavlink import (
    MavlinkParameterConnection,
    ParameterBatchResult,
    ReadbackRule,
    finite_float,
    readback_rules_for_payload,
    set_and_read_back_parameters,
)
from .monitor import first_seq4_edge_after_armed_auto_front_half


# Module-private authorization sentinel. Only ``validate_trigger_trace`` stamps
# a TriggerEvidence with this exact object, and execution checks it by identity.
# It is deliberately not exported; combined with provenance revalidation at
# execution, a directly-constructed evidence object cannot forge authorization.
_AUTHORIZATION_TOKEN = object()


@dataclass(frozen=True)
class TriggerEvidence:
    """Validated proof that the ADR-0020 injection trigger actually occurred.

    A live injection plan is authorized only when it carries one of these,
    minted by :func:`validate_trigger_trace`. It is produced from a structured
    monitor trace (the seq/armed/mode event records the monitor observes),
    validated through the canonical monitor helper
    ``first_seq4_edge_after_armed_auto_front_half`` — never a second trigger
    definition. The seq-4 edge event also supplies the trigger-time latitude and
    elapsed time used to resolve GLTCH degree payloads.

    Authorization is not a plain ``validated=True`` flag a caller can set: it is
    an internal token stamped only by the validator, and it is re-checked by
    replaying the stored source trace through the canonical validator at
    execution time (see :func:`is_authorized`). A hand-built evidence object with
    ``validated=True`` therefore cannot authorize a write.
    """

    validated: bool
    reason: str
    seq4_event: dict[str, Any] = field(default_factory=dict)
    front_half_sequences: list[int] = field(default_factory=list)
    source_trace: tuple[Any, ...] = ()
    _token: object | None = None

    def is_authorized(self) -> bool:
        """Re-verify provenance: the token identity AND a replay of the trace."""
        if not self.validated or self._token is not _AUTHORIZATION_TOKEN:
            return False
        # Revalidate the stored source trace through the canonical validator so a
        # forged flag/token without a genuinely valid trace still fails closed.
        return first_seq4_edge_after_armed_auto_front_half(list(self.source_trace))

    def as_dict(self) -> dict[str, Any]:
        return {
            "validated": self.validated,
            "authorized": self.is_authorized(),
            "reason": self.reason,
            "seq4_event": _json_safe(self.seq4_event),
            "front_half_sequences": list(self.front_half_sequences),
            "source": "monitor.first_seq4_edge_after_armed_auto_front_half",
        }


def validate_trigger_trace(trace: Any) -> TriggerEvidence:
    """Validate a structured monitor trace into deterministic trigger evidence.

    Fails closed (``validated=False``, no token) for empty, missing, malformed,
    unarmed, wrong-mode, duplicate, regressive, or out-of-order traces without
    raising. Uses only the canonical monitor helper for the ordered
    seq-1->3->4 armed/AUTO navigation contract, with the seq-2 DO command
    optional in ``MISSION_CURRENT`` telemetry. Only this function stamps the
    internal authorization token.
    """

    if not isinstance(trace, (list, tuple)) or not trace:
        return TriggerEvidence(validated=False, reason="empty_or_malformed_trigger_trace")
    events = list(trace)
    if not first_seq4_edge_after_armed_auto_front_half(events):
        return TriggerEvidence(validated=False, reason="trigger_precondition_not_met")

    seq4_event: dict[str, Any] | None = None
    front_half: list[int] = []
    front_half_sequences = {
        *defaults.INJECTION_TRIGGER["front_half_required_sequences"],
        *defaults.INJECTION_TRIGGER["front_half_optional_sequences"],
    }
    for event in events:
        if not isinstance(event, dict):
            return TriggerEvidence(validated=False, reason="malformed_trigger_event")
        seq = event.get("seq")
        if isinstance(seq, int) and seq in front_half_sequences and seq not in front_half:
            front_half.append(seq)
        if seq == 4:
            seq4_event = dict(event)
            break
    if seq4_event is None:
        return TriggerEvidence(validated=False, reason="no_seq4_edge_event")
    return TriggerEvidence(
        validated=True,
        reason="validated_seq4_edge_armed_auto",
        seq4_event=seq4_event,
        front_half_sequences=sorted(front_half),
        source_trace=tuple(events),
        _token=_AUTHORIZATION_TOKEN,
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else None
    return value


@dataclass(frozen=True)
class RestoreStep:
    elapsed_since_trigger_s: float
    payload: dict[str, float]
    readback_rules: dict[str, ReadbackRule]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "elapsed_since_trigger_s": self.elapsed_since_trigger_s,
            "payload": dict(self.payload),
            "readback_rules": {
                name: rule.as_dict() for name, rule in self.readback_rules.items()
            },
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GpsInjectionPlan:
    case_id: str
    fault_type: str
    trigger: dict[str, Any]
    trigger_event: dict[str, Any]
    injection_payload: dict[str, float]
    readback_rules: dict[str, ReadbackRule]
    restore_plan: list[RestoreStep] = field(default_factory=list)
    ready_to_inject: bool = True
    failures: list[dict[str, Any]] = field(default_factory=list)
    launch_performed: bool = False
    live_readback_performed: bool = False
    # Execution authorization is separate from payload resolution. A preview can
    # resolve a payload but is never execution-authorized; only a plan built from
    # validated trigger evidence (or a nominal no-write plan) may be executed.
    preview_only: bool = True
    trigger_evidence: TriggerEvidence | None = None

    @property
    def success(self) -> bool:
        return self.ready_to_inject

    @property
    def requires_trigger_authorization(self) -> bool:
        """A non-nominal plan that writes parameters needs trigger evidence."""
        return self.fault_type != "nominal" and bool(self.injection_payload)

    @property
    def execution_authorized(self) -> bool:
        """True only when the plan may be executed as a live injection.

        For a parameter-writing plan this requires trigger evidence whose
        provenance still validates (token identity plus a replay of the source
        trace), so neither a preview nor a hand-built ``validated=True`` object
        can authorize a write.
        """
        if not self.ready_to_inject:
            return False
        if not self.requires_trigger_authorization:
            # Nominal / no-write plans are non-mutating and never fault a vehicle.
            return True
        if self.preview_only:
            return False
        evidence = self.trigger_evidence
        return evidence is not None and evidence.is_authorized()

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "fault_type": self.fault_type,
            "trigger": dict(self.trigger),
            "trigger_event": dict(self.trigger_event),
            "injection_payload": dict(self.injection_payload),
            "readback_rules": {
                name: rule.as_dict() for name, rule in self.readback_rules.items()
            },
            "restore_plan": [step.as_dict() for step in self.restore_plan],
            "ready_to_inject": self.ready_to_inject,
            "success": self.success,
            "failures": list(self.failures),
            "launch_performed": self.launch_performed,
            "live_readback_performed": self.live_readback_performed,
            "plan_only": True,
            "preview_only": self.preview_only,
            "requires_trigger_authorization": self.requires_trigger_authorization,
            "execution_authorized": self.execution_authorized,
            "trigger_evidence": (
                self.trigger_evidence.as_dict()
                if self.trigger_evidence is not None
                else None
            ),
        }


@dataclass(frozen=True)
class InjectionExecutionResult:
    success: bool
    reason: str
    plan: GpsInjectionPlan
    parameter_result: ParameterBatchResult | None = None
    launch_performed: bool = False
    live_readback_performed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "ok": self.success,
            "reason": self.reason,
            "plan": self.plan.as_dict(),
            "parameter_result": (
                self.parameter_result.as_dict()
                if self.parameter_result is not None
                else None
            ),
            "launch_performed": self.launch_performed,
            "live_readback_performed": self.live_readback_performed,
        }


def _build_plan(
    case: TestCase,
    trigger_event: Mapping[str, Any] | None,
    *,
    preview_only: bool,
    trigger_evidence: TriggerEvidence | None,
) -> GpsInjectionPlan:
    fault_type = str(case.parameters.get("fault_type", ""))
    failures: list[dict[str, Any]] = []
    # ``event`` and ``trigger`` may be malformed public inputs. Normalize them
    # inside the fail-closed path (as ValueError, not a raw dict()/TypeError)
    # so a malformed TestCase, trigger, or trigger_event returns a structured
    # not-ready plan instead of escaping as an uncaught exception.
    event: dict[str, Any] = {}
    trigger: dict[str, Any] = {}

    try:
        event = _as_event_mapping("trigger_event", trigger_event)
        # The trigger metadata is required, non-empty mapping input for any
        # fault-writing case (every generated fault case carries the populated
        # ADR-0020 trigger). A missing / None / empty / non-mapping trigger on a
        # fault case is malformed public input and must fail closed; nominal
        # no-write cases do not require a trigger.
        trigger = _resolve_case_trigger(fault_type, case.parameters.get("trigger"))
        injection_payload, restore_plan = _resolve_payload_and_restore(case, event)
        readback_rules = readback_rules_for_payload(injection_payload)
    except ValueError as exc:
        failures.append({"reason": "plan_resolution_failed", "detail": str(exc)})
        injection_payload = {}
        readback_rules = {}
        restore_plan = []

    return GpsInjectionPlan(
        case_id=case.case_id,
        fault_type=fault_type,
        trigger=trigger,
        trigger_event=event,
        injection_payload=injection_payload,
        readback_rules=readback_rules,
        restore_plan=restore_plan,
        ready_to_inject=not failures,
        failures=failures,
        preview_only=preview_only,
        trigger_evidence=trigger_evidence,
    )


def build_live_injection_plan(
    case: TestCase,
    trigger_event: Mapping[str, Any] | None = None,
) -> GpsInjectionPlan:
    """Resolve a case into a PREVIEW parameter plan without executing it.

    This resolves the payload from a reference latitude/time for inspection but
    is never execution-authorized: a preview carries no validated trigger
    evidence, so :func:`execute_injection_plan` refuses to run it for any
    fault that writes parameters. Use :func:`build_authorized_injection_plan`
    with a validated monitor trace to obtain an executable plan.
    """

    return _build_plan(
        case,
        trigger_event,
        preview_only=True,
        trigger_evidence=None,
    )


def build_authorized_injection_plan(
    case: TestCase,
    trigger_trace: Any,
) -> GpsInjectionPlan:
    """Build an execution-authorized plan from a validated monitor trace.

    ``trigger_trace`` is the structured seq/armed/mode event record the monitor
    observes. It is validated through :func:`validate_trigger_trace` (which uses
    the canonical monitor helper); only a validated trace authorizes execution.
    An invalid trace yields a not-ready, not-authorized plan and writes nothing.
    The seq-4 edge event supplies the trigger-time latitude/elapsed time used to
    resolve GLTCH degree payloads.
    """

    evidence = validate_trigger_trace(trigger_trace)
    if not evidence.validated:
        # A malformed public ``trigger`` must not crash this not-ready return on a
        # bare ``dict()`` TypeError/ValueError; normalize it fail-closed to {}.
        trigger = case.parameters.get("trigger", {})
        return GpsInjectionPlan(
            case_id=case.case_id,
            fault_type=str(case.parameters.get("fault_type", "")),
            trigger=dict(trigger) if isinstance(trigger, Mapping) else {},
            trigger_event=dict(evidence.seq4_event),
            injection_payload={},
            readback_rules={},
            restore_plan=[],
            ready_to_inject=False,
            failures=[{"reason": "trigger_not_validated", "detail": evidence.reason}],
            preview_only=False,
            trigger_evidence=evidence,
        )

    return _build_plan(
        case,
        evidence.seq4_event,
        preview_only=False,
        trigger_evidence=evidence,
    )


def execute_injection_plan(
    plan: GpsInjectionPlan,
    connection: MavlinkParameterConnection | None,
    *,
    timeout_s: float = 5.0,
) -> InjectionExecutionResult:
    """Execute a previously built plan against an explicit connection only.

    A non-nominal plan that writes parameters must carry validated trigger
    authorization (a preview never does). Any unauthorized plan is rejected
    before a single connection call, so it makes zero parameter writes/reads.
    """

    if not plan.ready_to_inject:
        return InjectionExecutionResult(
            success=False,
            reason="plan_not_ready",
            plan=plan,
        )
    if plan.requires_trigger_authorization and not plan.execution_authorized:
        # Preview-only or unvalidated-trigger plan: refuse before any write/read.
        return InjectionExecutionResult(
            success=False,
            reason="trigger_authorization_missing",
            plan=plan,
        )
    if not plan.injection_payload:
        return InjectionExecutionResult(
            success=True,
            reason="no_injection_writes",
            plan=plan,
        )
    if connection is None:
        return InjectionExecutionResult(
            success=False,
            reason="mavlink_connection_unavailable",
            plan=plan,
        )

    try:
        result = set_and_read_back_parameters(
            connection,
            plan.injection_payload,
            readback_rules=plan.readback_rules,
            timeout_s=timeout_s,
        )
    except ValueError as exc:
        # Batch preflight rejected the plan before any write occurred.
        return InjectionExecutionResult(
            success=False,
            reason=f"batch_preflight_rejected: {exc}",
            plan=plan,
        )
    return InjectionExecutionResult(
        success=result.success,
        reason="injection_readback_ok" if result.success else "injection_readback_failed",
        plan=plan,
        parameter_result=result,
        live_readback_performed=True,
    )


def execute_restore_step(
    step: RestoreStep,
    connection: MavlinkParameterConnection | None,
    *,
    timeout_s: float = 5.0,
) -> ParameterBatchResult | None:
    """Execute one restore step. Future live code owns timing and scheduling."""

    if connection is None:
        return None
    return set_and_read_back_parameters(
        connection,
        step.payload,
        readback_rules=step.readback_rules,
        timeout_s=timeout_s,
    )


def _resolve_payload_and_restore(
    case: TestCase,
    trigger_event: Mapping[str, Any],
) -> tuple[dict[str, float], list[RestoreStep]]:
    fault_type = str(case.parameters.get("fault_type"))
    recipe = case.parameters.get("fault_recipe") or {}
    if not isinstance(recipe, Mapping):
        raise ValueError("fault_recipe must be a mapping")

    _validate_optional_finite_event_value(trigger_event, "trigger_time_s")

    if fault_type == "nominal":
        return {}, []
    if fault_type == "slow_drift":
        payload = _resolve_slow_drift_payload(recipe, trigger_event)
        return payload, []
    if fault_type == "step_glitch":
        payload = _resolve_step_glitch_payload(recipe, trigger_event)
        return payload, []
    if fault_type == "hard_denial":
        payload = {"SIM_GPS1_ENABLE": 0.0}
        restore = _duration_restore(
            recipe=recipe,
            duration_key="denial_duration_s",
            payload={"SIM_GPS1_ENABLE": 1.0},
            reason="restore GPS enable after bounded denial window",
        )
        return payload, restore
    if fault_type == "jamming":
        payload = {"SIM_GPS1_JAM": 1.0}
        restore = _duration_restore(
            recipe=recipe,
            duration_key="jam_duration_s",
            payload={"SIM_GPS1_JAM": 0.0},
            reason="clear GPS jamming after bounded jam window",
        )
        return payload, restore
    raise ValueError(f"Unsupported gps_failure fault_type: {fault_type}")


def _resolve_slow_drift_payload(
    recipe: Mapping[str, Any],
    trigger_event: Mapping[str, Any],
) -> dict[str, float]:
    latitude_deg = _required_event_float(
        trigger_event,
        "trigger_latitude_deg",
        aliases=("latitude_deg", "lat_deg"),
    )
    elapsed_s = _required_event_float(
        trigger_event,
        "elapsed_since_trigger_s",
        aliases=("elapsed_s",),
    )
    if "drift_rate_mps" in recipe:
        rate_mps = finite_float("drift_rate_mps", recipe["drift_rate_mps"])
    else:
        rate_mps = _required_event_float(
            trigger_event,
            "selected_drift_rate_mps",
            aliases=("drift_rate_mps",),
        )
    return glitch.slow_drift_payload(
        rate_mps,
        elapsed_s,
        latitude_deg,
        axis=str(recipe.get("axis", "east")),
    )


def _resolve_step_glitch_payload(
    recipe: Mapping[str, Any],
    trigger_event: Mapping[str, Any],
) -> dict[str, float]:
    latitude_deg = _required_event_float(
        trigger_event,
        "trigger_latitude_deg",
        aliases=("latitude_deg", "lat_deg"),
    )
    magnitude_m = _required_recipe_float(recipe, "offset_magnitude_m")
    return glitch.step_glitch_payload(
        magnitude_m,
        latitude_deg,
        axis=str(recipe.get("axis", "east")),
    )


def _duration_restore(
    *,
    recipe: Mapping[str, Any],
    duration_key: str,
    payload: dict[str, float],
    reason: str,
) -> list[RestoreStep]:
    if duration_key not in recipe:
        return []
    duration_s = finite_float(duration_key, recipe[duration_key])
    if duration_s <= 0:
        raise ValueError(f"{duration_key} must be > 0")
    return [
        RestoreStep(
            elapsed_since_trigger_s=duration_s,
            payload=dict(payload),
            readback_rules=readback_rules_for_payload(payload),
            reason=reason,
        )
    ]


def _required_event_float(
    event: Mapping[str, Any],
    name: str,
    *,
    aliases: tuple[str, ...] = (),
) -> float:
    for key in (name, *aliases):
        if key in event:
            return finite_float(key, event[key])
    alias_text = ", ".join((name, *aliases))
    raise ValueError(f"missing required trigger event value: {alias_text}")


def _required_recipe_float(recipe: Mapping[str, Any], name: str) -> float:
    """Read a required numeric recipe field, failing closed as ``ValueError``.

    The recipe equivalent of :func:`_required_event_float`: a missing field is a
    deterministic ``ValueError`` (never a leaked ``KeyError``), and a present but
    non-numeric / non-finite value (``None``, a non-numeric string, ``NaN``,
    ``+inf``, ``-inf``) fails closed through :func:`finite_float`.
    """

    if name not in recipe:
        raise ValueError(f"missing required recipe value: {name}")
    return finite_float(name, recipe[name])


def _as_event_mapping(name: str, value: Any) -> dict[str, Any]:
    """Coerce a public trigger_event input to a dict, failing closed.

    ``None`` becomes an empty mapping (a benign "no event yet" preview). A genuine
    mapping is copied. Anything else (a list, string, or number posing as a
    trigger_event) is a malformed public input and raises ``ValueError`` so the
    caller returns a structured not-ready plan rather than crashing on a bare
    ``dict()`` ``TypeError``.

    Note: the case ``trigger`` *metadata* is stricter — see
    :func:`_resolve_case_trigger`. ``trigger_event`` may legitimately be empty for
    a preview; the required trigger metadata may not be for a fault case.
    """

    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    raise ValueError(f"{name} must be a mapping")


def _resolve_case_trigger(fault_type: str, value: Any) -> dict[str, Any]:
    """Validate the case ``trigger`` metadata, failing closed for fault cases.

    Every generated fault case carries the populated ADR-0020 injection trigger.
    For any parameter-writing fault (anything other than ``nominal``) a missing,
    ``None``, empty, or non-mapping trigger is malformed public input and raises
    ``ValueError`` — so a malformed ``TestCase`` cannot resolve a payload or
    execute a write. A nominal no-write case does not require a trigger, so an
    absent/empty trigger there normalizes to ``{}``.
    """

    if value is not None and not isinstance(value, Mapping):
        raise ValueError("trigger must be a mapping")
    trigger = dict(value) if isinstance(value, Mapping) else {}
    if fault_type not in ("", "nominal") and not trigger:
        raise ValueError("missing required trigger metadata for fault case")
    return trigger


def _validate_optional_finite_event_value(
    event: Mapping[str, Any],
    name: str,
) -> None:
    if name in event:
        finite_float(name, event[name])
