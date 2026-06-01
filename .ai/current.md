# Current Work

Status: Phase 7 cutover is PASS as of 2026-05-24. `workspace_next` is the
production workspace for the governed ArduPilot + Gazebo simulation workflows
covered by `governance/decisions/ADR-0005-workspace-next-cutover.md`. The old
workspace `/home/ahmed/ardupilot_workspace` is deprecated fallback/reference
and must not be edited without explicit operator authorization.

`ADR-0004` remains the clean-run and workspace-plugin policy: broad pre-run
cleanup is required for governed runs, and Gazebo runtime must use only the
workspace-built plugin. Launch and wind-matrix entrypoints fail closed when
that plugin build is missing. Phase 6 evidence and operations, Phase 5
campaign/test migration, Phase 4 config and asset normalization, Phase 3
documentation rebuild, and Phase 2 runtime parity remain PASS.
Phase 8 retired the old root compatibility symlink bridge from live runtime
path resolution and moved launch, bridge, analysis, wind-matrix runner, and
campaign test-suite implementation ownership into organized
`src/sim_ard_gaw/` homes. `compat_scripts/` remains wrapper-only for old imports
and script paths. Evidence:
`evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`.

Active feature work: the `test_suite` migration completed its Phase 3 sequence
(3A–3G) on 2026-06-01. The staged `wind_matrix` plugin is fully zero-legacy
(environment, MAVLink control/monitor, and wind injection all plugin-owned) and
was live-proven against the retained legacy tool run directly; the Phase 3G gate
is accepted and Phase 4 (one second non-wind plugin, zero framework-core edits)
is unblocked. Phase 5 (legacy script retirement) still requires Phase 4. See
`governance/runbooks/features/test_suite_migration/` and
`evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md`.

Active plan:

- `governance/runbooks/migration/full_migration_plan.md`
- `governance/standards/change_control.md`
- `docs/operations/migration_status.md`

Next required work:

1. Smoke-test the non-core launch targets (`plane-airspeed-lidar`,
   `plane-altitude-wind`, `plane-rebuild`, `plane-staircase`).
2. Capture a `copter-lidar` LiDAR obstacle return (handshake already proven).
3. Capture full wind-matrix evidence if that broader claim is needed.
4. Remove thin compatibility wrappers only if old import/script paths are no
   longer needed.

Phase 7 facts:

- Cutover report:
  `evidence/reports/migration/CUTOVER_2026-05-24.md`
- Final shadow parity record:
  `evidence/reports/migration/shadow_parity_2026-05-24.md`
- Cutover ADR:
  `governance/decisions/ADR-0005-workspace-next-cutover.md`
- Post-policy reproof review:
  `evidence/reports/migration/PHASE_7_REPROOF_2026-05-24.md`.
- Rollback guidance now lives at
  `governance/runbooks/operations/workspace_cutover_rollback.md`.
- Runtime policy decision:
  `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`.
- Superseded blocked records:
  `evidence/reports/migration/CUTOVER_2026-05-21.md` and
  `evidence/reports/migration/shadow_parity_2026-05-21.md`.
- The old workspace was not modified during cutover.

Phase 8 facts:

- Launch and wind-matrix path constants now resolve directly through owned
  `assets/`, `config/`, `var/`, and `src/sim_ard_gaw/` homes.
- Retained manual, sequential, and suite wind-matrix SITL paths now use
  explicit `var/` state for BIN discovery instead of falling back to
  `src/ardupilot/logs`.
- The root legacy symlink bridge is removed after the direct-path refactor and
  targeted checks.
- `src/sim_ard_gaw/compat_scripts/` is now wrapper-only; implementation
  ownership lives under `launch/`, `bridges/`, `analysis/`,
  `campaigns/wind_matrix/`, and `campaigns/test_suite/`.

Phase 6 facts:

- `docs/operations/evidence_workflow.md` defines the operator path from raw
  runtime output under `var/` to selected proof under `evidence/`.
- `evidence/indexes/evidence_catalog.md` is the cross-phase proof catalog; the
  Phase 4 asset and parameter/config indexes remain specialized indexes.
- Reusable launch/runtime, vehicle, campaign, and promotion templates live
  under `evidence/templates/`, not `evidence/reports/`.
- `make doctor` now runs both the structure validator and
  `scripts/maintenance/validate_evidence.sh`; the Phase 6 check covers raw log
  leakage, raw run-directory leakage, raw-looking signatures inside evidence
  homes, report-home shape, evidence homes, template inventory, catalog sanity,
  and retained curated-root catalog coverage.
- The Phase 6 example reuses the real Phase 2 logger promotion: raw logger
  output stays under `var/logs/flight_logger/`, while the curated logger
  summary under `evidence/curated_logs/` and Phase 2 report remain the promoted
  proof.

Phase 5 facts:

- Compatibility runners and Phase-1 `test_suite` wrappers are retained.
- Owned campaign hardening helpers now cover manifest locking, additive
  terminal-status taxonomy, mission-contract validation, XML/SDF world-wind
  handling, and parameter-file hash provenance.
- `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md` records the pre-edit
  assessment, unit/integration/parity validation, tiny campaign PASS, the
  invalidated first `4,4` comparison, and the corrected workspace-plugin
  recheck.
- Curated tiny result artifacts live under
  `evidence/curated_logs/phase5_tiny_rr_20260521/`; raw simulator output stays
  under `var/`.
- `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/` is
  retained as diagnostic proof of the Phase 5 audit-gap remediation path, not
  ArduPilot-side wind parity proof. The raw corrected comparison attempt is
  `var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/wind_x_04_y_04/runs/attempt_002/`.
