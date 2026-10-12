# Real-Flight IMU Analysis Plan

## Objective

Characterize IMU vibration and INS/EKF behavior in the five supplied real-flight
ArduPilot DataFlash logs for B73, Shahin fuel, Shahin electrical, and Shaba7.
The immediate deliverable is a reviewable working analysis for a CTO briefing,
not a GPS-denied performance claim.

## Inputs

Raw logs are read in place from `var/real_flights/` (renamed from
`var/Real-Flights/` on 2026-10-12; file names now use the flight slugs, for
example `2026-07-29_105334_b73_2.bin`). They remain untracked runtime data. The analysis must record each input's size and SHA-256 hash so
that every result can be traced to an exact log.

## Output Boundary

Decoded working tables, figures, and draft reports live under
`var/analysis/real_flight_imu_analysis_20260901/`. Nothing is promoted to
`evidence/` in this phase.

Since 2026-10-12 the analysis code is tracked: `analysis_core.py` and
`analyze_flights.py` live in `src/sim_ard_gaw/analysis/real_flight/`, and the
unit tests in `tests/unit/test_real_flight_analysis_core.py`. The original
operator request kept them under `var/analysis/`.

## Analysis Questions

1. What IMU, vibration, raw/batch-sampling, and EKF messages exist in each log,
   and at what usable rates?
2. During automatically detected airborne intervals, how large are VIBE X/Y/Z,
   how often do they cross the ArduPilot guidance bands, and do accelerometer
   clipping counters increase?
3. Where batch-sampled IMU data exists, what dominant accelerometer and gyro
   spectral components are visible, and how do they vary with flight time?
4. What do redundant IMUs show: consistency, temperature range, error counters,
   clipping, and sensor-instance availability?
5. Where EKF3 messages exist, what do innovations, test ratios, reset counters,
   filter status, and estimated IMU bias indicate under normal GPS-aided flight?
6. Which comparisons are valid across aircraft, and which are confounded by
   firmware/logging differences, flight duration, maneuvers, or absent fields?

## Method Rules

- Separate whole-log, armed, and airborne statistics; use airborne statistics
  for the main vibration comparison.
- Treat published ArduPilot vibration levels as operational guidance, not an
  aircraft certification boundary.
- Do not infer high-frequency spectral health from the low-rate `IMU` message.
  Report spectra only from `ISBH`/`ISBD` batches whose timing and sample-rate
  metadata are internally consistent.
- Do not emulate GPS denial by simply double-integrating logged acceleration.
  GPS-aided logs can characterize current sensor/fusion behavior but cannot
  validate unaided position endurance.
- Quantify missing data explicitly. Do not silently compare unlike message sets.
- Keep English/Arabic narrative interpretation separate from machine-generated
  numeric tables.

## Deliverables

- Re-runnable Python command-line analysis under the output boundary.
- Unit tests for the pure numerical and interval-selection functions.
- Per-flight and fleet-level CSV/JSON summaries with provenance.
- Time-series and spectral PNG figures.
- A bilingual Markdown technical report and a concise CTO presentation outline.
- A teaching guide explaining each script/function, the engineering reasoning,
  common traps, and how to extend the analysis.

## Completion Checks

- Run unit tests for the analysis code.
- Run the analysis against all five logs without parser failure.
- Reconcile generated flight inventory against the five supplied files.
- Inspect representative plots for readability and numeric consistency.
- Run `make doctor` because this plan adds governance structure.

## Limits And Follow-Up

This phase is observational. It cannot establish GPS-denied drift rate without
a governed experiment that supplies truth independent of the estimator and a
defined denial interval. Any recommendation for a later test campaign must be
presented as a proposal, not as a result of these normal GPS-aided flights.
