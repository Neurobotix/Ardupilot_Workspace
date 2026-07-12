# GPS Failure Runbook

Status: Phase 1 Chunk 3 is implemented pending review. The GPS failure lane has
the no-SITL plugin foundation, locked static mission and GPS parameter overlay,
and structural tests. Full Phase 1 remains open. No live SITL/Gazebo GPS
failure run, parameter readback, or curated evidence claim exists.

## Current State

- Phase 0 (design lock) accepted 2026-07-06.
- Phase 1 Chunks 1–2 provide plugin construction, case listing, payload
  conversion/previews, schema probing, dry-run JSON, and unit tests.
- Phase 1 Chunk 3 adds the locked mission, GPS overlay, default-stack
  integration, and static/no-SITL contract tests.
- No live run, live parameter readback, realized mission-duration validation,
  or curated evidence exists.

## Static Default Stack

- SITL target: `plane-cte`
- Gazebo target: `gazebo-plane-cte`
- Mission: `assets/missions/gps_failure_behavior_mission.waypoints`
- Params: `config/vehicles/plane_base.parm` + `config/overlays/plane_gps.parm`
  in that order.

The overlay pins the four EKF knee parameters, complete primary EKF source set,
and calm SITL wind. These checked-in values provide reproducible static inputs;
they do not prove the empirical knee. Live readback and realized straight-leg
duration remain Phase-2 requirements.

## No-SITL CLI

- `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` exists for
  no-SITL `--list-cases`, `--dry-run --case <case_id>`, and `--probe-schema`.
- Live GPS failure commands are unavailable in Phase 1; there is no
  live SITL/Gazebo launch path in this CLI yet.

Example no-SITL checks:

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --list-cases
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --probe-schema
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --dry-run --case slow_drift_0p5_mps --reference-latitude-deg -35.363262 --preview-elapsed-s 90
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_phase1.py
```

## Live-Run Gate (Phase 2)

Before any live matrix: read back every injected `SIM_GPS1_*` param, read live
`EK3_POS_I_GATE` / `EK3_GLITCH_RAD` / `FS_EKF_THRESH` / `EK3_GPS_CHECK`, and
confirm the straight-leg duration. See
`governance/runbooks/features/gps_failure_behavior/plan.md`.

## References

- Lane description: `docs/architecture/gps_failure_lane.md`
- Feature runbook: `governance/runbooks/features/gps_failure_behavior/`
