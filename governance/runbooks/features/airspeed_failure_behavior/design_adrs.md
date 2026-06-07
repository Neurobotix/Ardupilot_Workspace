# Airspeed Failure Behavior — ADR Drafts (now Accepted; promoted)

Status of this file: **design detail backing six Accepted ADRs.** These were
accepted by the operator on 2026-06-03 and promoted to numbered records in
`governance/decisions/`. This file is retained as the full reasoning, payload
tables, alternatives, and open validation items that the terse promoted ADRs
point back to.

Promotion map:

| This draft section | Promoted ADR |
| --- | --- |
| Airspeed Failure Mission Design | `governance/decisions/ADR-0006-airspeed-failure-mission-design.md` |
| Airspeed Failure Case Payloads And Ratio Sweep | `ADR-0007-airspeed-failure-case-payloads-and-ratio-sweep.md` |
| Airspeed Failure Reset Protocol | `ADR-0008-airspeed-failure-reset-protocol.md` |
| Airspeed Failure Injection Trigger | `ADR-0009-airspeed-failure-injection-trigger.md` |
| Airspeed Failure Reference Wind | `ADR-0010-airspeed-failure-reference-wind.md` |
| Airspeed Failure Behavior Classification | `ADR-0011-airspeed-failure-behavior-classification.md` |

The decisions reflect agreed design, not unilateral choices. Where a value still
depends on a live measurement it is flagged as a Phase-2 calibration item, not
guessed. The sections below keep their `Status: Proposed` headings as the
original draft text; the authoritative status is Accepted via the promoted ADRs
above. They are grounded by `design_research.md` in this directory; read it
first.

Shared facts (proven from local source — see `design_research.md`):

- The default lane stack uses `ARSPD_TYPE 100` -> `AP_Airspeed_SITL` backend,
  which reads `state.airspeed_raw_pressure[i]`.
- `SIM_ARSPD_*` faults are applied in
  `src/ardupilot/libraries/AP_HAL_SITL/sitl_airspeed.cpp`.
- `SIM_ARSPD_OFS` does not affect `TYPE 100`. `SIM_ARSPD_FAIL` is a forced
  airspeed value, not a boolean. `SIM_ARSPD_RATIO` biases reported airspeed only
  via its mismatch with the **vehicle-side** `ARSPD_RATIO` (source default `2`).
  `SIM_ARSPD_PITOT` only acts when `SIM_ARSPD_FAILP != 0`. `SIM_ARSPD_RND` is Pa
  noise (source default `2.0`).

Decisions locked with the operator (summary; details in each ADR):

1. Mission: new purpose-built `airspeed_failure_behavior_mission.waypoints`
   (100 m cruise, 800 m reciprocal legs, inject on entering seq 4, ends in RTL,
   no landing). Replaces the old validation mission for this lane.
2. Ratio cases are a **signed-percentage airspeed-bias sweep** (a recipe, not a
   hand-written list). End goal: +10..+100% and -10..~-50/-70%. One bias per
   flight. v1 flies a thin slice only.
3. `fail_primary` = `SIM_ARSPD_FAIL=1` (forced ~1 m/s stuck-low). Single case, no
   variations in v1.
4. Reference wind = fixed Gazebo ENU `x=-5, y=0, z=0` m/s, published before
   mission start, sign confirmed in smoke.
5. Classification thresholds are calibrated from `healthy_reference` and the
   sweep itself, not fixed upfront; only coarse validity gates are fixed.

---

# ADR (Proposed): Airspeed Failure Mission Design

Status: Proposed

## Context

The old `airspeed_validation_mission.waypoints` was built for airspeed
**integration** testing (does the sensor chain read correctly in wind). The
fault-injection lane has different needs: inject one fault at a fixed,
repeatable point and observe the autopilot's response over a long, clean cruise
segment in both wind directions. Reusing the integration mission would muddy its
provenance and its geometry is not tuned for fault observation.

## Decision

Create a new purpose-built mission:
`assets/missions/airspeed_failure_behavior_mission.waypoints`.

Geometry (home `lat=-35.363262, lon=149.165237`, Mini Talon fixed-wind world):

