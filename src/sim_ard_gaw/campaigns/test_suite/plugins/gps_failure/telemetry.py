"""Live telemetry normalization for the gps_failure monitor.

The helpers are deliberately connection-agnostic and fake-testable. They do not
open a MAVLink connection; callers pass an explicit connection/message object.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from . import defaults
from .source_contract import (
    EKF_GPS_GLITCHING,
    pos_test_ratio_from_live_pos_horiz_variance,
)


MAV_CMD_SET_MESSAGE_INTERVAL = 511
MAV_RESULT_ACCEPTED = 0
MESSAGE_IDS = {
    "HEARTBEAT": 0,
    "GPS_RAW_INT": 24,
    "ATTITUDE": 30,
    "GLOBAL_POSITION_INT": 33,
    "MISSION_CURRENT": 42,
    "SIMSTATE": 164,
    "EKF_STATUS_REPORT": 193,
    "STATUSTEXT": 253,
}
SAFETY_ARMED = 128
ARDUPLANE_AUTO_MODE = 10


@dataclass(frozen=True)
class TelemetryRateRequest:
    message_type: str
    message_id: int
    interval_us: int
    ok: bool
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "message_type": self.message_type,
            "message_id": self.message_id,
            "interval_us": self.interval_us,
            "ok": self.ok,
            "error": self.error,
        }


def request_telemetry_rates(
    connection: Any,
    *,
    rate_hz: float = 5.0,
    ack_timeout_s: float = 1.0,
    message_types: tuple[str, ...] = defaults.TELEMETRY_MESSAGE_TYPES,
) -> list[TelemetryRateRequest]:
    if rate_hz <= 0:
        raise ValueError("rate_hz must be > 0")
    if ack_timeout_s <= 0:
        raise ValueError("ack_timeout_s must be > 0")
    interval_us = int(1_000_000 / rate_hz)
    mav = getattr(connection, "mav", None)
    sender = getattr(mav, "command_long_send", None)
    if not callable(sender):
        raise ValueError("connection.mav.command_long_send is required")
    receiver = getattr(connection, "recv_match", None)
    if not callable(receiver):
        raise ValueError("connection.recv_match is required for COMMAND_ACK")

    results: list[TelemetryRateRequest] = []
    target_system = int(getattr(connection, "target_system", 1))
    target_component = int(getattr(connection, "target_component", 1))
    for message_type in message_types:
        message_id = MESSAGE_IDS[message_type]
        try:
            sender(
                target_system,
                target_component,
                MAV_CMD_SET_MESSAGE_INTERVAL,
                0,
                message_id,
                interval_us,
                0,
                0,
                0,
                0,
                0,
            )
            ack = receiver(type=["COMMAND_ACK"], blocking=True, timeout=ack_timeout_s)
            ack_error = _command_ack_error(ack)
            results.append(
                TelemetryRateRequest(
                    message_type,
                    message_id,
                    interval_us,
                    ack_error is None,
                    ack_error,
                )
            )
        except Exception as exc:
            results.append(
                TelemetryRateRequest(message_type, message_id, interval_us, False, str(exc))
            )
    return results


def normalize_message(msg: Any, *, arrival_monotonic_s: float) -> dict[str, Any]:
    arrival = _finite_value(arrival_monotonic_s)
    if arrival is None:
        raise ValueError("arrival_monotonic_s must be finite")
    msg_type = _message_type(msg)
    base: dict[str, Any] = {
        "type": msg_type,
        "arrival_monotonic_s": arrival,
        "time_boot_ms": _optional_finite_attr(msg, "time_boot_ms"),
        "time_usec": _optional_finite_attr(msg, "time_usec"),
    }

    if msg_type == "HEARTBEAT":
        custom_mode = _optional_int_attr(msg, "custom_mode")
        base.update(
            {
                "mode": _mode_name(custom_mode),
                "custom_mode": custom_mode,
                "base_mode": _optional_int_attr(msg, "base_mode"),
                "armed": _armed_flag(getattr(msg, "base_mode", 0)),
            }
        )
    elif msg_type == "MISSION_CURRENT":
        base["seq"] = _optional_int_attr(msg, "seq")
    elif msg_type == "STATUSTEXT":
        text = getattr(msg, "text", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace").rstrip("\x00")
        base.update({"severity": _optional_int_attr(msg, "severity"), "text": str(text)})
    elif msg_type == "GLOBAL_POSITION_INT":
        base.update(
            {
                "lat_deg_e7": _optional_finite_attr(msg, "lat"),
                "lon_deg_e7": _optional_finite_attr(msg, "lon"),
                "relative_alt_mm": _optional_finite_attr(msg, "relative_alt"),
                "belief_position_source": "GLOBAL_POSITION_INT",
            }
        )
    elif msg_type == "SIMSTATE":
        base.update(
            {
                "lat_deg_e7": _optional_finite_attr(msg, "lat"),
                "lon_deg_e7": _optional_finite_attr(msg, "lng"),
                "truth_position_source": "SIMSTATE",
            }
        )
    elif msg_type == "ATTITUDE":
        base.update(
            {
                "roll_rad": _optional_finite_attr(msg, "roll"),
                "pitch_rad": _optional_finite_attr(msg, "pitch"),
                "yaw_rad": _optional_finite_attr(msg, "yaw"),
            }
        )
    elif msg_type == "EKF_STATUS_REPORT":
        variance = _optional_finite_attr(msg, "pos_horiz_variance")
        flags = _optional_int_attr(msg, "flags")
        if variance is None:
            base.update(
                {
                    "ok": False,
                    "error": "missing_or_malformed_pos_horiz_variance",
                    "pos_horiz_variance": None,
                    "pos_test_ratio": None,
                    "flags": flags,
                    "gps_glitching": None,
                }
            )
            return base
        if flags is None:
            base.update(
                {
                    "ok": False,
                    "error": "missing_or_malformed_ekf_flags",
                    "pos_horiz_variance": variance,
                    "pos_test_ratio": None,
                    "flags": None,
                    "gps_glitching": None,
                }
            )
            return base
        try:
            ratio = pos_test_ratio_from_live_pos_horiz_variance(variance)
        except ValueError as exc:
            base.update(
                {
                    "ok": False,
                    "error": str(exc),
                    "pos_horiz_variance": variance,
                    "pos_test_ratio": None,
                    "flags": flags,
                    "gps_glitching": None,
                }
            )
            return base
        base.update(
            {
                "ok": True,
                "pos_horiz_variance": variance,
                "pos_test_ratio": ratio,
                "flags": flags,
                "gps_glitching": bool(flags & EKF_GPS_GLITCHING),
            }
        )
    elif msg_type == "GPS_RAW_INT":
        base.update(
            {
                "fix_type": _optional_int_attr(msg, "fix_type"),
                "satellites_visible": _optional_int_attr(msg, "satellites_visible"),
            }
        )
    return base


def _message_type(msg: Any) -> str:
    get_type = getattr(msg, "get_type", None)
    if callable(get_type):
        return str(get_type())
    return str(getattr(msg, "_type", type(msg).__name__))


def _optional_finite_attr(msg: Any, name: str) -> float | None:
    return _finite_value(getattr(msg, name, None))


def _finite_value(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_int_attr(msg: Any, name: str) -> int | None:
    value = getattr(msg, name, None)
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    if not parsed.is_integer():
        return None
    return int(parsed)


def _armed_flag(base_mode: Any) -> bool | None:
    try:
        return bool(int(base_mode) & SAFETY_ARMED)
    except (TypeError, ValueError):
        return None


def _mode_name(custom_mode: Any) -> str | None:
    if custom_mode is None:
        return None
    try:
        mode_number = int(custom_mode)
    except (TypeError, ValueError):
        return str(custom_mode)
    if mode_number == ARDUPLANE_AUTO_MODE:
        return "AUTO"
    return str(mode_number)


def _command_ack_error(ack: Any) -> str | None:
    if ack is None:
        return "missing_command_ack"
    if _message_type(ack) != "COMMAND_ACK":
        return f"unexpected_ack_type:{_message_type(ack)}"
    command = _optional_int_attr(ack, "command")
    if command != MAV_CMD_SET_MESSAGE_INTERVAL:
        return f"unexpected_ack_command:{command}"
    result = _optional_int_attr(ack, "result")
    if result != MAV_RESULT_ACCEPTED:
        return f"command_ack_rejected:{result}"
    return None
