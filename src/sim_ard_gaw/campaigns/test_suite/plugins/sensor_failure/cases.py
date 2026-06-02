"""Declarative GPS fault cases for the sensor_failure plugin.

Phase 4 scope: GPS only, exactly two case types (Ahmed's decision). The
structure is deliberately a list of `GpsFaultCase` records so the plugin can be
extended to the other 021 families (imu/compass/airspeed/baro/battery/
rangefinder) by adding records — NO framework or orchestration edits. Those
families are intentionally NOT built now; see the plugin README/report.

Each case carries:
- the SIM_GPS1_* parameter overrides to inject mid-flight (verified spellings),
- the verdict mode (`hard_denial` vs `degradation`) the analyzer/verdict use,
- a human-readable fault description for provenance.

The actual param values for the glitch case are computed from the verified
metres->degrees conversion in defaults, not hard-coded, so the 50 m intent is
explicit and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import defaults


@dataclass(frozen=True)
class GpsFaultCase:
    case_id: str
    sensor: str
    mode: str
    verdict_mode: str  # "hard_denial" | "degradation"
    description: str
    # SIM_* params to set at the injection waypoint (name -> value).
    inject: dict[str, float] = field(default_factory=dict)
    # SIM_* params that define the healthy baseline to (re)assert pre-arm.
    baseline: dict[str, float] = field(default_factory=dict)
    severity: str = "high"
    tags: tuple[str, ...] = ()


def _glitch_inject() -> dict[str, float]:
    lat_deg, lon_deg, alt_m = defaults.gps_glitch_offsets_deg_m(defaults.GLITCH_OFFSET_M)
    return {
        defaults.SIM_GPS1_GLTCH_X: lat_deg,
        defaults.SIM_GPS1_GLTCH_Y: lon_deg,
        defaults.SIM_GPS1_GLTCH_Z: alt_m,
    }


# The GPS cases. Order is the suite's natural order. `gps_baseline` runs the
# identical mission with NO fault, capturing the control envelope the fault
# cases are characterized AGAINST. Putting it first means a sequential campaign
# establishes the baseline before the fault cases.
GPS_CASES: tuple[GpsFaultCase, ...] = (
    GpsFaultCase(
        case_id="gps_baseline",
        sensor="gps",
        mode="baseline",
        verdict_mode="baseline",
        description=(
            "Control run: identical mission, NO GPS fault injected. Captures the "
            "normal attitude/altitude/position-tracking envelope through the same "
            "post-trigger observation window, so the fault cases can be reported "
            "as deviations from real measured behavior rather than guessed bounds."
        ),
        inject={},          # no fault -> baseline no-op at the trigger waypoint
        baseline={
            defaults.SIM_GPS1_ENABLE: 1.0,
            defaults.SIM_GPS1_GLTCH_X: 0.0,
            defaults.SIM_GPS1_GLTCH_Y: 0.0,
            defaults.SIM_GPS1_GLTCH_Z: 0.0,
        },
        tags=("gps", "baseline", "control"),
    ),
    GpsFaultCase(
        case_id="gps_disable",
        sensor="gps",
        mode="disable",
        verdict_mode="hard_denial",
        description=(
            "Hard GPS denial: set SIM_GPS1_ENABLE=0 mid-square. PASS = vehicle "
            "safely handles loss (expected failsafe such as RTL/loiter/glide per "
            "FS_LONG_ACTN, or bounded dead-reckoning keeping attitude/altitude "
            "in band). Mission completion is NOT required."
        ),
        inject={defaults.SIM_GPS1_ENABLE: 0.0},
        baseline={defaults.SIM_GPS1_ENABLE: 1.0},
        tags=("gps", "denial", "failsafe"),
    ),
    GpsFaultCase(
        case_id="gps_glitch_50m",
        sensor="gps",
        mode="glitch",
        verdict_mode="degradation",
        description=(
            "~50 m position glitch: set SIM_GPS1_GLTCH_{X,Y} (deg) mid-square. "
            "PASS = EKF/position estimate stays bounded and the vehicle keeps "
            "flying acceptably (no excursion beyond tolerance, attitude/altitude "
            "in band)."
        ),
        inject=_glitch_inject(),
        baseline={
            defaults.SIM_GPS1_GLTCH_X: 0.0,
            defaults.SIM_GPS1_GLTCH_Y: 0.0,
            defaults.SIM_GPS1_GLTCH_Z: 0.0,
        },
        tags=("gps", "glitch", "degradation"),
    ),
)

CASES_BY_ID: dict[str, GpsFaultCase] = {case.case_id: case for case in GPS_CASES}
ALL_CASE_IDS: tuple[str, ...] = tuple(case.case_id for case in GPS_CASES)


def select_cases(case_ids: list[str] | tuple[str, ...] | None) -> list[GpsFaultCase]:
    """Return the selected cases in suite order. None selects all."""
    if not case_ids:
        return list(GPS_CASES)
    unknown = [cid for cid in case_ids if cid not in CASES_BY_ID]
    if unknown:
        raise ValueError(
            f"Unknown sensor_failure case_id(s): {unknown}. "
            f"Known: {list(ALL_CASE_IDS)}"
        )
    wanted = set(case_ids)
    return [case for case in GPS_CASES if case.case_id in wanted]


def case_inject_as_jsonable(case: GpsFaultCase) -> dict[str, Any]:
    """Provenance-friendly view of a case's intended fault."""
    return {
        "case_id": case.case_id,
        "sensor": case.sensor,
        "mode": case.mode,
        "verdict_mode": case.verdict_mode,
        "severity": case.severity,
        "description": case.description,
        "inject_params": dict(case.inject),
        "baseline_params": dict(case.baseline),
    }
