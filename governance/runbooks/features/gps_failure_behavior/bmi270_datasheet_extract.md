# BMI270 Datasheet Extract For SITL IMU Modeling

Source: Bosch Sensortec BMI270 datasheet, document revision 1.6, document
number `BST-BMI270-DS000-08`, March 2026. Local operator-provided files:

- `/home/ahmed/Downloads/bst-bmi270-ds000.pdf`
- `/home/ahmed/Downloads/BMI270_datasheet_preserved.md`

This extract is for planning only. It maps datasheet values to candidate
ArduPilot SITL parameters for the proposed INS-only / realistic-IMU extension
of the GPS failure lane. It does not prove that SITL exactly reproduces the
physical BMI270 installed in an airframe.

Review note, 2026-08-03: this file was cross-checked against the operator's
compact engineering quick reference derived from the same Bosch datasheet. The
unit conversions and the SITL-facing bias/noise target numbers below did not
need arithmetic correction. This revision adds missing timing/configuration
values useful for matching real logs and clarifies where the datasheet gives a
rounded headline value and a more exact ODR-table value for the same condition.
The companion source validation
`imu_sitl_source_validation.md` confirms the ArduPilot BMI270 driver settings
and the SITL parameter semantics used by the mapping tables below.

## ArduPilot Driver-Matched BMI270 Profile

The datasheet contains reset defaults, multiple ranges, and multiple
ODR/filter/noise-mode choices. For this project, the most important profile is
the one selected by the local ArduPilot BMI270 driver source, because that is
what a real ArduPilot board using `AP_InertialSensor_BMI270` would publish to
the estimator.

The source-confirmed driver profile is:

| Property | ArduPilot BMI270 driver setting | Modeling consequence |
| --- | --- | --- |
| Device ID | `0x24`, ArduPilot devtype `0x38` | Use this to verify real logs actually came from BMI270. |
| Backend rate | `1600 Hz` | SITL cannot claim BMI270 timing realism unless logged sample cadence is checked. |
| Accelerometer range | `+-16 g` | Prefer the `2048 LSB/g` sensitivity row, not the reset-default `+-8 g` row. |
| Accelerometer ODR/filter | `1600 Hz`, high-performance / OSR4 path per source comments | The 200 Hz normal-mode noise table is a reference target, not the driver-matched operating point. |
| Gyroscope range | `+-2000 dps` | Prefer the `16.384 LSB/dps` sensitivity row. |
| Gyroscope ODR/filter/noise | `3.2 kHz` source, filtered FIFO downsampled to `1600 Hz`, high-performance filter and low-noise mode | Prefer performance-mode gyro noise values when deriving first targets. |
| Temperature readout | source conversion `raw * 0.002 + 23` | Close to datasheet `1/512 K/LSB`; useful for log interpretation, not direct SITL drift by itself. |

Therefore, the tables below keep the broader datasheet values, but executable
SITL profiles should start from this source-matched profile unless the target
hardware logs or board configuration prove a different BMI270 setup.

## Device Summary

The BMI270 is a 6-axis IMU with:

- 16-bit triaxial accelerometer.
- 16-bit triaxial gyroscope.
- package: 14-pin LGA, `2.5 x 3.0 x 0.83 mm`.
- chip ID register value: `0x24`.
- accelerometer ranges: `+-2 g`, `+-4 g`, `+-8 g`, `+-16 g`.
- gyroscope ranges: `+-125 dps`, `+-250 dps`, `+-500 dps`, `+-1000 dps`,
  `+-2000 dps`.
- accelerometer ODR range: `0.78 Hz` to `1.6 kHz` overall; normal/performance
  mode tables cover `12.5 Hz` to `1600 Hz`.
- gyroscope ODR range: `25 Hz` to `6.4 kHz` overall; normal/performance data
  register mode covers `25 Hz` to `3.2 kHz`, while `6.4 kHz` uses FIFO readout.
