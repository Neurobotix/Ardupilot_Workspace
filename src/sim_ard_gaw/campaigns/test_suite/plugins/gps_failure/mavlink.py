"""No-SITL-testable MAVLink parameter contract helpers for gps_failure."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import time
from typing import Any, Mapping, Protocol

from . import defaults


class MavlinkParameterConnection(Protocol):
    """Small parameter subset expected from a MAVLink-like connection."""

    def param_fetch_one(self, name: str) -> None:
        ...

    def param_set_send(self, name: str, value: float) -> None:
        ...

    def recv_match(self, **kwargs: Any) -> Any:
        ...


@dataclass(frozen=True)
class ReadbackRule:
    expected: float
    tolerance: float

    def as_dict(self) -> dict[str, float]:
        return {"expected": self.expected, "tolerance": self.tolerance}


@dataclass(frozen=True)
class ParameterWriteResult:
    param: str
    requested_value: float
    observed_value: float | None
    ok: bool
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "param": self.param,
            "requested_value": self.requested_value,
            "observed_value": self.observed_value,
            "ok": self.ok,
            "error": self.error,
        }


@dataclass(frozen=True)
class ParameterReadResult:
    param: str
    value: float | None
    ok: bool
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "param": self.param,
            "value": self.value,
            "ok": self.ok,
            "error": self.error,
        }


@dataclass(frozen=True)
class ReadbackFailure:
    param: str
    reason: str
    expected: float | None = None
    actual: float | None = None
    tolerance: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "param": self.param,
            "reason": self.reason,
            "expected": self.expected,
            "actual": self.actual,
            "tolerance": self.tolerance,
        }


@dataclass(frozen=True)
class ReadbackComparison:
    success: bool
    readbacks_observed: dict[str, float]
    missing_parameters: list[str] = field(default_factory=list)
    tolerance_failures: list[ReadbackFailure] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "ok": self.success,
            "readbacks_observed": dict(self.readbacks_observed),
            "missing_parameters": list(self.missing_parameters),
            "tolerance_failures": [
                failure.as_dict() for failure in self.tolerance_failures
            ],
        }


@dataclass(frozen=True)
class ParameterBatchResult:
    writes_attempted: list[ParameterWriteResult]
    readbacks_observed: dict[str, float]
    missing_parameters: list[str]
    tolerance_failures: list[ReadbackFailure]
    success: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "writes_attempted": [
                write.as_dict() for write in self.writes_attempted
            ],
            "readbacks_observed": dict(self.readbacks_observed),
            "missing_parameters": list(self.missing_parameters),
            "tolerance_failures": [
                failure.as_dict() for failure in self.tolerance_failures
            ],
            "success": self.success,
            "ok": self.success,
        }


class MavlinkParameterAdapter:
    """Adapter for fakes now and a real MAVLink connection later."""

    def __init__(self, connection: MavlinkParameterConnection) -> None:
        self._connection = connection

    def set_parameter(
        self,
        name: str,
        value: float,
        *,
        timeout_s: float = 5.0,
    ) -> ParameterWriteResult:
        requested = finite_float(f"{name} requested", value)
        try:
            observed = _call_set(self._connection, name, requested, timeout_s)
            observed_value = finite_float(f"{name} set readback", observed)
            return ParameterWriteResult(
                param=name,
                requested_value=requested,
                observed_value=observed_value,
                ok=True,
            )
        except Exception as exc:
            return ParameterWriteResult(
                param=name,
                requested_value=requested,
                observed_value=None,
                ok=False,
                error=str(exc),
            )

    def read_parameter(
        self,
        name: str,
        *,
        timeout_s: float = 5.0,
    ) -> ParameterReadResult:
        try:
            value = _call_read(self._connection, name, timeout_s)
            observed = finite_float(f"{name} readback", value)
            return ParameterReadResult(param=name, value=observed, ok=True)
        except Exception as exc:
            return ParameterReadResult(param=name, value=None, ok=False, error=str(exc))


def set_one_parameter(
    connection: MavlinkParameterConnection,
    name: str,
    value: float,
    *,
    timeout_s: float = 5.0,
) -> ParameterWriteResult:
    """Set one parameter after rejecting non-finite write values."""

    return MavlinkParameterAdapter(connection).set_parameter(
        name,
        value,
        timeout_s=timeout_s,
    )


def read_one_parameter(
    connection: MavlinkParameterConnection,
    name: str,
    *,
    timeout_s: float = 5.0,
) -> ParameterReadResult:
    return MavlinkParameterAdapter(connection).read_parameter(name, timeout_s=timeout_s)


def set_many_parameters(
    connection: MavlinkParameterConnection,
    payload: Mapping[str, float],
    *,
    timeout_s: float = 5.0,
) -> list[ParameterWriteResult]:
    """Set parameters in sorted-name order for deterministic replay."""

    adapter = MavlinkParameterAdapter(connection)
    return [
        adapter.set_parameter(name, payload[name], timeout_s=timeout_s)
        for name in sorted(payload)
    ]


def read_parameters(
    connection: MavlinkParameterConnection,
    names: list[str] | tuple[str, ...],
    *,
    timeout_s: float = 5.0,
) -> dict[str, ParameterReadResult]:
    adapter = MavlinkParameterAdapter(connection)
    return {
        name: adapter.read_parameter(name, timeout_s=timeout_s)
        for name in sorted(names)
    }


def readback_rules_for_payload(payload: Mapping[str, float]) -> dict[str, ReadbackRule]:
    rules: dict[str, ReadbackRule] = {}
    for name in sorted(payload):
        if name not in defaults.PARAMETER_METADATA:
            raise ValueError(f"Unknown SIM_GPS parameter: {name}")
        expected = finite_float(f"{name} expected", payload[name])
        tolerance = finite_float(
            f"{name} tolerance",
            defaults.PARAMETER_METADATA[name]["readback_tolerance"],
        )
        if tolerance < 0:
            raise ValueError(f"{name} tolerance must be >= 0")
        rules[name] = ReadbackRule(expected=expected, tolerance=tolerance)
    return rules


def normalize_readback_rules(
    rules: Mapping[str, ReadbackRule | Mapping[str, float]],
) -> dict[str, ReadbackRule]:
    normalized: dict[str, ReadbackRule] = {}
    for name in sorted(rules):
        rule = rules[name]
        if isinstance(rule, ReadbackRule):
            expected = rule.expected
            tolerance = rule.tolerance
        elif isinstance(rule, Mapping):
            if "expected" not in rule or "tolerance" not in rule:
                raise ValueError(
                    f"{name} readback rule must define both expected and tolerance"
                )
            expected = rule["expected"]
            tolerance = rule["tolerance"]
        else:
            # A non-mapping, non-ReadbackRule rule object is malformed: fail
            # closed with ValueError so the public batch contract is consistent.
            raise ValueError(f"{name} readback rule is malformed")
        expected_value = finite_float(f"{name} expected", expected)
        tolerance_value = finite_float(f"{name} tolerance", tolerance)
        if tolerance_value < 0:
            raise ValueError(f"{name} tolerance must be >= 0")
        normalized[name] = ReadbackRule(
            expected=expected_value,
            tolerance=tolerance_value,
        )
    return normalized


def compare_readbacks(
    rules: Mapping[str, ReadbackRule | Mapping[str, float]],
    observed: Mapping[str, float],
) -> ReadbackComparison:
    normalized_rules = normalize_readback_rules(rules)
    observed_finite: dict[str, float] = {}
    missing: list[str] = []
    failures: list[ReadbackFailure] = []

    for name, rule in normalized_rules.items():
        if name not in observed:
            missing.append(name)
            continue
        try:
            actual = finite_float(f"{name} actual", observed[name])
        except ValueError:
            failures.append(
                ReadbackFailure(
                    param=name,
                    reason="non_finite",
                    expected=rule.expected,
                    tolerance=rule.tolerance,
                )
            )
            continue
        observed_finite[name] = actual
        if abs(actual - rule.expected) > rule.tolerance:
            failures.append(
                ReadbackFailure(
                    param=name,
                    reason="out_of_tolerance",
                    expected=rule.expected,
                    actual=actual,
                    tolerance=rule.tolerance,
                )
            )

    return ReadbackComparison(
        success=not missing and not failures,
        readbacks_observed=observed_finite,
        missing_parameters=missing,
        tolerance_failures=failures,
    )


def read_back_injected_parameters(
    connection: MavlinkParameterConnection,
    rules: Mapping[str, ReadbackRule | Mapping[str, float]],
    *,
    timeout_s: float = 5.0,
) -> ParameterBatchResult:
    normalized_rules = normalize_readback_rules(rules)
    reads = read_parameters(
        connection,
        tuple(normalized_rules),
        timeout_s=timeout_s,
    )
    observed = {
        name: read.value
        for name, read in reads.items()
        if read.ok and read.value is not None
    }
    comparison = compare_readbacks(normalized_rules, observed)
    read_errors = [
        ReadbackFailure(param=name, reason=str(read.error or "read_failed"))
        for name, read in reads.items()
        if not read.ok
    ]
    return ParameterBatchResult(
        writes_attempted=[],
        readbacks_observed=comparison.readbacks_observed,
        missing_parameters=[
            *comparison.missing_parameters,
            *[failure.param for failure in read_errors],
        ],
        tolerance_failures=[*comparison.tolerance_failures, *read_errors],
        success=comparison.success and not read_errors,
    )


def preflight_batch(
    payload: Mapping[str, float],
    readback_rules: Mapping[str, ReadbackRule | Mapping[str, float]] | None,
) -> tuple[dict[str, float], dict[str, ReadbackRule]]:
    """Validate an entire injection batch before any connection call.

    This is the atomic preflight stage for :func:`set_and_read_back_parameters`.
    It validates the payload type, every parameter name, every parameter value,
    the readback-rule structure, expected values, tolerances, and the
    payload/rule key correspondence. It performs no writes and no reads; on any
    problem it raises ``ValueError`` before the first mutation, so a caller that
    lets the exception propagate has performed zero writes and zero reads.

    Returns the validated (payload, rules) pair for deterministic replay.
    """

    _require_mapping("payload", payload)

    validated_payload: dict[str, float] = {}
    for name in sorted(payload):
        if name not in defaults.PARAMETER_METADATA:
            raise ValueError(f"Unknown SIM_GPS parameter: {name}")
        validated_payload[name] = finite_float(f"{name} requested", payload[name])

    if readback_rules is None:
        rules = readback_rules_for_payload(validated_payload)
    else:
        rules = normalize_readback_rules(readback_rules)

    payload_names = set(validated_payload)
    rule_names = set(rules)
    missing_rules = sorted(payload_names - rule_names)
    if missing_rules:
        raise ValueError(f"missing readback rule for injected parameters: {missing_rules}")
    extra_rules = sorted(rule_names - payload_names)
    if extra_rules:
        raise ValueError(
            f"readback rules include parameters absent from the payload: {extra_rules}"
        )

    return validated_payload, rules


def set_and_read_back_parameters(
    connection: MavlinkParameterConnection,
    payload: Mapping[str, float],
    *,
    readback_rules: Mapping[str, ReadbackRule | Mapping[str, float]] | None = None,
    timeout_s: float = 5.0,
) -> ParameterBatchResult:
    """Set and read back a batch atomically after full preflight validation.

    The complete batch is validated by :func:`preflight_batch` before the first
    connection call. On any validation failure this raises ``ValueError`` with
    zero writes and zero reads performed. Transport/readback failures *after*
    successful validation still produce a deterministic structured result.
    """

    validated_payload, rules = preflight_batch(payload, readback_rules)
    writes = set_many_parameters(connection, validated_payload, timeout_s=timeout_s)
    observed = {
        write.param: write.observed_value
        for write in writes
        if write.ok and write.observed_value is not None
    }
    comparison = compare_readbacks(rules, observed)
    write_failures = [
        ReadbackFailure(param=write.param, reason=str(write.error or "write_failed"))
        for write in writes
        if not write.ok
    ]
    return ParameterBatchResult(
        writes_attempted=writes,
        readbacks_observed=comparison.readbacks_observed,
        missing_parameters=[
            *comparison.missing_parameters,
            *[failure.param for failure in write_failures],
        ],
        tolerance_failures=[*comparison.tolerance_failures, *write_failures],
        success=comparison.success and not write_failures,
    )


def finite_float(name: str, value: object) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be finite") from None
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _require_mapping(name: str, value: object) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")


def _call_set(
    connection: MavlinkParameterConnection,
    name: str,
    value: float,
    timeout_s: float,
) -> float:
    set_method = getattr(connection, "set_parameter", None)
    if callable(set_method):
        return finite_float(f"{name} set readback", set_method(name, value))

    connection.param_set_send(name, value)
    return _wait_for_param_value(connection, name, timeout_s)


def _call_read(
    connection: MavlinkParameterConnection,
    name: str,
    timeout_s: float,
) -> float:
    read_method = getattr(connection, "read_parameter", None)
    if callable(read_method):
        return finite_float(f"{name} readback", read_method(name))

    connection.param_fetch_one(name)
    return _wait_for_param_value(connection, name, timeout_s)


def _wait_for_param_value(
    connection: MavlinkParameterConnection,
    name: str,
    timeout_s: float,
) -> float:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        msg = connection.recv_match(type=["PARAM_VALUE"], blocking=True, timeout=0.5)
        if msg is None:
            continue
        if _param_id(msg) == name:
            return float(getattr(msg, "param_value"))
    raise TimeoutError(f"Timed out waiting for parameter {name}")


def _param_id(msg: Any) -> str:
    value = getattr(msg, "param_id", "")
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").rstrip("\x00")
    return str(value).rstrip("\x00")
