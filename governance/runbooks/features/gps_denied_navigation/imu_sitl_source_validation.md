# IMU SITL Source Validation For INS-Only BMI270 Experiments

Status: source-code validation note. This is not a live-run result and does not
authorize an experiment.

Date: 2026-08-03

Scope: validate, from local ArduPilot source code, which IMU-related SITL
parameters can be used for the proposed no-GPS / INS-only / BMI270-realism
extension of the GPS failure behavior lane.

Primary sources inspected:

- `src/ardupilot/libraries/SITL/SITL.cpp`
- `src/ardupilot/libraries/SITL/SITL.h`
- `src/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_SITL.cpp`
- `src/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_SITL.h`
- `src/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_BMI270.cpp`
- `src/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_BMI270.h`
- `src/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_Backend.h`
- `src/ardupilot/libraries/AP_Param/AP_Param.cpp`
- `src/ardupilot/Tools/autotest/vehicle_test_suite.py`

## Executive Result

ArduPilot has two separate mechanisms that matter here:

1. A real hardware BMI270 driver exists in `AP_InertialSensor_BMI270`. It tells
   us how ArduPilot configures a physical BMI270 when that driver is used.
2. The normal SITL IMU path is `AP_InertialSensor_SITL`. It does not instantiate
   the BMI270 hardware driver. It produces synthetic gyro and accel samples
   from simulator state and applies `SIM_*` parameters.

Therefore, the correct scientific interpretation is:

- use the BMI270 driver source to identify the real ArduPilot BMI270 range,
  sample-rate, FIFO, filter, and scale assumptions;
- use the SITL source to choose which `SIM_*` parameters can approximate the
  physical sensor errors;
- do not claim that SITL is running a BMI270 model unless a custom BMI270 SITL
  model is added later.

## Parameter Name Ground Truth

The top-level SITL parameter group uses the prefix `SIM_`. The IMU-specific
parameter table `var_ins` is included as an extension with no extra subgroup
prefix, so entries such as `ACC1_BIAS` become `SIM_ACC1_BIAS`.

Vector parameters are exposed as scalar MAVLink parameters with `_X`, `_Y`, and
`_Z` suffixes. `AP_Param.cpp` explicitly special-cases `AP_Vector3f`, reserves
space for `_X/_Y/_Z`, appends those suffixes, and resolves names ending in
`_X`, `_Y`, or `_Z` back to the vector elements.

The resulting confirmed scalar names include:

```text
SIM_ACC1_BIAS_X
SIM_ACC1_BIAS_Y
SIM_ACC1_BIAS_Z

SIM_GYR1_BIAS_X
SIM_GYR1_BIAS_Y
SIM_GYR1_BIAS_Z

SIM_ACC1_SCAL_X
SIM_ACC1_SCAL_Y
SIM_ACC1_SCAL_Z

SIM_GYR1_SCALE_X
SIM_GYR1_SCALE_Y
SIM_GYR1_SCALE_Z
```

The same pattern exists for additional simulated IMUs:

```text
SIM_ACC2_BIAS_*, SIM_ACC3_BIAS_*, SIM_ACC4_BIAS_*, SIM_ACC5_BIAS_*
SIM_GYR2_BIAS_*, SIM_GYR3_BIAS_*, SIM_GYR4_BIAS_*, SIM_GYR5_BIAS_*
SIM_ACC2_SCAL_*, SIM_ACC3_SCAL_*, SIM_ACC4_SCAL_*, SIM_ACC5_SCAL_*
SIM_GYR2_SCALE_*, SIM_GYR3_SCALE_*, SIM_GYR4_SCALE_*, SIM_GYR5_SCALE_*
SIM_ACC1_RND through SIM_ACC5_RND
SIM_GYR1_RND through SIM_GYR5_RND
```

Availability of the higher-numbered IMUs depends on `INS_MAX_INSTANCES`; the
source has guarded entries up to 5. The default compile-time definition is
`INS_MAX_INSTANCES = 3 + INS_AUX_INSTANCES`, with `INS_AUX_INSTANCES` defaulting
to `0`.

