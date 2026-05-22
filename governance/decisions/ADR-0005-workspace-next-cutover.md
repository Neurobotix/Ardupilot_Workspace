# ADR-0005: Workspace Next Cutover

Date: 2026-05-24

Status: Accepted

## Context

Phase 7 decides whether `/home/ahmed/ardupilot_workspace_next` can become the
production workspace and whether `/home/ahmed/ardupilot_workspace` can move from
production reference to deprecated fallback.

Earlier Phase 7 evidence from 2026-05-21 was blocked because final proof had
not been rerun after the clean-run and workspace-plugin policy. ADR-0004 later
made broad pre-run cleanup the governed clean-run policy and made the
workspace-built Gazebo plugin the only accepted runtime plugin path.

On 2026-05-24, fresh final proof was captured under:

- `evidence/reports/migration/PHASE_7_REPROOF_2026-05-24.md`
- `evidence/reports/migration/shadow_parity_2026-05-24.md`
- `evidence/reports/migration/CUTOVER_2026-05-24.md`
- raw runtime output under `var/runs/phase7_final_20260524/`

The old workspace was not modified.

## Decision

Accept `/home/ahmed/ardupilot_workspace_next` as the production workspace for
the governed ArduPilot + Gazebo simulation workflows documented in the current
operations docs.

Move `/home/ahmed/ardupilot_workspace` to deprecated fallback/reference status.
It may be read for rollback or historical comparison, but it is not the active
production workspace after this decision.

Keep the Phase 8 compatibility boundary retained: `src/sim_ard_gaw/compat_scripts/`,
the `test_suite` compatibility wrappers, and organized symlink-backed views may
remain until Phase 8 replacement ownership and parity evidence are complete.

## Evidence Accepted

- `make doctor`, `make test-parity`, launch help, compile, import, and unit
  checks passed in the 2026-05-24 reproof and final validation.
- The runtime plugin proof selected only
  `build/ardupilot_gazebo/libArduPilotPlugin.so`, SHA-256
  `1d4089bb6306ecc602e484e9b4e3e77dfb7ecf6649a4292ba872f6d420415fc0`.
- A representative plane workflow proved fresh SITL/Gazebo/MAVLink operation.
- A final x=4, y=4 bounded campaign run completed the square and loiter phases,
  ran analysis, recorded parameter hashes, used no local parameter override,
  and strictly verified Gazebo wind topic echo.
- Post-fix cleanup proof captured live `gz sim`, `gz sim server`, and
  `gz sim gui` processes before cleanup, then recorded zero matching simulator
  processes after cleanup.

## Accepted Risks

- This cutover does not claim a full wind-matrix campaign pass.
- This cutover accepts square-and-loiter campaign proof for the Phase 7
  representative campaign gate; full landing/disarm completion remains outside
  the Phase 7 production boundary.
- Non-core launch targets such as `plane-airspeed-lidar`,
  `plane-altitude-wind`, `plane-rebuild`, and `plane-staircase` remain
  not-yet-runtime-tested unless later dated evidence says otherwise.
- `copter-lidar` obstacle return remains unproven; prior evidence proves the
  vehicle/bridge handshake and `DISTANCE_SENSOR` streaming only.
- The root repository still has no root commit. That is a repository lifecycle
  issue, not a blocker for the dated runtime/evidence cutover.
- Phase 8 compatibility retirement remains partial by design.

## Rollback

Use `governance/runbooks/operations/workspace_cutover_rollback.md` if a promoted workflow
fails after cutover. The old workspace is retained as deprecated fallback and
must not be edited unless a later operator decision explicitly authorizes that.

## Consequences

- Current production-status docs, `.ai` state, and evidence indexes must point
  to the 2026-05-24 cutover reports.
- The 2026-05-21 blocked Phase 7 reports remain historical and superseded.
- Future production claims must cite dated evidence from `workspace_next`.
