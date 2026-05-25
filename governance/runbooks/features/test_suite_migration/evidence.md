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

## Phase 3 (staged attempt runner)

- Primary report:
  `evidence/reports/features/2026-05-25_test_suite_migration_phase_3.md`
- Runbook:
  `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`

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

- Staged-mode live SITL/Gazebo single-attempt diff against legacy
  `run_one.py`: not started; required before any staged-mode cutover claim.
- Phase 4 second-plugin evidence: not started.
- Phase 5 compatibility-retirement evidence: not started; depends on
  Phase 4 acceptance.
