# INS-Only And Realistic IMU Characterization Plan

Status: planning draft with Layer 1 no-GPS absence contract and guarded Layer 2
live-discovery path implemented on 2026-08-03. No SITL/Gazebo live result,
feasibility claim, flight-mode claim, or dead-reckoning success claim is made
here until an operator runs and reviews the discovery attempt.

## Purpose

This work extends the GPS failure behavior lane with a separate question:

What does ArduPlane do when GPS is absent from the start, and how does that
behavior change when the simulated IMU is configured to resemble the real IMU
used by the aircraft?

The existing GPS failure lane is not an INS-only lane. It starts from a
GPS-aided EKF configuration, injects GPS faults after a controlled mission
baseline, then measures how the vehicle and EKF respond. This new work must be
kept separate because the initial condition is different: GPS should not exist
as a sensor, an EKF source, a mission trigger dependency, or a recovery source.

## Scientific Question

The experiment has three nested questions.

1. Can the configured ArduPlane + EKF3 stack initialize, arm, and enter any
   useful controlled mode when GPS is absent from boot?
2. If a GPS-free controlled mode is possible, what is the baseline behavior
   with the cleanest simulated IMU settings?
3. If the real IMU's datasheet-derived bias, noise, scale, bandwidth, and drift
   properties are applied to SITL, how does the GPS-free behavior change?

The first question is a discovery gate. If the stack refuses to initialize,
arm, or enter AUTO without GPS, that refusal is a valid observed behavior, not
a failed experiment.

## Current Source Facts

The current GPS lane uses GPS as an EKF aiding source:

- `config/overlays/plane_gps.parm` sets `EK3_SRC1_POSXY=3`,
  `EK3_SRC1_VELXY=3`, and `EK3_SRC1_VELZ=3`, where `3` is GPS.
- `assets/worlds/mini_talon_gps_runway.sdf` loads Gazebo's NavSat system.
- `assets/models/mini_talon/model.sdf` contains a `navsat_sensor`, so the
  no-GPS foundation uses a dedicated `mini_talon_ins_only` model variant.
- `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/source_contract.py`
  expects GPS-aided absolute-position evidence before a normal GPS-fault
  observation is accepted.

ArduPilot source also sets important limits on what may be possible:

- EKF3 Plane bootstrap contains a no-GPS-lock rejection path for fly-forward
  Plane assumptions.
- ArduPlane AUTO takeoff contains an explicit no-auto-takeoff-without-GPS-lock
  check.
- ArduPlane `CIRCLE` mode is explicitly described in source as a mode that can
  be used without GPS.

Therefore, the first live experiment must be a discovery smoke, not a waypoint
science mission.

## Definitions

`No GPS present` means all of the following are true:

- the GPS driver is disabled or reports no GPS;
- the Gazebo world does not provide NavSat;
- EKF source parameters do not select GPS for position, velocity, or yaw;
- the monitor does not require `GPS_RAW_INT` as a success condition;
- the source contract records GPS absence as the intended setup, not as a
  post-trigger fault;
- analysis separates simulator truth from any onboard belief estimate that is
  still available.

`INS-only` means the EKF can only propagate horizontal position and velocity
from inertial states, with any explicitly allowed non-GPS aids documented.
For a minimal first experiment, likely allowed non-GPS aids are:

- barometer for vertical position;
- compass for yaw;
- IMU gyroscope and accelerometer data.

This is not the same as saying the aircraft has a certified standalone INS.
It is a simulated GPS-free inertial/dead-reckoning condition.

`Realistic IMU` means SITL's IMU error model is configured using values
derived from the real IMU datasheet and, later if available, real stationary
and motor-on logs. Datasheet values alone are not enough to prove exact
real-world equivalence.

## Hypotheses

Primary hypothesis:

ArduPlane will not behave like the existing GPS fault campaign when GPS is
absent from boot. It may refuse EKF initialization, arming, AUTO takeoff, or
AUTO mission execution before any meaningful dead-reckoning behavior can be
observed.

Secondary hypothesis:

If a GPS-free controlled mode is possible, zero added IMU bias will be the best
case in SITL, but it will not prove successful dead reckoning. It only proves
that no deliberate accelerometer or gyro bias was added.

Tertiary hypothesis:

Accelerometer bias is the cleanest first independent variable for producing
horizontal inertial position drift. Gyro bias and gyro drift are also important
but affect attitude, yaw, and control coupling before they appear as position
error.

## Configuration Design

Add a new GPS-lane envelope, tentatively named `ins_only_no_gps`.

Expected parameter overlay:

```text
config/overlays/plane_gps_ins_only.parm
```

The first draft should include:

