# Feature Runbook: test_suite Migration — Evidence Pointers

This file is a pointer index, not a copy of the underlying evidence.
Raw evidence stays under `evidence/`.

## Phase 1 (wrapper parity)

- Primary report:
  `evidence/reports/features/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md`

## Phase 2 (generic manifest / data model)

- Primary report:
  `evidence/reports/features/2026-05-25_test_suite_migration_phase_2.md`
- Runbook:
  `governance/runbooks/features/test_suite_migration/phase_2_generic_manifest.md`

## Phase 3A (staged attempt runner)

- Primary report:
  `evidence/reports/features/2026-05-25_test_suite_migration_phase_3.md`
- Runbook:
  `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`
- Scope:
  accepted opt-in staged implementation with static/unit/integration/CLI
  evidence. This is not live staged runtime parity and not generic framework
  proof.

## Phase 3B (staged-boundary audit / negative proof)

- Primary report:
  `evidence/reports/features/2026-05-29_test_suite_migration_phase_3b.md`
- Scope:
  no-SITL staged-boundary proof passed for "does not call
  `run_one.run_one(...)`", but self-review found staged mode still depends on
  legacy runner helper code across config, CLI, manifest, environment,
  control, monitor, stimulus, and analysis.
- Required before Phase 4:
  Phase 3C-3G must build and prove a full zero-legacy staged wind system in
  parallel with legacy mode before generic runtime readiness or second-plugin
  work is used as proof.
- Gate:
  Phase 4 second-plugin proof remains blocked.

## Phase 3C (legacy-runner import blocker / staged foundation)

- Primary report:
  `evidence/reports/features/2026-05-29_test_suite_migration_phase_3c.md`
- Scope:
  no-SITL foundation proof for the legacy-runner import blocker and current
  core/plugin boundary. Staged config/defaults, combo-key case generation,
  plugin-owned wind manifest setup/additive generic fields, plugin
  construction, `plugin.attempt_runner()`, and CLI parser/bootstrap work while
  imports of `run_one.py`, `run_matrix.py`, and
  `run_matrix_round_robin.py` are blocked. Generic core no longer carries the
  flagged wind-matrix manifest, monitor, or legacy status-string fallback
  behavior. Staged auto defaults to the supported `before-arm` wind phase, and
  campaign summaries use the same `accept_square_only` policy as manifest
  accepted counts. A 2026-05-31 follow-up closes review findings for plugin
  manifest atomic writes, staged `running`/terminal manifest persistence,
  stale-running reconciliation, and avoidable legacy helper use in stimulus
  attempt-directory/run-config creation.
- Follow-up report (2026-05-31, H-1 .. H-9):
  `evidence/reports/features/2026-05-31_test_suite_phase3c_followup_fixes.md`
  with audit `governance/audits/2026-05-31_test_suite_phase3c_followup_findings.md`.
  Migrates the Phase 3F analysis substage (BIN/analysis/summary/cleanup/run-alias/
  slot-timeout) to plugin-owned `plugins/wind_matrix/analysis_helpers.py`,
  canonicalizes staged running/terminal attempt directories (H-1), adds the
  `run_suite` flag-parity guard (H-5), and fixes two test defects introduced
  during the in-progress fix work (f-string braces, wrong mock namespace).
- Strict high-finding fix report (2026-05-31, scoped to manifest reconciliation
  parity + staged run-config exact migrated-field parity):
  `evidence/reports/features/2026-05-31_test_suite_phase3c_manifest_run_config_parity_fixes.md`.
  This narrows/corrects the earlier H-7 overclaim from the follow-up report.
- Limit:
  live zero-legacy staged runtime is not proven. Runtime/environment,
  MAVLink control/monitor, and runtime wind injection still need Phase 3D-3F
  replacement. Phase 3C is not a full generic architecture proof.
- Gate:
  Phase 4 remains blocked.

## Phase 3D (zero-legacy runtime/environment)

