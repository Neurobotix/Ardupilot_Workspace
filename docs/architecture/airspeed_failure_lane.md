# Airspeed Failure Lane

The airspeed failure lane deliberately degrades or corrupts the simulated
airspeed signal on a Mini Talon ArduPlane SITL + Gazebo stack, then records
what the aircraft does. The goal is **behavior characterization** — not
safety certification and not recovery-controller design.

This is the second `test_suite` plugin family alongside the CTE wind-matrix
lane. CTE is not the primary score here; it can be retained only as optional
supporting path-quality context when an attempt completes enough route geometry.

Current status:

- Phase 0 (design lock): accepted 2026-06-03.
- Phase 1 (no-SITL plugin foundation): accepted 2026-06-05.
- Phase 2 (live measurement smoke): accepted 2026-06-06; raw root
  `var/runs/airspeed_failure_behavior_20260606T164050810132Z/`.
- Phase 3/4A (ratio/ramp/pulse characterization): accepted 2026-06-14 for a
  bounded scope. The accepted evidence is the signed ratio sweep
  +10..+100/−10..−50 (2026-06-08/09), headwind pulse ladder +10..+130, and
  stepped ramps +100/+200 (2026-06-10), curated under
  `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/` and accepted by
  `evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`.
- Phase 4B (fixed-case repetition matrix / full-lane acceptance): open.
  Fixed-case repetitions for `healthy_reference`, `ofs_noop_probe`, `noise_5`,
  `noise_10`, `pitot_500pa`, and `fail_primary` remain unclosed.

The 2026-06-14 acceptance is a bounded behavior-characterization claim, not a
safety claim and not full fixed-case lane acceptance. Do not treat Phase 2 smoke
as a complete behavior result; it is four-case raw measurement output only.

## Default Stack

| Item | Value |
| --- | --- |
| Mission | `assets/missions/airspeed_failure_behavior_mission.waypoints` |
| SITL target | `plane-cte` |
| Gazebo target | `gazebo-plane-cte` |
| Base params | `config/vehicles/plane_base.parm` |
| Airspeed overlay | `config/overlays/plane_airspeed.parm` (14/10/22 conservative) |

The aggressive high-wind CTE stress overlay lives separately in
`config/overlays/plane_airspeed_cte_high_wind_aggressive.parm` and is not part
of this lane's default stack.

## Mission

The lane uses `assets/missions/airspeed_failure_behavior_mission.waypoints`, a
purpose-built mission. The legacy `airspeed_validation_mission.waypoints` was
for airspeed integration testing; its provenance is separate and it is not used
here (ADR-0006).

| seq | command | role |
| --- | --- | --- |
| 0 | home | WPL home row |
| 1 | `NAV_TAKEOFF` (22) | Climb to **100 m AGL** Eastbound |
| 2 | `DO_CHANGE_SPEED` (178) | Command **15 m/s** cruise |
| 3 | `NAV_WAYPOINT` | East settle leg (~300 m E) |
| **4** | `NAV_WAYPOINT` | **East measurement leg end (~1100 m E, 800 m leg); fault injected on entering seq 4** |
| 5 | `NAV_WAYPOINT` | Reciprocal turn offset (~150 m N) |
| 6 | `NAV_WAYPOINT` | West measurement leg start |
| 7 | `NAV_WAYPOINT` | West measurement leg end (800 m leg) |
| 8 | `NAV_WAYPOINT` | Return toward home |
| 9 | `NAV_RETURN_TO_LAUNCH` (20) | **Mission ends in RTL; no landing sequence** |

Cruise altitude is 100 m AGL — vertical margin so altitude loss or TECS
fighting a corrupt signal is observable before terrain. The 800 m East headwind
leg (~80 s at ~10 m/s groundspeed with the −5 m/s fixed reference wind) plus
the 800 m West tailwind leg (~40 s at ~20 m/s) provide post-injection
observation time.