- The detailed Gazebo plugin fallback incident record is
  `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`.

Phase 4 facts:

- Canonical asset and parameter indexes now live under `evidence/indexes/`.
- Shared config categories are explicit: vehicle bases and standalone stacks
  under `config/vehicles/`, feature overlays under `config/overlays/`,
  campaign lane files under `config/campaigns/`, archives under
  `config/archive/`.
- Plane launch compatibility still appends
  `.private/config/plane_params.local.parm` for most plane lanes when present.
  That local override is not shared canonical config; the shared assets and
  config paths now resolve directly through owned workspace homes.
- Recovered production-era parameter stacks are indexed as historical evidence
  under `evidence/curated_logs/recovered_param_stacks/`.
- `plane_base.parm` remains sensor-neutral for enablement: it keeps generic
  `AIRSPEED_*` defaults while the airspeed overlay or campaign lane files enable
  the Gazebo sensor path and add lane-specific/high-wind overrides.

Phase 3 facts:

- Canonical docs rebuilt: `docs/onboarding/installation.md`,
  `docs/operations/troubleshooting.md`,
  `docs/architecture/simulation_lanes.md`, and the evidence-aware campaign
  boundary in `docs/campaigns/wind_matrix.md`.
- Every archived doc under `docs/archive/src_docs/` has a recorded disposition
  (`PROMOTED`, `REWRITTEN`, `ARCHIVED_ONLY`, or
  `DROPPED_FROM_CANONICAL_USE`) in
  `governance/audits/2026-05-20_phase3_docs_errata.md`.
- Archived docs that are intentionally contradicted carry an ARCHIVED errata
  banner pointing to the canonical replacement.
- Known bad refs (legacy flight-log dir, retired LiDAR runway world, retired
  altitude-wind log checker, obsolete base-plane airspeed param) are absent
  from or qualified in canonical docs.
- Completion pass reconciled the Copter LiDAR lane map with the Phase 2
  2026-05-21 handshake evidence without claiming an obstacle return.
- Audit remediation removed duplicate install guidance from runtime notes,
  narrowed install evidence wording, and closed the Phase 3 runbook checklist.

Latest evidence:

- Phase 6 evidence and operations:
  `evidence/reports/migration/PHASE_6_EVIDENCE_OPS_2026-05-21.md`
- Phase 4 config and asset normalization:
  `evidence/reports/migration/PHASE_4_CONFIG_ASSETS_2026-05-21.md`
- Phase 3 documentation rebuild:
  `evidence/reports/migration/PHASE_3_DOCS_2026-05-20.md`
- Phase 2 runtime parity:
  `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`
- Phase 2 per-target curated runtime evidence:
  `evidence/curated_logs/phase_2_runtime_2026-05-20/`
- Phase 1 structure hardening:
  `evidence/reports/migration/PHASE_1_STRUCTURE_2026-05-20.md`
- Phase 0 baseline: `evidence/reports/migration/PHASE_0_BASELINE_2026-05-20.md`

Phase 2 facts:

- Production and new launch target names match exactly, with one intentional
  difference: `wind-check-altitude` is retired in `workspace_next`.
- `make doctor`, `make test-parity`, and structure validation pass. `make
  doctor` requires `ripgrep`; it was installed during this phase.
- `plane`, `plane-cte`, `plane-lidar`, and `copter` each proved a full
  SITL/Gazebo/MAVLink handshake (GPS fix, EKF3, arming, Gazebo physics
  coupling). `plane-cte`, `plane-lidar`, and `copter` flew (46.9 m, 52.5 m,
  10.0 m).
- `bridge-plane` proved an end-to-end LiDAR path: Gazebo `/lidar` -> bridge ->
  MAVLink -> ArduPilot, with `AGL` readings tracking the plane's climb.
- Two runtime defects were found and fixed in
  `src/sim_ard_gaw/compat_scripts/launch.sh`: copter launchers now load
  `config/vehicles/copter_params.parm` with `--wipe-eeprom` (frame class/type),
  and bridge launchers run `python3 -u` so bridge status is observable.
- `scripts/ops/capture_round.sh` decodes raw tlogs into working output under
  `var/` by default; reviewed selected summaries require explicit
  `--promote-reviewed --evidence-id <new-id>` promotion into a versioned
  curated artifact. Historical Phase 2 evidence that predated root commits is
  now represented by tracked curated reports and indexes.
- All required runtime smoke targets ran with direct evidence, including
  `copter-lidar`, `bridge-copter`, and `logger` (run 2026-05-21). `copter-lidar`
  proved the handshake but not a LiDAR obstacle return.
- The old workspace was read for production comparison only during Phase 2 and
  was not modified. It became deprecated fallback/reference after ADR-0005.

Phase 1 facts:

- `make doctor` calls `scripts/maintenance/validate_structure.sh`.
- Required top-level homes, symlinks, raw log leakage, nested private state,
  `.private/` policy, gitignore coverage, stale canonical references, and
  required migration-plan links are validated.
- Phase 1 is not a runtime parity claim.

Known Phase 0 baseline facts:

- Phase 0 production reference was `/home/ahmed/ardupilot_workspace`; after
  ADR-0005 it is deprecated fallback/reference.
- Production root commit: `a483a534fac1755ea9ba9a007f062981913366d6`.
- At Phase 0, `workspace_next` had no root `HEAD` commit yet. Later tracked
  migration commits supersede that bootstrap state.
- Raw logs were not copied into `workspace_next`.
- `workspace_next` basic structural checks passed during Phase 0.

Do not edit the old workspace without explicit operator authorization.