- programmable low-pass filtering.
- temperature sensor.
- offset compensation for accelerometer and gyroscope.
- gyroscope component retrimming (CRT) for sensitivity compensation.
- operating ambient temperature range: `-40 deg C` to `+85 deg C`.
- supply range: `VDD=1.71..3.6 V`, `VDDIO=1.2..3.6 V`.

The package, chip ID, supply, and interface facts are not direct SITL knobs, but
they are useful when confirming that the real board and logs correspond to a
BMI270 configuration rather than a different IMU variant.

## Accelerometer Core Values

| Property | Datasheet value | SITL relevance |
| --- | ---: | --- |
| Resolution | 16 bit | Useful for quantization context; SITL does not directly expose BMI270 ADC counts. |
| Range | `+-2/+-4/+-8/+-16 g` | Choose the range that the real firmware/driver uses; default register reset is `+-8 g`. |
| Sensitivity at `+-2 g` | `16384 LSB/g` | Count-to-g conversion only. |
| Sensitivity at `+-4 g` | `8192 LSB/g` | Count-to-g conversion only. |
| Sensitivity at `+-8 g` | `4096 LSB/g` | Count-to-g conversion only. |
| Sensitivity at `+-16 g` | `2048 LSB/g` | Count-to-g conversion only. |
| Sensitivity error | `+-0.4 %` | Candidate for `SIM_ACC1_SCAL_*` if SITL scale semantics are confirmed. |
| Sensitivity temperature drift | `0.004 %/K` | Not directly modeled by existing GPS-lane code. |
| Sensitivity supply-voltage drift | `0.0001 %/V` | Not useful unless supply variation is modeled. |
| Zero-g offset | `+-20 mg` | Candidate for `SIM_ACC1_BIAS_*`. |
| Zero-g offset temperature drift | `+-0.25 mg/K` | Candidate for a temperature-profile extension, not a direct static overlay. |
| Zero-g offset supply drift | `<0.5 mg/V` | Usually omit unless supply variation is part of the experiment. |
| Power-supply rejection ratio | `<8 mg/50 mV` from `100 Hz` to `1 MHz` | Usually omit unless supply ripple is measured or intentionally modeled. |
| Output noise density | `0.16 mg/sqrt(Hz)` at `+-8 g`, normal mode | Candidate for estimating RMS noise; SITL `SIM_ACC1_RND` is not a pure datasheet white-noise knob. |
| RMS noise | `1.51 mg-rms` at `ODR=200 Hz`, `BW=80 Hz`, `+-8 g`, normal mode | Better starting value for a 200 Hz profile. |
| Nonlinearity | `0.5 %FS` at `+-2 g` | Not directly modeled unless a separate nonlinear sensor model is added. |
| ODR accuracy, accel-only at 25 deg C | `1 %` | Timing/sample-rate realism context, not a direct bias knob. |
| ODR accuracy, IMU at 25 deg C | `1.7 %` | Timing/sample-rate realism context when accel and gyro are both enabled. |
| ODR accuracy temperature drift, accel-only | `0.03 %/K` | Usually lower priority than bias and vibration for this experiment. |
| ODR accuracy temperature drift, IMU | `0.0037 %/K` | Usually lower priority than bias and vibration for this experiment. |
| Cross-axis sensitivity | `1 %` | Not directly modeled by current SITL parameter overlay. |
| Alignment error | `0.5 deg` relative to package | Could be modeled by sensor orientation/mounting, not by the simple bias overlay. |
| PCB-strain zero-g offset | `+-0.010 mg/microstrain` | Installation effect; needs airframe strain data to use. |
| Startup time | `2 ms` | Not important for long flight behavior, but relevant to boot realism. |

### Accelerometer ODR, Bandwidth, And RMS Noise

Normal/performance mode, normal filter mode `ACC_CONF.acc_bwp=0x02`, `+-8 g`:

The headline accelerometer characteristic table quotes the `200 Hz` RMS-noise
condition with `BW=80 Hz`. The ODR-specific bandwidth table for
`ACC_CONF.acc_bwp=0x02` quotes a `200 Hz` 3 dB cutoff of `89 Hz`. Use `1.51 mg`
as the RMS target either way; the `89 Hz` value below is the ODR table cutoff.