| seq | command | location | role |
| --- | --- | --- | --- |
| 0 | home | home | WPL home row |
| 1 | `NAV_TAKEOFF` (22) | climb East | climb to **100 m AGL** |
| 2 | `DO_CHANGE_SPEED` (178) | — | command **15 m/s** cruise |
| 3 | `NAV_WAYPOINT` (16) | ~300 m E | East settle leg start (stabilize cruise) |
| **4** | `NAV_WAYPOINT` (16) | ~1100 m E | **East measurement leg end (800 m leg); INJECT on entering seq 4** |
| 5 | `NAV_WAYPOINT` (16) | ~1100 m E, 150 m N | reciprocal turn offset |
| 6 | `NAV_WAYPOINT` (16) | ~1100 m E, 150 m N | West measurement leg start |
| 7 | `NAV_WAYPOINT` (16) | ~300 m E, 150 m N | West measurement leg end (800 m leg) |
| 8 | `NAV_WAYPOINT` (16) | ~home, 150 m N | return toward home |
| 9 | `NAV_RETURN_TO_LAUNCH` (20) | — | **mission ends in RTL; no landing sequence** |

Locked design parameters (operator-approved 2026-06-03):

- **Cruise altitude: 100 m AGL.** High vertical margin so altitude loss / TECS
  fighting a bad airspeed is observable well before terrain.
- **Measurement leg length: 800 m.** At the commanded 15 m/s with the -5 m/s
  reference wind, the East (headwind) measurement leg is ~80 s of post-injection
  cruise (groundspeed ~10 m/s); the West (tailwind) leg is ~40 s (groundspeed
  ~20 m/s). Enough for TECS/throttle/pitch to settle (~10-20 s) plus drift
  observation, without wasting sim time.
- **Injection on entering seq 4** (start of the 800 m East headwind leg), so the
  fault is seen across the full East leg and the reciprocal West leg.
- **Ends in RTL, no landing.** Completion = front-half progress + both
  measurement legs flown + the mission's RTL reached and stabilized. Then the
  flight ends and the next attempt starts fresh.

### Completion semantics (important interaction with classification)

Because the mission ends in RTL, "completion" is an **RTL-reached** event, not a
landing disarm. The classifier MUST distinguish:

- **planned mission-end RTL** (the seq 9 RTL command reached after the
  measurement legs) -> counts toward `nominal_completion` / `degraded_completion`;
- **fault-triggered early RTL / failsafe** (autopilot switches to RTL or a
  failsafe mode *before* the measurement legs are done, because of the injected
  fault) -> `autopilot_contained`, NOT completion.

The distinguishing signal is mission progress at the moment of the AUTO->RTL
transition: planned RTL happens after seq 8; fault RTL happens earlier. See the
Classification ADR.

## Alternatives considered

- **Reuse the old validation mission.** Rejected: integration-test provenance,
  shorter 40 m / 600 m geometry not tuned for fault observation.
- **1200 m legs.** Rejected with operator: ~120 s headwind cruise is wasteful;
  ~80 s (800 m) is enough for the control loop to fully express the fault.
- **End with a full landing sequence (like the old mission).** Rejected with
  operator: landing adds time and a low-altitude phase that is irrelevant to
  airspeed-fault behavior; RTL is a cleaner, faster completion event.
- **Inject later (only a final leg faulted).** Rejected: wastes the long East
  leg; injecting at seq 4 maximizes clean post-injection observation.

## Evidence / sources

`assets/missions/airspeed_failure_behavior_mission.waypoints` (this file);
mission-progress / RTL detection patterns in
`plugins/wind_matrix/mavlink_control.py`; `design_research.md`.

## Consequences

- Clean provenance; the integration mission is untouched.
- The completion detector keys on the RTL transition + mission progress, which
  the building agent must implement (the wind-matrix monitor keys on disarm
  after landing; this lane differs).

## Open validation items

1. Confirm the seq numbering survives upload (the `DO_CHANGE_SPEED` at seq 2 is a
   DO command; verify the live `MISSION_CURRENT` sequence still presents WP4 as
   `seq==4`).
2. Measure the realized post-injection East-leg duration on the smoke build
   (target ~80 s; confirms the observation window and feeds `MIN_POST_INJECTION_S`).
3. Confirm the RTL completion event is cleanly detectable (mode -> RTL +
   stabilized at RTL altitude / near home) on the smoke build.

---

# ADR (Proposed): Airspeed Failure Case Payloads And Ratio Sweep

Status: Proposed

## Context

