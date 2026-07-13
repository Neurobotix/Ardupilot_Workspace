# GPS Failure Runbook

Status: Phase 1 Chunk 6 is implemented pending review. The GPS failure lane has
the no-SITL plugin foundation, locked static mission and GPS parameter overlay,
structural tests, a synthetic no-SITL mechanism gate, a fake-testable
runtime/MAVLink parameter contract, and integration-readiness wiring into the
shared suite path (a `--preflight` readiness report). Full Phase 1 remains open.
No live SITL/Gazebo GPS failure run, real parameter readback, BIN/log parsing,
or curated evidence claim exists.

## Current State

- Phase 0 (design lock) accepted 2026-07-06.
- Phase 1 Chunks 1–2 provide plugin construction, case listing, payload
  conversion/previews, schema probing, dry-run JSON, and unit tests.
- Phase 1 Chunk 3 adds the locked mission, GPS overlay, default-stack
  integration, and static/no-SITL contract tests.
- Phase 1 Chunk 4 adds `mechanism_gate.py`, a synthetic-record evaluator for
  the ADR-0018 `posTestRatio >= 1.0` mechanism boundary.
- Phase 1 Chunk 5 adds `mavlink.py` and `runtime.py` for deterministic
  parameter write/readback contracts and trigger-metadata-based injection plans.
  Unit tests use fakes only; no live MAVLink connection is opened.
- Phase 1 Chunk 6 adds `readiness.py` and the `--preflight` CLI action, wiring
  the lane into the shared suite path and emitting a no-SITL readiness report
  (`ready_for_live_run=false` with explicit live blockers).
- A 2026-07-13 strict-review pass resolved six confirmed Phase-1 BLOCKERs
  (no-SITL, with regression tests): ADR-0020 trigger-gated executable injection
  plans with preview strictly non-executable, substantive behavior evidence in
  the analyzer, contradiction-safe manifest acceptance, `gps_injection.json` in
  the artifact schema, and atomic MAVLink batch prevalidation. Acceptance is
  still pending remaining review findings.
- No live run, live parameter readback, realized mission-duration validation,
  BIN/log parsing, or curated evidence exists.

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
  no-SITL `--list-cases`, `--dry-run --case <case_id>`, `--probe-schema`, and
  `--preflight` (integration-readiness report).
- Live GPS failure commands are unavailable in Phase 1; there is no
  live SITL/Gazebo launch path in this CLI yet.

Example no-SITL checks:

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --list-cases
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --probe-schema
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --preflight
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --dry-run --case slow_drift_0p5_mps --reference-latitude-deg -35.363262 --preview-elapsed-s 90
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_mavlink.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_phase1.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_mechanism_gate.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_readiness.py
```

## Live-Run Gate (Phase 2)

Before any live matrix: read back every injected `SIM_GPS1_*` param, read live
`EK3_POS_I_GATE` / `EK3_GLITCH_RAD` / `FS_EKF_THRESH` / `EK3_GPS_CHECK`, and
confirm the straight-leg duration. See
`governance/runbooks/features/gps_failure_behavior/plan.md`.

## References

- Lane description: `docs/architecture/gps_failure_lane.md`
- Feature runbook: `governance/runbooks/features/gps_failure_behavior/`
