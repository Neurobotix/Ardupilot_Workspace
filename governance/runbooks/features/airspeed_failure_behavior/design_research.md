# Airspeed Failure Behavior — Design Research Report

Status: research / pre-implementation. Not accepted evidence.

Date: 2026-06-03

Author role: design review (no live SITL run performed for this report).

## Purpose

This report grounds the five unresolved design concerns for the airspeed
failure behavior lane in primary sources (current local ArduPilot SITL source,
the validation mission, the existing wind-matrix plugin runtime, and the
accepted CTE evidence). It feeds five ADR drafts in
`design_adrs.md` in this directory.

It is deliberately skeptical. Where a value is unknown it is named as a
must-measure item for Phase 2 smoke, not guessed.

## Scope And Non-Goals

- Behavior characterization of degraded/corrupted simulated airspeed on the
  Mini Talon / ArduPlane SITL + Gazebo stack.
- Not a safety certification, not a recovery-controller design.
- No live SITL campaign run for this report. No config values changed.

## Most Important Finding First: The Actual Signal Path

The runbook, the case names, and the `011_Sensor_Failure_Injection` JSON all
describe `SIM_ARSPD_*` semantics at a surface level. Reading the *actual*
consumers in the current local source changes several design assumptions. The
chain for the default lane stack (`ARSPD_TYPE 100`) is:

```text
Gazebo physics + wind
  -> JSON/Gazebo FDM true airspeed         (SIM_JSON.cpp sets state.airspeed)
  -> SITL analog airspeed fault model      (AP_HAL_SITL/sitl_airspeed.cpp,
                                            applies SIM_ARSPD_* faults)
  -> state.airspeed_raw_pressure[i]        (differential pressure, Pa)
  -> AP_Airspeed_SITL backend (TYPE=100)   (AP_Airspeed_SITL.cpp reads that Pa)
  -> AP_Airspeed vehicle conversion        (AP_Airspeed.cpp:
                                            airspeed = sqrt(diff_pressure * ARSPD_RATIO))
  -> EKF / TECS / ArduPlane
```

Primary source lines:

- `src/ardupilot/libraries/SITL/SITL_Airspeed.cpp` — parameter table and
  defaults for the `SIM_ARSPD_*` group.
- `src/ardupilot/libraries/AP_HAL_SITL/sitl_airspeed.cpp` —
  `SITL_State::_update_airspeed(true_airspeed)`; the only place the
  `SIM_ARSPD_*` values are applied.
- `src/ardupilot/libraries/SITL/AP_Airspeed_SITL.cpp` —
  `get_differential_pressure()` returns `state.airspeed_raw_pressure[i]` for
  `ARSPD_TYPE 100`.
- `src/ardupilot/libraries/SITL/SIM_JSON.cpp` — sets `state.airspeed` from the
  Gazebo/JSON FDM.
- `src/ardupilot/libraries/AP_HAL_SITL/SITL_State.cpp` — calls
  `_update_airspeed(_sitl->state.airspeed)`.
- `src/ardupilot/libraries/AP_Airspeed/AP_Airspeed.cpp` (~lines 665–706) — the
  vehicle-side conversion `airspeed = sqrt(pressure * param.ratio)`.
- `src/ardupilot/libraries/AP_Airspeed/AP_Airspeed_Params.cpp` (~line 65) —
  vehicle-side `ARSPD_RATIO` default is `2`.

### What `sitl_airspeed.cpp` actually does (verbatim logic)

