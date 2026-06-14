# Raw Data Index — Airspeed Failure Behavior 2026-06-11

All paths are workspace-relative, under `var/` (disposable runtime/analysis
homes; not tracked in git). If `var/` is cleaned, the curated CSV/JSON/PNG
artifacts in this package and the interim report remain the reviewed proof;
re-deriving them requires re-running the lane.

## Run roots (raw attempt trees, manifests, SITL state, .BIN logs)

Positive one-bias-per-flight sweep (3 accepted attempts each unless noted;
2026-06-08):

- `var/runs/airspeed_failure_behavior_ratio_p10_20260608T121445Z/`
- `var/runs/airspeed_failure_behavior_ratio_p20_20260608T124125Z/`
- `var/runs/airspeed_failure_behavior_ratio_p30_20260608T125821Z/`
- `var/runs/airspeed_failure_behavior_ratio_p40_20260608T142724Z/`
- `var/runs/airspeed_failure_behavior_ratio_p50_20260608T144048Z/`
- `var/runs/airspeed_failure_behavior_ratio_p60_20260608T145338Z/`
- `var/runs/airspeed_failure_behavior_ratio_p70_20260608T150628Z/`
- `var/runs/airspeed_failure_behavior_ratio_p80_20260608T151917Z/`
- `var/runs/airspeed_failure_behavior_ratio_p90_20260608T153204Z/`
- `var/runs/airspeed_failure_behavior_ratio_p100_20260608T154448Z/`
  (**2 accepted**: `attempt_002` failed pre-injection and does not count)

Negative one-bias-per-flight sweep (3 accepted attempts each; 2026-06-09):

- `var/runs/airspeed_failure_behavior_ratio_m10_20260609T103836Z/`
- `var/runs/airspeed_failure_behavior_ratio_m20_20260609T104931Z/`
- `var/runs/airspeed_failure_behavior_ratio_m30_20260609T110035Z/`
- `var/runs/airspeed_failure_behavior_ratio_m40_20260609T111108Z/`
- `var/runs/airspeed_failure_behavior_ratio_m50_20260609T111832Z/`

Within-flight experiments (1 accepted attempt each; 2026-06-10):

- `var/runs/airspeed_failure_behavior_ratio_bias_pulse_p10_to_p130_headwind_20260610T075155Z/`
  - BIN: `_sitl_state/ratio_bias_pulse_p10_to_p130_headwind/attempt_001/logs/00000001.BIN`
- `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p100_headwind_20260610T111134Z/`
  - BIN: `_sitl_state/ratio_bias_ramp_p10_to_p100_headwind/attempt_001/logs/00000001.BIN`
- `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p200_headwind_20260610T122611Z/`
  - BIN: `_sitl_state/ratio_bias_ramp_p10_to_p200_headwind/attempt_001/logs/00000001.BIN`

Excluded (not cited by this package):

- `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p100_headwind_20260609T133408Z/`
  — abandoned earlier ramp root with no manifest; superseded by the
  2026-06-10 run.

## Analysis packages (raw derived output the curated files were copied from)

- `var/analysis/airspeed_failure_ratio_sweep_20260609T074109Z/` (positive side)
- `var/analysis/airspeed_failure_ratio_sweep_full_20260611T000000Z/`
  (full signed sweep; generator script retained in the directory)
- `var/analysis/airspeed_failure_pulse_ladder_bin_20260610T075155Z/`
- `var/analysis/airspeed_failure_pulse_ladder_health_20260611T000000Z/`
  (ARSP U/H/Hp/TR per window; generator script retained in the directory)
- `var/analysis/airspeed_failure_ramp_p10_to_p100_headwind_20260610T111134Z_bin/`
- `var/analysis/airspeed_failure_ramp_p10_to_p200_headwind_20260610T122611Z_bin/`
- `var/analysis/airspeed_failure_ramp_repro_p100_vs_p200_overlap_20260610T122611Z_bin/`

Note: the generator scripts for the 2026-06-09/10 analysis packages were not
retained; their outputs are reproducible from the raw run artifacts and BIN
logs above. The two 2026-06-11 packages retain their generator scripts.

## Accepted-attempt accounting

47 accepted observations total: 44 sweep attempts (15 bias levels), 1 pulse
ladder, 1 standard ramp, 1 extended ramp. Acceptance per attempt was verified
against `manifest.json` rows plus per-attempt `airspeed_injection.json`
(readback ok, reset ok), `reference_wind.json` (verified echo), and the
required artifact set on 2026-06-11.
