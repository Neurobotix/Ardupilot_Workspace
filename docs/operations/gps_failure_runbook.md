# GPS Failure Runbook

Status: Phase 1 no-SITL foundation is **Accepted** (2026-07-13, final no-SITL
review). The GPS failure lane has the no-SITL plugin foundation, locked static
mission and GPS parameter overlay, structural tests, a synthetic no-SITL
mechanism gate, a fake-testable runtime/MAVLink parameter contract, and
integration-readiness wiring into the shared suite path. A pre-smoke Phase 2
implementation path now exists for later authorized live smoke, including
explicit telemetry/source-contract helpers, production mission-adapter wiring,
cleanup hardening, and decoded-record BIN analysis helpers. Phase 2 live smoke
remains unverified: no live SITL/Gazebo GPS failure run, real parameter
readback, real mission timing, real BIN/log parsing, or curated evidence claim
exists. A strict pre-smoke review rejected the initial live path; its fixes were
implemented and no-live tested, then a fresh strict no-live review on 2026-07-14
found no remaining BLOCKER or HIGH finding and accepted the exact corrected
diff for the single nominal live smoke. That acceptance is not a live result.

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
  the artifact schema, and atomic MAVLink batch prevalidation. Pre-smoke Phase 2
  remains unaccepted until authorized live smoke supplies dated evidence.
- No live run, live parameter readback, realized mission-duration validation,
  real BIN/log parsing, or curated evidence exists.
- The guarded live path now constructs mission control from the live MAVLink
  master and gates mechanism acceptance on the EKF/GPS source contract, but
  those paths remain no-SITL/fake tested only until authorized smoke.
- Pre-smoke hardening now waits for the Plane target's cleanup barrier before
  starting Gazebo, requires fresh heartbeat/SIMSTATE trigger evidence, latches
  one injection attempt, gates on every write/restore and verified cleanup,
  scopes behavior/BIN analysis to the injection window, and makes the CLI stop
  on the first non-accepted terminal record. These are no-live implementation
  facts, not smoke evidence.

## Static Default Stack

- SITL target: `plane-gps` (dedicated GPS failure identity)
- Gazebo target: `gazebo-plane-gps` (dedicated GPS failure identity)
- Mission: `assets/missions/gps_failure_behavior_mission.waypoints`
- Params: `config/vehicles/plane_base.parm` + `config/overlays/plane_gps.parm`
  in that order, with no airspeed overlay and no local plane override.

The overlay pins the four EKF knee parameters, complete primary EKF source set,
and calm SITL wind. These checked-in values provide reproducible static inputs;
they do not prove the empirical knee. Live readback and realized straight-leg
duration remain Phase-2 requirements.

### Dedicated launch identities (structural only, corrected 2026-07-13)

`plane-gps` and `gazebo-plane-gps` exist structurally in the governed launcher
and are **not** the CTE/airspeed targets:

- `plane-gps` loads exactly `plane_base.parm -> plane_gps.parm`. It does not
  load `plane_airspeed.parm` and does not append
  `.private/config/plane_params.local.parm` (the local override is excluded
  unconditionally and the launcher prints that exclusion). It wipes EEPROM, uses
  `var/runs/sitl/plane-gps` and a `plane-gps` MAVProxy identity, and emits
  `udp:127.0.0.1:14551`.
- `gazebo-plane-gps` reuses the sensor-neutral base runway world
  `assets/worlds/mini_talon_runway.sdf` (GPS/NavSat, calm, no wind publisher, no
  airspeed sensor, no LiDAR bridge). It is a dedicated target, not an alias of
  `gazebo-plane`.
- Using the earlier `plane-cte` / `gazebo-plane-cte` for GPS was unsafe: those
  load the airspeed overlay and the local override, a different stack than this
  contract. See ADR-0021 (2026-07-13 amendment).

These targets are structurally implemented and covered by no-SITL structural
tests only. They have **not** been live-smoke verified; no live GPS failure run,
parameter readback, or evidence claim exists. Phase 2 remains pending.

## No-SITL CLI

- `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` exists for
  no-SITL `--list-cases`, `--dry-run --case <case_id>`, `--probe-schema`, and
  `--preflight` (integration-readiness report).
- A guarded Phase 2 smoke runner exists for the protected smoke slice only:
  `--live-phase2-smoke --confirm-live-phase2`, or
  `--live-case <case> --confirm-live-phase2` for one of the protected cases
  below. Do not run it without explicit live-smoke authorization.
- `--phase2-smoke-plan` is plan-only and does not start SITL/Gazebo or open
  MAVLink.

Example no-SITL and guard checks (the `--live-case nominal` command without
confirmation must fail before launch):

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --list-cases
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --probe-schema
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --preflight
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --phase2-smoke-plan
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --live-case nominal
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --dry-run --case slow_drift_0p5_mps --reference-latitude-deg -35.363262 --preview-elapsed-s 90
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_mavlink.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_phase2_path.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_phase1.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_mechanism_gate.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_readiness.py
```

## Live-Run Gate (Phase 2)

Before any live matrix: read back every injected `SIM_GPS1_*` param, read live
`EK3_POS_I_GATE` / `EK3_GLITCH_RAD` / `FS_EKF_THRESH` / `EK3_GPS_CHECK` plus
`EK3_SRC1_POSXY` / `EK3_SRC1_VELXY` / `EK3_SRC1_POSZ` / `EK3_SRC1_VELZ` /
`EK3_SRC1_YAW`, require `EK3_GLITCH_RAD > 0`, integral source enums, and EKF
absolute-position status flags as the validated GPS-aiding proxy, and confirm
the exact checked-in source set (`3/3/1/3/1`) and knee values plus the
straight-leg duration. Trigger authorization additionally requires fresh,
co-temporal heartbeat and SIMSTATE evidence; cleanup, all scheduled operations,
and an accepted terminal record must succeed. See
`governance/runbooks/features/gps_failure_behavior/plan.md`.

Protected Phase 2 smoke implementation slice:

- `nominal`
- `slow_drift_0p5_mps`
- `hard_denial_15s`

The full Phase 3 matrix remains gated; do not infer that `--phase2-smoke-plan`
or the protected Phase 2 live flags authorize a full matrix run.

## References

- Lane description: `docs/architecture/gps_failure_lane.md`
- Feature runbook: `governance/runbooks/features/gps_failure_behavior/`