```c
airspeed   = true_airspeed / EAS2TAS(alt);
diff_press = airspeed^2 / arspd.ratio;                 // arspd.ratio = SIM_ARSPD_RATIO
airspeed   = sqrt(|arspd.ratio*(diff_press + arspd.noise*rand())|);   // noise in Pa

if (is_positive(arspd.fail))   airspeed = arspd.fail;  // FAIL is a forced value
if (arspd.fail_pressure != 0)  airspeed = f(fail_pressure, baro, fail_pitot_pressure);

airspeed_pressure = airspeed^2 / arspd.ratio;
if (arspd.signflip) airspeed_pressure *= -1;           // SIGN flips pressure sign
airspeed_raw = airspeed_pressure + arspd.offset;       // OFS added here (Pa domain)

state.airspeed_raw_pressure[i] = airspeed_pressure;    // <-- TYPE=100 reads THIS
airspeed_pin_voltage[i] = PASCAL_TO_VOLTS(airspeed_raw);   // <-- only TYPE=2 analog
```

### Consequences that change the case design

1. **`SIM_ARSPD_OFS` (offset) has NO effect on `ARSPD_TYPE 100`.** The offset is
   added only to `airspeed_raw`/`airspeed_pin_voltage`, which feeds the analog
   (`TYPE_ANALOG=2`) backend. `state.airspeed_raw_pressure[i]` — the value the
   SITL backend (TYPE=100) reads — is computed *before* the offset is applied.
   The default lane uses `ARSPD_TYPE 100`. So an `OFS`-based bias case would be
   silently non-observable on the default stack. The runbook's required
   parameter list still includes `SIM_ARSPD_OFS`, but none of the eight named v1
   cases actually use it; this is consistent, and we should keep `OFS` out of
   the active case payloads for the default stack and document why.
   *Must-verify in Phase 2:* confirm via a deliberate `OFS`-only probe that the
   reported airspeed does not move on `TYPE 100`.

2. **`SIM_ARSPD_FAIL` is not a boolean enable; it is a forced airspeed value in
   m/s.** `if (is_positive(arspd.fail)) airspeed = arspd.fail;`. The param is an
   `AP_Float`. Setting `SIM_ARSPD_FAIL=1` does not mean "fail = on"; it forces
   the simulated true airspeed used for the pressure calc to **1 m/s**, i.e. a
   near-zero differential pressure / "stuck low" reading. The generated-doc
   `@Values: 0:Disabled, 1:Enabled` annotation is misleading relative to the
   runtime math. For `fail_primary` we should request `SIM_ARSPD_FAIL=1` and
   describe the expected effect precisely as "airspeed reads ~1 m/s
   (near-zero / stuck-low), not a NaN or a health flag." If we want a "reads
   zero" fault we would use a value that produces ~0 differential pressure.
   *Decision input:* `1` gives a clearly observable, repeatable stuck-low
   reading and matches the `011` JSON typical value, so request `1` and document
   the true semantics. Do not infer "enable" from the name.

3. **`SIM_ARSPD_RATIO` does not scale reported airspeed by itself.** In the SITL
   model `ratio` both divides (`diff_press = v^2/ratio`) and multiplies
   (`airspeed = sqrt(ratio*...)`), so on the generation side it cancels for the
   noise-free term. The reported airspeed bias comes from the mismatch between
   `SIM_ARSPD_RATIO` and the **vehicle-side** `ARSPD_RATIO`:

   ```text
   reported_airspeed ≈ sqrt( (v^2 / SIM_ARSPD_RATIO) * ARSPD_RATIO )
                     = v * sqrt( ARSPD_RATIO / SIM_ARSPD_RATIO )
   ```

   So `ratio_1_3`/`ratio_0_7` cannot be read as "1.3x / 0.7x airspeed." With the
   vehicle default `ARSPD_RATIO=2`:
   - `SIM_ARSPD_RATIO=1.3` -> factor `sqrt(2/1.3)=1.24x` airspeed (high bias).
   - `SIM_ARSPD_RATIO=0.7` -> factor `sqrt(2/0.7)=1.69x` airspeed (high bias).

   Both come out as *high* bias against the default vehicle ratio, which is not
   what "0.7 = low bias" implies. The clean way to get a true high/low scale
   pair is to define the cases **relative to the vehicle `ARSPD_RATIO` actually
   in effect**, i.e. set `SIM_ARSPD_RATIO = ARSPD_RATIO / k^2` for a target
   factor `k`. This is the single most important open item for the ratio cases.
   *Must-verify in Phase 2:* read back the effective vehicle `ARSPD_RATIO` on
   the smoke build (base params may set it; the overlay sets `ARSPD_AUTOCAL 0`
   and `ARSPD_SKIP_CAL 1`, which keep it from drifting but do not define its
   value). Then compute the two `SIM_ARSPD_RATIO` values that yield a symmetric
   high/low airspeed factor (e.g. 1.3x and 0.77x) and lock them from measured
   data, not from the raw `0.7/1.3` literals.

