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

## Future Evidence Report

After acceptance, the dated evidence report should use:

```text
evidence/reports/features/<date>_airspeed_failure_behavior.md
```

## Supporting Existing Evidence

These files support the candidate decision and implementation design. They are
not accepted evidence for the airspeed failure behavior plugin itself.

- Airspeed chain follow-up:
  `evidence/curated_logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md`
- Sensor-failure parameter research:
  `evidence/curated_logs/011_Sensor_Failure_Injection/sitl_sensor_failure_params.agent.json`
- Default mission:
  `assets/missions/airspeed_validation_mission.waypoints`
- Airspeed overlay:
  `config/overlays/plane_airspeed.parm`

## Evidence Rules

- Runtime logs stay under `var/`.
- Curated proof goes under `evidence/curated_logs/`.
- Dated reports go under `evidence/reports/features/`.
- Code, generated scripts, and transient analysis output do not belong in
  `evidence/`.
- A run can be an accepted behavior observation even when the aircraft behavior
  is degraded or bad, provided injection and analysis are complete.
