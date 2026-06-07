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
- Phase 3 (full v1 matrix): unlocked by Phase 2; not yet run.
- Phase 4 (evidence curation): not yet implemented.

No curated feature evidence exists. Do not treat Phase 2 smoke as an accepted
behavior result; it is four-case raw measurement output only.

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
| `sign_reversed` | `SIM_ARSPD_SIGN=1` (pressure sign flip → collapse to ~0) | severe |

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
  `FAIL=0` disables it (source default).
- **`SIM_ARSPD_OFS` has no effect on `ARSPD_TYPE 100`.** The offset is added
  only to the analog voltage path. `state.airspeed_raw_pressure[i]` — the value
  the SITL backend reads for TYPE 100 — is computed before the offset. No active
  case uses `OFS`; it is included in the parameter schema only as a name-probe.
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

Curated evidence (Phase 4 only, after acceptance):
`evidence/curated_logs/airspeed_failure_behavior_<date>/`

Dated evidence report (Phase 4 only):
`evidence/reports/features/<date>_airspeed_failure_behavior.md`

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