4. **`SIM_ARSPD_SIGN` flips the differential pressure sign.** Reported airspeed
   uses `sqrt(MAX(pressure,0)*ratio)` (or `fabsf` in the abs branch), so a
   negative pressure typically clamps the computed airspeed to ~0. The
   observable effect is a stuck-near-zero airspeed, similar in *direction* to
   `fail_primary` but via a different mechanism. Expect "airspeed collapses to
   ~0." Whether the EKF/TECS reaction differs from `fail_primary` is an
   empirical question for the campaign, which is exactly the kind of behavior
   contrast this lane exists to characterize.

5. **`SIM_ARSPD_FAILP` and `SIM_ARSPD_PITOT` act together through one branch.**
   The failure-pressure branch fires when `fail_pressure != 0`, and inside it
   `tube_pressure = |fail_pressure - baro_pressure + fail_pitot_pressure|`. So
   `SIM_ARSPD_PITOT` only contributes once `SIM_ARSPD_FAILP` is non-zero.
   Setting `SIM_ARSPD_PITOT=500` alone (with `FAILP=0`) does **not** enter the
   branch and has no effect. For a "pitot 500 Pa" fault we must set
   `SIM_ARSPD_FAILP` non-zero. The cleanest, well-defined `pitot_500pa` payload
   is `SIM_ARSPD_FAILP=500` (this drives the documented impact-pressure formula
   relative to baro), optionally with `SIM_ARSPD_PITOT` left at 0. Using
   `SIM_ARSPD_PITOT=500` with `FAILP=0` would be a silent no-op trap.
   *Must-verify in Phase 2:* confirm reported airspeed moves with
   `FAILP=500, PITOT=0` and quantify the resulting steady airspeed against baro
   at the mission altitude.

6. **`SIM_ARSPD_RND` (noise) is in Pa, applied to differential pressure.** The
   default in source is `2.0` Pa. Noise reduces with speed because it is added
   to the pressure, then square-rooted. The `noise_5`/`noise_10` cases set Pa
   noise amplitude. At ~15 m/s and `ARSPD_RATIO≈2`, nominal differential
   pressure is ~`v^2/ratio ≈ 112 Pa`, so a `±5`/`±10` Pa noise band is a small
   relative perturbation; this is likely a *mild* case. The exact airspeed
   standard deviation must be measured, not asserted.

### Net effect on the cases (locked design, 2026-06-03)

Fixed (non-ratio) cases:

| Case | Mechanism after code review | Expected severity (hypothesis) |
| --- | --- | --- |
| `healthy_reference` | source defaults (`RND=2.0`, others off) | none (reference) |
| `noise_5` | `SIM_ARSPD_RND=5` Pa | mild |
| `noise_10` | `SIM_ARSPD_RND=10` Pa | mild |
| `pitot_500pa` | `SIM_ARSPD_FAILP=500` (NOT `PITOT` alone) | moderate; magnitude vs baro TBD |
| `fail_primary` | `SIM_ARSPD_FAIL=1` -> forced ~1 m/s (locked, single case) | severe (stuck low) |
| `sign_reversed` | `SIM_ARSPD_SIGN=1` -> pressure sign flip | severe (collapse to ~0) |

