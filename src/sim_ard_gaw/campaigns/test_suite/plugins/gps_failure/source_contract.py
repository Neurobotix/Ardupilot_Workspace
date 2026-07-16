"""Source-verified EKF/GPS contract checks for gps_failure.

This module intentionally models exact proof and validated proxy proof
separately. The pinned source exposes ``PV_AidingMode == AID_ABSOLUTE``
internally, but not as a direct MAVLink/BIN field. Phase 2 therefore requires a
validated proxy: live/source parameters selecting GPS horizontal aiding plus the
EKF absolute-horizontal-position flag and not constant-position mode. Mechanism
classification fails closed when that proxy is absent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping

from . import defaults


EKF_POS_HORIZ_ABS = 1 << 4
EKF_PRED_POS_HORIZ_ABS = 1 << 7
EKF_CONST_POS_MODE = 1 << 6
EKF_GPS_GLITCHING = 1 << 15

EXPECTED_SOURCE_READBACKS = {
    "EK3_SRC1_POSXY": 3,
    "EK3_SRC1_VELXY": 3,
    "EK3_SRC1_POSZ": 1,
    "EK3_SRC1_VELZ": 3,
    "EK3_SRC1_YAW": 1,
}
EXPECTED_KNEE_READBACKS = {
    "EK3_POS_I_GATE": 500.0,
    "EK3_GLITCH_RAD": 25.0,
    "FS_EKF_THRESH": 0.8,
    "EK3_GPS_CHECK": 31.0,
}


@dataclass(frozen=True)
class SourceContract:
    ok: bool
    validated_proxy: bool
    exact_aiding_proof: bool
    reasons: list[str] = field(default_factory=list)
    readbacks: dict[str, float] = field(default_factory=dict)
    estimator_flags: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "validated_proxy": self.validated_proxy,
            "exact_aiding_proof": self.exact_aiding_proof,
            "reasons": list(self.reasons),
            "readbacks": dict(self.readbacks),
            "estimator_flags": self.estimator_flags,
            "source": {
                "absolute_aiding": (
                    "PV_AidingMode == AID_ABSOLUTE is internal; live Phase 2 "
                    "uses EK3_SRC1_POSXY/VELXY GPS plus EKF absolute-position "
                    "status flags as a named proxy"
                ),
                "glitch_radius": "EK3_GLITCH_RAD must be > 0",
                "primary_core": "BIN XKF4.PI is frontend->getPrimaryCoreIndex()",
                "belief_position": "BIN POS Lat/Lng is AP_AHRS::get_location() canonical belief",
            },
        }


def required_live_readback_names(
    injected_or_restored: Mapping[str, float] | None = None,
) -> tuple[str, ...]:
    names = set(defaults.LIVE_READBACK_PARAMS)
    names.update(injected_or_restored or {})
    return tuple(sorted(names))


def validate_source_contract(
    readbacks: Mapping[str, object],
    *,
    estimator_flags: int | None,
) -> SourceContract:
    parsed: dict[str, float] = {}
    reasons: list[str] = []

    for name in defaults.KNEE_READBACK_PARAMS + defaults.SOURCE_CONTRACT_PARAMS:
        if name not in readbacks:
            reasons.append(f"missing_readback:{name}")
            continue
        try:
            value = _finite_float(name, readbacks[name])
        except (TypeError, ValueError):
            reasons.append(f"non_finite_readback:{name}")
            continue
        parsed[name] = value

    if parsed.get("EK3_GLITCH_RAD", 0.0) <= 0.0:
        reasons.append("ek3_glitch_rad_not_positive")
    for name, expected in EXPECTED_KNEE_READBACKS.items():
        value = parsed.get(name)
        if value is not None and not math.isclose(
            value,
            expected,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            reasons.append(f"readback_mismatch:{name}")
    for name, expected in EXPECTED_SOURCE_READBACKS.items():
        value = parsed.get(name)
        reason_name = name.lower()
        if not _is_integer_value(value):
            reasons.append(f"{reason_name}_not_integer")
        elif value is not None and int(value) != expected:
            reasons.append(f"{reason_name}_unexpected_source")

    if estimator_flags is None:
        reasons.append("missing_estimator_flags")
    else:
        if estimator_flags & EKF_CONST_POS_MODE:
            reasons.append("ekf_const_pos_mode")
        if not estimator_flags & EKF_POS_HORIZ_ABS:
            reasons.append("ekf_pos_horiz_abs_flag_missing")

    ok = not reasons
    return SourceContract(
        ok=ok,
        validated_proxy=ok,
        exact_aiding_proof=False,
        reasons=reasons,
        readbacks=parsed,
        estimator_flags=estimator_flags,
    )


def pos_test_ratio_from_live_pos_horiz_variance(value: object) -> float:
    parsed = _finite_float("pos_horiz_variance", value)
    if parsed < 0:
        raise ValueError("pos_horiz_variance must be non-negative")
    return parsed * parsed


def pos_test_ratio_from_xkf4_sp(value: object) -> float:
    parsed = _finite_float("XKF4.SP", value)
    if parsed < 0:
        raise ValueError("XKF4.SP must be non-negative")
    # pymavlink's DFReader has already applied the XKF4 format multiplier.
    # The decoded SP value is sqrt(posTestRatio), not the stored integer.
    return parsed * parsed


def _finite_float(name: str, value: object) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be finite") from None
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _is_integer_value(value: float | None) -> bool:
    return value is not None and value.is_integer()
