# Tailwind Pulse Evaluator Correction and Reanalysis

Date: 2026-06-23 UTC  
Scope: airspeed-failure protected tailwind pulse evaluator and two-attempt offline reanalysis  
Status: **PASS for evaluator correction and corrected interpretation of these two attempts**

## Scope

This work corrects three post-flight analysis defects found while reviewing
`var/runs/tailwind_standard_speed15_pulse_p130_n1/`:

1. wall-clock schedule timestamps were compared directly with the SITL BIN
   clock, which drifted by 10-61 seconds across these attempts;
2. `ARSP.U=1` was treated as proof that AHRS was using the sensor, although the
   actual logged source is `CTUN.AsT` and can switch to synthetic airspeed
   before `ARSP.U` changes;
3. only the final pulse was evaluated, so the rejection and disable thresholds
   across the 13-window ladder were not reported.

The corrected implementation uses in-BIN `SIM_ARSPD_RATIO` `PARM` transitions
as window boundaries, requires `CTUN.AsT=1` for raw-to-believed mechanism rows,
and records both the first AHRS source rejection and first `ARSP.U` parameter
disable across every fault window.

## Raw and Curated Inputs

- Raw root: `var/runs/tailwind_standard_speed15_pulse_p130_n1/`
- Working reanalysis:
  `var/analysis/tailwind_standard_speed15_pulse_p130_reanalysis_20260623/`
- Curated summary:
  `evidence/curated_logs/airspeed_failure_tailwind_pulse_reanalysis_2026-06-23/`

The raw root and original manifests remain unchanged. The original manifests
retain their historical false-negative `sensor_rejected_before_verification`
verdicts; this report and curated summary are the additive correction record.

## Corrected Results

| Attempt | Corrected status | Clamp rows | Mean clamp error | First AHRS source rejection | First ARSP disable | Fault windows / errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `clamp_verified` | 10 | 0.462 m/s | +50% | +60% | 13 / 0 |
| 2 | `clamp_verified` | 11 | 0.390 m/s | +50% | +60% | 13 / 0 |

The protected clamp tolerance is 2.0 m/s. Both attempts also pass:

- `AHRS_WIND_MAX=15` readback;
- TECS 15 m/s commanded-cruise consistency;
- at least 10 aligned `CTUN.AsT=1` rows in the representative +130% window.

The corrected result therefore treats both attempts as valid, interpretable
degraded observations. No rerun is required for these two attempts.

## Commands

```bash
source setup.bash
./env/bin/python3 \
  var/analysis/tailwind_standard_speed15_pulse_p130_reanalysis_20260623/reanalyze.py

./env/bin/python3 -m unittest \
  tests.unit.test_airspeed_mechanism_gate \
  tests.unit.test_airspeed_tailwind_phase2

pyright \
  src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/mechanism_gate.py \
  src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/analyzers.py \
  tests/unit/test_airspeed_mechanism_gate.py

make doctor
```

## Validation

- Mechanism-gate and tailwind suites: **28 tests passed**.
- Airspeed Phase 1, campaign contracts, generic manifest, and staged-attempt
  regression suites: **90 tests passed**.
- Targeted `pyright`: **0 errors, 0 warnings**.
- Targeted `compileall`: **PASS**.
- `git diff --check`: **PASS**.
- `make doctor`: **PASS**, including evidence catalog and curated-root checks.

## Limitations

- This is offline analysis of two SITL attempts, not new live evidence.
- The result validates mechanism interpretation, not flight safety.
- The remaining tailwind ramp/configuration attempts are not covered here.
- Historical raw manifests are intentionally immutable; consumers must follow
  this dated correction record for the accepted interpretation.

## Old Workspace Statement

`/home/ahmed/ardupilot_workspace` was not modified.
