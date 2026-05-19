# Test Result: Airspeed Follow-Up Validation

---
test_id: 007_Plane_Airspeed_FollowUp
date: 2026-04-02
vehicle: Mini Talon with Airspeed
status: PASS_WITH_ISSUES
tested_by: Codex
---

## Summary

This follow-up closes the gap left by `003_Plane_Airspeed`.

The airspeed chain is now supported by direct evidence across four layers:

1. real-target startup behavior,
2. Gazebo sensor noise isolation,
3. ArduPilot SITL-side airspeed noise isolation,
4. reciprocal-leg mission validation in wind.

The current conclusion is:

- the fixed-wing airspeed integration is working end to end,
- the old stale-offset startup failure is understood,
- the reciprocal-leg validation shows the correct wind-response sign flip,
- but the early AUTO segment of the validation mission is still dynamically messy and should not be mistaken for a pure airspeed-sensor problem.

## What Changed Since 003

`003_Plane_Airspeed` documented implementation only. It still referenced an old bridge-based understanding and did not yet prove flight behavior.

This follow-up adds evidence for:

- `ARSPD_SKIP_CAL=1` and `ARSPD_OFFSET=0` as the clean startup state,
- the effect of pitot pressure noise in Gazebo,
- the effect of `SIM_ARSPD_RND` and `SIM_ARSPD2_RND` in SITL,
- the reciprocal-leg `ARSP - GPS` sign flip expected from a `5 m/s` wind.

## Test Stack

### T03: Real-Target Startup Calibration

Purpose:
- prove the real aircraft path is healthy,
- diagnose why some runs showed `0 m/s`.

Key result:
- `00000158.BIN`: startup calibration learned live wind as offset
- `00000161.BIN`: skip-cal enabled, but stale offset survived
- `00000162.BIN`: clean wiped run with `ARSPD_OFFSET=0` held a stable `4.8-5.0 m/s`

Interpretation:
- the old broken behavior was real,
- the fix requires both `ARSPD_SKIP_CAL=1` and clean SITL state,
- stale EEPROM/SITL storage can preserve a bad offset.

### T04: Gazebo Sensor Noise Isolation

Purpose:
- isolate the Gazebo airspeed sensor layer without ArduPilot interpretation.

Method:
- temporary copied model assets only,
- temp `model.sdf` patched to test `stddev=0.01` vs `stddev=0.0`,
- `ArduPilotPlugin` removed from the temp copy so `/airspeed` could be measured directly.

Result:

| Case | Pressure mean (Pa) | Abs-pressure stddev (Pa) |
|------|--------------------|--------------------------|
| `stddev=0.01` | `15.317666` | `0.971591` |
| `stddev=0.0` | `15.269545` | `0.003655` |

Interpretation:
- the Gazebo pressure noise term is material,
- zeroing it sharply tightens the raw sensor signal.

### T05: SITL Airspeed Noise Isolation

Purpose:
- isolate ArduPilot SITL-side airspeed randomization.

Method:
- isolated temp SITL directories with `-w` and `--use-dir`,
- same clean startup state in both runs,
- only `SIM_ARSPD_RND` and `SIM_ARSPD2_RND` changed.

Result:

| Case | Mean ARSP (m/s) | ARSP stddev (m/s) |
|------|------------------|-------------------|
| `SIM_ARSPD*=2` | `4.860246` | `0.098119` |
| `SIM_ARSPD*=0` | `4.866248` | `0.000353` |

Interpretation:
- SITL-side randomization is also real,
- removing it produces a much cleaner stationary ARSP trace without changing the mean much.

### T07: Reciprocal-Leg Flight Validation

Purpose:
- validate the full stack in realistic wind-dependent flight.

Mission logic:
- take off,
- command `15 m/s`,
- fly a headwind leg,
- turn,
- fly a tailwind leg,
- compare airspeed against groundspeed.

Scored windows:
- eastbound: heading `80-100 deg`, `wp_seq in {3,4}`, `rel_alt >= 30`, `groundspeed >= 8`
- westbound: heading `260-280 deg`, `wp_seq in {6,7}`, `rel_alt >= 30`, `groundspeed >= 8`

Result:

| Run | Segment | Mean ARSP-GPS (m/s) | Samples |
|-----|---------|----------------------|---------|
| Before | Eastbound | `+4.631998` | `317` |
| Before | Westbound | `-5.402736` | `501` |
| After | Eastbound | `+4.413837` | `112` |
| After | Westbound | `-5.079883` | `80` |

Interpretation:
- the reciprocal sign flip is correct in both runs,
- the wind-response magnitude is about right,
- the airspeed chain is therefore believable end to end.

## Current Assessment

### What Is Verified

- the aircraft model publishes a usable airspeed signal,
- the plugin path into ArduPilot works,
- startup offset corruption is understood and avoidable,
- Gazebo pitot noise and SITL airspeed randomization were both isolated and measured,
- reciprocal flight behavior shows the correct wind-response sign flip.

### What Is Still Open

- the first part of the AUTO mission is still dynamically rough,
- the early `ARSP - GPS` spikes align with heading and groundspeed excursions,
- this looks more like flight-control / mission-capture behavior than a stale-offset recurrence,
- the after-case eastbound leg still needs cleaner steady-state behavior if we want a presentation-quality validation plot.

## Public Conclusion

The Mini Talon airspeed integration should now be treated as:

- **validated end to end**
- **safe to document as working**
- **not yet presentation-perfect in the first AUTO segment**

That last point is important. The remaining weakness is no longer "does airspeed work?" It is "how cleanly does the aircraft settle into the validation mission?"