The lane needs exact `SIM_ARSPD_*` payloads. The `011` parameter JSON and the
original case names imply naive semantics the actual SITL source contradicts
(see `design_research.md`). In particular the ratio cases are not a 2-case
high/low pair but the eventual **end goal of a full signed-percentage airspeed
bias sweep**. One bias value per flight; never two in one flight.

## Decision

### A. Fixed (non-ratio) cases

| Case | Hypothesis | Payload (set) | Effect | Units | Severity | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| `healthy_reference` | No fault; baseline + threshold calibration source | *(assert source defaults; set nothing)* | reference signal | — | none | High |
| `noise_5` | Mild Pa noise tolerated | `SIM_ARSPD_RND=5` | noise on diff pressure | Pa | mild | High payload / Med effect |
| `noise_10` | Higher Pa noise tolerated | `SIM_ARSPD_RND=10` | larger noise band | Pa | mild | High payload / Med effect |
| `pitot_500pa` | Trapped/blocked pitot fixed pressure | `SIM_ARSPD_FAILP=500` (`PITOT=0`) | airspeed driven by impact-pressure formula vs baro | Pa | moderate | Med payload / Low effect-size |
| `fail_primary` | Primary sensor forced low | `SIM_ARSPD_FAIL=1` | reported airspeed forced to ~1 m/s (stuck low) | m/s (forced value) | severe | High |

`fail_primary` is locked at `SIM_ARSPD_FAIL=1`, a single case, no variations in
v1 (operator decision). It is documented as a **forced value** (airspeed reads
~1 m/s), not a boolean enable.

`SIM_ARSPD_OFS` is unused on the `TYPE 100` stack (non-observable); it stays in
the parameter-probe name-existence list only.

### B. Ratio bias sweep (the end goal; a recipe, not a hand list)

The ratio lane is a **signed-percentage reported-airspeed bias sweep**. Each
case requests a target bias factor `k` on the *reported airspeed*; the injected
`SIM_ARSPD_RATIO` is computed from the measured vehicle `ARSPD_RATIO`.

Equation (derived in `design_research.md`):

```text
reported_airspeed  =  true_airspeed * sqrt( ARSPD_RATIO / SIM_ARSPD_RATIO )

Define bias factor   k  =  reported / true   =  1 + (bias_percent / 100)

Solve for the injected param:
    SIM_ARSPD_RATIO  =  ARSPD_RATIO / k^2
```

Properties (state these cleanly wherever the cases are documented):

- The bias is **inversely proportional to `SIM_ARSPD_RATIO`** (larger injected
  ratio -> lower reported airspeed) and proportional to the vehicle `ARSPD_RATIO`.
- `bias_percent > 0` => airspeed reads HIGH (`SIM_ARSPD_RATIO < ARSPD_RATIO`).
- `bias_percent < 0` => airspeed reads LOW (`SIM_ARSPD_RATIO > ARSPD_RATIO`).
- `ARSPD_RATIO` is the **vehicle** param (source default 2); it MUST be read back
  from the smoke build, because base params may override the default. The
  injected `SIM_ARSPD_RATIO` numbers are therefore computed at run time from the
  measured vehicle ratio, not hard-coded.

End-goal sweep (one flight per value, signed):

```text
high bias:  +10, +20, +30, +40, +50, +60, +70, +80, +90, +100  (%)
low  bias:  -10, -20, -30, -40, -50  [, -60, -70 if still flyable]  (%)
```

Low-side reach is physically capped: "-100%" = reads zero = that is
the forced-low regime, not a ratio case. The case generator MUST refuse or clamp
`bias_percent` beyond a configured low-side floor (default floor:
`-70%`; expect realistic data only to ~-50%). This guard is documented, not
silent.

Naming (replaces the misleading `ratio_1_3`/`ratio_0_7`):

```text
ratio_bias_p10, ratio_bias_p20, ... ratio_bias_p100   (reads high)
ratio_bias_m10, ratio_bias_m20, ... ratio_bias_m50    (reads low)
```

`pNN` = +NN% reported-airspeed bias, `mNN` = -NN%. The name encodes the
*airspeed effect*, never the raw `SIM_ARSPD_RATIO` value.

### C. v1 thin slice (prove the feature, not the science)

v1 exists to prove the generator + injection + analysis chain works, with a
"medium analysis" sanity check — NOT to burn time on the full sweep. v1 runs:

```text
healthy_reference
noise_5, noise_10
pitot_500pa
fail_primary
ratio_bias_p10, ratio_bias_p30, ratio_bias_p50   (thin high slice)
ratio_bias_m10, ratio_bias_m30, ratio_bias_m50   (thin low slice)
```