**Completion semantics:** completion = front-half progress (seq 1–3) + both
measurement legs + planned seq-9 RTL reached and stabilized. A fault-triggered
early RTL/failsafe (AUTO→RTL before the measurement legs finish) is classified
`autopilot_contained`, not completion. The discriminator is the maximum mission
seq reached at the AUTO→RTL transition.

## Reference Wind

Fixed Gazebo world-frame ENU: `x=-5, y=0, z=0` m/s. In Gazebo ENU
(`+X=East, +Y=North`), `x=-5` is a westward-blowing wind — headwind on the
Eastbound leg, tailwind on the Westbound leg. Expected healthy steady-state:
Eastbound `ARSP≈15, GPS≈10, ARSP−GPS≈+5`; Westbound `ARSP≈15, GPS≈20,
ARSP−GPS≈−5`.

The wind is published via `gz topic` before mission start and must be strictly
echo-verified before arming. Unverified wind = not an accepted observation.
The fixed wind is kept well inside the CTE wind-envelope edge (~14–17 m/s
resultant) so wind remains a controlled constant, not the independent variable.
Decisions in ADR-0010.

## Injection Trigger

The fault is injected on **entering seq 4**: the first `MISSION_CURRENT`
message with `seq == 4` after confirmed front-half progress (seq has been 1, 2,
and 3), first-edge latched, never re-fired. A missed or late trigger is a
`pre_injection_failure`, not a late injection. Decisions in ADR-0009.

## Case Set

### Fixed Cases

| Case | Fault payload | Expected severity |
| --- | --- | --- |
| `healthy_reference` | source defaults (no injection) | none (reference) |
| `ofs_noop_probe` | `SIM_ARSPD_OFS=2500` (Pa-domain analog offset) | none for `ARSPD_TYPE=100`; Phase 2 confirmed no-op once |
| `noise_5` | `SIM_ARSPD_RND=5` (Pa) | mild |
| `noise_10` | `SIM_ARSPD_RND=10` (Pa) | mild |
| `pitot_500pa` | `SIM_ARSPD_FAILP=500` (Pa) | severe signal corruption; Phase 2 measured one degraded completion |
| `fail_primary` | `SIM_ARSPD_FAIL=1.0` (forced ~1 m/s stuck-low) | severe |

### Ratio Bias Sweep

The ratio cases are a **signed-percentage reported-airspeed bias sweep**, not a
fixed pair. One bias per flight. The injected parameter is computed as:

```
SIM_ARSPD_RATIO = ARSPD_RATIO / k²,  k = 1 + bias_percent/100
```

where `ARSPD_RATIO` is the **measured vehicle ratio** in live runs (read from
the clean SITL boot; Phase 2 confirmed `ARSPD_RATIO=2.0`). Naming:
`ratio_bias_pNN` (reads high) / `ratio_bias_mNN` (reads low). End goal:
+10..+100% and −10..~−50/−70%.

The **v1 thin slice** (`±10/30/50`) proves the chain. The full sweep is the
documented end goal; extending it is a longer input list, no code change.

### Headwind Stepped Ramp

`ratio_bias_ramp_p10_to_p100_headwind` is a separate within-flight stepped-ramp
case, not a replacement for the one-bias-per-flight sweep. The extended
boundary-probe variant is `ratio_bias_ramp_p10_to_p200_headwind`. Both use
`assets/missions/airspeed_failure_headwind_ramp_mission.waypoints`: 100 m AGL,
a longer Eastbound climb/settle runway, and one continuous headwind line holder.
The mission has no RTL waypoint; the monitor ends each run after the final
scheduled observation and resets the simulated airspeed parameters.

The schedule starts on entering seq 4 with a 60 s verified baseline window. It
then raises reported-airspeed bias by +10% per level, with 60 s per level,
using the same `SIM_ARSPD_RATIO = ARSPD_RATIO / k²` recipe recomputed from the
measured vehicle `ARSPD_RATIO` in live runs. The standard ramp ends at +100.
The extended ramp continues through +200 to probe the failure/stall boundary
after the +100 run showed a stable degraded equilibrium. There is no reset
between levels.

