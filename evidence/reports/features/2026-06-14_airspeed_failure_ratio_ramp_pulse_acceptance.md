# Airspeed Failure Ratio/Ramp/Pulse Characterization Acceptance

Date/time: 2026-06-14 12:33:56 EEST (+0300)

Status: **PASS for bounded Phase 4A scope**. This report accepts the
ratio-bias sweep, headwind pulse-ladder, and headwind stepped-ramp
characterization for the `airspeed_failure` behavior lane. It does **not**
accept the original full fixed-case repetition matrix, does **not** close the
fixed-case Phase 4B scope, and is not a safety or hardware claim.

## Scope

Accepted scope:

- one-bias-per-flight signed ratio-bias sweep;
- headwind pulse ladder `ratio_bias_pulse_p10_to_p130_headwind`;
- headwind stepped ramps `ratio_bias_ramp_p10_to_p100_headwind` and
  `ratio_bias_ramp_p10_to_p200_headwind`;
- bounded interpretation of the Mini Talon ArduPlane SITL + Gazebo stack under
  one fixed parameter stack, one fixed wind vector, and the mission families
  named below.

Deferred/open scope:

- fixed-case repetition matrix for `healthy_reference`, `ofs_noop_probe`,
  `noise_5`, `noise_10`, `pitot_500pa`, and `fail_primary`;
- final full-lane acceptance that includes those fixed-case repetitions;
- any safety, hardware, cross-airframe, cross-parameter, or real-world claim.

## Commands

No new live SITL or Gazebo commands were run for this acceptance report.

Validation/audit commands for the acceptance implementation:

```bash
source setup.bash && ./env/bin/python3 -m unittest tests.unit.test_airspeed_failure_phase1
source setup.bash && ./env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py tests/unit/test_airspeed_failure_phase1.py
source setup.bash && /home/ahmed/.local/bin/pyright src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py tests/unit/test_airspeed_failure_phase1.py
git diff --check
make doctor
```

Result: all commands above passed on 2026-06-14. No live SITL/Gazebo command
was run.

## Evidence

Primary technical analysis:

- `evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`

Curated package:

- `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/`
- manifest: `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/manifest.json`
- raw source index:
  `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/raw_data_index.md`

Raw run roots named by the curated package:

- positive ratio sweep:
  `var/runs/airspeed_failure_behavior_ratio_p10_20260608T121445Z/`
  through `var/runs/airspeed_failure_behavior_ratio_p100_20260608T154448Z/`;
- negative ratio sweep:
  `var/runs/airspeed_failure_behavior_ratio_m10_20260609T103836Z/`
  through `var/runs/airspeed_failure_behavior_ratio_m50_20260609T111832Z/`;
- pulse ladder:
  `var/runs/airspeed_failure_behavior_ratio_bias_pulse_p10_to_p130_headwind_20260610T075155Z/`;
- ramp +100:
  `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p100_headwind_20260610T111134Z/`;
- ramp +200:
  `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p200_headwind_20260610T122611Z/`.

The abandoned 2026-06-09 ramp root is excluded by the curated package and is
not part of this acceptance.

## Stack, Wind, And Payloads

Stack: ArduPlane SITL (`plane-cte`) + Gazebo Mini Talon, base params
`config/vehicles/plane_base.parm` plus
`config/overlays/plane_airspeed.parm`.

Relevant parameter values verified per attempt in the source artifacts:
`AIRSPEED_CRUISE=14`, `AIRSPEED_MIN=10`, `AIRSPEED_MAX=22`,
`ARSPD_TYPE=100`, `ARSPD_USE=1`, `ARSPD_RATIO=2.0`,
`ARSPD_OPTIONS=11`, `ARSPD_WIND_MAX=0`, `ARSPD_WIND_GATE=5`,
`TECS_PITCH_MAX=15`, and `PTCH_LIM_MAX_DEG=20`. Per-attempt parameter-file
hashes are recorded in the raw `run_config.json` files referenced by the
curated package.

Fixed wind: Gazebo ENU `x=-5, y=0, z=0` m/s, strict echo verified per accepted
attempt. The wind is a headwind on the Eastbound leg and tailwind on the
Westbound leg in the reciprocal mission.

Ratio payload recipe: `SIM_ARSPD_RATIO = ARSPD_RATIO / k^2`, where
`k = 1 + bias_percent / 100`, recomputed from measured vehicle
`ARSPD_RATIO=2.0` in live runs.

Mission families:

- ratio sweep:
  `assets/missions/airspeed_failure_behavior_mission.waypoints`;