Ratio cases are NOT a 2-case high/low pair. They are the end goal of a **signed
percentage reported-airspeed bias sweep** (see "Ratio is a sweep" below and the
Case Payloads ADR). Each flight tests one bias factor; the injected
`SIM_ARSPD_RATIO` is computed from the measured vehicle `ARSPD_RATIO`.

`SIM_ARSPD_OFS` is intentionally unused on the default `TYPE 100` stack
(non-observable). It stays in the schema/probe list only so the probe can prove
the name exists on the build.

### Ratio is a sweep, not two cases (operator decision, 2026-06-03)

End goal: characterize how behavior changes as reported airspeed is biased by a
**signed percentage**, both high and low, one bias per flight:

```text
high:  +10, +20, ... +100  (%)   reads HIGH
low:   -10, -20, ... -50 [..-70] (%)   reads LOW
```

The injected param is computed per case from the equation
`SIM_ARSPD_RATIO = ARSPD_RATIO / k^2`, where `k = 1 + bias_percent/100` and
`ARSPD_RATIO` is the **measured vehicle** ratio. Bias is inversely proportional
to `SIM_ARSPD_RATIO`. Low side is physically capped (−100% = reads zero =
`fail_primary`, not a ratio case); the generator clamps below a configured floor
(~−70%). Naming: `ratio_bias_pNN` / `ratio_bias_mNN` (encodes the airspeed
effect, not the param value). The case generator is a recipe: feed it a list of
`bias_percent` values and it stamps out the cases — extending the sweep is a
longer input list, no code change.

v1 flies a thin slice only (e.g. ±10/30/50) to prove the chain works with a
medium analysis; the full ±10..±100 sweep is the documented end goal the
foundation is built for.

## Source Defaults vs Overlay vs Runtime

Source defaults (from `SITL_Airspeed.cpp`):

| Param | Source default | Units | Notes |
| --- | --- | --- | --- |
| `SIM_ARSPD_RND` | `2.0` | Pa | noise on differential pressure |
| `SIM_ARSPD_OFS` | `2013` | (labeled m/s; added in Pa domain) | analog path only |
| `SIM_ARSPD_FAIL` | `0` | m/s when positive | forced airspeed value |
| `SIM_ARSPD_FAILP` | `0` | Pa | failure pressure; gates the fail branch |
| `SIM_ARSPD_PITOT` | `0` | Pa | pitot term, only via the FAILP branch |
| `SIM_ARSPD_SIGN` | `0` | enum 0/1 | pressure sign flip |
| `SIM_ARSPD_RATIO` | `1.99` | ratio | SITL-side ratio (see note 3) |

Critical reset nuance: the **healthy reference is not all zeros.** Source
defaults `RND=2.0` and `RATIO=1.99` are non-zero. A naive reset to `0` would
make the "reset" state differ from both source default and a clean boot, and
`RATIO=0` would divide by zero / break the model. The reset payload must restore
**source defaults**, not zeros (see reset ADR). The overlay
`config/overlays/plane_airspeed.parm` sets no `SIM_ARSPD_*` values, so on the
default stack the boot state for these params equals the source defaults unless
a `.private` overlay or base params set them.

*Must-verify in Phase 2:* capture `param show SIM_ARSPD_*` on the smoke build
immediately after boot, before any injection, and treat that as the canonical
reset baseline. Record it as an artifact. Do not assume the source default and
the runtime default are identical until shown.

## Injection Trigger: Mission Geometry

The lane uses the new purpose-built mission
`assets/missions/airspeed_failure_behavior_mission.waypoints` (QGC WPL 110), NOT
the old validation mission (operator decision, 2026-06-03). Geometry:

- seq 0: home row.
- seq 1: `NAV_TAKEOFF` (cmd 22), climb East to **100 m AGL**.
- seq 2: `DO_CHANGE_SPEED` (cmd 178), target airspeed 15 m/s (a DO command, no
  lat/lon, passed through instantly).
