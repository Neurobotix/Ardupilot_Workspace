# Workspace Status

Canonical path: `docs/operations/workspace_status.md`.

This workspace is the active production workspace for the governed ArduPilot +
Gazebo fault-injection and evidence workflows covered by
`governance/decisions/ADR-0005-workspace-next-cutover.md`.

## Current Platform

- Working lanes: `wind_matrix`, `airspeed_failure`, and `gps_failure`.
- Runtime output belongs under `var/`.
- Reviewed proof belongs under `evidence/` with dated reports, manifests,
  hashes, or curated artifacts.
- Local-only overlays, secrets, and notes belong under `.private/`.
- Governed Gazebo runs use
  `build/ardupilot_gazebo/libArduPilotPlugin.so`; installed plugin fallback is
  forbidden by
  `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`.

## Lane Status

| Lane | Current status | Primary docs |
| --- | --- | --- |
| `wind_matrix` | Staged `test_suite` path is the supported framework path; the wind-matrix legacy attempt strategy was retired on 2026-06-30. Direct runner files remain live operator entry points. Full-matrix evidence beyond bounded proof still needs dated evidence. | `docs/campaigns/wind_matrix.md`, `docs/operations/launch_targets.md` |
| `airspeed_failure` | Phase 2 measurement smoke and bounded Phase 4A ratio/ramp/pulse characterization are accepted; fixed-case repetition/full-lane acceptance remains open. | `docs/architecture/airspeed_failure_lane.md`, `docs/operations/airspeed_failure_runbook.md` |
| `gps_failure` | Phase 1 no-SITL foundation is accepted; corrected raw/live validation exists through bounded v4/v5 paths; active mission v6 is structurally tested only and unflown, with no curated Phase 2 claim promoted. | `docs/architecture/gps_failure_lane.md`, `docs/operations/gps_failure_runbook.md` |

## Open Evidence Gaps

- Non-core launch targets (`plane-airspeed-lidar`, `plane-altitude-wind`,
  `plane-rebuild`, `plane-staircase`) still need runtime evidence before they
  can be promoted beyond their current status.
- `copter-lidar` has handshake and flight proof, but no captured obstacle
  return.
- Wider wind-matrix campaign claims require new governed evidence.
- Airspeed fixed-case Phase 4B and GPS v6 live campaign claims remain open
  until dated evidence says otherwise.

## Historical Records

The workspace migration completed on 2026-05-24 under
`governance/decisions/ADR-0005-workspace-next-cutover.md` and
`evidence/reports/migration/CUTOVER_2026-05-24.md`. The final compatibility
wrapper removal completed on 2026-06-30 under
`evidence/reports/migration/PHASE_8_COMPAT_FINAL_REMOVAL_AUDIT_2026-06-30.md`,
and the wind-matrix legacy attempt strategy was retired the same day under
`evidence/reports/migration/WIND_MATRIX_LEGACY_STRATEGY_RETIREMENT_2026-06-30.md`.

Historical migration plans and phase records remain under
`governance/runbooks/migration/` and `evidence/reports/migration/`. They are
provenance, not the present-tense operating state.

## Rule For Future Work

Any change must update its designated home plus related docs, `.ai`, evidence,
and governance records. Use `governance/standards/change_control.md`.
