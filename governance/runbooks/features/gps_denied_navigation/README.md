# GPS-Denied Navigation — Feature Bundle

Start here to find every file that belongs to the GPS-denied navigation study.

Feature slug: `gps_denied_navigation`
Current status: home created 2026-10-12; study plan written 2026-10-12
(`plan.md`), Phase 0 data collection open. No GPS-denied result, claim, or
evidence exists yet. The INS-only
implementation that was started in August is preserved, unmerged, on the
branch `archive/ins-only-stash`.

## Read Order

1. `plan.md` — goal, phases, Phase 1 test matrix, metrics, outdoor safety
   rules, roles, open decisions, task tracker.
2. `data_request.md` — Phase 0 data request to the field engineers.
3. `ins_only_plan.md` — INS-only IMU characterization plan (August draft).
4. `design_research.md` — reading notes on the two EKF / GPS-denied papers.
5. `imu_sitl_source_validation.md` — how ArduPilot SITL simulates the IMU.
6. `bmi270_datasheet_extract.md` — BMI270 IMU datasheet values used for
   realistic noise and bias profiles.
7. `implementation.md` — code, config, asset, and runtime homes.
8. `review.md` — acceptance records (none yet).

## This Bundle

| File | Purpose |
| --- | --- |
| `plan.md` | Study plan (2026-10-12) |
| `data_request.md` | Phase 0 data request: aircraft performance, hardware, configuration, flight logs, future logging |
| `ins_only_plan.md` | INS-only IMU characterization plan; moved from `gps_failure_behavior/ins_only_imu_characterization_plan.md` |
| `design_research.md` | Paper notes; moved from `docs/presentations/ekf_gps_denied/paper_notes.md` |
| `imu_sitl_source_validation.md` | SITL IMU source walk-through; moved from `gps_failure_behavior/` |
| `bmi270_datasheet_extract.md` | BMI270 datasheet extract; moved from `gps_failure_behavior/` |
| `implementation.md` | Homes and the state of the recovered implementation |
| `review.md` | Review and acceptance records |

## Related Homes

| Path | What it is |
| --- | --- |
| `config/overlays/plane_gps_ins_only.parm` | INS-only parameter overlay (`ins_only_no_gps` envelope) |
| `assets/worlds/mini_talon_gps_ins_only_runway.sdf` | INS-only runway world |
| `assets/models/mini_talon_ins_only/` | Mini Talon model for the INS-only world |
| `src/sim_ard_gaw/analysis/real_flight/` | Real-flight DataFlash analysis code (IMU vibration, redundant IMUs, EKF3) |
| `tests/unit/test_real_flight_analysis_core.py` | Unit tests for that analysis |
| `governance/runbooks/features/real_flight_imu_analysis/` | Separate study: five-flight IMU vibration baseline that feeds this one |
| `governance/runbooks/features/gps_failure_behavior/` | GPS fault-injection campaign lane; the source of the INS-only discovery work |
| `docs/presentations/ekf_gps_denied/` | EKF / GPS-denied deck (gitignored, local only) |
| `var/real_flights/` | Raw real-flight `.bin` logs (ignored; renamed from `var/Real-Flights/` on 2026-10-12), plus `2025-12-30_094938_shahin_e_flight_information.pdf`: data-request items A to C answered from the Shahin-E log (kept local, not in git) |
| `src/sim_ard_gaw/analysis/real_flight/shahin_flight_envelope.py` | Extracts the Shahin-E flight envelope (params, level flight, turns, climbs, wind) as SITL model targets |
| `var/analysis/real_flight_imu_analysis_20260901/` | Real-flight analysis working output and reports (ignored) |
| `var/research/ekf_papers/` | Extracted text and page renders of the two papers (ignored) |
| `var/runs/gps_denied_navigation/` | Runtime output for this study (ignored); holds the two 2026-08-03 INS-only discovery runs |
| branch `archive/ins-only-stash` | Recovered INS-only implementation (27 tracked files); see `implementation.md` |