- seq 3: `NAV_WAYPOINT` (cmd 16), Eastbound settle leg start, ~300 m East.
- **seq 4: `NAV_WAYPOINT`, Eastbound MEASUREMENT leg end, ~1100 m East (800 m
  measurement leg).**
- seq 5: North offset (~150 m N) for the reciprocal turn.
- seq 6: West measurement leg start.
- seq 7: West measurement leg end, ~300 m East / 150 m N (800 m leg).
- seq 8: return toward home (150 m N of home).
- seq 9: `NAV_RETURN_TO_LAUNCH` (cmd 20). **Mission ends in RTL; no landing.**

Key point for the trigger: when `MISSION_CURRENT.seq == 4`, the vehicle has just
finished settling on seq 3 and is now **flying the straight 800 m Eastbound
headwind measurement leg toward WP4**. That is the longest stable straight cruise
segment. Injecting **when seq 4 becomes the current target** (entering seq 4)
places the fault at the start of that leg, with ~800 m (~80 s at ~10 m/s
groundspeed in the −5 m/s headwind) of cruise ahead, plus the full reciprocal
West leg, for post-injection observation before the flight ends in RTL.

Contrast: triggering on `MISSION_ITEM_REACHED.seq == 4` injects only after the
vehicle reaches WP4 (~1100 m East), at the *end* of the measurement leg,
immediately before the turn — almost no clean straight window remains. Wrong for
this lane.

Completion note: because the mission ends in RTL, "completion" is an RTL-reached
event, not a landing disarm. The classifier must distinguish a **planned
mission-end RTL** (seq 9, after seq 8) from a **fault-triggered early RTL/failsafe**
(AUTO->RTL before the measurement legs finish). The discriminator is the max
mission `seq` reached at the AUTO->RTL transition. See the Mission Design and
Classification ADRs.

Available, reliable MAVLink signals (confirmed used in
`plugins/wind_matrix/mavlink_control.py`):

- `MISSION_CURRENT` — `.seq` = waypoint currently being navigated to. Fires when
  seq becomes current. This is the "entering seq N" signal. **Recommended
  trigger source.**
- `MISSION_ITEM_REACHED` — `.seq` = waypoint just reached. "Passing seq N."
- `HEARTBEAT` — mode + armed bits. Used for mode-change containment detection.
- `STATUSTEXT` — autopilot messages (EKF, failsafe, errors).
- `NAV_CONTROLLER_OUTPUT` — `wp_dist`, nav bearing; available but a noisier
  trigger than `MISSION_CURRENT`.

Race/debounce facts from the existing monitor: it already keys on
`MISSION_CURRENT.seq` transitions and guards against "mission jumped to seq=N
before front-half progress" (a late-joining or skipped-start race). The airspeed
trigger should reuse the same first-edge-latching discipline: fire once, on the
first `MISSION_CURRENT` message with `seq == 4` after confirmed front-half
progress (seq has been 1..3), and never re-fire.

Failure modes to record: seq 4 never becomes current (mission skipped/short),
mode changed out of AUTO before seq 4 (pre-injection failure), telemetry gap
across the seq 3->4 transition (missed edge), vehicle disarmed/RTL before seq 4.

## Reference Wind: Frame, Mechanism, Magnitude

The new mission carries the same fixed-wind assumption: Gazebo ENU
`<linear_velocity>-5 0 0</linear_velocity>`, "ENU axes: +X East, +Y North",
aircraft starting East into wind. So `x=-5` is wind blowing toward −X (a
westward-blowing wind) — a headwind on the Eastbound measurement leg and a
tailwind on the Westbound leg. Expected steady-state: Eastbound `ARSP≈15,
GPS≈10, ARSP−GPS≈+5`; Westbound `ARSP≈15, GPS≈20, ARSP−GPS≈−5`. (Locked value:
`x=-5, y=0, z=0`; the exact world/topic name in use must be confirmed in smoke.)