```text
GPS1_TYPE 0
GPS2_TYPE 0
SIM_GPS1_TYPE 0
SIM_GPS1_ENABLE 0
SIM_GPS2_TYPE 0
SIM_GPS2_ENABLE 0
SIM_GPS3_TYPE 0
SIM_GPS3_ENABLE 0
SIM_GPS4_TYPE 0
SIM_GPS4_ENABLE 0

EK3_SRC_OPTIONS 0
EK3_SRC1_POSXY 0
EK3_SRC1_VELXY 0
EK3_SRC1_POSZ 1
EK3_SRC1_VELZ 0
EK3_SRC1_YAW 1

SIM_ACC1_BIAS_X 0
SIM_ACC1_BIAS_Y 0
SIM_ACC1_BIAS_Z 0
SIM_GYR1_BIAS_X 0
SIM_GYR1_BIAS_Y 0
SIM_GYR1_BIAS_Z 0
```

The implemented foundation now provides:

```text
config/overlays/plane_gps_ins_only.parm
assets/worlds/mini_talon_gps_ins_only_runway.sdf
assets/models/mini_talon_ins_only/
envelope: ins_only_no_gps
case: ins_only_no_gps_boot_zero_bias
guarded live command:
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --live-case ins_only_no_gps_boot_zero_bias --envelope ins_only_no_gps --confirm-live-phase2
```

These names must be validated against live ArduPilot parameter readback before
the overlay is treated as executable truth. Vector parameter suffix handling
must be tested because ArduPilot may expose vector values through `_X`, `_Y`,
and `_Z` parameter names.

Arming-check changes must not be broad by default. If arming checks block the
discovery run, record the exact blocking check first. Only then decide whether
a narrowly documented forced/bypass variant is scientifically useful.

Expected Gazebo world:

```text
assets/worlds/mini_talon_gps_ins_only_runway.sdf
```

It should keep the proven Mini Talon runway pose and IMU system, but remove the
NavSat system. It should not introduce wind, airspeed, lidar, optical flow, or
visual odometry unless a later phase explicitly adds those as separate aids.

## Case Design

Phase A case:

```text
ins_only_no_gps_boot_zero_bias
```

This case has no post-trigger injection. The fault is the initial condition.
It measures:

- boot;
- parameter readback;
- GPS absence;
- EKF initialization state;
- arming result;
- mode-entry result for AUTO, CIRCLE, and at least one stabilized manual-like
  mode such as FBWA if the control path supports it;
- cleanup and raw-log capture.

Phase B cases, only if Phase A proves a runnable controlled mode:

```text
ins_only_accel_bias_x_<dose>
ins_only_accel_bias_y_<dose>
ins_only_gyro_bias_z_<dose>
```

The first dose ladder should be conservative and derived from both SITL unit
semantics and the real IMU datasheet. Do not copy GPS drift rates into IMU
parameters. IMU parameters have different units and dynamics.

## IMU Datasheet Mapping

The BMI270 datasheet extraction must produce a plain-English table for:

- accelerometer measurement ranges;
- gyroscope measurement ranges;
- accelerometer sensitivity or resolution per range;
- gyroscope sensitivity or resolution per range;
- accelerometer zero-g offset or offset tolerance;
- gyroscope zero-rate offset or bias tolerance;
- noise density for accelerometer and gyroscope;
- output data rates and bandwidth/filter modes;
- temperature sensitivity or offset drift where specified;
- startup/calibration notes that affect interpretation;
- units and conversion formulas.

The mapping into SITL should be explicit:

| Real IMU property | Candidate SITL parameter | Notes |
| --- | --- | --- |
| accelerometer constant offset | `SIM_ACC1_BIAS_*` | Use m/s^2. Convert `mg` by multiplying by `0.00980665`. |
| gyroscope constant offset | `SIM_GYR1_BIAS_*` | Use rad/s. Convert deg/s by multiplying by `pi / 180`. |
| accelerometer noise or vibration | `SIM_ACC1_RND` | Source validation shows this is a throttle-gated vibration amplitude, not a direct white-noise injector by itself. Pair with `SIM_VIB_FREQ` or `SIM_VIB_MOT_MAX` and validate realized log RMS/spectrum. |
| gyroscope noise or vibration | `SIM_GYR1_RND` | Source validation shows this is expressed in deg/s, converted to rad/s, and throttle-scaled when motors are on. Treat as synthetic noise/vibration, not direct datasheet white noise. |
| gyro drift rate | `SIM_DRIFT_SPEED` | SITL uses deg/s/minute. Datasheet often gives bias stability or temperature drift, so direct mapping is approximate. |
| gyro drift period | `SIM_DRIFT_TIME` | SITL uses a synthetic triangular drift waveform; source implementation has a full cycle of `2 * SIM_DRIFT_TIME`. |
| accelerometer scale error | `SIM_ACC1_SCAL_*` | Source validation confirms the name. Nonzero values divide accel by the configured scalar; default `0` disables this extra scaling. |
| gyroscope scale error | `SIM_GYR1_SCALE_*` | Source validation confirms the name. Values are percent multipliers: `2.0` means `1.02x`. |