## Simulated IMU Count And Rates

`SIM_IMU_COUNT` controls how many simulated IMUs are created. Its default is
`2`. During SITL inertial sensor backend setup, ArduPilot creates
`AP_InertialSensor_SITL` backends for each IMU instance from `0` to
`SIM_IMU_COUNT - 1`.

The SITL backend sample-rate constants are:

```text
INS_SITL_SENSOR_A = gyro 1000 Hz, accel 1000 Hz
INS_SITL_SENSOR_B = gyro 760 Hz, accel 800 Hz
```

The creation loop uses sensor B for `i == 1` and sensor A otherwise. With the
default two-IMU setup, IMU 1 uses A and IMU 2 uses B.

Implication: if the experiment sets only `SIM_ACC1_*` and `SIM_GYR1_*`, it
modifies the first simulated IMU only. That is good for inconsistency and
primary-IMU sensitivity studies, but bad if the scientific intention is "all
installed IMUs have the same BMI270-class error." For whole-aircraft realism,
mirror the intended profile across every enabled `SIM_IMU_COUNT` instance or
explicitly set `SIM_IMU_COUNT=1` and record that single-IMU simplification.

## Real BMI270 Driver Configuration

The local source contains a real BMI270 driver:

```text
src/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_BMI270.cpp
src/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_BMI270.h
```

The driver registers physical BMI270 accel and gyro devices with
`DEVTYPE_BMI270 = 0x38` and a backend rate of `1600 Hz`.

### Accel Configuration

`configure_accel()` writes:

```text
ACC_CONF  = (1 << 7) | 0x0C = 0x8C
ACC_RANGE = 0x03
```

Source comments state this means high-performance mode, OSR4 filtering, and
`1600 Hz`; `ACC_RANGE=0x03` is `+-16 g`.

The parse path assumes `16 g` full scale:

```text
accel_scale = (1 / 32768) * GRAVITY_MSS * 16
```

That equals:

```text
16 g / 32768 counts = 2048 LSB/g
1 LSB = 16 * 9.80665 / 32768 = 0.0047884 m/s^2
```

This matches the BMI270 datasheet sensitivity for `+-16 g`.

### Gyro Configuration

`configure_gyro()` writes:

```text
GYRO_CONF  = (1 << 7) | (1 << 6) | (2 << 4) | 0x0D = 0xED
GYRO_RANGE = 0x08
```

Source comments state this means high-performance filter mode, high-performance
noise mode, normal filtering at `3.2 kHz`, and `2000 dps` full scale. The code
sets the OIS range bit as well because the author found that otherwise the
prefiltered FIFO path behaved as `250 dps`; the comment says that behavior is
not documented in the datasheet.

The FIFO downsample register is written with:

```text
FIFO_DOWNS = (1 << 7) | (1 << 3) | 0x01
```

Source comments state this uses filtered data downsampled by `2^1` to `1600 Hz`.

The parse path assumes `2000 dps` full scale:

```text
gyro_scale = radians(2000) / 32767
```

That equals:

```text
2000 dps / 32767 counts = 0.061037 dps/LSB
1 LSB = 0.0010653 rad/s
```

This is consistent with the datasheet `+-2000 dps` sensitivity of
`16.384 LSB/dps`.

### Temperature Handling

The BMI270 driver enables the temperature sensor through `PWR_CTRL=0x0E`.
During FIFO reads, it reads the temperature registers every 100 backend
callbacks. At `1600 Hz`, that is approximately every `62.5 ms`; the code
comment says "temperature sensor updated every 10ms", but the counter logic
does not read every 10 ms.

The conversion in source is:

```text
temperature_C = raw * 0.002 + 23.0
```

The datasheet conversion is `1/512 K/LSB`, which is
`0.001953125 K/LSB`. The source uses a close approximation.

### Real-Driver Implication For This Experiment