- stepped ramps:
  `assets/missions/airspeed_failure_headwind_ramp_mission.waypoints`;
- pulse ladder:
  `assets/missions/airspeed_failure_headwind_pulse_ladder_mission.waypoints`.

## Accepted Observation Counts

Accepted observations: **47**.

- ratio sweep: 44 accepted observations;
- pulse ladder: 1 accepted observation;
- ramp +100: 1 accepted observation;
- ramp +200: 1 accepted observation.

Known excluded observation: the `ratio_bias_p100` `attempt_002` pre-injection
failure is not counted.

Acceptance quality: all 47 accepted observations had verified wind echo,
seq-4 injection or schedule application with successful readback, sufficient
post-injection observation for the bounded claim, required curated artifacts,
and verified reset. No failed launch, failed readback, failed reset,
unverified-wind, or pre-injection failure is counted as accepted behavior.

## Behavior Class Counts

Behavior classes across the 47 accepted observations:

- `nominal_completion`: 13
- `degraded_completion`: 31
- `loss_of_control_or_timeout`: 3
- `autopilot_contained`: 0

The slow +100 ramp's coarse artifact classifier labels that attempt
`nominal_completion`, while the BIN-derived window analysis shows measurable
degradation. This classifier-granularity limitation is retained as a limitation
of the accepted bounded characterization.

## Accepted Findings

Within this bounded scope, the evidence supports these findings:

- positive one-bias-per-flight reported-airspeed bias produces a monotonic
  degradation trend from +30 upward, with altitude-loss growth flattening near
  +90/+100;
- the negative sweep is asymmetric, with monitor-terminated low-altitude aborts
  at -40 after valid injections and degraded completion again at -50;
- abrupt positive bias pulses make the airspeed-health machinery visible:
  pulse windows from +60 upward cross `ARSPD_WIND_GATE=5` and trigger sensor
  disable/re-enable events;
- the same positive biases reached gradually by +10% ramp steps remain accepted
  by the airspeed health machinery under this stack (`ARSP.U=1`, `Hp=1`, low
  `ARSP.TR`), while the aircraft settles into a degraded equilibrium;
- the extended +200 ramp shows control-envelope saturation after roughly
  +80..+100: raw reported airspeed continues rising while true airspeed,
  groundspeed, altitude, throttle, pitch/elevator response, and sensor state are
  effectively flat;
  - **Correction (ADR-0015, 2026-06-16):** the mechanism of this "saturation"
    was identified by the later envelope-matrix work. The flat believed-airspeed
    value (~22 m/s) is the `AHRS_WIND_MAX` clamp (`ground_speed + AHRS_WIND_MAX`,
    with `AHRS_WIND_MAX=15`), NOT a control-authority or `AIRSPEED_MAX` envelope
    limit. Raw `ARSP` keeps rising to ~37 m/s while the clamp holds the believed
    value near `ground_speed + 15`; the sensor stays in use and healthy
    (`ARSP.U=1`) — clamped, not rejected. This corrects only the mechanism; the
    observation above (raw rises, believed/true/alt flat) stands as logged.
- the +100 and +200 ramp overlap reproduces closely enough to support the
  single-configuration interpretation recorded by the June 11 report.

## Limitations

- One SITL configuration only: same workspace, same vehicle model, same
  parameter stack, same fixed wind, and same mission family.
- Single accepted attempt for pulse ladder, +100 ramp, and +200 ramp.
- Ratio-sweep aggregate tables are MAVLink-artifact derived; pulse/ramp
  controller and health conclusions are BIN-derived.
- Fixed-case repetitions remain open. The Phase 2 measurement-smoke
  observations for `healthy_reference`, `ofs_noop_probe`, `pitot_500pa`, and
  `fail_primary` are not enough by themselves to satisfy the fixed-case
  repetition contract; `noise_5` and `noise_10` still have no accepted live
  observations in the current evidence set.
- The generating plugin and documentation changes were uncommitted working-tree
  state at run time; raw `run_config.json` files preserve dirty-state
  provenance.

## Old Workspace Statement

No changes were made to `/home/ahmed/ardupilot_workspace` for this acceptance
report. The old workspace remains read-only deprecated fallback/reference.

## Verdict

**PASS for Phase 4A ratio/ramp/pulse characterization.**

**OPEN for Phase 4B fixed-case repetition matrix.** Full original lane
acceptance remains unavailable until the fixed-case matrix is either completed
or deliberately revised by a documented governance decision with bounded
claims.
