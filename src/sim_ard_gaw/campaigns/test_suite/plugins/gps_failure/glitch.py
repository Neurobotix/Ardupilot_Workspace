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
    cos_latitude = _safe_cos_latitude(latitude_deg)
    return {
        "SIM_GPS1_GLTCH_X": float(north_m) / METRES_PER_LATITUDE_DEGREE,
        "SIM_GPS1_GLTCH_Y": float(east_m)
        / (METRES_PER_LATITUDE_DEGREE * cos_latitude),
        "SIM_GPS1_GLTCH_Z": 0.0,
    }


def step_glitch_payload(
    magnitude_m: float,
    latitude_deg: float,
    axis: str = "east",
) -> dict[str, float]:
    """Resolve a fixed metre-domain GPS step glitch to GLTCH degrees."""
    if magnitude_m < 0:
        raise ValueError("magnitude_m must be >= 0")
    east_m, north_m = _axis_offset(float(magnitude_m), axis)
    return meters_east_north_to_glitch_degrees(east_m, north_m, latitude_deg)


def slow_drift_payload(
    rate_mps: float,
    elapsed_s: float,
    latitude_deg: float,
    axis: str = "east",
) -> dict[str, float]:
    """Resolve a ramped GPS drift at elapsed time to GLTCH degrees."""
    if rate_mps < 0:
        raise ValueError("rate_mps must be >= 0")
    if elapsed_s < 0:
        raise ValueError("elapsed_s must be >= 0")
    return step_glitch_payload(rate_mps * elapsed_s, latitude_deg, axis=axis)


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
        "example_reference_latitude_deg": float(example_reference_latitude_deg),
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
    if not recipe:
        return None
    fault_type = recipe.get("fault_type")
    axis = str(recipe.get("axis", "east"))
    if fault_type == "step_glitch":
        return {
            "latitude_deg": float(latitude_deg),
            "elapsed_s": float(elapsed_s),
            "elapsed_affects_payload": False,
            "payload": step_glitch_payload(
                float(recipe["offset_magnitude_m"]),
                latitude_deg,
                axis=axis,
            ),
            "not_live_payload": True,
        }
    if fault_type == "slow_drift" and "drift_rate_mps" in recipe:
        return {
            "latitude_deg": float(latitude_deg),
            "elapsed_s": float(elapsed_s),
            "elapsed_affects_payload": True,
            "offset_m": float(recipe["drift_rate_mps"]) * float(elapsed_s),
            "payload": slow_drift_payload(
                float(recipe["drift_rate_mps"]),
                elapsed_s,
                latitude_deg,
                axis=axis,
            ),
            "not_live_payload": True,
        }
    return None


def _safe_cos_latitude(latitude_deg: float) -> float:
    latitude = float(latitude_deg)
    if not math.isfinite(latitude):
        raise ValueError("latitude_deg must be finite")
    if latitude < -90.0 or latitude > 90.0:
        raise ValueError("latitude_deg must be within [-90, 90]")
    cos_latitude = math.cos(math.radians(latitude))
    if abs(cos_latitude) < MIN_SAFE_LONGITUDE_COSINE:
        raise ValueError("latitude_deg is too close to a pole for longitude conversion")
    return cos_latitude


def _axis_offset(magnitude_m: float, axis: str) -> tuple[float, float]:
    axis_name = axis.lower()
    if axis_name == "east":
        return magnitude_m, 0.0
    if axis_name == "west":
        return -magnitude_m, 0.0
    if axis_name == "north":
        return 0.0, magnitude_m
    if axis_name == "south":
        return 0.0, -magnitude_m
    raise ValueError("axis must be one of: east, west, north, south")
