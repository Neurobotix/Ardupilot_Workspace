"""Named wind profiles and direction-neutral track arithmetic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WindProfile:
    profile_id: str
    vector_enu_mps: tuple[float, float, float]
    measurement_track_unit_enu: tuple[float, float, float] = (1.0, 0.0, 0.0)

    @property
    def expected_arsp_minus_gps_mps(self) -> float:
        return -sum(
            wind * track
            for wind, track in zip(
                self.vector_enu_mps,
                self.measurement_track_unit_enu,
                strict=True,
            )
        )

    def as_dict(self) -> dict[str, Any]:
        x, y, z = self.vector_enu_mps
        tx, ty, tz = self.measurement_track_unit_enu
        return {
            "profile_id": self.profile_id,
            "vector_enu_mps": {"x": x, "y": y, "z": z},
            "measurement_track_unit_enu": {"x": tx, "y": ty, "z": tz},
            "expected_arsp_minus_gps_mps": self.expected_arsp_minus_gps_mps,
            "expected_arsp_minus_gps_formula": (
                "-(wind_vector_enu dot measurement_track_unit_enu)"
            ),
        }


HEADWIND_EASTBOUND = WindProfile(
    profile_id="headwind_eastbound",
    vector_enu_mps=(-5.0, 0.0, 0.0),
)
TAILWIND_EASTBOUND = WindProfile(
    profile_id="tailwind_eastbound",
    vector_enu_mps=(5.0, 0.0, 0.0),
)
WIND_PROFILES = {
    HEADWIND_EASTBOUND.profile_id: HEADWIND_EASTBOUND,
    TAILWIND_EASTBOUND.profile_id: TAILWIND_EASTBOUND,
}


def get_wind_profile(profile_id: str) -> WindProfile:
    try:
        return WIND_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(
            f"Unknown airspeed wind profile {profile_id!r}; "
            f"expected one of {sorted(WIND_PROFILES)}"
        ) from exc