The full ±10..±100 sweep is the documented end goal the foundation is built for;
the generator is parameterized so extending the slice is just a longer input
list, no code change.

### Readback tolerances

- Enum/integer-valued (`SIGN`, and `FAIL` used as an integer here): exact match.
- Float (`RND`, `FAILP`, `RATIO`): `abs(readback - requested) <= 1e-3`.
- Readback is on the **`SIM_ARSPD_*` parameter values**, not on resulting
  airspeed. The airspeed-effect check lives in the analyzer.

### Reset / default values

Restore **source defaults**, not zeros (see Reset Protocol ADR):
`RND=2.0, OFS=2013, FAIL=0, FAILP=0, PITOT=0, SIGN=0, RATIO=1.99`.

## Alternatives considered

- **Literal `SIM_ARSPD_RATIO=0.7/1.3`.** Rejected: both yield HIGH bias against
  the default vehicle ratio (1.24x and 1.69x); "0.7 = low" is false. The sweep
  uses the `ARSPD_RATIO/k^2` recipe instead.
- **Keep names `ratio_1_3`/`ratio_0_7`.** Rejected: actively misleading once the
  param value is computed, not literal. Renamed to `ratio_bias_pNN/mNN`.
- **Sweep the param percentage instead of the airspeed percentage.** Rejected
  with operator: airspeed-percent (k) is the physically meaningful, comparable
  quantity (`bias_percent` confirmed = reported-airspeed percent).
- **`fail_primary` variations (stuck-cruise, stuck-high).** Deferred: operator
  locked v1 to `FAIL=1` stuck-low only.
- **`OFS` bias case / `PITOT`-only case.** Rejected: no effect on `TYPE 100` /
  no effect unless `FAILP!=0`.

## Evidence / sources

`SITL_Airspeed.cpp`, `AP_HAL_SITL/sitl_airspeed.cpp`, `AP_Airspeed_SITL.cpp`,
`AP_Airspeed/AP_Airspeed.cpp`, `AP_Airspeed/AP_Airspeed_Params.cpp`;
`evidence/curated_logs/011_Sensor_Failure_Injection/...json` (secondary);
`design_research.md`.

## Consequences

- The case generator is a parameterized sweep: input a list of `bias_percent`
  values + the fixed cases; it computes `SIM_ARSPD_RATIO` per case from the
  measured vehicle `ARSPD_RATIO` at run time.
- Ratio cases cannot be numerically locked until Phase 2 reads `ARSPD_RATIO`.
  Phase 1 (no-SITL) implements them with a `calibration_required` flag and the
  equation; Phase 3 must not fly them with an unverified vehicle ratio.
- `pitot_500pa` effect size depends on baro at 100 m; quantify in smoke.

## Open validation items

1. Read back vehicle `ARSPD_RATIO`, `ARSPD_USE`, `ARSPD_TYPE` on the smoke build;
   compute and store the per-case `SIM_ARSPD_RATIO` values.
2. Probe-confirm `OFS`-only is a no-op on `TYPE 100`.
3. Quantify `FAILP=500` realized airspeed vs baro at 100 m AGL.
4. Quantify `FAIL=1` (~1 m/s).
5. Confirm `RND=5/10` realized airspeed σ; reclassify severity from data.
6. Confirm the low-side ratio floor: how negative can `bias_percent` go before
   the flight is just "stuck near zero"? Set the generator clamp from data.

---

# ADR (Proposed): Airspeed Failure Reset Protocol

Status: Proposed

## Context

Each attempt injects `SIM_ARSPD_*` faults. Without disciplined reset a fault can
leak into the next attempt. "Reset to 0" is wrong: source defaults are `RND=2.0`
and `RATIO=1.99`, and `RATIO=0` would break the model (division). Reset must
restore the captured boot baseline.

## Decision

Per-attempt **fresh SITL process** is the primary isolation; explicit param
reset is defense-in-depth. One bias/fault per process; the next attempt boots
clean.

1. **Each attempt runs in its own SITL process** (consistent with ADR-0004
   clean-run policy and the wind-matrix per-attempt model). A fresh process boots
   `SIM_ARSPD_*` to source/overlay defaults, structurally preventing leakage even
   if a reset fails.
