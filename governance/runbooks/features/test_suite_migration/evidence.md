# Feature Runbook: test_suite Migration — Evidence Pointers

This file is a pointer index, not a copy of the underlying evidence.
Raw evidence stays under `evidence/`.

## Phase 1 (wrapper parity)

- Primary report:
  `evidence/reports/features/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md`

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

These Phase-1 wrapper-parity claims must remain schema-compatible
with the legacy manifest layout in these curated roots until Phase 2
(generic data model) adds additive fields:

- `evidence/curated_logs/017_params_old_009_matrix_r3_plugin_fixed/`
- `evidence/curated_logs/018_New_Param_Full_CTE_Matrix/`
- `evidence/curated_logs/phase5_tiny_rr_20260521/`

## Future evidence (not yet produced)

- Phase 2 evidence report: not started.
- Phase 3 split evidence (live SITL/Gazebo single-attempt diff against
  legacy `run_one.py`): not started; gates Phase 3 entry.
- Phase 4 second-plugin evidence: not started.
- Phase 5 compatibility-retirement evidence: not started; depends on
  Phase 4 acceptance.