Publication mechanism (confirmed reusable from
`plugins/wind_matrix/wind_injection.py`):

- Topic: `gz topic -t <WIND_TOPIC> -m gz.msgs.Wind -p
  "linear_velocity:{x:..,y:..,z:0}, enable_wind:true"`.
- Echo verification: `gz topic -e -t <WIND_TOPIC> -n 1`, parse `x/y/z` and
  `enable_wind`, compare within `WIND_ECHO_TOLERANCE_MPS`.
- The wind-matrix plugin also supports a preloaded SDF world whose
  `<wind><linear_velocity>` is validated to match, then refreshed on the topic.

Why `x=-5, y=0, z=0` is the right fixed wind for this lane (not calm, not a big
vector):

- Calm wind makes airspeed ≈ groundspeed, so `ARSP−GPS` carries almost no
  signal and several airspeed faults become hard to separate from nominal in the
  groundspeed channel. A non-trivial steady wind is what makes the airspeed
  channel *independently observable*.
- `5 m/s` against a `15 m/s` cruise command yields a clean, large, sign-flipping
  `ARSP−GPS ≈ ±5 m/s` between reciprocal legs — easy to falsify and already the
  documented design intent of the mission.
- It stays far below the cruise/`AIRSPEED_MAX` envelope (overlay cruise 14,
  command 15, max 22), so the lane does **not** become a wind/CTE envelope test.
  The CTE envelope edge is ~14–17 m/s resultant wind (accepted CTE evidence);
  5 m/s is deep in the "completes cleanly" region. This keeps wind a *controlled
  constant*, not the independent variable.

Tension to note: the mission commands `DO_CHANGE_SPEED 15`, while the default
overlay sets `AIRSPEED_CRUISE 14`. The 15 m/s command sits inside the 14/22
envelope, so it is acceptable, but the reference-wind and classification
artifacts should record the **commanded** 15 m/s as the airspeed setpoint used
for residual/threshold reasoning, not the 14 m/s cruise default. (Cruise altitude
is 100 m AGL in the new mission.)

Open item: confirm the actual Gazebo wind frame/sign convention on the smoke
build by reading back the live `wind_info` and the realized `ARSP−GPS` sign on
the Eastbound leg of `healthy_reference`. The ArduPilot/Gazebo wind sign
convention has bitten this project before; do not lock the sign from comments
alone.

## Classification Signals Available In Logs

From ArduPlane SITL BIN + MAVLink (fields used by existing plugins or standard
ArduPilot logging):

- Airspeed: `ARSP` BIN message (`Airspeed`, `DiffPress`, `Health`), MAVLink
  `VFR_HUD.airspeed`.
- Groundspeed: `GPS.Spd`, MAVLink `VFR_HUD.groundspeed`,
  `GLOBAL_POSITION_INT` velocity.
- Altitude: `BARO`/`POS`/`CTUN.Alt`, MAVLink `GLOBAL_POSITION_INT.relative_alt`.
- Throttle / TECS: `CTUN` (`ThO` throttle out, `As` airspeed, `TAs` target
  airspeed), `TECS` message (`sp`, `dsp`, `th`, `ph`) where logged.
- Pitch: `ATT.Pitch`, MAVLink `ATTITUDE.pitch`.
- Mode changes: `MODE` BIN message, MAVLink `HEARTBEAT` custom mode.
- Mission progress: `CMD`/`MISSION_CURRENT`, `MISSION_ITEM_REACHED`.
- Status text: `MSG` BIN, MAVLink `STATUSTEXT` (EKF variance, airspeed health,
  failsafe).

This is enough to populate every required analysis artifact named in
`implementation.md`. The TECS-specific artifact is the only one with a real risk
of missing fields; it must be marked optional-when-unavailable per the plan.

## What Must Be Measured Before Anything Locks

Phase 2 smoke (one `healthy_reference`, one `fail_primary`) must capture and
record:

