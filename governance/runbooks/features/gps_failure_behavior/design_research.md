# GPS Failure Behavior — Design Research Report

Status: research / pre-implementation. Not accepted evidence.

Date: 2026-07-06

Author role: design review (no live SITL run performed for this report).

## Purpose

This report grounds the GPS failure behavior lane's design in primary sources:
the current local ArduPilot SITL GPS fault model and the EKF3 position-fusion
gate. It feeds the ADR drafts in `design_adrs.md` in this directory.

It is deliberately skeptical. Where a value depends on runtime state (e.g. the
exact drift rate at which the knee lands) it is named as a must-measure item for
Phase 2 smoke, not guessed. Source is authoritative for design because the build
under test *is* the source.

## Scope And Non-Goals

- Behavior characterization of degraded/corrupted simulated GPS on the Mini
  Talon / ArduPlane SITL + Gazebo stack.
- Not a safety certification, not a recovery-controller design.
- No live SITL campaign run for this report. No config values changed.

## Most Important Finding First: The Actual Signal Path

Unlike airspeed (which corrupts a control *input*), a GPS fault corrupts the
vehicle's *position measurement*, which the EKF then actively accepts or rejects
through its own innovation-consistency gate. The fault does not directly move
the aircraft — it moves a measurement that the filter chooses whether to
believe. That gate is the whole experiment.

The chain for the default lane stack (`AHRS_EKF_TYPE 3`, EKF3, GPS position
source) is:

```text
SITL FDM true position (lat/lon/alt)
  -> SIM_GPS1_* fault model            (SIM_GPS.cpp: glitch added to lat/lon/alt,
                                        or jam/enable/numsats corruption)
  -> simulated GPS fix delivered to    (AP_GPS backend)
  -> EKF3 position fusion gate         (AP_NavEKF3_PosVelFusion.cpp:
                                        posTestRatio vs 1.0)
  -> fused (belief moves) OR rejected  (below gate => fused; above => not fused,
                                        only a reset can move belief)
  -> ArduPlane nav / TECS / failsafe
```

Primary source lines (verified 2026-07-06 against the local tree):

- `src/ardupilot/libraries/SITL/SIM_GPS.cpp` — the `GPSParms` table
  (`SIM_GPS1_*`) and the fault application.
- `src/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_PosVelFusion.cpp` (~lines
  816–871) — `posTestRatio`, the gate test, and the glitch-reset path.
- `src/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_Control.cpp` (~lines 391–487) —
  `posTimeout` transitions.
- `src/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_core.h` (~line 1072) —
  `posTimeout` semantics.

### What SIM_GPS.cpp actually does (verbatim)

Glitch (the `slow_drift` and `step_glitch` knob) is added directly to the fix,
in degrees for lat/lon and metres for alt:

```c
// SIM_GPS.cpp ~548
Vector3f glitch_offsets = params.glitch;   // SIM_GPS1_GLTCH_{X,Y,Z}
d.latitude  += glitch_offsets.x;           // DEGREES
d.longitude += glitch_offsets.y;           // DEGREES
d.altitude  += glitch_offsets.z;           // METRES
```

This is why `slow_drift` and `step_glitch` share one knob: both write
`GLTCH_{X,Y}`; the only difference is whether the plugin *ramps* the offset
(drift) or *steps* it once (glitch). Onset rate is the single independent
variable between them.

Jamming (`SIM_GPS1_JAM=1`) is a stochastic, self-parametrizing routine — it has
no severity dial:

```c
// SIM_GPS.cpp ~266  simulate_jamming()
// blackout for 1000 + (random16 % 5000) ms, then chaotic sats/position churn
```

This confirms the design decision to treat jamming as binary and characterize
its spread through duration and repeats, not a severity sweep. It is also the
"self-betraying" fault: the churn is incoherent, so the EKF sees wildly
inconsistent innovations rather than a clean, believable lie.

## The Knee: EKF3 Position-Innovation Gate (verbatim mechanism)

The knee is defined by ArduPilot's own gate, not a threshold we invented. From
`AP_NavEKF3_PosVelFusion.cpp`:

```c
// ~820
ftype maxPosInnov2 = sq(MAX(0.01 * (ftype)frontend->_gpsPosInnovGate, 1.0))
                     * (varInnovVelPos[3] + varInnovVelPos[4]);
posTestRatio = (sq(innovVelPos[3]) + sq(innovVelPos[4])) / maxPosInnov2;

if (posTestRatio < 1.0f || (PV_AidingMode == AID_NONE)) {
    posCheckPassed = true;           // FUSE the fix -> belief moves
    ...
}
```

Verified facts this establishes:

1. **The knee is `posTestRatio` crossing `1.0`.** Below `1.0` the fix passes the
   consistency check and is fused; the belief moves toward the (drifting) fix.
2. **`EK3_POS_I_GATE` (`_gpsPosInnovGate`) is in centi-sigma.** The `0.01 *`
   multiplier means the parameter is 100× the gate's sigma width. This is
   exactly why the overlay must pin it: it sets where `1.0` lands in metres of
   innovation, and therefore where the knee lands in m/s of drift.
3. **`posTestRatio` scales with innovation² / variance.** A *slow* drift keeps
   innovation small each step (the fix barely disagrees with the prediction), so
   `posTestRatio` stays below `1.0` — fused, silent. A *fast* drift or a large
   step makes innovation large, so `posTestRatio` exceeds `1.0` — rejected.

### The subtlety that refines "silent_drift"