2. **Reset payload = captured boot baseline**, read once per process from
   `param show SIM_ARSPD_*` after boot, before any injection. If the baseline
   read fails, the attempt is `pre_injection_failure` and does not count.
   Expected baseline (confirm in smoke): `RND=2.0, OFS=2013, FAIL=0, FAILP=0,
   PITOT=0, SIGN=0, RATIO=1.99`.
3. **Timing:** assert baseline before injection AND reset after the attempt.
   Order: boot -> capture baseline -> assert baseline -> inject at trigger ->
   read back injected -> (attempt runs) -> reset to baseline -> read back reset.
4. **Readback:** reset success requires reading back every reset param within
   injection tolerance (`1e-3` float, exact enum).
5. **Reset failure handling:** record `reset_status="failed"` + mismatched params
   in `airspeed_injection.json`. It does not invalidate the *current* observation
   (fault already observed, process discarded); the next attempt's mandatory boot
   baseline assertion is the real guard.
6. **Live vs restart:** all `SIM_ARSPD_*` are live-settable via MAVLink
   `PARAM_SET`; none need reboot or `--wipe-eeprom`. EEPROM wipe is the launcher
   clean-run policy, not per-case reset. Do not persist `SIM_ARSPD_*`.

## Artifact fields (`airspeed_injection.json`)

```text
boot_baseline: {param: value, ...}
baseline_matches_source_default: bool
requested_payload: {param: value, ...}        # includes computed SIM_ARSPD_RATIO for ratio cases
ratio_case: {bias_percent, k, vehicle_arspd_ratio, computed_sim_arspd_ratio}  # ratio cases only
readback_after_inject: {param: value, ...}
inject_readback_status: ok|failed
reset_payload: {param: value, ...}            # == boot_baseline
readback_after_reset: {param: value, ...}
reset_status: ok|failed|skipped
mismatched_params: [...]
timestamps_utc: {baseline, inject, reset}
```

## Alternatives considered

- **Reset to zeros.** Rejected: differs from boot baseline; `RATIO=0` breaks the
  model.
- **Shared long-lived SITL, reset-only isolation.** Rejected: one failed reset
  silently contaminates the next case.
- **`--wipe-eeprom` per case.** Rejected as reset mechanism: slow; these are
  runtime SITL params.

## Evidence / sources

`SITL_Airspeed.cpp` defaults; ADR-0004; wind-matrix per-attempt model;
`design_research.md`.

## Consequences

- Reset correctness depends on a real captured baseline; fails closed if the
  baseline read fails.
- Fresh process per attempt is slower but matches the existing lane and removes
  the worst leakage mode.

## Open validation items

1. Confirm post-boot `SIM_ARSPD_*` baseline equals source defaults on the build.
2. Confirm every `SIM_ARSPD_*` accepts live `PARAM_SET` without reboot.

---

# ADR (Proposed): Airspeed Failure Injection Trigger

Status: Proposed

## Context

"Inject at mission sequence 4" needs an exact, repeatable definition. In the new
`airspeed_failure_behavior_mission`, seq 4 is the END of the 800 m East
measurement leg; seq 3 is its start. The operator's requirement: a very accurate,
repeatable injection point with enough remaining flight to observe the response.

## Decision

**Trigger = the first `MISSION_CURRENT` message reporting `seq == 4` after
confirmed front-half progress (`seq` observed at 1..3 in AUTO while armed).**
This is "entering seq 4": the aircraft has settled on seq 3 and begins the
straight 800 m East headwind measurement leg toward WP4. Injection lands at the
START of that leg, leaving ~800 m (~80 s) of clean headwind cruise plus the full
reciprocal West leg for observation.

Trigger discipline:

- **First-edge latch:** fire exactly once on the first `seq == 4` current message;
  never re-fire (reuse the wind-matrix monitor seq-edge pattern).
- **Front-half guard:** require prior `seq` in 1..3 while armed in AUTO, to reject
  a late-joining monitor or a jumped mission (existing `invalid_start_reason`
  guard).
- **Record requested vs actual:** store requested trigger
  (`MISSION_CURRENT.seq==4, first edge`) and realized trigger (UTC timestamp,
  observed seq, mode, relative altitude, `wp_dist` if available).

Telemetry inputs: `MISSION_CURRENT` (primary), `HEARTBEAT` (armed + AUTO gate),
`STATUSTEXT` (context), optional `NAV_CONTROLLER_OUTPUT.wp_dist` (artifact only).

## Fallback / failure handling

