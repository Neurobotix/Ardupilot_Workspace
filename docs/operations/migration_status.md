# Migration Status

Current state: `workspace_next` is the production workspace for the governed
ArduPilot + Gazebo simulation workflows covered by
`governance/decisions/ADR-0005-workspace-next-cutover.md`. The old workspace
`/home/ahmed/ardupilot_workspace` is deprecated fallback/reference and must not
be edited without explicit operator authorization.

The migration is governed by:

- `governance/runbooks/migration/full_migration_plan.md`
- `governance/standards/change_control.md`
- `docs/operations/migration_status.md`
- `governance/runbooks/operations/shadow_parity.md`

## What Is Already Done

- Corporate directory structure exists.
- Runtime compatibility layer exists.
- Curated historical evidence was copied.
- Raw logs were not migrated.
- `.private/` is local-only and gitignored.
- Basic validation passed and is recorded in `evidence/reports/operations/VALIDATION_2026-05-19.md`.
- Phase 0 Foundation Freeze baseline is recorded in
  `evidence/reports/migration/PHASE_0_BASELINE_2026-05-20.md`.
- Phase 1 Structure Hardening is complete and recorded in
  `evidence/reports/migration/PHASE_1_STRUCTURE_2026-05-20.md`.
- Shared runtime facts formerly present in ignored private notes are promoted to
  `docs/operations/sitl_gazebo_runtime.md`.
- `make doctor` now enforces required top-level homes, symlinks, raw log
  leakage, nested private state, `.private/` policy, gitignore coverage, stale
  canonical references, and required migration-plan links.
- Phase 2 dependency unblock is complete: ignored local `src/ardupilot/`,
  `src/SITL_Models/`, and `env/` runtime dependencies are present for
  validation.
- Phase 2 Runtime Parity is PASS, recorded in
  `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`. Static checks pass
  and every required runtime smoke target proved a direct SITL/Gazebo/MAVLink
  handshake: `copter`, `copter-lidar`, `plane`, `plane-lidar`, `plane-cte`,
  the matching `gazebo-*` worlds, `bridge-plane`, `bridge-copter`, `logger`,
  and `cleanup`. `bridge-plane` proved an end-to-end LiDAR data path; `logger`
  captured live telemetry to `var/logs/flight_logger/`.
- Phase 2 caveat: `copter-lidar` proved the handshake but not a LiDAR obstacle
  return; non-core launch targets remain untested.
- Phase 3 Documentation Rebuild is complete, recorded in
  `evidence/reports/migration/PHASE_3_DOCS_2026-05-20.md`.
- Phase 4 Config And Asset Normalization is complete, recorded in
  `evidence/reports/migration/PHASE_4_CONFIG_ASSETS_2026-05-21.md`.
- Phase 5 Campaign And Test Migration is complete, recorded in
  `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`. Compatibility
  campaign runners remain, campaign safety helpers moved under
  `src/sim_ard_gaw/campaigns/`, a one-case tiny round-robin result was
  promoted to `evidence/curated_logs/phase5_tiny_rr_20260521/`. The first
  one-case `4,4` production-reference comparison remediation under
  `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/` is
  retained as plugin-fallback diagnostic evidence, not ArduPilot-side wind
  parity proof; the corrected workspace-plugin recheck is recorded in the
  Phase 5 report and
  `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`.
- Phase 6 Evidence And Operations is complete, recorded in
  `evidence/reports/migration/PHASE_6_EVIDENCE_OPS_2026-05-21.md`. The operator workflow
  is `docs/operations/evidence_workflow.md`, templates live under
  `evidence/templates/`, cross-phase proof is cataloged in
  `evidence/indexes/evidence_catalog.md`, and `make doctor` now includes the
  focused evidence validator.
- Phase 7 Cutover And Old Workspace Deprecation is PASS under accepted
  residuals, recorded in `evidence/reports/migration/CUTOVER_2026-05-24.md`,
  `evidence/reports/migration/shadow_parity_2026-05-24.md`, and
  `governance/decisions/ADR-0005-workspace-next-cutover.md`. The blocked
  2026-05-21 Phase 7 reports are superseded historical records.
- `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`
  now governs the Phase 7 runtime boundary: broad pre-run cleanup is the
  clean-run safety policy, and setup/launch/campaign runtime uses only the
  workspace-built Gazebo plugin.
- Phase 8 has retired the root compatibility symlink bridge from runtime path
  resolution and moved launch, bridge, analysis, wind-matrix runner, and
  campaign test-suite implementation ownership into organized
  `src/sim_ard_gaw/` homes. `compat_scripts/` remains wrapper-only for old
  imports and script paths. Evidence:
  `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`.

## What Is Not Done Yet

- Production dirty state from the Phase 0 baseline is not resolved.
- Non-core launch targets (`plane-airspeed-lidar`, `plane-altitude-wind`,
  `plane-rebuild`, `plane-staircase`) are not yet runtime-tested.
- `copter-lidar` LiDAR obstacle detection (handshake proven, obstacle return
  not captured).
- Full wind-matrix campaign evidence beyond the bounded Phase 5 tiny case.
- Thin compatibility wrappers remain in `src/sim_ard_gaw/compat_scripts/` for
  old imports and script paths.

## Phase 7 Cutover Decision

The Phase 7 readiness audit now closes as PASS with accepted residuals.
Structural validation, evidence guardrails, launch help, static imports, parity
tests, workspace-plugin proof, post-fix cleanup proof, representative plane
proof, and bounded x=4/y=4 square-and-loiter campaign proof are recorded in the
2026-05-24 reports.

Rollback guidance is ready at
`governance/runbooks/operations/workspace_cutover_rollback.md`. The old workspace remains
available only as deprecated fallback/reference after the accepted cutover ADR.

The cutover does not claim full wind-matrix readiness, full mission
landing/disarm campaign completion, non-core launch target runtime verification,
or full Phase 8 compatibility-wrapper removal.

## Rule For Future Work

Any change must update its designated home plus related docs, `.ai`, evidence,
and governance records. Use `governance/standards/change_control.md`.