If the aircraft's real ArduPilot firmware is using this BMI270 driver path, the
most defensible datasheet profile is not the default-register `+-8 g` profile.
The source indicates:

```text
Accelerometer range: +-16 g
Gyroscope range: +-2000 dps
Backend/FIFO rate: 1600 Hz
Gyro low-noise performance mode: enabled
Gyro ODR/filter setup: 3.2 kHz source downsampled to 1600 Hz filtered FIFO data
Accel ODR/filter setup: 1600 Hz high-performance / OSR4 path per source comments
```

Therefore, for BMI270-realistic SITL work, the datasheet rows to prefer are the
`+-16 g` sensitivity row for accel scale, the `+-2000 dps` row for gyro scale,
and the high-rate/performance noise rows unless real logs prove a different
board configuration.

## SITL Parameter Semantics

### `SIM_ACC1_BIAS_X/Y/Z`

Declaration:

```text
ACC1_BIAS, ACC2_BIAS, ACC3_BIAS, ACC4_BIAS, ACC5_BIAS
```

Type: `AP_Vector3f`, exposed as `_X/_Y/_Z`.

Default: `0` on each axis.

Unit: `m/s/s` from `SITL.h`.

Application in `generate_accel()`:

1. start with simulator acceleration state;
2. apply `SIM_ACC_TRIM` if nonzero;
3. apply `SIM_ACCn_SCAL` division if nonzero;
4. add `SIM_ACCn_BIAS`;
5. add baseline random noise;
6. add motor/vibration noise if configured and motors are on;
7. add IMU position offset effects;
8. apply optional temperature-cal disturbance;
9. rotate by `SIM_IMU_ORIENT`;
10. pass through normal inertial-sensor correction and publication.

Scientific meaning: a constant body-frame accelerometer offset before final
SITL IMU orientation/correction. It is the strongest direct mapping for
BMI270 zero-g offset.

BMI270 mapping:

```text
20 mg = 0.196133 m/s^2
0.25 mg/K = 0.00245166 m/s^2/K
```

Use one axis at a time first. Applying the max offset on all axes at once is a
valid later stress test, but it is a poor first discovery case because it mixes
axis coupling and estimator bias learning.

### `SIM_GYR1_BIAS_X/Y/Z`

Declaration:

```text
GYR1_BIAS, GYR2_BIAS, GYR3_BIAS, GYR4_BIAS, GYR5_BIAS
```

Type: `AP_Vector3f`, exposed as `_X/_Y/_Z`.

Default: `0` on each axis.

Unit: `rad/s`.

Application in `generate_gyro()`:

1. start with simulator roll/pitch/yaw rates converted to rad/s;
2. add synthetic `SIM_DRIFT_*` gyro drift equally to p, q, and r;
3. add baseline random gyro noise;
4. add throttle/vibration noise if configured and motors are on;
5. apply optional temperature-cal disturbance;
6. apply `SIM_GYRn_SCALE`;
7. add `SIM_GYRn_BIAS`;
8. rotate by `SIM_IMU_ORIENT`;
9. pass through normal inertial-sensor correction and publication.

Scientific meaning: a constant body-frame angular-rate offset. It is the
strongest direct mapping for BMI270 zero-rate offset.

BMI270 mapping:

```text
0.5 dps = 0.00872665 rad/s
0.015 dps/K = 0.000261799 rad/s/K
```

### `SIM_GYR1_RND`

Declaration:

```text
GYR1_RND, GYR2_RND, GYR3_RND, GYR4_RND, GYR5_RND
```

Type: `AP_Float`.

Default: `0`.

Unit: source storage says `degrees/second`; `generate_gyro()` converts it using
`radians(SIM_GYRn_RND) * throttle`.

Application:

- there is always a baseline gyro noise term of `radians(0.04)` times
  `rand_float()`;
- if `throttle > SIM_INS_THR_MIN`, the configurable gyro noise amplitude
  becomes `radians(SIM_GYRn_RND) * throttle`;
