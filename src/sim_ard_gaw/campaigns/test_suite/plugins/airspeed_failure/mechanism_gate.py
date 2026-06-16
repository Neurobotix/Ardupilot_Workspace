"""Mechanism validation gate for airspeed-bias runs (ADR-0016).

A run is interpretable only if its BIN log proves that the parameter we varied
actually moved the signal under test. This module is the automated guard that
would have caught the ADR-0015 failure, where AIRSPEED_MAX was varied while the
believed-airspeed limiter (AHRS_WIND_MAX) was held constant.

The gate is pure analysis over time series already present in the BIN:

- raw reported airspeed      ARSP.Airspeed
- believed/clamped airspeed  CTUN.As   (what TECS consumes)
- TECS speed demand/target   TECS.spdem
- GPS ground speed           GPS.Spd
- sensor in-use / health     ARSP.U / ARSP.H

It does NOT launch anything and does NOT depend on the live runner. The BIN
reader is injected, so the checks are unit-testable without a real log.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


# Tolerances are deliberate, fixed constants (no post-hoc tuning), per ADR-0016.
CLAMP_BAND_TOLERANCE_MPS = 2.0   # how close believed must sit to gnd+wind_max to count as "clamped"
TRACK_TOLERANCE_MPS = 3.0        # how close believed must track raw ARSP to count as "unclamped"
RAW_EXCESS_REQUIRED_MPS = 5.0    # raw must exceed the clamp bound by at least this for the test to be meaningful
WIND_MAX_READBACK_TOLERANCE = 1e-3
COMMANDED_CRUISE_TOLERANCE_MPS = 1.5  # TECS target vs intended cruise; gap beyond this implies DO_CHANGE_SPEED override


@dataclass
class GateCheck:
    name: str
    ok: bool
    detail: str


@dataclass
class GateResult:
    interpretable: bool
    tier: str
    checks: list[GateCheck] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "interpretable": self.interpretable,
            "tier": self.tier,
            "observation_quality_class": (
                "mechanism_verified" if self.interpretable else "mechanism_unverified"
            ),
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks
            ],
        }


@dataclass
class RunSignals:
    """Extracted, time-aligned scalars from one run's BIN, late-flight window.

    All *_late values are means over the final third of the post-settle flight,
    where the ramp bias is largest and the mechanism is clearest.
    """

    ahrs_wind_max: float | None
    raw_arsp_late: float | None
    believed_as_late: float | None
    gnd_speed_late: float | None
    tecs_target_late: float | None
    commanded_cruise_expected: float | None  # AIRSPEED_CRUISE intended for the cell
    arsp_use_all_one: bool
    raw_arsp_max: float | None


def evaluate(signals: RunSignals, *, tier: str, expected_wind_max: float) -> GateResult:
    """Apply the four ADR-0016 checks. `tier` is "protected" or "diagnostic"."""
    checks: list[GateCheck] = []

    # Check 1: AHRS_WIND_MAX readback matches the intended tier value.
    wm = signals.ahrs_wind_max
    c1 = wm is not None and abs(wm - expected_wind_max) <= WIND_MAX_READBACK_TOLERANCE
    checks.append(
        GateCheck(
            "ahrs_wind_max_readback",
            c1,
            f"read {wm}, expected {expected_wind_max}",
        )
    )

    # Check 2: believed airspeed behaved as the tier predicts.
    checks.append(_check_believed_behaviour(signals, tier))

    # Check 3: commanded cruise was the intended one (TECS target ~= expected cruise).
    checks.append(_check_commanded_cruise(signals))

    # Check 4: all three signals are present (raw / believed / target).
    present = all(
        v is not None
        for v in (signals.raw_arsp_late, signals.believed_as_late, signals.tecs_target_late)
    )
    checks.append(
        GateCheck(
            "three_signals_present",
            present,
            "raw ARSP, believed CTUN.As, and TECS target all extracted",
        )
    )

    return GateResult(
        interpretable=all(c.ok for c in checks),
        tier=tier,
        checks=checks,
    )


def _check_believed_behaviour(signals: RunSignals, tier: str) -> GateCheck:
    raw = signals.raw_arsp_late
    believed = signals.believed_as_late
    gnd = signals.gnd_speed_late
    wm = signals.ahrs_wind_max
    if raw is None or believed is None:
        return GateCheck("believed_behaviour", False, "missing raw or believed airspeed")

    if tier == "protected":
        if gnd is None or wm is None:
            return GateCheck("believed_behaviour", False, "missing gnd speed or wind_max")
        bound = gnd + wm
        # The test is only meaningful if raw actually pushed past the clamp bound.
        if (signals.raw_arsp_max or raw) < bound + RAW_EXCESS_REQUIRED_MPS:
            return GateCheck(
                "believed_behaviour",
                False,
                f"raw never exceeded clamp bound {bound:.1f} by {RAW_EXCESS_REQUIRED_MPS} m/s; mechanism not exercised",
            )
        ok = abs(believed - bound) <= CLAMP_BAND_TOLERANCE_MPS
        return GateCheck(
            "believed_behaviour",
            ok,
            f"protected: believed {believed:.1f} vs clamp bound gnd+wind_max {bound:.1f} (tol {CLAMP_BAND_TOLERANCE_MPS})",
        )

    if tier == "diagnostic":
        # Clamp off: believed should track raw, NOT sit at gnd+wind_max.
        ok = abs(believed - raw) <= TRACK_TOLERANCE_MPS
        return GateCheck(
            "believed_behaviour",
            ok,
            f"diagnostic: believed {believed:.1f} vs raw {raw:.1f} (tol {TRACK_TOLERANCE_MPS}); clamp must be inactive",
        )

    return GateCheck("believed_behaviour", False, f"unknown tier {tier!r}")


def _check_commanded_cruise(signals: RunSignals) -> GateCheck:
    target = signals.tecs_target_late
    expected = signals.commanded_cruise_expected
    if target is None or expected is None:
        return GateCheck(
            "commanded_cruise",
            False,
            "missing TECS target or expected cruise",
        )
    # The target sits near the commanded cruise (TECS adds small wind/landing
    # compensation, typically < ~1 m/s). A gap beyond COMMANDED_CRUISE_TOLERANCE
    # means the flown target did not follow the intended cruise -- the classic
    # symptom of a stale DO_CHANGE_SPEED overriding AIRSPEED_CRUISE (ADR-0015/16).
    # NOTE: this only discriminates intended cruise values that differ by more
    # than the tolerance; cells whose cruise values are closer than that cannot
    # be distinguished by TECS target alone and must be confirmed by mission
    # inspection (no DO_CHANGE_SPEED waypoint present).
    ok = abs(target - expected) <= COMMANDED_CRUISE_TOLERANCE_MPS
    return GateCheck(
        "commanded_cruise",
        ok,
        f"TECS target {target:.1f} vs expected cruise {expected:.1f} "
        f"(tol {COMMANDED_CRUISE_TOLERANCE_MPS}; gap beyond this implies "
        f"DO_CHANGE_SPEED overrode AIRSPEED_CRUISE)",
    )


# --- BIN extraction (separated so the checks above are testable without a log) ---

def extract_signals_from_bin(
    bin_path: str,
    *,
    expected_cruise: float | None,
    reader: Callable[[str], Any] | None = None,
) -> RunSignals:
    """Read a BIN and reduce to the late-flight scalars the gate needs.

    `reader` defaults to pymavlink; it is injectable for testing.
    """
    active_reader: Callable[[str], Any]
    if reader is None:
        from pymavlink import mavutil  # type: ignore[import-not-found]

        def _default_reader(path: str) -> Any:
            return mavutil.mavlink_connection(path)

        active_reader = _default_reader
    else:
        active_reader = reader

    conn = active_reader(bin_path)
    arsp: list[float] = []
    arsp_use: list[Any] = []
    ctun: list[float] = []
    gnd: list[float] = []
    tgt: list[float] = []
    wind_max: float | None = None

    while True:
        msg = conn.recv_match(blocking=False)
        if msg is None:
            break
        t = msg.get_type()
        d = msg.to_dict()
        if t == "ARSP":
            if d.get("Airspeed") is not None:
                arsp.append(d["Airspeed"])
            arsp_use.append(d.get("U"))
        elif t == "CTUN":
            if d.get("As") is not None:
                ctun.append(d["As"])
        elif t == "GPS":
            if d.get("Spd") is not None:
                gnd.append(d["Spd"])
        elif t == "TECS":
            if d.get("spdem") is not None:
                tgt.append(d["spdem"])
        elif t == "PARM" and d.get("Name") == "AHRS_WIND_MAX":
            wind_max = d.get("Value")

    return RunSignals(
        ahrs_wind_max=wind_max,
        raw_arsp_late=_late_mean(arsp),
        believed_as_late=_late_mean(ctun),
        gnd_speed_late=_late_mean(gnd),
        tecs_target_late=_late_mean(tgt),
        commanded_cruise_expected=expected_cruise,
        arsp_use_all_one=bool(arsp_use) and set(v for v in arsp_use if v is not None) == {1},
        raw_arsp_max=max(arsp) if arsp else None,
    )


def _late_mean(series: Sequence[float]) -> float | None:
    vals = [v for v in series if v is not None]
    if not vals:
        return None
    third = max(1, len(vals) // 3)
    tail = vals[-third:]
    return sum(tail) / len(tail)