Interpretation boundary: this is accumulated degradation in one flight. It is
useful for seeing how altitude, TECS, elevator/servo outputs, airspeed sensor
use, and loss/stall behavior evolve as the false airspeed gets progressively
worse under continuous headwind. It is not an independent dose-response
replacement for the one-bias-per-flight sweep.

Completion discriminator: the reciprocal mission still requires planned RTL
after the East/West legs (`seq >= 8` at AUTO→RTL). The stepped-ramp mission is
monitor-complete at `ramp_complete`; it does not use RTL as the success
condition.

### Headwind Pulse Ladder

`ratio_bias_pulse_p10_to_p130_headwind` is a separate within-flight
pulse-ladder case, not a replacement for the one-bias-per-flight sweep. It uses
`assets/missions/airspeed_failure_headwind_pulse_ladder_mission.waypoints`:
100 m AGL, a longer Eastbound climb/settle runway, and one continuous headwind
line holder. The mission has no RTL waypoint; the monitor ends the run after
the final scheduled observation and resets the simulated airspeed parameters.

The schedule starts on entering seq 4 with a verified baseline window. It then
alternates +10, reset, +20, reset, ... +130, with 60 s per window, using the
same `SIM_ARSPD_RATIO = ARSPD_RATIO / k²` recipe recomputed from the measured
vehicle `ARSPD_RATIO` in live runs. Baseline phases read back the boot
`SIM_ARSPD_*` baseline before the next fault phase begins.

Interpretation boundary: each fault window is separated by a baseline reset and
settle period, but later windows still share one flight history, airframe
energy state, and controller integrator history. Treat this as threshold and
transient evidence, not as independent dose-response samples. A crash, stall,
low-altitude abort, timeout, or failsafe after valid readback is valid behavior
for this case. A clean stop is accepted only after the final +130% observe
window completes.

Completion discriminator: the pulse-ladder mission is monitor-complete at
`pulse_ladder_complete`; it does not use RTL as the success condition.

| Case | Bias | Effect |
| --- | --- | --- |
| `ratio_bias_p10` | +10% | Reads ~10% high |
| `ratio_bias_p30` | +30% | Reads ~30% high |
| `ratio_bias_p50` | +50% | Reads ~50% high |
| `ratio_bias_m10` | −10% | Reads ~10% low |
| `ratio_bias_m30` | −30% | Reads ~30% low |
| `ratio_bias_m50` | −50% | Reads ~50% low |

Dry-run ratio case values use the configured ratio as a planning recipe. Live
ratio cases are resolved after clean boot by recomputing `SIM_ARSPD_RATIO` from
the measured MAVLink `ARSPD_RATIO` readback before injection. Full calibration is
a Phase 3 matrix item.

## Key `SIM_ARSPD_*` Semantics

These are the most important caveats derived from reading the SITL source
directly. The case names can be misleading without them.

- **`SIM_ARSPD_FAIL` is not a boolean enable.** It is a forced airspeed value
  in m/s. `FAIL=1` forces ~1 m/s (stuck-low), not "failure on/off." Setting
  `FAIL=0` disables it (source default). The upstream source annotation still
  labels `FAIL` as `0:Disabled, 1:Enabled`; this lane treats that annotation as
  misleading and follows the runtime math.
- **`SIM_ARSPD_OFS` has no effect on `ARSPD_TYPE 100`.** The offset is added
  only to the analog voltage path. `state.airspeed_raw_pressure[i]` — the value
  the SITL backend reads for TYPE 100 — is computed before the offset. No active
  case uses `OFS`; it is included in the parameter schema only as a name-probe.
  The upstream source labels the units as m/s, but the runtime adds the value in
  the pressure/analog path.
- **`SIM_ARSPD_SIGN` is not an active case in this lane.** It flips the
  simulated differential-pressure sign, but the default vehicle
  `ARSPD_TUBE_ORDR=2`/AUTO conversion uses absolute pressure. Under this stack
  it is not a sustained stuck-low/collapse fault. It remains in the schema only
  so live attempts can assert and reset the source default.
