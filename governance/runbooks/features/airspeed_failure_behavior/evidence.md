# Airspeed Failure Behavior Evidence Pointers

No accepted airspeed failure behavior evidence yet.

## Future Raw Run Roots

Raw runtime output must use:

```text
var/runs/airspeed_failure_behavior_*
```

## Future Curated Package

After acceptance, curated proof should use:

```text
evidence/curated_logs/airspeed_failure_behavior_<date>/
```

The curated package should include selected summaries/manifests only, not raw
runtime trees. Expected selected artifacts include campaign summary, manifest
snapshot, run-config or provenance summaries, and representative bounded
attempt artifacts needed to support the report.

## Future Evidence Report

After acceptance, the dated evidence report should use:

```text
evidence/reports/features/<date>_airspeed_failure_behavior.md
```

The report must include the exact commands, date/time and timezone, raw run
roots, effective parameter stack and hashes, fixed wind vector/frame/readback,
case payloads, accepted-observation counts, behavior-class counts,
observation-quality counts, limitations, and old-workspace modification
statement.

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
not accepted evidence for the airspeed failure behavior plugin itself.

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