- **seq 4 never current within the mission window:** no injection;
  `pre_injection_failure`, reason `seq4_not_reached`.
- **Mode left AUTO before seq 4:** no injection; `pre_injection_failure`, reason
  `mode_left_auto_pre_injection`.
- **Missed seq 3->4 edge (first MISSION_CURRENT seen is >= 5):** do NOT
  retro-inject; `pre_injection_failure`, reason `missed_seq4_edge`. A late
  injection on the turn would corrupt the comparable observation window and is
  worse than no data.
- **No front-half progress:** `pre_injection_failure`, reason
  `no_front_half_progress`.

Failing closed (vs a time/distance fallback) protects the whole point of the
lane: a clean, comparable post-injection window across cases. A missed trigger is
a discarded attempt, retried fresh, never a degraded-but-counted one.

## Alternatives considered

- **`MISSION_ITEM_REACHED.seq==4` (reaching seq 4).** Rejected: injects at the
  END of the leg (1100 m E), right before the turn; almost no straight window.
- **Time/altitude trigger.** Rejected for the fault: less repeatable, decoupled
  from geometry.
- **`wp_dist` distance trigger.** Rejected as primary (noisier); artifact only.

## Evidence / sources

`assets/missions/airspeed_failure_behavior_mission.waypoints` (seq map);
`plugins/wind_matrix/mavlink_control.py` (`MISSION_CURRENT` seq-edge, front-half
guard); `design_research.md`.

## Consequences

- Injection at the start of the longest straight leg; observation window ~800 m
  East + full West leg + RTL.
- Some attempts discarded as `pre_injection_failure`; accepted-observation
  accounting already expects this.

## Open validation items

1. Measure the realized seq 3->4 leg duration (~80 s expected) to confirm the
   window and feed `MIN_POST_INJECTION_S`.
2. Confirm `MISSION_CURRENT.seq` presents WP4 as `seq==4` after upload (the
   seq-2 `DO_CHANGE_SPEED` passes through quickly).

---

# ADR (Proposed): Airspeed Failure Reference Wind

Status: Proposed

## Context

Airspeed faults are most observable when a known, steady, non-trivial wind makes
airspeed and groundspeed diverge. The wind must be small enough not to turn the
lane into a wind/CTE envelope test. Operator: keep a (calm-ish) wind, value not
required to be exactly -5,0,0 but that is acceptable.

## Decision

**Fixed reference wind = `x=-5.0, y=0.0, z=0.0` m/s in the Gazebo world ENU
frame**, published before mission start.

- **Frame:** Gazebo world ENU (+X East, +Y North). `x=-5` = wind blowing toward
  -X (West) = headwind on the Eastbound measurement leg, tailwind Westbound.
- **Mechanism:** `gz topic -t <WIND_TOPIC> -m gz.msgs.Wind -p
  "linear_velocity:{x:-5.000,y:0.000,z:0.000}, enable_wind:true"`, reusing
  `plugins/wind_matrix/wind_injection.py`.
- **Verification (strict echo, HARD GATE):** `gz topic -e -t <WIND_TOPIC> -n 1`,
  parse `x/y/z` + `enable_wind`, require match within tolerance. An unverified
  wind makes `ARSP-GPS` interpretation invalid, so an unverified-wind attempt is
  NOT an accepted observation.
- **Tolerance:** `WIND_ECHO_TOLERANCE_MPS` (reuse wind-matrix default; record the
  value). z ~ 0.
- **Timing:** after heartbeat, **before mission start / before takeoff**, so the
  whole flight sees steady wind. If a preloaded fixed-wind SDF world is used,
  validate its `<wind><linear_velocity>` matches and refresh on the topic
  (existing `preloaded_wind_artifact` pattern).

Why -5,0,0 specifically: the magnitude is gentle (well below the ~14-17 m/s
cruise-limited CTE envelope edge, so the lane is not a wind test), yet large
enough to give a clean, sign-flipping `ARSP-GPS ~ +5 East / -5 West` that doubles
as a free per-attempt wind sanity check. Keeping the exact mission-design vector
means the expected `+5/-5` reference is already specified, not re-derived.

## Artifact fields (`reference_wind.json`)

