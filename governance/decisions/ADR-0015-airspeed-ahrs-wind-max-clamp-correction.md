# ADR-0015: AHRS_WIND_MAX Clamp Correction To The Envelope Matrix

Status: Accepted

Date: 2026-06-16

Corrects: ADR-0012, ADR-0014 (the `AIRSPEED_MAX` plateau hypothesis and the P1
prediction). Annotates: the "control-envelope saturation" finding in
`evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`.

This ADR does not delete any run. The max18/max28 ramp campaigns remain valid
data; only their original interpretation is corrected.

## Context

ADR-0012 proposed an envelope sensitivity matrix whose headline question (P1 in
ADR-0014) was: does the +200 ramp plateau-onset move when `AIRSPEED_MAX` moves?
The pre-registered decision rule treated a non-moving plateau as evidence that
`AIRSPEED_MAX` is "exonerated" and some other limit (pitch/energy) dominates.

We flew the max-only cells (`AIRSPEED_MAX` = 18 and 28, both at n=3) plus
cruise17 and scaled18_28 at n=1. Altitude loss was effectively identical across
all cells (max18 n=3 mean 15.93 m, std 0.058; max28 n=3 mean 15.90 m, std 0.044;
difference 0.027 m ≈ 0.5σ). The original reading was "P1 holds: `AIRSPEED_MAX`
exonerated."

That reading is wrong. The experiment varied a parameter that does not act on
the signal we were measuring.

## What the BIN logs actually show

Verified from `var/runs/envelope_matrix_max28_n3/.../00000001.BIN` (and
consistent across the other cells):

- Raw reported airspeed `ARSP.Airspeed` rises with the ramp to ~37 m/s at +200%.
- Believed airspeed `CTUN.As` (what TECS consumes) plateaus at ~22 m/s.
- GPS ground speed is ~7.8-8.1 m/s on the headwind leg.
- `ARSP.U = 1` and `ARSP.H = 1` for all 14366 ARSP samples: the sensor is in use
  and healthy for the entire flight. It is never rejected.

The ~22 m/s plateau equals `ground_speed + AHRS_WIND_MAX` (≈ 8 + 15 = 23). It is
not `AIRSPEED_MAX`.

## Root cause: two different parameters were conflated

Confirmed against local ArduPilot source:

1. `AHRS_WIND_MAX` clamps the *believed* airspeed
   (`libraries/AP_AHRS/AP_AHRS.cpp:985-992`):

   ```cpp
   if (_wind_max > 0 && AP::gps().status() >= AP_GPS::GPS_OK_FIX_2D) {
       const float gnd_speed = AP::gps().ground_speed();
       float true_airspeed = airspeed_ret * get_EAS2TAS();
       true_airspeed = constrain_float(true_airspeed,
                                       gnd_speed - _wind_max,
                                       gnd_speed + _wind_max);
       airspeed_ret = true_airspeed / get_EAS2TAS();
   }
   ```

   The clamp is active only when `AHRS_WIND_MAX > 0`. `AHRS_WIND_MAX = 0` is a
   magic disable value (no clamp), not a zero-width window.

2. `AIRSPEED_MAX` clamps the *demanded/target* airspeed, not the sensor estimate
   (`ArduPlane/navigation.cpp:293`):

   ```cpp
   target_airspeed_cm = constrain_int32(target_airspeed_cm,
                                        airspeed_lower_bound*100,
                                        aparm.airspeed_max*100);
   ```

   It bounds what TECS is allowed to ask for. It does not say "never believe a
   sensor reading above this value."

In every matrix cell `AHRS_WIND_MAX` was held at 15 (inherited unchanged from the
baseline overlay). So the active limiter on believed airspeed was identical
across all cells, while we varied `AIRSPEED_MAX`, which does not touch that
signal. The cells came out identical because the real limiter never moved.

This also distinguishes clamp from rejection: the slow ramp was *clamped*
(`AHRS_WIND_MAX`, `ARSP.U` stays 1), not *rejected* (the abrupt pulse trips the
`ARSPD_WIND_GATE` health gate and toggles `ARSP.U`). The two mechanisms are
separate, and the matrix exercised neither of the knobs that move them.

## Decision

1. **The P1 conclusion in ADR-0014 ("`AIRSPEED_MAX` exonerated") is withdrawn.**
   The max18/max28 comparison cannot support any claim about `AIRSPEED_MAX`,
   because `AIRSPEED_MAX` does not act on the believed-airspeed signal under this
   stack. No "exoneration" and no "pitch-limit" conclusion may be drawn from it.

2. **The max18/max28/cruise17/scaled18_28 runs are retained** as valid evidence
   of a *different* and real finding: under `AHRS_WIND_MAX = 15`, a slow positive
   ratio ramp is silently clamped to `ground_speed + AHRS_WIND_MAX` while the
   sensor remains in use and healthy. This is the "slow drift is clamped, not
   rejected" result; it is the protected-stack behavior, not an artifact.

3. **`AHRS_WIND_MAX` becomes a first-class experimental variable.** The redesign
   (ADR-0016, planned) splits the lane into tiers:
   - Tier 1 (protected): `AHRS_WIND_MAX = 15` — what the real configured vehicle
     does. The existing runs already populate this tier.
   - Tier 2 (diagnostic): `AHRS_WIND_MAX = 0` — what TECS does if it receives the
     full lie. To be added; must be validated, not assumed (see Consequence 3).

4. **The mission's hardcoded `DO_CHANGE_SPEED = 15` is identified as the
   cruise-axis defect.** In AUTO, a positive `DO_CHANGE_SPEED` overrides
   `AIRSPEED_CRUISE`, so cruise17 and scaled18_28 flew at 15 m/s and did not test
   the cruise axis. Any future cruise-axis cell needs a per-cruise mission target
   (or removal of the fixed `DO_CHANGE_SPEED`), tracked in the redesign.

5. **A pre-analysis validation gate is required** before any future cell is
   interpreted: each run must prove from its BIN that the varied parameter
   actually moved the signal under test (e.g. believed airspeed `CTUN.As`, or
   `TECS` target), and must report raw `ARSP.Airspeed`, clamped `CTUN.As`, and
   `TECS` target as separate signals. This is the guard that would have caught
   the present error.

## Consequences

- ADR-0012 and ADR-0014 are marked corrected by this ADR; their original text is
  preserved for provenance, with a status banner pointing here.
- The 2026-06-14 acceptance report's "control-envelope saturation" finding is
  annotated: the saturation it describes is the `AHRS_WIND_MAX` clamp, not an
  `AIRSPEED_MAX` or control-authority envelope limit. The report's accepted
  observation counts and behavior classes are unaffected.
- **Tier 2 must be validated before it is trusted.** Setting `AHRS_WIND_MAX = 0`
  removes the AHRS clamp, but `ARSPD_WIND_GATE = 5` and the EKF airspeed
  innovation gate remain and may independently reject or limit the lie. A Tier 2
  run must confirm on the BIN that `CTUN.As` actually tracks raw `ARSP.Airspeed`
  before any "TECS fully believes the lie" claim is made.
- No safety, hardware, cross-airframe, or real-world claim is made or changed.
