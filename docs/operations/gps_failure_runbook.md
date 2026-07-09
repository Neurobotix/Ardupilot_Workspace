# GPS Failure Runbook

Status: Phase 1 Chunk 1 no-SITL foundation. The GPS failure lane has a plugin
skeleton, deterministic case catalog, registry entry, and dry-run CLI. There is
still no live SITL/Gazebo GPS failure run, mission asset, GPS parameter overlay,
or curated evidence claim.

## Current State

- Phase 0 (design lock) accepted 2026-07-06.
- Phase 1 Chunk 1 no-SITL code exists for `gps_failure`: plugin construction,
  case listing, schema probe, dry-run JSON, and unit tests.
- No live mission, `config/overlays/plane_gps.parm`, or curated evidence exists
  yet.

## Planned Stack (from the design lock)

- SITL target: `plane-cte`
- Gazebo target: `gazebo-plane-cte`
- Mission: `assets/missions/gps_failure_behavior_mission.waypoints` (future;
  not created in Phase 1 Chunk 1)
- Params: `config/vehicles/plane_base.parm` + `config/overlays/plane_gps.parm`
  (planned by ADR-0021; `plane_gps.parm` is not created in Phase 1 Chunk 1)

## No-SITL CLI

- `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` exists for
  no-SITL `--list-cases`, `--dry-run --case <case_id>`, and `--probe-schema`.
- Live GPS failure commands are unavailable in Phase 1 Chunk 1; there is no
  live SITL/Gazebo launch path in this CLI yet.

Example no-SITL checks:

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --list-cases
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --dry-run --case hard_denial_15s
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