```text
requested_mps: {x:-5.0, y:0.0, z:0.0}
frame: "gazebo_world_enu"
topic: "<WIND_TOPIC>"
publication_timing: "before_mission_start"
method: "gz_topic_publish" | "preloaded_sdf_plus_refresh"
echo_parsed_mps: {x,y,z, enable_wind}
echo_tolerance_mps: <value>
verified: bool
realized_arsp_minus_gps_eastbound_mps: <measured>   # observability + sign check
note: "frame/sign confirmed against realized ARSP-GPS sign on healthy_reference"
```

## Alternatives considered

- **Calm (0,0,0).** Rejected with operator: airspeed ~ groundspeed; loses the
  cleanest observable (`ARSP-GPS` sign flip).
- **Larger wind (~12 m/s).** Rejected: nears the CTE envelope edge; confounds
  airspeed-fault behavior with wind-driven mission failure.
- **Crosswind (y != 0).** Rejected for v1: adds CTE/heading coupling without
  improving airspeed observability.

## Evidence / sources

`assets/missions/airspeed_failure_behavior_mission.waypoints` (wind assumption +
expected `+5/-5`); `plugins/wind_matrix/wind_injection.py`; CTE envelope edge in
`evidence/reports/features/2026-06-02_cte_wind_envelope_result.md`;
`design_research.md`.

## Consequences

- `ARSP-GPS ~ +5 East / -5 West` is a per-attempt observability + wind sanity
  gate.
- The lane stays in the clean-completion wind region; behavior differences are
  attributable to the airspeed fault.

## Open validation items

1. **Confirm the Gazebo wind sign/frame** by checking `healthy_reference`
   produces `ARSP-GPS ~ +5` on the East leg. This project has had wind-sign
   confusion before; do not lock the sign from comments. If inverted, flip the
   published `x` sign and document it.
2. Confirm the fixed-wind world / topic name in use and record it.

---

# ADR (Proposed): Airspeed Failure Behavior Classification

Status: Proposed

## Context

The lane assigns one behavior class per accepted observation, keeping observation
validity separate from behavior class. Thresholds must be physically meaningful
for Mini Talon SITL on this mission, not safety limits. Per operator: thresholds
are **calibrated from `healthy_reference` and from the sweep itself**, not fixed
upfront; only coarse validity gates are fixed. The whole point of the sweep is to
find where on the bias axis behavior transitions.

## Decision

### 1. Observation validity (gate, separate from behavior class)

Valid observation only if ALL hold:

- injection occurred at the locked trigger (`MISSION_CURRENT.seq==4` first edge);
- injection readback succeeded;
- reference wind verified (echo within tolerance);
- post-injection observation window >= `MIN_POST_INJECTION_S` OR a terminal state
  (RTL/failsafe/timeout) was reached after injection;
- required log fields present (`ARSP`, `GPS.Spd`, altitude, mode, mission seq).

Otherwise `pre_injection_failure` or `analysis_incomplete`; neither counts.

### 2. Behavior classes (valid observations only)

| Class | Criteria (first match wins) |
| --- | --- |
| `loss_of_control_or_timeout` | Post-injection altitude loss > `ALT_LOSS_MAX_M` below injection altitude, OR sustained uncommanded attitude/altitude divergence, OR monitor timeout after valid injection without completion. |
| `autopilot_contained` | No clean completion, but the autopilot contained it: **fault-triggered early RTL/failsafe** (AUTO->RTL before seq 8 / before measurement legs done), or a mode change that held a bounded envelope. Distinguished from completion by mission progress at the AUTO->RTL transition. |
| `degraded_completion` | Mission completes (planned seq 9 RTL reached + stabilized after both legs), but with measurable degradation vs `healthy_reference` calibrated bands. |
| `nominal_completion` | Planned mission-end RTL reached + stabilized with post-injection metrics within `healthy_reference` calibrated bands. |

`pre_injection_failure` and `analysis_incomplete` are validity outcomes assigned
by the gate; listed in the enum for completeness.

**Planned-RTL vs fault-RTL rule (critical for this mission):** the mission ends
in RTL, so completion is an RTL event. A planned mission-end RTL (seq 9, after
seq 8 progress) -> nominal/degraded completion. A fault-triggered RTL/failsafe
BEFORE the measurement legs finish -> `autopilot_contained`, not completion. The
discriminator is the maximum mission `seq` reached at the AUTO->RTL transition.

### 3. Thresholds

**Fixed first-pass (coarse validity gates; flagged arbitrary, revise from data):**

- `MIN_POST_INJECTION_S = 20` s — minimum post-injection observation for a valid
  behavior read. *Provisional;* check against the measured ~80 s East-leg
  duration and TECS settling. (Raised from 15 to 20 given the longer leg.)
