"""Live telemetry normalization for the gps_failure monitor.

The helpers are deliberately connection-agnostic and fake-testable. They do not
open a MAVLink connection; callers pass an explicit connection/message object.
"""
from __future__ import annotations

import math
from typing import Any

from .source_contract import (
    EKF_GPS_GLITCHING,
    pos_test_ratio_from_live_pos_horiz_variance,
)


DELIVERY_REQUIRED_MESSAGE_TYPES = (
    "HEARTBEAT",
    "MISSION_CURRENT",
    "MISSION_ITEM_REACHED",
    "GLOBAL_POSITION_INT",
    "ATTITUDE",
    "SIMSTATE",
    "EKF_STATUS_REPORT",
    "GPS_RAW_INT",
)
EVENT_DRIVEN_OPTIONAL_MESSAGE_TYPES = ("STATUSTEXT",)
SAFETY_ARMED = 128
ARDUPLANE_AUTO_MODE = 10
ARDUPLANE_RTL_MODE = 11


def request_live_streams(
    connection: Any,
    *,
    rate_hz: int = 5,
) -> dict[str, Any]:
    """Request GPS-owned Plane streams; validate success from received data.

    STATUSTEXT is event-driven and therefore must never be treated as a stream
    request whose COMMAND_ACK is required for the monitor to proceed.
    """

    if isinstance(rate_hz, bool) or not isinstance(rate_hz, int) or rate_hz <= 0:
        raise ValueError("rate_hz must be a positive integer")
    from . import mavlink

    mavlink.request_live_streams(connection, rate_hz=rate_hz)
    return {
        "method": "MAV_DATA_STREAM",
        "implementation": "gps_failure.mavlink.request_live_streams",
        "rate_hz": rate_hz,
        "command_ack_required": False,
        "delivery_required_message_types": list(DELIVERY_REQUIRED_MESSAGE_TYPES),
        "event_driven_optional_message_types": list(
            EVENT_DRIVEN_OPTIONAL_MESSAGE_TYPES
        ),
        "delivery_validation": "observed monitor message types",
    }


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
    elif msg_type == "MISSION_ITEM_REACHED":
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
    elif msg_type == "NAV_CONTROLLER_OUTPUT":
        base["wp_dist_m"] = _optional_finite_attr(msg, "wp_dist")
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
    if mode_number == ARDUPLANE_RTL_MODE:
        return "RTL"
    return str(mode_number)