| ODR Hz | 3 dB cutoff Hz | RMS noise typ mg | Group delay typ ms |
| ---: | ---: | ---: | ---: |
| 12.5 | 5.5 | 0.38 | 80 |
| 25 | 11 | 0.53 | 40 |
| 50 | 22 | 0.75 | 20.5 |
| 100 | 44 | 1.06 | 10.5 |
| 200 | 89 | 1.51 | 5.4 |
| 400 | 178 | 2.13 | 2 |
| 800 | 343 | 2.96 | 1.3 |
| 1600 | 740 | 4.35 | 0.6 |

## Gyroscope Core Values

| Property | Datasheet value | SITL relevance |
| --- | ---: | --- |
| Resolution | 16 bit | Useful for count-to-rate context. |
| Range | `+-125/+-250/+-500/+-1000/+-2000 dps` | Choose the real driver range. Default register reset is `+-2000 dps`. |
| Sensitivity at `+-2000 dps` | `16.384 LSB/dps` | Count-to-rate conversion only. |
| Sensitivity at `+-1000 dps` | `32.768 LSB/dps` | Count-to-rate conversion only. |
| Sensitivity at `+-500 dps` | `65.536 LSB/dps` | Count-to-rate conversion only. |
| Sensitivity at `+-250 dps` | `131.072 LSB/dps` | Count-to-rate conversion only. |
| Sensitivity at `+-125 dps` | `262.144 LSB/dps` | Count-to-rate conversion only. |
| Sensitivity error | `+-2 %` | Candidate for `SIM_GYR1_SCALE_*` if SITL scale semantics are confirmed. |
| Sensitivity error after CRT | `+-0.4 %` | Use this only if the real system runs CRT. |
| Sensitivity temperature drift | `0.02 %/K` | Not directly modeled by current GPS-lane code. |
| Sensitivity supply-voltage drift | `0.0005 %/V` | Usually omit unless supply variation is modeled. |
| Zero-rate offset | `+-0.5 dps` | Candidate for `SIM_GYR1_BIAS_*`. |
| Zero-rate offset temperature drift | `+-0.015 dps/K` | Candidate for a temperature-profile extension. |
| Zero-rate supply drift | `0.02 dps/V` | Usually omit unless supply variation is modeled. |
| Power-supply rejection ratio | `0.40 dps/50 mV` from `100 Hz` to `1 MHz` | Usually omit unless supply ripple is measured or intentionally modeled. |
| Output noise density, performance | `0.007 dps/sqrt(Hz)` | Candidate for RMS conversion. |
| Output noise density, normal | `0.010 dps/sqrt(Hz)` | Candidate for RMS conversion. |
| RMS noise, performance | `0.07 dps-rms` at `ODR=200 Hz`, `BW=74.6 Hz` | Rounded headline value; the ODR table gives `61.4 mdps` for the same 200 Hz performance profile. |
| RMS noise, normal | `0.09 dps-rms` at `ODR=200 Hz`, `BW=74.6 Hz` | Rounded headline value; the ODR table gives `87.7 mdps` for the same 200 Hz normal profile. |
| Nonlinearity | `0.01 %FS` at `+-250` and `+-2000 dps` | Not directly modeled unless a nonlinear model is added. |
| ODR accuracy at 25 deg C | `1.7 %` | Timing/sample-rate realism context, not a direct bias knob. |
| ODR accuracy temperature drift | `0.0037 %/K` | Usually lower priority than bias and vibration for this experiment. |
| Cross-axis sensitivity | `0.2 %` | Not directly modeled by the simple overlay. |
| Alignment error | `0.5 deg` relative to package | Could be modeled by mounting/orientation, not simple bias. |
| PCB-strain zero-rate offset | `+-1.5 mdps/microstrain` | Needs installation strain data to use. |
| g-sensitivity | `0.1 dps/g` | Important for aggressive flight/vibration; not directly modeled by current simple SITL knobs. |
| Startup time | `45 ms` normal, `2 ms` fast-start | Mostly boot-realism context. |