- `ALT_LOSS_MAX_M = 30` m below the 100 m injection altitude as the
  loss-of-control altitude floor. *Provisional;* 30 m is ~30% of the 100 m cruise
  altitude — "clearly not holding altitude," not a safety claim. Revise from
  `healthy_reference` + `fail_primary` smoke.

**Calibrated from data (do NOT fix upfront):**

From `healthy_reference` smoke (write `reference_baseline.json` consumed by other
cases):

- Nominal airspeed-tracking band: mean/σ of `ARSP` vs commanded 15 m/s on the
  post-injection-point East leg. `degraded` vs `nominal` boundary = healthy mean
  ± k·σ (k TBD, e.g. 3).
- Nominal `ARSP-GPS` band (~+5 East, ~-5 West) and noise.
- Nominal altitude-hold band at 100 m AGL.
- Nominal time to reach planned RTL / mission duration baseline.
- Nominal throttle (`CTUN.ThO`) operating band.

From the **sweep itself** (the scientific output, not a preset):

- The bias-axis transition points: at what `bias_percent` does behavior move
  nominal -> degraded -> contained -> loss-of-control, in each wind direction.
  These are RESULTS to be reported, not thresholds set in advance. The classifier
  applies the calibrated bands per case; the transition map emerges from running
  the sweep.

Single-healthy-run bands are provisional; with 3 accepted healthy observations
use pooled statistics.

### 4. Required artifacts (per accepted observation)

`run_config.json`, `reference_wind.json`, `airspeed_injection.json`,
`airspeed_behavior_summary.json`, `airspeed_signal_metrics.{json,csv}`,
`mission_progress.json` (incl. max seq reached + AUTO->RTL transition seq),
`mode_timeline.{json,csv}`, `altitude_speed_envelope.json`, and
`tecs_response.json` when TECS/CTUN fields are logged (mark unavailable
otherwise; absence alone does not force `analysis_incomplete` if the rest
classify behavior).

### 5. Reason strings (examples)

- `"nominal_completion: ARSP within healthy band (mean 14.9, σ 0.4); alt held 100±3 m; planned RTL reached after seq 8"`
- `"degraded_completion: ratio_bias_p50 ARSP bias +48%; planned RTL reached; throttle saturated 22% of East leg"`
- `"autopilot_contained: AUTO->RTL 4.1 s after fail_primary injection at seq 4 (max seq 4, before measurement legs done); altitude bounded"`
- `"loss_of_control_or_timeout: altitude fell 41 m below injection altitude within 19 s of forced-low injection"`
- `"pre_injection_failure: seq4 current edge never observed (max seq 3); no injection"`
- `"analysis_incomplete: ARSP field absent from BIN; cannot compute airspeed metrics"`

## Alternatives considered

- **CTE square-RMS as primary scorer.** Rejected per plan: CTE needs completed
  geometry that severe cases will not fly; CTE stays optional supporting context.
- **Fix all thresholds upfront.** Rejected with operator: bands are
  platform/mission specific and the sweep's job is to *find* the transitions;
  only coarse validity gates are fixed.
- **Single combined validity+behavior score.** Rejected: plan/review require
  validity to be separable so a bad flight is still a valid observation.

## Evidence / sources

`plan.md`/`implementation.md` behavior vocabulary; available log fields in
`design_research.md`; mission RTL-completion semantics in the Mission Design ADR
above; CTE metric discipline in
`evidence/reports/features/2026-06-02_cte_wind_envelope_result.md`.

## Consequences

- Classification is reproducible and falsifiable; most numeric boundaries derive
  from measured healthy behavior and the sweep, not assertion.
- The two coarse fixed thresholds are the main subjectivity; flagged, scheduled
  for revision after smoke.

## Open validation items

1. Calibrate all healthy-reference bands from smoke (airspeed, `ARSP-GPS`,
   altitude, throttle, time-to-RTL).
2. Set `MIN_POST_INJECTION_S` from the measured East-leg duration + TECS settling.
3. Set `ALT_LOSS_MAX_M` from observed `fail_primary` altitude behavior at 100 m.
4. Confirm `TECS`/`CTUN` field availability in the SITL BIN.
5. Confirm the planned-RTL vs fault-RTL discriminator (max-seq-at-RTL) is clean
   on the smoke build.
