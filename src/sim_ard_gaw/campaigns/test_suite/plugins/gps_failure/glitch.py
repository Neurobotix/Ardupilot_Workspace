"""Pure GLTCH conversion helpers for GPS fault recipes."""
from __future__ import annotations

import math
from typing import Any


METRES_PER_LATITUDE_DEGREE = 111_320.0
MIN_SAFE_LONGITUDE_COSINE = 1.0e-6

GLITCH_FRAME = "local tangent frame: +east metres, +north metres"
GLITCH_SIGN_CONVENTION = (
    "positive north -> positive SIM_GPS1_GLTCH_X latitude degrees; "
    "positive east -> positive SIM_GPS1_GLTCH_Y longitude degrees"
)
GLITCH_CONVERSION_RECIPE = (
    "SIM_GPS1_GLTCH_X = north_m / 111320; "
    "SIM_GPS1_GLTCH_Y = east_m / (111320 * cos(latitude_deg)); "
    "SIM_GPS1_GLTCH_Z remains 0.0 and is not a v1 fault axis"
)
EXAMPLE_REFERENCE_LATITUDE_DEG = 0.0


def meters_east_north_to_glitch_degrees(
    east_m: float,
    north_m: float,
    latitude_deg: float,
) -> dict[str, float]:
    """Convert local metre offsets to SITL SIM_GPS1_GLTCH degree payloads."""
    east = _finite_float("east_m", east_m)
    north = _finite_float("north_m", north_m)
    cos_latitude = _safe_cos_latitude(latitude_deg)
    return {
        "SIM_GPS1_GLTCH_X": north / METRES_PER_LATITUDE_DEGREE,
        "SIM_GPS1_GLTCH_Y": east / (METRES_PER_LATITUDE_DEGREE * cos_latitude),
        "SIM_GPS1_GLTCH_Z": 0.0,
    }


def step_glitch_payload(
    magnitude_m: float,
    latitude_deg: float,
    axis: str = "east",
) -> dict[str, float]:
    """Resolve a fixed metre-domain GPS step glitch to GLTCH degrees."""
    magnitude = _finite_float("magnitude_m", magnitude_m)
    if magnitude < 0:
        raise ValueError("magnitude_m must be >= 0")
    east_m, north_m = _axis_offset(magnitude, axis)
    return meters_east_north_to_glitch_degrees(east_m, north_m, latitude_deg)


def slow_drift_payload(
    rate_mps: float,
    elapsed_s: float,
    latitude_deg: float,
    axis: str = "east",
) -> dict[str, float]:
    """Resolve a ramped GPS drift at elapsed time to GLTCH degrees."""
    rate = _finite_float("rate_mps", rate_mps)
    elapsed = _finite_float("elapsed_s", elapsed_s)
    if rate < 0:
        raise ValueError("rate_mps must be >= 0")
    if elapsed < 0:
        raise ValueError("elapsed_s must be >= 0")
    return step_glitch_payload(rate * elapsed, latitude_deg, axis=axis)


def glitch_recipe_metadata(
    *,
    requires_live_resolution: bool,
    example_reference_latitude_deg: float = EXAMPLE_REFERENCE_LATITUDE_DEG,
) -> dict[str, Any]:
    """Shared metadata that documents the GLTCH frame/unit contract."""
    return {
        "frame": GLITCH_FRAME,
        "sign_convention": GLITCH_SIGN_CONVENTION,
        "conversion": GLITCH_CONVERSION_RECIPE,
        "example_reference_latitude_deg": _finite_float(
            "example_reference_latitude_deg",
            example_reference_latitude_deg,
        ),
        "requires_live_resolution": bool(requires_live_resolution),
        "altitude_fault_axis": False,
    }


def preview_payload_from_recipe(
    recipe: dict[str, Any] | None,
    *,
    latitude_deg: float,
    elapsed_s: float,
) -> dict[str, Any] | None:
    """Resolve a dry-run payload preview for supported GLTCH recipes."""
    latitude = _finite_float("latitude_deg", latitude_deg)
    elapsed = _finite_float("elapsed_s", elapsed_s)
    if elapsed < 0:
        raise ValueError("elapsed_s must be >= 0")
    if not recipe:
        return None
    fault_type = recipe.get("fault_type")
    axis = str(recipe.get("axis", "east"))
    if fault_type == "step_glitch":
        payload = step_glitch_payload(
            float(recipe["offset_magnitude_m"]),
            latitude,
            axis=axis,
        )
        preview = {
            "latitude_deg": latitude,
            "elapsed_s": elapsed,
            # The injected payload is a fixed step: elapsed time never changes the
            # magnitude. For a bounded glitch elapsed time still decides whether
            # the offset is present at all, which the hold fields below express.
            "elapsed_affects_payload": False,
            "payload": payload,
            "not_live_payload": True,
        }
        hold_duration_s = recipe.get("glitch_hold_duration_s")
        if hold_duration_s is None:
            preview["bounded"] = False
            return preview
        hold_s = _finite_float("glitch_hold_duration_s", hold_duration_s)
        if hold_s <= 0:
            raise ValueError("glitch_hold_duration_s must be > 0")
        preview.update(
            {
                "bounded": True,
                "glitch_hold_duration_s": hold_s,
                "offset_active_at_elapsed": elapsed < hold_s,
                "restore_payload": {name: 0.0 for name in payload},
            }
        )
        return preview
    if fault_type == "slow_drift" and "drift_rate_mps" in recipe:
        drift_rate = _finite_float("drift_rate_mps", recipe["drift_rate_mps"])
        return {
            "latitude_deg": latitude,
            "elapsed_s": elapsed,
            "elapsed_affects_payload": True,
            "offset_m": drift_rate * elapsed,
            "payload": slow_drift_payload(
                drift_rate,
                elapsed,
                latitude,
                axis=axis,
            ),
            "not_live_payload": True,
        }
    return None


def _safe_cos_latitude(latitude_deg: float) -> float:
    latitude = _finite_float("latitude_deg", latitude_deg)
    if latitude < -90.0 or latitude > 90.0:
        raise ValueError("latitude_deg must be within [-90, 90]")
    cos_latitude = math.cos(math.radians(latitude))
    if abs(cos_latitude) < MIN_SAFE_LONGITUDE_COSINE:
        raise ValueError("latitude_deg is too close to a pole for longitude conversion")
    return cos_latitude


def _finite_float(name: str, value: object) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be finite") from None
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _axis_offset(magnitude_m: float, axis: str) -> tuple[float, float]:
    magnitude = _finite_float("magnitude_m", magnitude_m)
    axis_name = axis.lower()
    if axis_name == "east":
        return magnitude, 0.0
    if axis_name == "west":
        return -magnitude, 0.0
    if axis_name == "north":
        return 0.0, magnitude
    if axis_name == "south":
        return 0.0, -magnitude
    raise ValueError("axis must be one of: east, west, north, south")