If the datasheet gives typical and maximum values, keep both. The experiment
should use at least three profiles:

- `datasheet_typical`;
- `datasheet_worst_case`;
- `measured_airframe`, added later only if real logs are available.

## Measurements

Every attempt should record:

- parameter stack and readbacks;
- GPS driver/type/status;
- EKF source readbacks;
- EKF status flags;
- mode transition attempts and outcomes;
- arming/prearm text;
- IMU-related parameters;
- `SIMSTATE` truth when available;
- AHRS/global/local position fields if published;
- attitude envelope;
- altitude envelope;
- DataFlash BIN selected after cleanup;
- terminal workflow status.

The main behavior outputs are:

- `gps_absence_contract.json`;
- `imu_profile.json`;
- `ins_only_boot_summary.json`;
- `truth_vs_belief.json`, only if a belief position is available;
- `attitude_altitude_envelope.json`;
- terminal manifest row with separate workflow and behavior status.

## Acceptance Model

Accepted does not mean safe or successful.

Accepted means:

- the selected no-GPS and IMU profile was actually applied;
- GPS absence was proven;
- the intended mode attempts were recorded;
- terminal state and cleanup were recorded;
- raw log capture either succeeded or failed with a clear reason.

Possible accepted behavior classes:

- `gps_free_prearm_rejected`;
- `gps_free_ekf_init_rejected`;
- `gps_free_arm_rejected`;
- `gps_free_auto_rejected`;
- `gps_free_controlled_mode_entered`;
- `gps_free_dead_reckoning_drift`;
- `gps_free_attitude_or_altitude_loss`;
- `gps_free_unexpected_disarm_or_crash`.

The first four are valid outcomes for Phase A.

## Implementation Route

Likely code homes:

- `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/defaults.py`:
  add the named envelope and expected readbacks.
- `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/case_generator.py`:
  add initial-condition cases that do not use seq-4 injection.
- `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/source_contract.py`:
  add a no-GPS contract separate from the GPS-aided source contract.
- `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/monitor.py`:
  support boot/mode discovery without requiring mission-current seq-4.
- `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/bin_analysis.py`:
  preserve truth-vs-belief analysis when possible, but fail closed when belief
  position is unavailable instead of inventing one.
- `src/sim_ard_gaw/launch/launch.sh`:
  add a dedicated Gazebo target only if the new world cannot be selected through
  an existing explicit envelope path.
- `tests/unit/`:
  add no-SITL tests for parameter stack, no-NavSat world, source contract,
  case generation, and CLI guards.

## Test Plan

No-SITL tests first:

- parameter overlay parser proves GPS sources are absent;
- world structural test proves NavSat is absent and IMU remains present;
- source contract accepts intended GPS absence and rejects accidental GPS
  aiding;
- case generator marks `ins_only_no_gps_boot_zero_bias` as an initial-condition
  case with no injection payload;
- live CLI remains confirmation-guarded;
- readiness output labels the experiment as discovery-only;
- fake live-path tests prove GPS-ready gates are not used for the no-GPS
  envelope, expected arming refusal is captured as data, and the INS-only
  monitor writes discovery artifacts without an injection.

Then a single guarded discovery live run:

- one attempt;
- zero automatic retries;
- stop after terminal discovery outcome;
- raw output under `var/`;
- no curated evidence promotion until review.

## Risks

- The stack may refuse EKF initialization before any flight behavior exists.
- AUTO may be structurally impossible without GPS under the current Plane
  configuration.
- A forced arming or forced mode variant may answer a different question and
  must be labeled separately.
- Datasheet values describe the sensor component, not the installed airframe
  environment. Vibration, mounting, temperature, power, and calibration can
  dominate the real behavior.
- SITL's IMU model is not a perfect physical sensor model. Some datasheet
  values will map approximately or not at all.

## Next Step

Run one guarded `ins_only_no_gps_boot_zero_bias` live discovery attempt through
the existing round-robin campaign automation under a fresh `var/runs/...` root:

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --live-phase2-round-robin-campaign --envelope ins_only_no_gps --campaign-cases ins_only_no_gps_boot_zero_bias --confirm-live-phase2 --confirm-live-campaign --campaign-root "$(pwd)/var/runs/gps_ins_only_discovery_$(date -u +%Y%m%dT%H%M%SZ)"
```

Then review `gps_absence_contract.json`, `imu_profile.json`,
`ins_only_boot_summary.json`, `mode_timeline.json`, and the attempt-local raw
BIN before deciding whether Phase B datasheet-derived IMU profiles are
scientifically meaningful. Use `bmi270_datasheet_extract.md` and
`imu_sitl_source_validation.md` together to draft those later profiles. Do not
add forced-arming or bypass variants until the natural no-GPS refusal/entry
point is recorded.