- if `SIM_VIB_FREQ` and `SIM_VIB_MOT_MAX` are zero, that amplitude is added as
  extra random gyro noise;
- if vibration frequency or motor vibration is configured, that amplitude is
  used in sinusoidal vibration terms.

Scientific meaning: this is not a pure datasheet white-noise-density knob. It
is a throttle-dependent synthetic gyro noise/vibration amplitude.

BMI270 mapping status: weak. It can be tuned to match a measured log RMS, but
the parameter value itself should not be set by directly converting
`dps/sqrt(Hz)` or `dps-rms` from the datasheet.

### `SIM_ACC1_RND`

Declaration:

```text
ACC1_RND, ACC2_RND, ACC3_RND, ACC4_RND, ACC5_RND
```

Type: `AP_Float`.

Default: `0`.

Unit: source storage says `m/s/s`.

Application:

- there is always baseline accel noise of about `0.01 m/s/s` times
  `rand_float()`;
- if `throttle > SIM_INS_THR_MIN`, the configurable accel amplitude becomes
  `SIM_ACCn_RND`;
- unlike gyro, the configurable accel amplitude is only injected through
  `SIM_VIB_FREQ` or `SIM_VIB_MOT_MAX` vibration terms;
- if both vibration knobs are zero, setting `SIM_ACCn_RND` alone does not
  create direct additional white accelerometer noise in the visible code path.

Scientific meaning: this is a vibration amplitude, not a direct accelerometer
white-noise parameter.

BMI270 mapping status: weak unless paired with a designed vibration model and
then validated against logs. For a stationary no-motor comparison, do not
expect `SIM_ACC1_RND` alone to reproduce the BMI270 RMS noise.

### `SIM_DRIFT_SPEED` And `SIM_DRIFT_TIME`

Declaration:

```text
SIM_DRIFT_SPEED default 0.05
SIM_DRIFT_TIME  default 5
```

Source comments:

```text
DRIFT_SPEED = gyro drift rate of change in degrees/second/minute
DRIFT_TIME  = gyro drift duration of one full drift cycle, period in minutes
```

Implementation:

```text
period = SIM_DRIFT_TIME * 2
minutes = fmod(now_minutes, period)
if minutes < period / 2:
    drift = minutes * radians(SIM_DRIFT_SPEED)
else:
    drift = (period - minutes) * radians(SIM_DRIFT_SPEED)
```

The implemented waveform is triangular, always nonnegative, and added equally
to roll, pitch, and yaw rates before per-axis gyro scale and bias. With defaults
the drift grows to:

```text
0.05 deg/s/min * 5 min = 0.25 deg/s
```

then returns to zero over the next 5 minutes. The full source-code cycle is
therefore `2 * SIM_DRIFT_TIME`, even though the parameter description says
`DRIFT_TIME` is the full period. Treat the implementation as authoritative.

Scientific meaning: synthetic gyro drift waveform. It is not a direct BMI270
datasheet behavior. The datasheet gives zero-rate offset and temperature drift,
not this triangular waveform.

BMI270 mapping status: weak. Prefer static gyro bias and hot/cold static bias
profiles before using `SIM_DRIFT_*`.

### `SIM_GYR1_SCALE_X/Y/Z`

Declaration:

```text
GYR1_SCALE, GYR2_SCALE, GYR3_SCALE, GYR4_SCALE, GYR5_SCALE
```

Type: `AP_Vector3f`, exposed as `_X/_Y/_Z`.

Default: `0`.

Source storage comment: percentage.

Application:

```text
gyro.x *= (1 + SIM_GYRn_SCALE_X * 0.01)
gyro.y *= (1 + SIM_GYRn_SCALE_Y * 0.01)
gyro.z *= (1 + SIM_GYRn_SCALE_Z * 0.01)
```

Scientific meaning: direct multiplicative gyro scale factor, expressed in
percent.

BMI270 mapping:

```text
raw datasheet sensitivity error: +-2 %
after CRT: +-0.4 %
```