### Gyroscope ODR, Bandwidth, And RMS Noise

Normal/performance mode, normal filter mode `GYR_CONF.gyr_bwp=0x02`,
`+-2000 dps`:

For the `200 Hz` row, this table uses the ODR-specific values. That is why it
lists `77 Hz`, `87.7 mdps`, and `61.4 mdps` rather than the rounded headline
condition of `BW=74.6 Hz`, `0.09 dps`, and `0.07 dps`.

| ODR Hz | 3 dB cutoff Hz | RMS noise normal mdps | RMS noise performance mdps | Group delay typ ms |
| ---: | ---: | ---: | ---: | ---: |
| 25 | 11 | 31.0 | 21.7 | 40 |
| 50 | 20 | 43.9 | 30.7 | 20.5 |
| 100 | 39 | 62.0 | 43.4 | 10.8 |
| 200 | 77 | 87.7 | 61.4 | 5.97 |
| 400 | 152 | 124 | 86.9 | 3.55 |
| 800 | 300 | 176 | 123 | 2.34 |
| 1600 | 557 | 248 | 174 | 0.97 |
| 3200 | 751 | 431 | 302 | 0.82 |
| 6400 | 712 | 500 | 350 | 0.68 |

## Temperature Sensor

| Property | Datasheet value | Relevance |
| --- | ---: | --- |
| Temperature sensor resolution | 16 bit | Diagnostic only unless a temperature profile is modeled. |
| Measurement range | `-41` to `87 deg C` | Useful for bounding temperature-sweep profiles. |
| Output at 23 deg C | `0 LSB` | Register-level interpretation. |
| Sensitivity | `512 LSB/K` | Temperature conversion. |
| ODR with gyroscope on in normal/performance mode | `100 Hz` | Temperature tracking can be fast when gyro is active. |
| ODR in other modes | `0.78 Hz` | Slower update if gyro is not active. |
| Register resolution | `1 / 2^9 K/LSB` | Same as `512 LSB/K`. |

## Register-Level Defaults Useful For Real Logs

These are not SITL parameters, but they help interpret a real BMI270 driver
configuration before we decide which simulated profile is fair:

| Register | Reset / value | Meaning for this study |
| --- | ---: | --- |
| `CHIP_ID` at `0x00` | `0x24` | Confirms the device identity. |
| `ACC_CONF` at `0x40` | reset `0xA8` | Encodes accelerometer ODR/filter state; confirm the real driver writes the intended ODR and `acc_bwp`. |
| `ACC_RANGE` at `0x41` | reset `0x02` | Default accelerometer range is `+-8 g`. |
| `GYR_CONF` at `0x42` | reset `0xA9` | Encodes gyro ODR/filter/noise-performance state; confirm whether low-noise performance is enabled. |
| `GYR_RANGE` at `0x43` | reset `0x00` | Default gyro range is `+-2000 dps`. |
| `PWR_CTRL` at `0x7D` | reset `0x00` | Sensors are disabled by default until the driver enables accel/gyro/temp/aux. |
| `PWR_CONF.adv_power_save` | inter-write delay at least `450 us` when enabled | Relevant to driver bring-up timing, not long-flight drift. |
| `SENSORTIME_0..2` | 24-bit counter, `39.0625 us/LSB` | Useful for checking real sample cadence and aligning IMU samples. |

## Offset And Sensitivity Compensation

Accelerometer manual offset compensation:

- 8-bit two's-complement offset registers.
- offset resolution: `3.9 mg`.
- offset range: `+-0.5 g`.
- independent of selected accelerometer range.

Gyroscope manual offset compensation:

- 10-bit two's-complement offset field per axis.
- offset resolution: `61 mdps`.
- offset range: `+-31 dps`.
- independent of selected gyroscope range.

Gyroscope sensitivity compensation:

- manual gain compensation uses rate ratio `omega_reference / omega_measured`.
- encoded as 11-bit fixed-point `1.10`.
- resolution: `2^-10 = 0.0009765`, about `0.09765 %`.
- range: `0.75` to `1.25`, or `1 +-25 %`.
- CRT can reduce gyroscope sensitivity error to typical `+-0.4 %` if run
  correctly while motionless.

These compensation mechanisms describe what the real BMI270 can correct
internally. For SITL realism, decide whether the aircraft's real driver/profile
uses these compensation features. If compensation is normally enabled, use the
post-compensation residual values, not raw worst-case values.

## Unit Conversions For SITL

Use standard gravity:

```text
g0 = 9.80665 m/s^2
1 mg = 0.001 g = 0.00980665 m/s^2
1 dps = pi / 180 rad/s = 0.0174532925199433 rad/s
1 mdps = 0.001 dps = 1.74532925199433e-5 rad/s
```

Candidate maximum static offsets from datasheet:

```text
accel_zero_g_offset_max = 20 mg
                         = 0.196133 m/s^2

gyro_zero_rate_offset_max = 0.5 dps
                           = 0.00872665 rad/s
```

Candidate temperature drift examples:

```text
accel_offset_temp_drift = 0.25 mg/K
                        = 0.00245166 m/s^2/K

gyro_offset_temp_drift = 0.015 dps/K
                       = 0.000261799 rad/s/K
```

Noise examples:

```text
accel_noise_density = 0.16 mg/sqrt(Hz)
                    = 0.00156906 m/s^2/sqrt(Hz)

accel_rms_200hz = 1.51 mg-rms
                = 0.014807 m/s^2 rms

gyro_noise_density_perf = 0.007 dps/sqrt(Hz)
                        = 0.000122173 rad/s/sqrt(Hz)

gyro_noise_density_norm = 0.010 dps/sqrt(Hz)
                        = 0.000174533 rad/s/sqrt(Hz)

gyro_rms_200hz_perf = 61.4 mdps-rms
                    = 0.00107156 rad/s rms

gyro_rms_200hz_norm = 87.7 mdps-rms
                    = 0.00153082 rad/s rms
```

## Candidate SITL Mapping

| Datasheet property | Candidate SITL parameter | Directness | Notes |
| --- | --- | --- | --- |
| Accelerometer constant offset | `SIM_ACC1_BIAS_X/Y/Z` | strong | SITL adds this vector to simulated accelerometer data. Use m/s^2. |
| Gyroscope constant offset | `SIM_GYR1_BIAS_X/Y/Z` | strong | SITL adds this vector to simulated gyro data. Use rad/s. |
| Accelerometer sensitivity error | `SIM_ACC1_SCAL_X/Y/Z` | medium-high | Source-confirmed name. Nonzero values divide accel by the configured scalar, so a desired +0.4% reported accel error uses about `0.996016`, not `1.004`. |
| Gyroscope sensitivity error | `SIM_GYR1_SCALE_X/Y/Z` | strong | Source-confirmed name. Values are percent; `2.0` means multiply that gyro axis by `1.02`. |
| Accelerometer RMS noise | `SIM_ACC1_RND` | weak/approximate | Source shows this is a throttle-gated vibration amplitude. By itself, with `SIM_VIB_FREQ=0` and `SIM_VIB_MOT_MAX=0`, it is not a direct white-noise injector. |
| Gyroscope RMS noise | `SIM_GYR1_RND` | weak/approximate | Source shows degrees/second converted to rad/s and scaled by throttle when motors are on; it feeds random or vibration paths, not a datasheet white-noise-density model. |
| Gyroscope drift | `SIM_DRIFT_SPEED`, `SIM_DRIFT_TIME` | approximate | SITL implements a synthetic triangular gyro drift waveform. Full source-code cycle is `2 * SIM_DRIFT_TIME`; datasheet gives offset and temperature behavior, not this waveform. |
| Temperature drift | no simple current overlay | weak | Could be approximated by choosing static hot/cold bias profiles. |
| Cross-axis sensitivity | no simple current overlay | weak | Needs custom sensor model or mount/orientation approximation. |
| Alignment error | model or orientation config | weak | Better treated as installation/mounting, not BMI270 internal noise. |
| g-sensitivity | no simple current overlay | weak | Important but not directly represented by current simple parameters. |

