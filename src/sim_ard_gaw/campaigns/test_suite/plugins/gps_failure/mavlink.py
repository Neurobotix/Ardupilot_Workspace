"""No-SITL-testable MAVLink parameter contract helpers for gps_failure."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
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


class MavlinkConnectionFactory(Protocol):
    def __call__(self, endpoint: str, *, timeout_s: float) -> MavlinkParameterConnection:
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
        readback_tolerance: float | None = None,
    ) -> ParameterWriteResult:
        requested = finite_float(f"{name} requested", value)
        try:
            observed = _call_set(
                self._connection,
                name,
                requested,
                timeout_s,
                readback_tolerance=readback_tolerance,
            )
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

    tolerance = _default_readback_tolerance(name)
    return MavlinkParameterAdapter(connection).set_parameter(
        name,
        value,
        timeout_s=timeout_s,
        readback_tolerance=tolerance,
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
    readback_rules: Mapping[str, ReadbackRule | Mapping[str, float]] | None = None,
) -> list[ParameterWriteResult]:
    """Set parameters in sorted-name order for deterministic replay."""

    adapter = MavlinkParameterAdapter(connection)
    rules = normalize_readback_rules(readback_rules or readback_rules_for_payload(payload))
    return [
        adapter.set_parameter(
            name,
            payload[name],
            timeout_s=timeout_s,
            readback_tolerance=rules[name].tolerance,
        )
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


def read_live_contract_parameters(
    connection: MavlinkParameterConnection,
    *,
    injected_or_restored: Mapping[str, float] | None = None,
    timeout_s: float = 5.0,
) -> dict[str, ParameterReadResult]:
    """Read all Phase-2 GPS source-contract parameters from an explicit link."""

    names = set(defaults.LIVE_READBACK_PARAMS)
    names.update(injected_or_restored or {})
    return read_parameters(connection, tuple(sorted(names)), timeout_s=timeout_s)


def connect_mavlink(
    endpoint: str,
    *,
    timeout_s: float = 30.0,
    factory: MavlinkConnectionFactory | None = None,
) -> MavlinkParameterConnection:
    """Create a MAVLink connection only when explicitly called.

    Importing this module never imports pymavlink and never opens a socket. A
    fake ``factory`` can be supplied by tests; otherwise the real pymavlink
    import happens inside this function.
    """

    if factory is not None:
        connection = factory(endpoint, timeout_s=timeout_s)
    else:
        try:
            from pymavlink import mavutil  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("pymavlink is required for live GPS failure runs") from exc
        connection = mavutil.mavlink_connection(endpoint)
    heartbeat = getattr(connection, "wait_heartbeat", None)
    if callable(heartbeat):
        message = heartbeat(timeout=timeout_s)
        if message is None:
            close = getattr(connection, "close", None)
            if callable(close):
                close()
            raise TimeoutError(
                f"no MAVLink heartbeat received from {endpoint} within {timeout_s}s"
            )
    elif factory is None:
        raise RuntimeError("live MAVLink connection does not provide wait_heartbeat()")
    return connection


def request_live_streams(connection: Any, *, rate_hz: int = 5) -> None:
    """Request the Plane telemetry streams without ACK-gating event messages."""

    if isinstance(rate_hz, bool) or not isinstance(rate_hz, int) or rate_hz <= 0:
        raise ValueError("rate_hz must be a positive integer")
    mavutil, _ = _pymavlink_modules()
    streams = (
        mavutil.mavlink.MAV_DATA_STREAM_ALL,
        mavutil.mavlink.MAV_DATA_STREAM_POSITION,
        mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,
        mavutil.mavlink.MAV_DATA_STREAM_EXTRA2,
    )
    for stream_id in streams:
        try:
            connection.mav.request_data_stream_send(
                connection.target_system,
                connection.target_component,
                stream_id,
                rate_hz,
                1,
            )
        except Exception:
            continue


def wait_for_vehicle_ready(
    connection: Any,
    timeout_s: float,
    *,
    force_arm: bool,
) -> None:
    """Require AUTO availability, initialized mode, GPS, and EKF readiness."""

    mavutil, _ = _pymavlink_modules()
    deadline = time.time() + timeout_s
    auto_available = False
    gps_ready = False
    ekf_ready = False
    ready_heartbeats = 0
    last_prearm_text: str | None = None
    last_prearm_at = 0.0
    last_mode: str | None = None
    last_gps_fix_type: int | None = None
    last_gps_satellites: int | None = None
    last_ekf_flags: int | None = None
    message_counts = {
        "HEARTBEAT": 0,
        "STATUSTEXT": 0,
        "GPS_RAW_INT": 0,
        "EKF_STATUS_REPORT": 0,
    }
    request_live_streams(connection)
    next_stream_refresh_at = time.time() + defaults.READINESS_STREAM_REFRESH_S

    while time.time() < deadline:
        now = time.time()
        if now >= next_stream_refresh_at:
            # A request sent during the initial MAVProxy / wiped-EERPOM startup
            # edge can be lost before Plane has installed its stream rates.
            # Refreshing is idempotent and matches MAVLink stream semantics.
            request_live_streams(connection)
            next_stream_refresh_at = now + defaults.READINESS_STREAM_REFRESH_S
        mode_map = connection.mode_mapping()
        if mode_map and "AUTO" in mode_map:
            auto_available = True
        msg = connection.recv_match(
            type=["HEARTBEAT", "STATUSTEXT", "GPS_RAW_INT", "EKF_STATUS_REPORT"],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue
        msg_type = msg.get_type()
        if msg_type in message_counts:
            message_counts[msg_type] += 1
        if msg_type == "GPS_RAW_INT":
            fix_type = _coerce_int(getattr(msg, "fix_type", None))
            satellites = _coerce_int(getattr(msg, "satellites_visible", None))
            last_gps_fix_type = fix_type
            last_gps_satellites = satellites
            if (fix_type is not None and fix_type >= 3) or (
                satellites is not None and satellites >= 6
            ):
                gps_ready = True
            continue
        if msg_type == "EKF_STATUS_REPORT":
            flags = _coerce_int(getattr(msg, "flags", None))
            last_ekf_flags = flags
            if flags is not None:
                required = (
                    getattr(mavutil.mavlink, "EKF_ATTITUDE", 1)
                    | getattr(mavutil.mavlink, "EKF_VELOCITY_HORIZ", 2)
                    | getattr(mavutil.mavlink, "EKF_POS_HORIZ_ABS", 8)
                )
                ekf_ready = (flags & required) == required
            continue
        if msg_type == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            lower = text.lower()
            if "prearm" in lower:
                last_prearm_at = time.time()
                last_prearm_text = text
                if not force_arm:
                    defaults.log(f"  STATUSTEXT: {text}")
            if "gps" in lower and "detected" in lower:
                gps_ready = True
            if "ekf3" in lower and "using gps" in lower:
                gps_ready = True
                ekf_ready = True
            if "ahrs: ekf3 active" in lower:
                ekf_ready = True
            continue

        mode = mavutil.mode_string_v10(msg)
        last_mode = mode
        initialized = mode not in {"INITIALISING", "INITIALIZING"}
        prearm_clear = force_arm or (time.time() - last_prearm_at > 2.0)
        if auto_available and initialized and prearm_clear and gps_ready and ekf_ready:
            ready_heartbeats += 1
            if ready_heartbeats >= defaults.READY_HEARTBEATS_REQUIRED:
                defaults.log(
                    "Vehicle readiness confirmed: AUTO available, GPS ready, "
                    "EKF active."
                )
                return
        else:
            ready_heartbeats = 0

    state = (
        f"auto_available={auto_available}, mode={last_mode!r}, "
        f"gps_ready={gps_ready} (fix_type={last_gps_fix_type}, "
        f"satellites={last_gps_satellites}), ekf_ready={ekf_ready} "
        f"(flags={last_ekf_flags}), ready_heartbeats={ready_heartbeats}, "
        f"message_counts={message_counts}"
    )
    prearm = (
        f" Last prearm text: {last_prearm_text}."
        if last_prearm_text is not None and not force_arm
        else ""
    )
    raise TimeoutError(
        f"Vehicle did not become ready within {timeout_s:.0f}s; {state}.{prearm}"
    )


def upload_mission(connection: Any, mission_file: Path, timeout_s: float) -> list[Any]:
    """Upload a mission using the GPS plugin's owned MAVLink protocol."""

    mavutil, mavwp = _pymavlink_modules()
    if not mission_file.exists():
        raise FileNotFoundError(f"Mission file not found: {mission_file}")
    loader = mavwp.MAVWPLoader()
    loader.load(str(mission_file))
    items = [
        _mission_item_int(
            loader.wp(index),
            connection.target_system,
            connection.target_component,
            mavutil,
        )
        for index in range(loader.count())
    ]
    if not items:
        raise RuntimeError(f"Mission file has no items: {mission_file}")

    defaults.log(f"Uploading mission ({len(items)} items): {mission_file}")
    connection.waypoint_clear_all_send()
    drain_deadline = time.time() + 3.0
    while time.time() < drain_deadline:
        msg = connection.recv_match(
            type=["MISSION_ACK", "STATUSTEXT"], blocking=True, timeout=0.3
        )
        if msg is not None and msg.get_type() == "MISSION_ACK":
            break
    connection.waypoint_count_send(len(items))

    sent: set[int] = set()
    deadline = time.time() + timeout_s
    while True:
        if time.time() >= deadline:
            raise TimeoutError(
                f"Mission upload timed out after {timeout_s:.0f}s "
                f"(sent {len(sent)}/{len(items)} items)."
            )
        msg = connection.recv_match(
            type=[
                "MISSION_REQUEST",
                "MISSION_REQUEST_INT",
                "MISSION_ACK",
                "STATUSTEXT",
            ],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue
        msg_type = msg.get_type()
        if msg_type == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text and "mission" in text.lower():
                defaults.log(f"  STATUSTEXT: {text}")
            continue
        if msg_type == "MISSION_ACK":
            result = getattr(msg, "type", None)
            accepted = mavutil.mavlink.MAV_MISSION_ACCEPTED
            if result == accepted and len(sent) == len(items):
                defaults.log("Mission upload acknowledged.")
                return items
            if result == accepted:
                continue
            raise RuntimeError(f"Mission upload failed: {msg}")
        seq = int(getattr(msg, "seq", -1))
        if seq < 0 or seq >= len(items):
            raise RuntimeError(f"Vehicle requested invalid mission item seq={seq}.")
        item = items[seq]
        item.target_system = connection.target_system
        item.target_component = connection.target_component
        item.seq = seq
        item.pack(connection.mav)
        connection.mav.send(item)
        sent.add(seq)


def verify_mission(
    connection: Any,
    uploaded_items: list[Any],
    timeout_s: float,
) -> None:
    """Download the vehicle mission and require exact identity before arming."""

    mavutil, _ = _pymavlink_modules()
    expected_count = len(uploaded_items)
    mission_type = mavutil.mavlink.MAV_MISSION_TYPE_MISSION
    defaults.log(f"Verifying mission identity ({expected_count} items)")
    connection.mav.mission_request_list_send(
        connection.target_system,
        connection.target_component,
        mission_type,
    )
    deadline = time.time() + timeout_s
    reported_count: int | None = None
    while time.time() < deadline:
        msg = connection.recv_match(
            type=["MISSION_COUNT", "STATUSTEXT"], blocking=True, timeout=1.0
        )
        if msg is not None and msg.get_type() == "MISSION_COUNT":
            reported_count = int(msg.count)
            break
    if reported_count is None:
        raise TimeoutError(
            f"Mission verification: no MISSION_COUNT received within {timeout_s:.0f}s."
        )
    if reported_count != expected_count:
        raise RuntimeError(
            f"Mission verification: vehicle reports {reported_count}, "
            f"expected {expected_count}."
        )

    for seq in range(expected_count):
        connection.mav.mission_request_int_send(
            connection.target_system,
            connection.target_component,
            seq,
            mission_type,
        )
        item_deadline = time.time() + defaults.VERIFY_MISSION_ITEM_TIMEOUT_S
        got = None
        while time.time() < item_deadline:
            msg = connection.recv_match(
                type=["MISSION_ITEM_INT", "MISSION_ITEM", "STATUSTEXT"],
                blocking=True,
                timeout=1.0,
            )
            if msg is None or msg.get_type() not in {
                "MISSION_ITEM_INT",
                "MISSION_ITEM",
            }:
                continue
            if int(getattr(msg, "seq", -1)) == seq:
                got = msg
                break
        if got is None:
            raise TimeoutError(f"Mission verification: no item received for seq={seq}.")

        want = uploaded_items[seq]
        if seq == 0 and int(getattr(want, "current", 0)) == 1:
            defaults.log("  Mission verification: seq 0 home row count-checked only.")
            continue
        mismatches = _mission_item_mismatches(got, want, mavutil)
        if mismatches:
            raise RuntimeError(
                f"Mission verification: seq {seq} differs ({'; '.join(mismatches)})."
            )

    connection.mav.mission_ack_send(
        connection.target_system,
        connection.target_component,
        mavutil.mavlink.MAV_MISSION_ACCEPTED,
        mission_type,
    )
    defaults.log(f"Mission identity verified: {expected_count} items match.")


def arm_vehicle(connection: Any, timeout_s: float, force_arm: bool) -> None:
    mavutil, _ = _pymavlink_modules()
    deadline = time.time() + timeout_s
    next_send = 0.0
    param2 = defaults.FORCE_ARM_MAGIC if force_arm else 0.0
    while time.time() < deadline:
        now = time.time()
        if now >= next_send:
            connection.mav.command_long_send(
                connection.target_system,
                connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1,
                param2,
                0,
                0,
                0,
                0,
                0,
            )
            next_send = now + 2.0
        msg = connection.recv_match(
            type=["HEARTBEAT", "STATUSTEXT", "COMMAND_ACK"],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue
        if msg.get_type() == "HEARTBEAT" and bool(
            msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
        ):
            defaults.log(f"Vehicle armed in mode={mavutil.mode_string_v10(msg)}.")
            return
        if msg.get_type() == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text and any(
                token in text.lower() for token in ("arm", "prearm", "gps", "ekf")
            ):
                defaults.log(f"  STATUSTEXT: {text}")
    raise TimeoutError(f"Vehicle did not arm within {timeout_s:.0f}s.")


def settle_after_arm_before_auto(connection: Any, settle_s: float) -> None:
    deadline = time.time() + settle_s
    while time.time() < deadline:
        msg = connection.recv_match(
            type=["HEARTBEAT", "STATUSTEXT"], blocking=True, timeout=0.5
        )
        if msg is not None and msg.get_type() == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text and any(token in text.lower() for token in ("arm", "ekf", "gps")):
                defaults.log(f"  STATUSTEXT: {text}")


def set_auto_mode(connection: Any, timeout_s: float) -> None:
    mavutil, _ = _pymavlink_modules()
    deadline = time.time() + timeout_s
    next_send = 0.0
    while time.time() < deadline:
        now = time.time()
        if now >= next_send:
            connection.set_mode_apm("AUTO")
            next_send = now + 2.0
        msg = connection.recv_match(
            type=["HEARTBEAT", "STATUSTEXT", "COMMAND_ACK"],
            blocking=True,
            timeout=1.0,
        )
        if msg is None:
            continue
        if msg.get_type() == "HEARTBEAT" and mavutil.mode_string_v10(msg) == "AUTO":
            defaults.log("Vehicle entered AUTO mode.")
            return
        if msg.get_type() == "STATUSTEXT":
            text = str(getattr(msg, "text", "")).strip()
            if text and any(
                token in text.lower() for token in ("auto", "mode", "mission")
            ):
                defaults.log(f"  STATUSTEXT: {text}")
    raise TimeoutError(f"Vehicle did not enter AUTO within {timeout_s:.0f}s.")


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
        # A read that errored is reported once, via ``read_errors`` in
        # ``tolerance_failures``. It is absent from ``observed`` so
        # ``compare_readbacks`` also lists it as missing; drop that duplicate so
        # each failed parameter appears exactly once in ``missing_parameters``.
        missing_parameters=_merge_missing(comparison.missing_parameters, read_errors),
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
    writes = set_many_parameters(
        connection,
        validated_payload,
        timeout_s=timeout_s,
        readback_rules=rules,
    )
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
        # A write that errored is reported once, via ``write_failures`` in
        # ``tolerance_failures``. Its value never reaches ``observed`` so
        # ``compare_readbacks`` also lists it as missing; drop that duplicate so
        # each failed parameter appears exactly once in ``missing_parameters``.
        missing_parameters=_merge_missing(comparison.missing_parameters, write_failures),
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


def _merge_missing(
    missing_from_comparison: list[str],
    errors: list[ReadbackFailure],
) -> list[str]:
    """Merge comparison-missing names with transport-error param names once each.

    A read/write that errored is already reported in ``tolerance_failures`` and,
    because its value never reached the observed set, also shows up in the
    comparison's ``missing_parameters``. Deduplicate so each parameter name
    appears exactly once, preserving deterministic sorted order.
    """

    names = set(missing_from_comparison)
    names.update(failure.param for failure in errors)
    return sorted(names)


def _call_set(
    connection: MavlinkParameterConnection,
    name: str,
    value: float,
    timeout_s: float,
    *,
    readback_tolerance: float | None = None,
) -> float:
    set_method = getattr(connection, "set_parameter", None)
    if callable(set_method):
        return finite_float(f"{name} set readback", set_method(name, value))

    connection.param_set_send(name, value)
    return _wait_for_param_value(
        connection,
        name,
        timeout_s,
        expected=value,
        tolerance=readback_tolerance,
    )


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
    *,
    expected: float | None = None,
    tolerance: float | None = None,
) -> float:
    expected_value = (
        finite_float(f"{name} expected readback", expected)
        if expected is not None
        else None
    )
    tolerance_value = finite_float(
        f"{name} readback tolerance",
        0.0 if tolerance is None else tolerance,
    )
    if tolerance_value < 0:
        raise ValueError(f"{name} readback tolerance must be >= 0")

    deadline = time.time() + timeout_s
    last_observed: float | None = None
    while time.time() < deadline:
        msg = connection.recv_match(type=["PARAM_VALUE"], blocking=True, timeout=0.5)
        if msg is None:
            continue
        if _param_id(msg) == name:
            observed = finite_float(
                f"{name} PARAM_VALUE",
                getattr(msg, "param_value"),
            )
            if expected_value is None or abs(observed - expected_value) <= tolerance_value:
                return observed
            last_observed = observed
    if last_observed is not None:
        return last_observed
    raise TimeoutError(f"Timed out waiting for parameter {name}")


def _default_readback_tolerance(name: str) -> float | None:
    metadata = defaults.PARAMETER_METADATA.get(name)
    if not isinstance(metadata, Mapping):
        return None
    tolerance = metadata.get("readback_tolerance")
    if tolerance is None:
        return None
    return finite_float(f"{name} tolerance", tolerance)


def _param_id(msg: Any) -> str:
    value = getattr(msg, "param_id", "")
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").rstrip("\x00")
    return str(value).rstrip("\x00")


def _pymavlink_modules() -> tuple[Any, Any]:
    """Import protocol modules only inside explicitly invoked live helpers."""

    try:
        from pymavlink import mavutil, mavwp  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("pymavlink is required for live GPS failure runs") from exc
    return mavutil, mavwp


def _mission_item_int(
    waypoint: Any,
    target_system: int,
    target_component: int,
    mavutil: Any,
) -> Any:
    if waypoint.get_type() == "MISSION_ITEM_INT":
        waypoint.target_system = target_system
        waypoint.target_component = target_component
        return waypoint
    return mavutil.mavlink.MAVLink_mission_item_int_message(
        target_system,
        target_component,
        int(waypoint.seq),
        int(waypoint.frame),
        int(waypoint.command),
        int(waypoint.current),
        int(waypoint.autocontinue),
        float(waypoint.param1),
        float(waypoint.param2),
        float(waypoint.param3),
        float(waypoint.param4),
        int(float(waypoint.x) * 1.0e7),
        int(float(waypoint.y) * 1.0e7),
        float(waypoint.z),
    )


def _mission_item_mismatches(got: Any, want: Any, mavutil: Any) -> list[str]:
    mismatches: list[str] = []
    if int(got.command) != int(want.command):
        mismatches.append(f"command {int(got.command)}!={int(want.command)}")
    if int(want.command) == mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH:
        defaults.log(
            "  Mission verification: RTL row normalizes frame/position on download."
        )
        return mismatches
    if int(got.frame) != int(want.frame):
        mismatches.append(f"frame {int(got.frame)}!={int(want.frame)}")
    if int(got.current) != int(want.current):
        mismatches.append(f"current {int(got.current)}!={int(want.current)}")
    if int(got.autocontinue) != int(want.autocontinue):
        mismatches.append(
            f"autocontinue {int(got.autocontinue)}!={int(want.autocontinue)}"
        )
    if got.get_type() == "MISSION_ITEM_INT":
        got_x = int(got.x)
        got_y = int(got.y)
    else:
        got_x = int(round(float(got.x) * 1.0e7))
        got_y = int(round(float(got.y) * 1.0e7))
    if got_x != int(want.x):
        mismatches.append(f"x {got_x}!={int(want.x)}")
    if got_y != int(want.y):
        mismatches.append(f"y {got_y}!={int(want.y)}")
    if abs(float(got.z) - float(want.z)) > 0.01:
        mismatches.append(f"z {float(got.z):.3f}!={float(want.z):.3f}")
    for index in (1, 2, 3, 4):
        got_param = float(getattr(got, f"param{index}"))
        want_param = float(getattr(want, f"param{index}"))
        if abs(got_param - want_param) > 1e-3:
            mismatches.append(f"param{index} {got_param:.3f}!={want_param:.3f}")
    return mismatches


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
