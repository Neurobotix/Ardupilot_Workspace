# Airspeed Failure Behavior Evidence Pointers

Phase 2 live measurement smoke is accepted from raw runtime output. The
operator-directed 2026-06-11 curated package is accepted for bounded Phase 4A
ratio/ramp/pulse characterization by the 2026-06-14 acceptance report.
Fixed-case repetitions remain open as Phase 4B, and full-lane acceptance is not
closed.

## Raw Run Roots

Raw runtime output must use:

```text
var/runs/airspeed_failure_behavior_*
```

Accepted Phase 2 measurement-smoke raw root:

```text
var/runs/airspeed_failure_behavior_20260606T164050810132Z/
```

Phase 4A 2026-06-11 analysis raw roots are listed in:

```text
evidence/curated_logs/airspeed_failure_behavior_2026-06-11/raw_data_index.md
```

## Curated Packages

Curated proof should use:

```text
evidence/curated_logs/airspeed_failure_behavior_<date>/
```

Existing Phase 4A package:

```text
evidence/curated_logs/airspeed_failure_behavior_2026-06-11/
```

It includes selected summaries/manifests only, not raw runtime trees, and
supports bounded ratio/ramp/pulse characterization rather than fixed-case or
full-lane acceptance.

## Evidence Reports

Dated evidence reports should use:

```text
evidence/reports/features/<date>_airspeed_failure_behavior.md
```

Existing interim report:

```text
evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md
```

Bounded Phase 4A acceptance report:

```text
evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md
```

A final fixed-case/full-lane Phase 4B report, if created later, must include the exact commands,
date/time and timezone, raw run roots, effective parameter stack and hashes,
fixed wind vector/frame/readback, case payloads, accepted-observation counts,
behavior-class counts, observation-quality counts, limitations, and
old-workspace modification statement.

## Remaining Closure Requirements

Under the current Phase 3 contract, the lane still needs three accepted
observations per fixed case or a documented governance-consistent revision of
that contract. Current fixed-case evidence is limited to one accepted Phase 2
measurement-smoke observation each for `healthy_reference`, `ofs_noop_probe`,
`pitot_500pa`, and `fail_primary`; `noise_5` and `noise_10` have no accepted
live observations in the curated/current evidence set.

The 2026-06-11 package covers 47 accepted observations from signed ratio-bias
sweep, headwind pulse ladder, and headwind stepped ramps. The 2026-06-14
acceptance report closes that bounded scope as Phase 4A. It does not close
fixed-case repetition coverage.

## Required Attempt Artifacts

Each live attempt must produce or explicitly mark unavailable:

- `run_config.json`
- `reference_wind.json`
- `airspeed_injection.json`
- `airspeed_behavior_summary.json`
- `airspeed_signal_metrics.json` or `airspeed_signal_metrics.csv`
- `mission_progress.json`
- `mode_timeline.json` or `mode_timeline.csv`
- `altitude_speed_envelope.json`
- `tecs_response.json` when source log fields are available

Existing CTE/square analysis may be linked only as optional supporting context.
It is not the primary evidence for this lane.

## Supporting Existing Evidence

These files support the candidate decision and implementation design. They are
not accepted behavior results for Phase 3 or Phase 4 by themselves.

- Airspeed chain follow-up:
  `evidence/curated_logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md`
- Sensor-failure parameter research:
  `evidence/curated_logs/011_Sensor_Failure_Injection/sitl_sensor_failure_params.agent.json`
- Default mission (new, purpose-built for this lane):
  `assets/missions/airspeed_failure_behavior_mission.waypoints`. The legacy
  `assets/missions/airspeed_validation_mission.waypoints` is the old integration
  mission and is not used by this lane.
- Design research and ADR detail (locked decisions, 2026-06-03):
  `governance/runbooks/features/airspeed_failure_behavior/design_research.md`,
  `.../design_adrs.md`
- Accepted decisions (promoted 2026-06-03):
  `governance/decisions/ADR-0006-airspeed-failure-mission-design.md` ..
  `ADR-0011-airspeed-failure-behavior-classification.md`
- Default airspeed overlay (conservative production-like 14/10/22, restored
  2026-06-03): `config/overlays/plane_airspeed.parm`. The aggressive high-wind
  CTE tuning that previously lived here is now the separately named, non-default
  stress overlay `config/overlays/plane_airspeed_cte_high_wind_aggressive.parm`.
- Current ArduPilot airspeed SITL parameter source:
  `src/ardupilot/libraries/SITL/SITL_Airspeed.cpp`

## Evidence Rules

- Runtime logs stay under `var/`.
- Curated proof goes under `evidence/curated_logs/`.
- Dated reports go under `evidence/reports/features/`.
- Code, generated scripts, and transient analysis output do not belong in
  `evidence/`.
- A run can be an accepted behavior observation even when the aircraft behavior
  is degraded or bad, provided injection and analysis are complete.
- Failed launch, failed injection readback, failed reset, unverified fixed wind,
  pre-injection failure, or incomplete required artifacts do not count as
  accepted behavior observations.