If modeling uncompensated worst-case sensitivity, use values around `+2` or
`-2`. If the real system runs CRT correctly, use residual values around
`+0.4` or `-0.4`.

### `SIM_ACC1_SCAL_X/Y/Z`

Declaration:

```text
ACC1_SCAL, ACC2_SCAL, ACC3_SCAL, ACC4_SCAL, ACC5_SCAL
```

Type: `AP_Vector3f`, exposed as `_X/_Y/_Z`.

Default: `0`, which means disabled/no extra scale operation in this code path.

Source comment: the code divides by this value so `SIM_ACC*` values match the
`INS_ACCSCAL` calibration values.

Application:

```text
if SIM_ACCn_SCAL_X != 0:
    accel.x /= SIM_ACCn_SCAL_X
```

Scientific meaning: accelerometer scale-factor simulation, but with semantics
different from `SIM_GYRn_SCALE`. A value of `1.0` means no scale error. A value
below `1.0` makes the simulated accelerometer report high on that axis; a value
above `1.0` makes it report low.

For a desired sensor sensitivity error `epsilon`, where the raw sensor should
report:

```text
raw = true * (1 + epsilon)
```

the corresponding first-order setting is:

```text
SIM_ACCn_SCAL = 1 / (1 + epsilon)
```

Examples:

```text
desired accel sensitivity high by +0.4 %:
SIM_ACC1_SCAL_axis = 1 / 1.004 = 0.996016

desired accel sensitivity low by -0.4 %:
SIM_ACC1_SCAL_axis = 1 / 0.996 = 1.004016
```

The ArduPilot autotest `AccelCal` maps `SIM_ACC1_SCAL` to `INS_ACCSCAL`, which
supports this interpretation.

## Strong, Medium, And Weak Mappings

| Physical BMI270 property | Best SITL parameter | Confidence | Reason |
| --- | --- | --- | --- |
| Accel constant zero-g offset | `SIM_ACCn_BIAS_X/Y/Z` | Strong | Direct additive accel vector in `m/s/s`. |
| Gyro constant zero-rate offset | `SIM_GYRn_BIAS_X/Y/Z` | Strong | Direct additive gyro vector in `rad/s`. |
| Gyro sensitivity error | `SIM_GYRn_SCALE_X/Y/Z` | Strong | Direct percent multiplier. |
| Accel sensitivity error | `SIM_ACCn_SCAL_X/Y/Z` | Medium-high | Direct scale effect, but inverted/division semantics. |
| Gyro RMS noise | `SIM_GYRn_RND` | Weak | Throttle-dependent synthetic noise/vibration, not datasheet white noise. |
| Accel RMS noise | `SIM_ACCn_RND` | Weak | Vibration amplitude; not direct white noise unless paired with vibration model. |
| Gyro temperature drift | `SIM_GYRn_BIAS_*` static hot/cold profiles, or `SIM_IMUTn_GYR*` polynomial | Medium | Static profiles are transparent; IMUT polynomials need separate coefficient design. |
| Accel temperature drift | `SIM_ACCn_BIAS_*` static hot/cold profiles, or `SIM_IMUTn_ACC*` polynomial | Medium | Static profiles are transparent; IMUT polynomials need separate coefficient design. |
| Cross-axis sensitivity | none simple | Weak | Would require custom sensor model or orientation/matrix approximation. |
| Alignment error | `SIM_IMU_ORIENT`, `SIM_ACC_TRIM`, or model mount choice | Weak-medium | Can approximate installation, not internal cross-axis matrix exactly. |
| g-sensitivity | none simple | Weak | Not represented as gyro response to acceleration. |

## Recommended Scientific Profiles

### Profile A: Clean INS-Only Baseline

Purpose: isolate "can ArduPlane/EKF operate without GPS" from "what does IMU
degradation do."

Use:

```text
SIM_DRIFT_SPEED 0
SIM_DRIFT_TIME 0

SIM_ACC1_BIAS_X 0
SIM_ACC1_BIAS_Y 0
SIM_ACC1_BIAS_Z 0
SIM_GYR1_BIAS_X 0
SIM_GYR1_BIAS_Y 0
SIM_GYR1_BIAS_Z 0

SIM_ACC1_SCAL_X 0
SIM_ACC1_SCAL_Y 0
SIM_ACC1_SCAL_Z 0
SIM_GYR1_SCALE_X 0
SIM_GYR1_SCALE_Y 0
SIM_GYR1_SCALE_Z 0

SIM_ACC1_RND 0
SIM_GYR1_RND 0
```

If `SIM_IMU_COUNT=2` remains default, mirror equivalent zeroing across IMU 2
for explicitness.

### Profile B: BMI270 Static Offset Ladder

Purpose: test INS-only sensitivity to direct BMI270 offset bounds.

Use one axis and one sensor type at a time first:

```text
SIM_ACC1_BIAS_X 0.196133
SIM_GYR1_BIAS_X 0.00872665
```

Do not apply both in the same first run. First measure accel-only and gyro-only
effects separately.

### Profile C: BMI270 Scale-Factor Probe

Purpose: test sensitivity to datasheet scale-factor error.

Gyro:

```text
SIM_GYR1_SCALE_X 2.0      # +2 percent uncompensated case
SIM_GYR1_SCALE_X 0.4      # +0.4 percent post-CRT residual case
```

Accel:

```text
SIM_ACC1_SCAL_X 0.996016  # produces about +0.4 percent reported accel
SIM_ACC1_SCAL_X 1.004016  # produces about -0.4 percent reported accel
```

### Profile D: Noise/Vibration Tuning, Not Datasheet Direct Entry

Purpose: only after collecting real logs, tune synthetic SITL noise/vibration
so the logged RMS and spectral content resemble the real board.

Do not set `SIM_ACC1_RND` or `SIM_GYR1_RND` directly from datasheet RMS and
claim "BMI270 noise modeled." Instead:

1. run a stationary SITL log with a candidate setting;
2. compute realized IMU RMS and spectrum from logs;
3. compare against stationary real-board logs;
4. adjust until the realized log statistics match within a declared tolerance.

For accelerometer noise, also configure `SIM_VIB_FREQ` or `SIM_VIB_MOT_MAX` if
the desired effect is above baseline, because `SIM_ACC1_RND` alone is not a
plain white-noise source in the visible code.

## Required Validation Before Executable Overlays

Before promoting any executable no-GPS/BMI270 overlay:

1. Confirm `SIM_IMU_COUNT` for the target launch.
2. Decide whether the experiment models all IMUs or only IMU 1.
3. Confirm whether the real aircraft uses this BMI270 driver path, and record
   `INS*ID*` / devtype evidence if available.
4. Confirm whether the real board logs show BMI270 device ID `0x38` or a board
   hwdef explicitly using `IMU BMI270`.
5. If using noise knobs, create an offline RMS/spectrum validation check before
   calling the profile realistic.
6. If using temperature drift, prefer explicit static hot/cold bias profiles
   before polynomial `SIM_IMUTn_*` modeling.
7. Read back every `SIM_*` parameter at runtime in the first live attempt.

## Main Corrections To Earlier Planning Assumptions

1. `SIM_GYR1_SCALE_X/Y/Z` exists and is a percent multiplier.
2. `SIM_ACC1_SCAL_X/Y/Z` exists, but it is not the same semantics as gyro
   scale; it divides accel by the configured scalar and default `0` means the
   scale operation is disabled.
3. `SIM_ACC1_RND` is weaker than previously implied. It is not direct white
   accelerometer noise by itself.
4. `SIM_DRIFT_SPEED/TIME` is a synthetic triangular gyro drift, not datasheet
   drift. The implementation uses a full cycle of `2 * SIM_DRIFT_TIME`.
5. The physical BMI270 driver configures `+-16 g` accel and `+-2000 dps` gyro,
   so BMI270 datasheet modeling should use that real ArduPilot configuration
   unless the actual board/firmware proves otherwise.