When the check *fails* (`posTestRatio >= 1.0`), the fix is **not fused at all**
(barring `posTimeout`/`badIMUdata`). The belief does not drift gradually above
the gate — it stays put until the *reset* path fires:

```c
// ~844
const bool posVarianceIsTooLarge =
    (frontend->_gpsGlitchRadiusMax > 0) &&
    (P[8][8] + P[7][7]) > sq(ftype(frontend->_gpsGlitchRadiusMax));
if ((posTimeout || posVarianceIsTooLarge) && ...) {
    ResetPosition(resetDataSource::DEFAULT);   // snap belief onto the GPS
    ...
    posTestRatio = 0.0f;
}
```

So the behavior ladder maps cleanly onto the source:

- **`silent_drift`** = a drift slow enough that `posTestRatio < 1.0` throughout →
  fused every step → belief walks off truth continuously, no alarm. This is the
  dangerous regime and it lives *below* the gate.
- **`detected_rejected`** = `posTestRatio >= 1.0` sustained → fix rejected, not
  fused, variance climbs.
- **`reset_captured`** = variance exceeds `EK3_GLITCH_RAD²` (or `posTimeout`) →
  `ResetPosition` snaps the belief onto the faulted GPS in one discontinuity.

This is why the belief moves in exactly two ways — **gradual fusion below the
gate, or a discontinuous reset above it** — and never gradually above the gate.
The `reset_captured` band is a discrete, observable event (`ResetPosition` in the
`NKF*` log), which makes it a clean classifier.

### Accepted is not captured

A fix can pass the gate (`posTestRatio < 1.0`) yet barely move the belief,
because the Kalman gain is small when the state variance is low. A single
admitted drifted fix nudges the belief a little; only *sustained, cumulative*
drift walks it off. The mechanism tier (`posTestRatio`) tells you the fix was
*admitted*; only the behavior tier (truth-vs-belief gap) tells you the belief
was *captured*. This is the core reason the lane is two-tier and the reason the
truth-vs-belief gap is a mandatory logged field: it is the only signal that
reveals a lie the filter itself believes is fine.

## Must-Measure Items (Phase 2 smoke)

These depend on runtime state or the pinned overlay and are NOT guessed here:

- Live `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`, `FS_EKF_THRESH`, `EK3_GPS_CHECK`
  readback (the overlay sets them; smoke confirms them).
- The empirical knee: the drift rate at which `posTestRatio` crosses `1.0` for
  the pinned gate. Design brackets it at `0.2–8.0 m/s`; the exact value is a
  Phase-2 result.
- The single-fix rejection threshold in the magnitude domain (the `step_glitch`
  ladder brackets it at `10–500 m`).
- Realized straight-leg duration of the GPS mission (drift needs time).
- Whether v1 flies a thin slice or the full sweep first.

## Excluded Knobs (full reasoning)

Every `SIM_GPS1_*` knob is documented. The four headline faults are `GLTCH`
(drift + step), `ENABLE` (denial), `JAM` (jamming). The rest are excluded as
headline experiments, each for a mechanism reason:

| Knob | What it really does | Why NOT a headline experiment |
| --- | --- | --- |
| `NUMSATS` | sets reported satellite count; does not drop `have_lock` | Only a pre-arm readiness gate (`< 6` fails a check). Position stays truthful mid-flight, so it never trips the innovation gate or reset path. A sweep would only measure "when does arming get blocked." No mid-flight behavioral effect. |
| `VERR` | corrupts velocity, but the model auto-reports a matching `speed_acc` | Self-betrays — it hands the EKF a large speed-accuracy alongside the error, so the fix is down-weighted. Honest degradation, not deception. Self-limiting. Possible future modifier. |
| `LAG_MS` | delays the fix (staleness) | The EKF is built to compensate lag (fuses at the measurement timestamp). Modest lag is absorbed; huge lag is just a weaker `step_glitch`. Redundant and weaker. |
| `ACC` | changes claimed accuracy only; position stays truth | Pure self-report; moves nothing standalone. Its value is as a *modifier* that resizes the effective gate. Excluded standalone; the natural first modifier if layering. |
| `NOISE` | altitude-only sine (~12.6 s period) | Altitude-only; baro dominates the height estimate. Near-inert. Negative control only. |
| `DRFTALT` | altitude-only slow sine (~5 min period) | Altitude-only; baro-dominated. Negative control only. |

Layering a modifier onto a headline fault (e.g. `slow_drift` with degraded
`ACC` to resize the gate) is documented future work, not this lane.

## Why GPS Drift Has Memory (design consequence)

An accepted drifted fix updates the EKF *state* (the belief), and that state
carries forward. Zeroing `GLTCH` afterward stops *new* corruption but does not
un-corrupt the belief that already moved. Therefore:

- Each drift rate needs a clean flight from truth — one rate per flight. A later
  window in the same flight would start from an already-wrong belief and its
  measurement would be contaminated.
- The airspeed-style in-flight pulse-with-reset schedule is dropped for GPS,
  because the "reset" (zeroing the param) is not a clean reset of the belief.
- A second, separate instrument — one continuous ramp with no reset — is kept
  deliberately to measure *accumulation/endurance* (how bad it gets as drift
  piles up), which is a different question from the clean per-rate knee.

## Assumptions

- Default stack: EKF3, GPS as position source, the pinned `plane_gps.parm`
  overlay (see `plan.md` Default Stack and the Overlay ADR in `design_adrs.md`).
- The lane characterizes behavior; it does not implement recovery.
- Source is authoritative for Phase 0 design; live verification is Phase 2.
