# Real-Flight IMU Analysis Implementation

## Runtime Home

Code (tracked since 2026-10-12; originally under `var/analysis/` at the
operator's request):

- `src/sim_ard_gaw/analysis/real_flight/analysis_core.py`: pure numerical
  helpers.
- `src/sim_ard_gaw/analysis/real_flight/analyze_flights.py`: the DataFlash
  analyzer. Reads `var/real_flights/` and writes to
  `var/analysis/real_flight_imu_analysis_20260901/results/` by default.
- `tests/unit/test_real_flight_analysis_core.py`: unit tests.

Working output stays local runtime output at
`var/analysis/real_flight_imu_analysis_20260901/`: a teaching guide, a
technical report, a CTO briefing outline, generated tables, and figures. No raw log or generated analysis artifact is promoted to tracked
evidence in this phase.

## Pipeline

1. A discovery pass records SHA-256 provenance, firmware, selected parameters,
   message capability, GPS data, mode/arm events, and the main airborne window.
2. The airborne window is the longest sustained primary-GPS-speed segment at
   or above 8 m/s, with gaps up to 30 s bridged and 2 s terminal context.
3. A measurement pass calculates phase-aware VIBE, clipping, redundant-IMU,
   GPS, EKF3, and post-filter batch-spectral metrics.
4. Every flight receives detailed CSV/JSON/PNG output. Compact summaries are
   concatenated into fleet-level tables.

## Scientific Boundaries

- `VIBE` supplies operational vibration magnitude; low-rate `IMU` acceleration
  is not relabeled as vibration.
- FFT is calculated only from internally complete `ISBH`/`ISBD` batches.
- The available batches use `INS_LOG_BAT_OPT=2`, so conclusions are explicitly
  post-filter only.
- Missing Shahin `XKF*` and batch messages are recorded as missing capability,
  not inferred values.
- Normal GPS-aided flights characterize present health and fusion residuals;
  they do not establish unaided drift endurance.

## Primary Generated Entries

- `results/analysis_manifest.json`
- `results/flight_inventory.csv`
- `results/fleet_vibration_summary.csv`
- `results/fleet_clip_events.csv`
- `results/fleet_imu_summary.csv`
- `results/fleet_gps_summary.csv`
- `results/fleet_ekf_summary.csv`
- `results/fleet_spectral_summary.csv`
- `results/flights/<flight_id>/`

The manifest records exact input hashes and method constants.