## Suggested IMU Profiles

### Profile 1: clean SITL reference

Purpose: distinguish GPS-free stack refusal from intentional IMU degradation.

```text
SIM_ACC1_BIAS_X 0
SIM_ACC1_BIAS_Y 0
SIM_ACC1_BIAS_Z 0
SIM_GYR1_BIAS_X 0
SIM_GYR1_BIAS_Y 0
SIM_GYR1_BIAS_Z 0
SIM_ACC1_RND 0
SIM_GYR1_RND 0
```

Keep default SITL background noise and gyro drift unless the experiment
explicitly resets `SIM_DRIFT_SPEED`.

### Profile 2: BMI270 typical 200 Hz normal mode

Purpose: keep datasheet noise values as analysis targets. This is not an
executable parameter profile by itself.

Use the datasheet RMS values as analysis targets first. Do not assume
`SIM_ACC1_RND` and `SIM_GYR1_RND` map exactly.

```text
target_accel_rms_noise_mps2 0.014807
target_gyro_rms_noise_radps 0.00153082
```

If a SITL approximation is required, choose conservative `SIM_ACC1_RND`,
`SIM_GYR1_RND`, `SIM_VIB_FREQ`, and/or `SIM_VIB_MOT_MAX` values and verify
realized IMU log RMS and spectrum in a stationary run. Do not claim BMI270
noise realism from direct datasheet-to-`*_RND` conversion alone.

### Profile 3: BMI270 datasheet maximum static offset

Purpose: worst-case static offset from the datasheet without temperature
extension.

Apply one axis at a time first:

```text
SIM_ACC1_BIAS_X 0.196133
SIM_ACC1_BIAS_Y 0
SIM_ACC1_BIAS_Z 0

SIM_GYR1_BIAS_X 0.00872665
SIM_GYR1_BIAS_Y 0
SIM_GYR1_BIAS_Z 0
```

Do not apply all worst-case axes at once for the first discovery run. A
one-axis ladder gives cleaner interpretation.

### Profile 4: hot/cold offset residuals

Purpose: approximate temperature-induced offset change using static profiles.

For a temperature delta `dT_K` from calibration/reference temperature:

```text
accel_bias_delta_mps2 = dT_K * 0.00245166
gyro_bias_delta_radps = dT_K * 0.000261799
```

Example for `+20 K`:

```text
accel_bias_delta_mps2 = 0.0490332
gyro_bias_delta_radps = 0.00523598
```

Treat this as an approximation. The current plan does not model continuous
temperature ramps.

## What The Datasheet Cannot Tell Us Alone

The datasheet does not fully determine the aircraft's realized IMU error
because installed behavior depends on:

- board layout and mechanical strain;
- vibration spectrum from motor and propeller;
- mounting orientation and alignment;
- temperature profile during flight;
- whether Bosch/BMI270 offset compensation is used;
- whether gyroscope CRT is run;
- driver ODR/range/filter choices in the real autopilot build;
- airframe-specific electromagnetic and power-supply environment.

Therefore, the best evidence hierarchy is:

1. source code and datasheet mapping;
2. stationary real-board log;
3. motor-on restrained real-board log;
4. SITL profile tuned to match those logs;
5. GPS-free behavior experiment.

## Immediate Follow-Up Questions

Before creating executable overlays, confirm:

1. Which BMI270 accelerometer range is used on the real autopilot?
2. Which BMI270 gyroscope range is used?
3. Which ODR and filter mode are used?
4. Is gyroscope performance mode enabled?
5. Is offset compensation enabled?
6. Is gyroscope CRT run?
7. Do we have stationary and motor-on IMU logs from the actual vehicle?
8. Which body axis should receive the first controlled bias dose?

Until those are known, use the clean profile and one-axis datasheet maximum
offset profiles only as bounded discovery cases.