- **`SIM_ARSPD_PITOT` only acts when `SIM_ARSPD_FAILP != 0`.** Setting
  `PITOT=500` alone with `FAILP=0` is a silent no-op. The `pitot_500pa` case
  sets `FAILP=500`.
- **Reset restores source defaults, not zeros.** `SIM_ARSPD_RND` source default
  is `2.0` Pa, `SIM_ARSPD_RATIO` source default is `1.99`; resetting to `0`
  would break the SITL model. Each attempt captures a boot baseline and resets
  to it.

For the full signal-chain derivation and parameter table, see
[design_research.md](../../governance/runbooks/features/airspeed_failure_behavior/design_research.md).

## Behavior Classification

The plugin classifies observed behavior and observation quality, not safety.

| Class | Meaning |
| --- | --- |
| `nominal_completion` | Mission completes without material degradation after injection. |
| `degraded_completion` | Mission completes, but with measurable degradation in tracking, speed, altitude, or timing. |
| `autopilot_contained` | Autopilot changes mode, aborts progress, or contains the situation without a clean mission completion. |
| `loss_of_control_or_timeout` | Behavior becomes uncontrolled for the lane criteria, or the attempt times out after a valid injection. |
| `pre_injection_failure` | Attempt fails before the planned injection point. |
| `analysis_incomplete` | Artifacts are insufficient for a behavior classification. |

A degraded or failed flight counts as an accepted observation when injection
occurred and the required artifacts are present. Failed launch, failed
readback, pre-injection failure, or incomplete artifacts do not count.

Decisions in ADR-0011.

## Required Attempt Artifacts

Each live attempt must produce:

- `run_config.json`
- `reference_wind.json`
- `airspeed_injection.json`
- `airspeed_behavior_summary.json`
- `airspeed_signal_metrics.json`
- `mission_progress.json`
- `mode_timeline.json`
- `altitude_speed_envelope.json`
- `tecs_response.json` (optional when log fields unavailable, must be noted)

## Output Paths

Raw runtime output: `var/runs/airspeed_failure_behavior_<timestamp>/`

Curated interim evidence:
`evidence/curated_logs/airspeed_failure_behavior_2026-06-11/`

Interim evidence report:
`evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`

Bounded Phase 4A acceptance report:
`evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`

Future full-lane or fixed-case Phase 4B packages should use
`evidence/curated_logs/airspeed_failure_behavior_<date>/` and
`evidence/reports/features/<date>_airspeed_failure_behavior.md` only when dated
evidence supports that wider acceptance.

## Accepted Decisions

| ADR | Subject |
| --- | --- |
| [ADR-0006](../../governance/decisions/ADR-0006-airspeed-failure-mission-design.md) | Mission design (100 m cruise, 800 m legs, RTL end, inject seq 4) |
| [ADR-0007](../../governance/decisions/ADR-0007-airspeed-failure-case-payloads-and-ratio-sweep.md) | Case payloads and ratio-sweep recipe |
| [ADR-0008](../../governance/decisions/ADR-0008-airspeed-failure-reset-protocol.md) | Reset to source defaults, not zeros; boot-baseline capture |
| [ADR-0009](../../governance/decisions/ADR-0009-airspeed-failure-injection-trigger.md) | Injection trigger on entering seq 4 |
| [ADR-0010](../../governance/decisions/ADR-0010-airspeed-failure-reference-wind.md) | Fixed reference wind x=−5, y=0, z=0 ENU |
| [ADR-0011](../../governance/decisions/ADR-0011-airspeed-failure-behavior-classification.md) | Behavior-class vocabulary and observation-quality gating |

## Feature Runbook

The complete planning, implementation notes, and review history live under
[governance/runbooks/features/airspeed_failure_behavior/](../../governance/runbooks/features/airspeed_failure_behavior/).

How to run the plugin: [docs/operations/airspeed_failure_runbook.md](../operations/airspeed_failure_runbook.md).