1. `param show SIM_ARSPD_*` post-boot baseline (reset truth).
2. Effective vehicle `ARSPD_RATIO`, `ARSPD_USE`, `ARSPD_TYPE`. The measured
   `ARSPD_RATIO` is required to compute every ratio-sweep case's injected
   `SIM_ARSPD_RATIO = ARSPD_RATIO / k^2`; ratio cases cannot be numerically
   locked until this is read back.
3. Realized steady `ARSP`, `GPS.Spd`, `ARSP−GPS` on the Eastbound leg under the
   fixed `x=-5` wind (wind sign + observability check; calibrates thresholds).
4. Confirmation that `OFS`-only does not move `TYPE 100` airspeed (probe).
5. Confirmation that `FAILP=500, PITOT=0` does move airspeed, and by how much
   (now at 100 m AGL, not 40 m).
6. The exact `MISSION_CURRENT` timing of the seq 3->4 transition and the realized
   post-injection East-leg duration (~80 s expected) — feeds `MIN_POST_INJECTION_S`.
7. `fail_primary` (`FAIL=1`) realized airspeed (~1 m/s expected) and the
   autopilot's reaction (mode, TECS, altitude at 100 m) — calibrates the
   `loss_of_control_or_timeout` vs `autopilot_contained` boundary and
   `ALT_LOSS_MAX_M`.
8. Confirm the planned-RTL vs fault-RTL discriminator (max mission `seq` at the
   AUTO->RTL transition) is clean on the smoke build.
9. Confirm the low-side ratio floor: how negative can `bias_percent` go before
   the flight is just "stuck near zero"? Sets the generator clamp.

## Source And Evidence Citations

- ArduPilot SITL airspeed param table and defaults:
  `src/ardupilot/libraries/SITL/SITL_Airspeed.cpp`.
- SITL airspeed fault application (the authoritative semantics):
  `src/ardupilot/libraries/AP_HAL_SITL/sitl_airspeed.cpp`.
- SITL airspeed backend for `ARSPD_TYPE 100`:
  `src/ardupilot/libraries/SITL/AP_Airspeed_SITL.cpp`.
- Vehicle-side pressure->airspeed conversion and `ARSPD_RATIO` default `2`:
  `src/ardupilot/libraries/AP_Airspeed/AP_Airspeed.cpp`,
  `src/ardupilot/libraries/AP_Airspeed/AP_Airspeed_Params.cpp`.
- FDM airspeed source: `src/ardupilot/libraries/SITL/SIM_JSON.cpp`,
  `src/ardupilot/libraries/AP_HAL_SITL/SITL_State.cpp`.
- Mission geometry (new, purpose-built for this lane):
  `assets/missions/airspeed_failure_behavior_mission.waypoints`. The old
  `assets/missions/airspeed_validation_mission.waypoints` is the legacy
  integration mission and is NOT used by this lane.
- Wind publish/echo + mission-progress monitor patterns:
  `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/wind_injection.py`,
  `.../wind_matrix/mavlink_control.py`, `.../wind_matrix/monitor.py`.
- Sensor-failure parameter research (secondary, partially imprecise on
  semantics — see findings above):
  `evidence/curated_logs/011_Sensor_Failure_Injection/sitl_sensor_failure_params.agent.json`.
- CTE wind-envelope evidence (envelope edge ~14–17 m/s resultant wind; supports
  keeping fixed wind at 5 m/s):
  `evidence/reports/features/2026-06-02_cte_wind_envelope_result.md`,
  `docs/presentations/platform_briefing/cte_result_brief.md`.
- Default lane overlay (no `SIM_ARSPD_*` set):
  `config/overlays/plane_airspeed.parm`.

Generated parameter docs were not fetched online for this report; the local
source is the build under test and is authoritative over generated narrative
docs. If a Phase 2 probe disagrees with local source, the build wins and this
report must be corrected.