- Primary report:
  `evidence/reports/features/2026-05-31_test_suite_migration_phase_3d.md`
- Scope:
  no-SITL environment-ownership proof. `WindMatrixEnvironment.launch()` and
  `.cleanup()` now call plugin-owned `runtime.py`; neither resolves
  `run_matrix.*` or `run_one.*`. The Phase 3C import-blocker hard test
  now also exercises `env.launch()+cleanup()` with legacy runner imports
  blocked. MAVLink readiness (`assert_ready`) remains Phase 3E. Not live
  proof; Phase 4 remains blocked.
- Gate:
  Phase 4 remains blocked.

## Phase 3E (zero-legacy MAVLink control and monitor)

- Primary report:
  `evidence/reports/features/2026-06-01_test_suite_migration_phase_3e.md`
- Scope:
  no-SITL MAVLink control/monitor-ownership proof. Staged `assert_ready`,
  `WindMatrixAutoMissionControl`, and `WindMatrixDisarmMonitor` now call
  plugin-owned `mavlink_control.*` only; none resolves `run_one.*` or
  `run_matrix.*`. The Phase 3C import-blocker hard test extended with a
  Phase 3E block covering `assert_ready` + control + monitor execution with
  legacy runner imports blocked. The only remaining staged legacy dependency
  is `WindMatrixStimulus` runtime wind injection (`run_one.inject_wind` /
  `preloaded_wind_artifact`), owned by Phase 3F. Not live proof; Phase 4
  remains blocked.
- Gate:
  Phase 4 remains blocked.

## Phase 3F-3G (zero-legacy stimulus, artifacts, analysis, summary, live proof)

- Primary report:
  not yet available.
- Scope:
  planned follow-on work. Build test-suite-owned staged wind stimulus, BIN
  collection, analysis invocation, run summary, artifact handling, terminal
  error rows, and full live proof beside legacy mode.
- Gate:
  Phase 4 remains blocked until Phase 3G accepts full no-legacy staged tests
  plus bounded live staged wind proof and matching legacy comparison.

## Plan correction (2026-05-29)

- Primary report:
  `evidence/reports/features/2026-05-29_test_suite_migration_plan_correction.md`
- Scope:
  planning/governance correction only. It splits the old Phase 3 into Phase
  3A and Phase 3B. Later review expands the Phase 3 follow-on gate to
  Phase 3C-3G before Phase 4.

## Upstream evidence that Phase 1 relies on

- Governance Phase 5 campaign / test migration:
  `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`
  (manifest locking, terminal taxonomy, mission contract, wind world
  safety, tiny round-robin proof, parameter provenance).
- Governance Phase 8 compatibility retirement:
  `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`
  (moved runner ownership into `src/sim_ard_gaw/campaigns/wind_matrix/`,
  retained `compat_scripts/` as wrapper-only,
  `_legacy.py` retargeted at owned modules).
- Phase 5 Gazebo plugin fallback incident:
  `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`.
- Clean-run and workspace-plugin decision:
  `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`.

## Curated comparator log roots

These Phase-1 wrapper-parity claims remain schema-compatible with the
legacy manifest layout in these curated roots. Phase 2 adds a generic
reader view over them and writes generic fields only additively for new
framework attempts:

- `evidence/curated_logs/017_params_old_009_matrix_r3_plugin_fixed/`
- `evidence/curated_logs/018_New_Param_Full_CTE_Matrix/`
- `evidence/curated_logs/phase5_tiny_rr_20260521/`

## Future evidence (not yet produced)

- Phase 3B staged-mode live SITL/Gazebo wind proof against the retained legacy
  path: blocked as of
  `evidence/reports/features/2026-05-29_test_suite_migration_phase_3b.md`.
- Phase 4 second-plugin evidence: not started and not authorized until Phase
  3B is accepted.
- Phase 5 compatibility-retirement evidence: not started; depends on
  Phase 4 acceptance.
