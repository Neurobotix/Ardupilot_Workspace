# ADR-0016: Two-Tier Airspeed Bias Lane And Mechanism Validation Gate

Status: Proposed

Date: 2026-06-16

Builds on the correction in ADR-0015. Supersedes the experimental design (not
the mechanism) of ADR-0012 and the P1 prediction of ADR-0014. Retains the
plateau metric of ADR-0014 with the corrections required below.

## Context

ADR-0015 established that the envelope matrix failed because it varied
`AIRSPEED_MAX`, a parameter that does not act on the believed-airspeed signal,
while the true limiter (`AHRS_WIND_MAX = 15`) was held constant. The failure was
not caught at run time because nothing verified that the varied parameter
actually moved the measured signal. This ADR redesigns the lane so that class of
error cannot recur silently.

All mechanism claims below are verified against the local ArduPilot source tree:

- `AHRS_WIND_MAX` clamps believed airspeed at both the sensor path
  (`libraries/AP_AHRS/AP_AHRS.cpp:985-992`) and the EKF synthetic path
  (`AP_AHRS.cpp:1057-1060`); both are gated on `_wind_max > 0`, so
  `AHRS_WIND_MAX = 0` disables the clamp on both paths.
- `AIRSPEED_MAX` bounds only the demanded/target airspeed
  (`ArduPlane/navigation.cpp:293`); it never clips the believed sensor value.
- `DO_CHANGE_SPEED` overrides `AIRSPEED_CRUISE` in AUTO:
  `mode_auto_target_airspeed_cm()` returns `new_airspeed_cm` before the
  `aparm.airspeed_cruise` fallthrough (`ArduPlane/navigation.cpp:135-140`).

## Decision

### 1. The lane is split into two tiers, distinguished only by `AHRS_WIND_MAX`

- **Tier 1 — Protected stack (`AHRS_WIND_MAX = 15`).** The real configured
  vehicle. Question: how does the protected stack behave under positive airspeed
  bias? Expected mechanism: believed airspeed is clamped to
  `ground_speed + AHRS_WIND_MAX` while the sensor stays in use and healthy
  (`ARSP.U = 1`) for slow ramps; abrupt pulses additionally trip the
  `ARSPD_WIND_GATE` health gate. The existing max18/max28/cruise17/scaled18_28
  runs are Tier 1 evidence (with the mission caveat in section 3).

- **Tier 2 — Diagnostic, clamp removed (`AHRS_WIND_MAX = 0`).** Question: what
  does TECS do if it receives the full lie? This is a mechanism probe, not a
  safety claim, and must be validated before it is trusted (section 4).

The two tiers are never mixed in a single acceptance claim.

### 2. A mechanism validation gate is mandatory before any run is interpreted

This is the central anti-regression contract. A run is `interpretable` only if
its BIN proves all of:

1. `AHRS_WIND_MAX` readback equals the intended tier value.
2. Believed airspeed `CTUN.As` behaved as the tier predicts:
   - Tier 1: clamped near `ground_speed + AHRS_WIND_MAX` once raw `ARSP` exceeds
     that bound;
   - Tier 2: tracks raw `ARSP.Airspeed` within tolerance (i.e. no clamp acted).
3. The commanded cruise was the intended one: either `DO_CHANGE_SPEED` is absent
   and the flown target equals `AIRSPEED_CRUISE`, or its override is explicitly
   intended and recorded.
4. Three signals are extracted and reported separately: raw `ARSP.Airspeed`,
   clamped/believed `CTUN.As`, and the `TECS` target.

A run failing any check is classed `mechanism_unverified` and is not an accepted
observation. The gate is implemented analysis-side
(`tests/unit/test_airspeed_mechanism_gate.py` plus the gate module) and runs on
the BIN of every cell before interpretation. The gate is built and unit-tested
before any new flight.

### 3. The mission's hardcoded `DO_CHANGE_SPEED = 15` is removed

A new ramp mission omits the `DO_CHANGE_SPEED` waypoint. With it absent,
`mode_auto_target_airspeed_cm()` falls through to `AIRSPEED_CRUISE`
(`navigation.cpp:140`), so the overlay's cruise value is what is actually flown.
This makes the cruise axis testable and removes a second place where cruise was
defined. The new mission differs from
`assets/missions/airspeed_failure_headwind_ramp_mission.waypoints` by exactly the
removal of the `DO_CHANGE_SPEED` item; the difference is diff-verified.

Consequence: removing `DO_CHANGE_SPEED` changes the commanded baseline for every
cell from 15 to `AIRSPEED_CRUISE` (14 at baseline). The existing Tier 1 runs
remain valid as old-mission protected-stack evidence, but are not strictly
comparable to new-mission cells. Any cross-cell comparison must use one mission
family. This is recorded, not hidden.

### 4. Tier 2 requires a mechanism-verification flight before any Tier 2 claim

Setting `AHRS_WIND_MAX = 0` removes the AHRS clamp, but `ARSPD_WIND_GATE = 5` and
the EKF airspeed innovation gate remain and may independently reject or bound the
lie. Therefore the first Tier 2 run is a verification flight whose only job is to
confirm, via the gate's check 2, that `CTUN.As` tracks raw `ARSP`. If it does
not, Tier 2 is incomplete and those gates become additional variables; the ADR is
revised before any "TECS fully believes the lie" claim is made.

### 5. `AHRS_WIND_MAX` is a first-class matrix axis

The retained envelope axes (`AIRSPEED_MAX`, `AIRSPEED_CRUISE`) are only
re-flown after the mechanism gate exists, on the fixed mission, and any
`AIRSPEED_MAX` cell is interpreted strictly as a demanded-airspeed-bound test,
never as a believed-airspeed-clamp test.

## Alternatives considered

- **Per-cruise mission files (keep `DO_CHANGE_SPEED`, one per cruise value).**
  Rejected: keeps a second definition of cruise and re-introduces the
  two-knobs-disagree failure mode. Removing the waypoint is the single-source fix.
- **Trust Tier 2 without a verification flight.** Rejected: it repeats the
  original mistake (assuming a mechanism instead of proving it on the BIN).
- **Discard the existing runs.** Rejected by ADR-0015: they are valid Tier 1
  evidence.

## Consequences

- New artifacts: this ADR, the mechanism-gate module + tests, the fixed ramp
  mission, and the `plane_airspeed_windmax0.parm` Tier 2 overlay. The
  fault-injection core is untouched.
- The gate makes "we varied a knob that did nothing" a hard, automated failure
  rather than a conclusion discovered weeks later.
- No safety, hardware, cross-airframe, or real-world claim is made or changed.
