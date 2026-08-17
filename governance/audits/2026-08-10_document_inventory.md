# Document Inventory Audit

Date: 2026-08-10
Scope: tracked owned Markdown in `/home/ahmed/ardupilot_workspace_next`, excluding `src/ardupilot/`, `src/ardupilot_gazebo/`, `src/SITL_Models/`, `env/`, `docs/presentations/node_modules/`, `var/`, and `.private/`.
Action taken: inventory only. No files were deleted, moved, archived, or edited outside this audit file.

## Summary

This audit classified 229 tracked owned Markdown files. The conservative result is: no tracked file should be deleted now. The highest-risk cleanup candidates are not deletions; they are stale-reference corrections and an explicit decision about whether migration runbooks should remain in place because immutable evidence points at them.

| Bucket | Count |
| --- | ---: |
| Live | 86 |
| Historical (correctly filed) | 137 |
| Historical (misfiled) | 0 |
| Superseded | 3 |
| Duplicate | 0 |
| Orphan | 0 |
| Stale claim | 3 |

Key findings:

- The old `docs/operations/migration_status.md` status doc is absent and has been replaced by `docs/operations/workspace_status.md`, but the active rollback runbook still names the old path twice.
- Final cutover and compatibility retirement are genuinely complete by dated evidence, but moving `governance/runbooks/migration/` is not recommended now because `.ai`, current docs, `validate_structure.sh`, and immutable evidence reports still reference the current paths.
- `governance/runbooks/features/test_suite_migration/` is completed history, but it is still linked from current docs and many accepted evidence reports, so it should stay in place.
- GPS history is intentionally layered across `.ai/current.md`, `docs/operations/gps_failure_runbook.md`, `docs/architecture/gps_failure_lane.md`, and `governance/runbooks/features/gps_failure_behavior/`; the duplication risk is in repeated status prose, not in duplicate canonical homes.
- `docs/presentations/` has local Markdown and `node_modules/`, but the whole directory is ignored and no files there are tracked. That contradicts the presentation-template plan if the template is meant to be canonical docs.

## Method

Inbound reference count is a literal path occurrence count across tracked non-vendor workspace files, excluding the target file itself. It intentionally does not count basename-only mentions, relative Markdown links that omit the canonical path, or ignored local files. That makes low counts a signal to investigate, not deletion proof.

No files are classified `Orphan`. Per `records_lifecycle.md`, unlinked evidence reports, ADRs, audits, archived docs, and completed runbooks are still load-bearing records unless a specific successor and move plan exists.

## Inventory Table

| Path | Bucket | Reason | Proposed disposition | Inbound refs |
| --- | --- | --- | --- | ---: |
| `.ai/README.md` | Live | Agent protocol, pointer, or current issue state. | Keep current and pointer-only. | 20 |
| `.ai/audits/README.md` | Live | Agent protocol, pointer, or current issue state. | Keep current and pointer-only. | 0 |
| `.ai/current.md` | Live | Agent protocol, pointer, or current issue state. | Keep current and pointer-only. | 52 |
| `.ai/decisions/README.md` | Live | Agent protocol, pointer, or current issue state. | Keep current and pointer-only. | 0 |
| `.ai/entrypoint.md` | Live | Agent protocol, pointer, or current issue state. | Keep current and pointer-only. | 18 |
| `.ai/index.md` | Live | Agent protocol, pointer, or current issue state. | Keep current and pointer-only. | 59 |
| `.ai/issues/open.md` | Live | Agent protocol, pointer, or current issue state. | Keep current and pointer-only. | 37 |
| `AGENTS.md` | Live | Root entry point / workspace overview. | Keep current. | 21 |
| `CHANGELOG.md` | Historical (correctly filed) | Project change log retained for chronological history. | Keep. | 23 |
| `README.md` | Live | Root entry point / workspace overview. | Keep current. | 555 |
| `assets/missions/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 4 |
| `assets/missions/archive/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 1 |
| `assets/missions/mini_talon_airspeed_lidar/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 0 |
| `assets/models/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 0 |
| `assets/models/mini_talon_airspeed_lidar/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 0 |
| `assets/worlds/mini_talon_airspeed_lidar/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 0 |
| `config/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 3 |
| `config/archive/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 1 |
| `config/campaigns/mini_talon_airspeed_lidar/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 0 |
| `docs/README.md` | Live | Current human documentation in docs/. | Keep current. | 3 |
| `docs/architecture/airspeed_failure_lane.md` | Live | Current human documentation in docs/. | Keep current. | 8 |
| `docs/architecture/campaign_lanes.md` | Live | Current human documentation in docs/. | Keep current. | 7 |
| `docs/architecture/gps_failure_lane.md` | Live | Current human documentation in docs/. | Keep current. | 11 |
| `docs/architecture/simulation_lanes.md` | Live | Current human documentation in docs/. | Keep current. | 49 |
| `docs/architecture/workspace_map.md` | Live | Current human documentation in docs/. | Keep current. | 18 |
| `docs/archive/src_docs/FLIGHT_MODES.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/INSTALLATION.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/SIMULATION_LANES.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 1 |
| `docs/archive/src_docs/TROUBLESHOOTING.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/mini_talon_airspeed_lidar/README.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/report generation/README.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/report generation/report_template.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/report generation/theme.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/00_script_inventory.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/01_current_behavior.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/02_common_vs_different.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/03_findings.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/04_modularization_plan.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/05_testing_plan.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/06_high_wind_12_12_debug_history.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/07_wind_pipeline_investigation_handoff.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/08_automated_test_suite_blueprint.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/archive/src_docs/wind_matrix_scripts/09_matrix_launcher_environment_root_cause.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 1 |
| `docs/archive/src_docs/wind_matrix_scripts/README.md` | Historical (correctly filed) | Archived source doc; archive is a real historical home. | Keep in docs/archive. | 0 |
| `docs/campaigns/wind_matrix.md` | Live | Current human documentation in docs/. | Keep current. | 32 |
| `docs/onboarding/installation.md` | Live | Current human documentation in docs/. | Keep current. | 13 |
| `docs/onboarding/quick_start.md` | Live | Current human documentation in docs/. | Keep current. | 15 |
| `docs/operations/airspeed_failure_runbook.md` | Live | Current human documentation in docs/. | Keep current. | 7 |
| `docs/operations/evidence_workflow.md` | Live | Current human documentation in docs/. | Keep current. | 15 |
| `docs/operations/gps_failure_runbook.md` | Live | Current human documentation in docs/. | Keep current. | 13 |
| `docs/operations/launch_targets.md` | Live | Current human documentation in docs/. | Keep current. | 35 |
| `docs/operations/private_overlays.md` | Live | Current human documentation in docs/. | Keep current. | 4 |
| `docs/operations/sitl_gazebo_runtime.md` | Live | Current human documentation in docs/. | Keep current. | 8 |
| `docs/operations/troubleshooting.md` | Live | Current human documentation in docs/. | Keep current. | 12 |
| `docs/operations/workspace_status.md` | Live | Current human documentation in docs/. | Keep current. | 11 |
| `docs/vehicles/status.md` | Live | Current human documentation in docs/. | Keep current. | 18 |
| `evidence/curated_logs/001_Quad_LiDAR/TEST_RESULT_2026-01-15.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 1 |
| `evidence/curated_logs/002_Plane_Base/TEST_RESULT_2026-01-21.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 1 |
| `evidence/curated_logs/003_Plane_Airspeed/TEST_RESULT_2026-02-04.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 1 |
| `evidence/curated_logs/004_Plane_AutoMission/TEST_RESULT_2026-02-10.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 1 |
| `evidence/curated_logs/005_Plane_Landing/TEST_RESULT_2026-02-16.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 1 |
| `evidence/curated_logs/006_Plane_FlightLogger/TEST_RESULT_2026-02-18.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 1 |
| `evidence/curated_logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 3 |
| `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 1 |
| `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/raw_data_index.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 5 |
| `evidence/curated_logs/airspeed_failure_tailwind_pulse_reanalysis_2026-06-23/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/cte_wind_envelope_017_20260602/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/cte_wind_envelope_017_20260602/tables/cte_tables.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/cte_wind_envelope_017_20260602/written_conclusion_exec.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/cte_wind_envelope_017_20260602/written_conclusion_technical.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/phase5_tiny_rr_20260521/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/pillar_a_flight_results_20260602/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/pillar_a_flight_results_20260602/tables/pillar_a_summary.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/pillar_a_flight_results_20260602/written_conclusion.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/recovered_param_stacks/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/test_suite_phase3f_staged_live_20260601/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/curated_logs/test_suite_phase3g_legacy_compare_20260601/README.md` | Historical (correctly filed) | Curated evidence artifact or README retained for provenance. | Keep; do not edit or move. | 0 |
| `evidence/indexes/README.md` | Live | Active evidence index routing readers to proof. | Keep current, except approved stale-reference fixes. | 2 |
| `evidence/indexes/asset_index.md` | Live | Active evidence index routing readers to proof. | Keep current, except approved stale-reference fixes. | 7 |
| `evidence/indexes/evidence_catalog.md` | Stale claim | Active evidence index still has two current path cells pointing at removed migration_status.md. | Propose approved index correction; do not edit accepted reports. | 39 |
| `evidence/indexes/logs_README.md` | Live | Active evidence index routing readers to proof. | Keep current, except approved stale-reference fixes. | 4 |
| `evidence/indexes/parameter_config_index.md` | Live | Active evidence index routing readers to proof. | Keep current, except approved stale-reference fixes. | 9 |
| `evidence/reports/README.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 6 |
| `evidence/reports/features/2026-05-24_evidence_reports_reorganization.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 1 |
| `evidence/reports/features/2026-05-24_naming_convention_policy.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 2 |
| `evidence/reports/features/2026-05-25_test_suite_migration_phase_2.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 5 |
| `evidence/reports/features/2026-05-25_test_suite_migration_phase_3.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 3 |
| `evidence/reports/features/2026-05-29_test_suite_migration_phase_3b.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 5 |
| `evidence/reports/features/2026-05-29_test_suite_migration_phase_3c.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 8 |
| `evidence/reports/features/2026-05-29_test_suite_migration_plan_correction.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 2 |
| `evidence/reports/features/2026-05-31_test_suite_migration_phase_3d.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 5 |
| `evidence/reports/features/2026-05-31_test_suite_phase3c_followup_fixes.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 7 |
| `evidence/reports/features/2026-05-31_test_suite_phase3c_manifest_run_config_parity_fixes.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 7 |
| `evidence/reports/features/2026-05-31_test_suite_phase3c_review_fixes.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 4 |
| `evidence/reports/features/2026-06-01_test_suite_migration_phase_3e.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 6 |
| `evidence/reports/features/2026-06-01_test_suite_migration_phase_3f.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 4 |
| `evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 8 |
| `evidence/reports/features/2026-06-02_cte_wind_envelope_result.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 17 |
| `evidence/reports/features/2026-06-02_pillar_a_flight_results.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 2 |
| `evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 12 |
| `evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 15 |
| `evidence/reports/features/2026-06-23_tailwind_pulse_evaluator_correction.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 5 |
| `evidence/reports/features/AGENT_ENTRYPOINT_AND_RECORDS_LIFECYCLE_2026-05-24.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 1 |
| `evidence/reports/features/GIT_COMMIT_STYLE_ADOPTION_2026-05-24.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 1 |
| `evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 1 |
| `evidence/reports/features/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 7 |
| `evidence/reports/migration/CUTOVER_2026-05-21.md` | Superseded | Superseded by accepted cutover report dated 2026-05-24; retained as blocked historical evidence. | Keep as append-only evidence; route readers to successor. | 3 |
| `evidence/reports/migration/CUTOVER_2026-05-24.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 11 |
| `evidence/reports/migration/MIGRATION_PLAN_PACK_2026-05-20.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 1 |
| `evidence/reports/migration/PHASE_0_BASELINE_2026-05-20.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 4 |
| `evidence/reports/migration/PHASE_1_STRUCTURE_2026-05-20.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 3 |
| `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 18 |
| `evidence/reports/migration/PHASE_3_DOCS_2026-05-20.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 5 |
| `evidence/reports/migration/PHASE_4_CONFIG_ASSETS_2026-05-21.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 3 |
| `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 13 |
| `evidence/reports/migration/PHASE_6_EVIDENCE_OPS_2026-05-21.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 4 |
| `evidence/reports/migration/PHASE_7_REPROOF_2026-05-24.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 5 |
| `evidence/reports/migration/PHASE_8_COMPAT_FINAL_REMOVAL_AUDIT_2026-06-30.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 3 |
| `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-22.md` | Superseded | Superseded by Phase 8 report dated 2026-05-24 and final-removal audit dated 2026-06-30. | Keep as append-only evidence; route readers to successor. | 5 |
| `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 7 |
| `evidence/reports/migration/WIND_MATRIX_LEGACY_STRATEGY_RETIREMENT_2026-06-30.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 4 |
| `evidence/reports/migration/shadow_parity_2026-05-21.md` | Superseded | Superseded by shadow parity report dated 2026-05-24; retained as blocked historical evidence. | Keep as append-only evidence; route readers to successor. | 3 |
| `evidence/reports/migration/shadow_parity_2026-05-24.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 7 |
| `evidence/reports/operations/VALIDATION_2026-05-19.md` | Historical (correctly filed) | Append-only evidence report in the evidence report home. | Keep; do not edit or move. | 1 |
| `evidence/templates/README.md` | Live | Reusable evidence template or template README. | Keep. | 3 |
| `evidence/templates/campaign_result_report.md` | Live | Reusable evidence template or template README. | Keep. | 3 |
| `evidence/templates/evidence_promotion_checklist.md` | Live | Reusable evidence template or template README. | Keep. | 3 |
| `evidence/templates/launch_runtime_smoke_report.md` | Live | Reusable evidence template or template README. | Keep. | 4 |
| `evidence/templates/vehicle_verification_report.md` | Live | Reusable evidence template or template README. | Keep. | 4 |
| `governance/audits/2026-02-09_public_private_classification_legacy.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/AUDIT_LOG.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/COMMAND_AUDIT.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/CONTRADICTIONS.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/COVERAGE.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/DEAD_LINKS_AND_MISSING_TARGETS.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/EVIDENCE_MAP.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/FINAL_VERIFICATION.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/FINDINGS.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 1 |
| `governance/audits/2026-05-13_truth_audit/raw/ISSUE_AUDIT.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/PARAMETER_TRUTH.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/PROPOSED_FIX_PLAN.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-13_truth_audit/raw/README.md` | Live | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-19_migration_summary.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 1 |
| `governance/audits/2026-05-19_workspace_refactor_plan.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/2026-05-20_phase3_docs_errata.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 13 |
| `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 9 |
| `governance/audits/2026-05-31_test_suite_phase3c_followup_findings.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 7 |
| `governance/audits/2026-05-31_test_suite_phase3c_review_findings.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 4 |
| `governance/audits/2026-08-10_campaign_lane_test_coverage_gap.md` | Historical (correctly filed) | Audit/incident/errata record or audit directory guidance. | Keep. | 0 |
| `governance/audits/README.md` | Live | Audit/incident/errata record or audit directory guidance. | Keep. | 3 |
| `governance/decisions/ADR-0001-corporate-workspace-structure.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 0 |
| `governance/decisions/ADR-0002-private-overlays-only.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 0 |
| `governance/decisions/ADR-0003-phase5-campaign-safety-contract.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 3 |
| `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 13 |
| `governance/decisions/ADR-0005-workspace-next-cutover.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 21 |
| `governance/decisions/ADR-0006-airspeed-failure-mission-design.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 4 |
| `governance/decisions/ADR-0007-airspeed-failure-case-payloads-and-ratio-sweep.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0008-airspeed-failure-reset-protocol.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0009-airspeed-failure-injection-trigger.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0010-airspeed-failure-reference-wind.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0011-airspeed-failure-behavior-classification.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0012-airspeed-envelope-sensitivity-matrix.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0013-airspeed-envelope-overlay-mechanism.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0014-airspeed-plateau-metric-and-preregistered-predictions.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0015-airspeed-ahrs-wind-max-clamp-correction.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0016-airspeed-two-tier-bias-lane-and-validation-gate.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0017-gps-failure-fault-catalog.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 2 |
| `governance/decisions/ADR-0018-gps-failure-knee-and-classification.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0019-gps-failure-sweep-design.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0020-gps-failure-mission-and-trigger.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 1 |
| `governance/decisions/ADR-0021-gps-failure-parameter-overlay.md` | Historical (correctly filed) | Append-only ADR/durable decision record. | Keep; do not edit body or move. | 2 |
| `governance/runbooks/README.md` | Live | Runbook directory guidance. | Keep. | 9 |
| `governance/runbooks/features/README.md` | Live | Feature runbook/guidance in its feature home. | Keep pending disposition of the feature. | 6 |
| `governance/runbooks/features/airspeed_failure_behavior/README.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/airspeed_failure_behavior/design_adrs.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 8 |
| `governance/runbooks/features/airspeed_failure_behavior/design_research.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 2 |
| `governance/runbooks/features/airspeed_failure_behavior/evidence.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/airspeed_failure_behavior/implementation.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/airspeed_failure_behavior/plan.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/airspeed_failure_behavior/review.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 2 |
| `governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_0_9_chunk5_record.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_0_9_expectations.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 1 |
| `governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_0_9_inventory.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 1 |
| `governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_0_9_results_comparison.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_1_8_corrected_reanalysis.md` | Live | Feature context still supports open airspeed-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/gps_failure_behavior/README.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/gps_failure_behavior/bmi270_datasheet_extract.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/gps_failure_behavior/design_adrs.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 6 |
| `governance/runbooks/features/gps_failure_behavior/design_research.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/gps_failure_behavior/evidence.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/gps_failure_behavior/implementation.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/gps_failure_behavior/imu_sitl_source_validation.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/gps_failure_behavior/ins_only_imu_characterization_plan.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 0 |
| `governance/runbooks/features/gps_failure_behavior/plan.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 1 |
| `governance/runbooks/features/gps_failure_behavior/review.md` | Live | Feature context still supports open gps-failure campaign-lane work. | Keep. | 1 |
| `governance/runbooks/features/presentation_template/plan.md` | Stale claim | Plan says canonical template lives under docs/presentations, but that whole tree is ignored locally. | Decide whether to track the template or narrow the ignore rule. | 0 |
| `governance/runbooks/features/test_suite_migration/evidence.md` | Historical (correctly filed) | Completed feature runbook still referenced by docs and immutable evidence reports. | Keep; consider only an index note, not a move. | 13 |
| `governance/runbooks/features/test_suite_migration/phase_1_wrapper_parity.md` | Historical (correctly filed) | Completed feature runbook still referenced by docs and immutable evidence reports. | Keep; consider only an index note, not a move. | 5 |
| `governance/runbooks/features/test_suite_migration/phase_2_generic_manifest.md` | Historical (correctly filed) | Completed feature runbook still referenced by docs and immutable evidence reports. | Keep; consider only an index note, not a move. | 4 |
| `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md` | Historical (correctly filed) | Completed feature runbook still referenced by docs and immutable evidence reports. | Keep; consider only an index note, not a move. | 11 |
| `governance/runbooks/features/test_suite_migration/plan.md` | Historical (correctly filed) | Completed feature runbook still referenced by docs and immutable evidence reports. | Keep; consider only an index note, not a move. | 19 |
| `governance/runbooks/features/test_suite_migration/review.md` | Historical (correctly filed) | Completed feature runbook still referenced by docs and immutable evidence reports. | Keep; consider only an index note, not a move. | 21 |
| `governance/runbooks/migration/full_migration_plan.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 9 |
| `governance/runbooks/migration/phase_0_foundation_freeze.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 2 |
| `governance/runbooks/migration/phase_1_structure_hardening.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 2 |
| `governance/runbooks/migration/phase_2_runtime_parity.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 11 |
| `governance/runbooks/migration/phase_3_documentation_rebuild.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 2 |
| `governance/runbooks/migration/phase_4_config_asset_normalization.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 2 |
| `governance/runbooks/migration/phase_5_campaign_test_migration.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 5 |
| `governance/runbooks/migration/phase_6_evidence_operations.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 3 |
| `governance/runbooks/migration/phase_7_cutover_deprecation.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 4 |
| `governance/runbooks/migration/phase_8_compatibility_retirement.md` | Historical (correctly filed) | Completed migration runbook retained under lifecycle; evidence and validators still reference this home. | Keep for now; do not move without approved migration-history bundle and validator updates. | 11 |
| `governance/runbooks/operations/shadow_parity.md` | Live | Operational runbook for reusable procedure. | Keep current. | 8 |
| `governance/runbooks/operations/workspace_cutover_rollback.md` | Stale claim | Active rollback runbook still names removed docs/operations/migration_status.md. | Propose correction to workspace_status path after approval. | 7 |
| `governance/standards/change_control.md` | Live | Current governance standard. | Keep current. | 28 |
| `governance/standards/documentation.md` | Live | Current governance standard. | Keep current. | 5 |
| `governance/standards/evidence.md` | Live | Current governance standard. | Keep current. | 11 |
| `governance/standards/git_commit_style.md` | Live | Current governance standard. | Keep current. | 8 |
| `governance/standards/lane_documentation.md` | Live | Current governance standard. | Keep current. | 7 |
| `governance/standards/naming.md` | Live | Current governance standard. | Keep current. | 28 |
| `governance/standards/records_lifecycle.md` | Live | Current governance standard. | Keep current. | 10 |
| `governance/standards/workspace_structure.md` | Live | Current governance standard. | Keep current. | 1 |
| `scripts/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 8 |
| `scripts/maintenance/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 4 |
| `src/external/DEPENDENCIES.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 29580 |
| `src/sim_ard_gaw/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 5 |
| `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 25 |
| `tests/README.md` | Live | Directory README or developer-facing project documentation. | Keep with owning home. | 7 |

## Do Not Touch: Unlinked But Load-Bearing

These files have zero literal inbound path references in the tracked corpus but are still load-bearing by lifecycle, provenance, or directory role. Future cleanup should not mistake them for orphans.

| Path | Why it stays |
| --- | --- |
| `docs/archive/src_docs/FLIGHT_MODES.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/INSTALLATION.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/TROUBLESHOOTING.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/mini_talon_airspeed_lidar/README.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/report generation/README.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/report generation/report_template.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/report generation/theme.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/00_script_inventory.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/01_current_behavior.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/02_common_vs_different.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/03_findings.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/04_modularization_plan.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/05_testing_plan.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/06_high_wind_12_12_debug_history.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/07_wind_pipeline_investigation_handoff.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/08_automated_test_suite_blueprint.md` | Archived source doc; archive is a real historical home. |
| `docs/archive/src_docs/wind_matrix_scripts/README.md` | Archived source doc; archive is a real historical home. |
| `evidence/curated_logs/airspeed_failure_tailwind_pulse_reanalysis_2026-06-23/README.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/cte_wind_envelope_017_20260602/README.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/cte_wind_envelope_017_20260602/tables/cte_tables.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/cte_wind_envelope_017_20260602/written_conclusion_exec.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/cte_wind_envelope_017_20260602/written_conclusion_technical.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/README.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/phase5_tiny_rr_20260521/README.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/pillar_a_flight_results_20260602/README.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/pillar_a_flight_results_20260602/tables/pillar_a_summary.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/pillar_a_flight_results_20260602/written_conclusion.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/recovered_param_stacks/README.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/test_suite_phase3f_staged_live_20260601/README.md` | Curated evidence artifact or README retained for provenance. |
| `evidence/curated_logs/test_suite_phase3g_legacy_compare_20260601/README.md` | Curated evidence artifact or README retained for provenance. |
| `governance/audits/2026-02-09_public_private_classification_legacy.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/AUDIT_LOG.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/COMMAND_AUDIT.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/CONTRADICTIONS.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/COVERAGE.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/DEAD_LINKS_AND_MISSING_TARGETS.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/EVIDENCE_MAP.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/FINAL_VERIFICATION.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/ISSUE_AUDIT.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/PARAMETER_TRUTH.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/PROPOSED_FIX_PLAN.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-13_truth_audit/raw/README.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-05-19_workspace_refactor_plan.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/audits/2026-08-10_campaign_lane_test_coverage_gap.md` | Audit/incident/errata record or audit directory guidance. |
| `governance/decisions/ADR-0001-corporate-workspace-structure.md` | Append-only ADR/durable decision record. |
| `governance/decisions/ADR-0002-private-overlays-only.md` | Append-only ADR/durable decision record. |

## Migration Runbook Determination

`records_lifecycle.md` allows migration phase runbooks to move to a migration-history bundle only after final cutover and compatibility retirement are complete. Both dated conditions are met:

- Final cutover passed on 2026-05-24 under `governance/decisions/ADR-0005-workspace-next-cutover.md` and `evidence/reports/migration/CUTOVER_2026-05-24.md`.
- Compatibility wrapper removal completed on 2026-06-30 under `evidence/reports/migration/PHASE_8_COMPAT_FINAL_REMOVAL_AUDIT_2026-06-30.md`, whose steps 1-6 are DONE and whose conclusion is PASS.

However, this is a permission to move, not a requirement. A move is not recommended in the next cleanup pass because accepted evidence reports and current routing still point at the existing paths.

| Migration runbook | Current-scope references (docs/.ai/governance/scripts/Makefile/other tracked) | Evidence references | Validator exact-path dependency |
| --- | --- | --- | --- |
| `governance/runbooks/migration/full_migration_plan.md` | .ai/current.md (1); .ai/index.md (1); governance/runbooks/operations/shadow_parity.md (1); scripts/maintenance/validate_structure.sh (2) | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (3) | scripts/maintenance/validate_structure.sh (2) |
| `governance/runbooks/migration/phase_0_foundation_freeze.md` | none | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (1) | none |
| `governance/runbooks/migration/phase_1_structure_hardening.md` | none | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (1) | none |
| `governance/runbooks/migration/phase_2_runtime_parity.md` | scripts/maintenance/validate_structure.sh (8) | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (2) | scripts/maintenance/validate_structure.sh (8) |
| `governance/runbooks/migration/phase_3_documentation_rebuild.md` | none | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (1) | none |
| `governance/runbooks/migration/phase_4_config_asset_normalization.md` | none | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (1) | none |
| `governance/runbooks/migration/phase_5_campaign_test_migration.md` | .ai/entrypoint.md (1); .ai/index.md (1); governance/runbooks/features/test_suite_migration/plan.md (1) | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (1) | none |
| `governance/runbooks/migration/phase_6_evidence_operations.md` | .ai/index.md (1) | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (1) | none |
| `governance/runbooks/migration/phase_7_cutover_deprecation.md` | .ai/index.md (1) | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (2) | none |
| `governance/runbooks/migration/phase_8_compatibility_retirement.md` | .ai/entrypoint.md (1); .ai/index.md (1); scripts/maintenance/validate_structure.sh (6) | evidence/reports/features/2026-05-24_evidence_reports_reorganization.md (1); evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md (2) | scripts/maintenance/validate_structure.sh (6) |

Would moving them break `make doctor`? Very likely yes unless `scripts/maintenance/validate_structure.sh` is updated in the same change. Its stale-reference allowlist keys exact files such as `governance/runbooks/migration/phase_2_runtime_parity.md`, `phase_8_compatibility_retirement.md`, and `full_migration_plan.md`. Moving the files would also leave `.ai/index.md`, `.ai/entrypoint.md`, `.ai/current.md`, `docs/operations/workspace_status.md`, `governance/runbooks/operations/shadow_parity.md`, and evidence reports pointing at the old paths. Evidence reports cannot be edited to follow the move.

Recommendation: keep `governance/runbooks/migration/` in place. If Ahmed wants a tidier navigation surface, add a lightweight migration-history index that points to the existing files instead of moving them.

## Superseded, Duplicate, Or Stale Findings

| Finding | Evidence | Disposition proposal | Risk |
| --- | --- | --- | --- |
| `docs/operations/migration_status.md` is superseded by `docs/operations/workspace_status.md`, and the old file is gone. | `find ... -name migration_status.md` returns no file; `rg` still finds governance and evidence references. | Correct active governance references to `workspace_status.md`; leave evidence report mentions untouched. | Medium: active rollback instructions can point operators at a missing file. |
| `governance/runbooks/operations/workspace_cutover_rollback.md` has stale status-doc references. | Lines 63 and 76 name `docs/operations/migration_status.md`. | Propose correction in a later approved docs/governance edit. | Medium. |
| `evidence/indexes/evidence_catalog.md` has stale status-doc references in active index rows. | Rows for Phase 8 partial/pass still point to `docs/operations/migration_status.md`. | Because this task prohibits evidence edits, report only. If policy allows index maintenance later, update the index with a dated note. | Medium-high due evidence edit prohibition. |
| `governance/runbooks/features/presentation_template/plan.md` conflicts with `.gitignore`. | Plan says canonical template under `docs/presentations/`; `.gitignore:25` ignores `docs/presentations/` entirely. | Decide whether to track canonical presentation template files or revise the plan/docs to mark them local-only. | Medium. |
| GPS narrative appears in four homes. | `.ai/current.md`, `docs/operations/gps_failure_runbook.md`, `docs/architecture/gps_failure_lane.md`, and `governance/runbooks/features/gps_failure_behavior/`. | Keep all four homes, but reduce repeated status prose later: `.ai/current.md` should be the short active pointer, docs should hold operator/architecture truth, feature runbook should hold phase history. | Low-medium drift risk. |
| Phase-named test-suite migration runbooks are completed. | Current docs and many evidence reports still reference `governance/runbooks/features/test_suite_migration/`. | Keep in place; do not archive until current docs and immutable evidence constraints are deliberately handled. | High if moved. |
| README files describing removed `compat_scripts/` structure. | Tracked README scan found historical/retirement wording, not a live README claiming the removed wrapper exists. | No action for tracked READMEs. | Low. |
| Audits referencing deleted paths. | Historical audits contain many old `src/SIM_ARD_GAW`, old-workspace, and `compat_scripts` paths. | Keep; filenames do not materially misdescribe content. These are historical records, not current instructions. | Low if left alone, high if edited. |

## Reality Versus Records Lifecycle

- Reality matches the standard for evidence, ADRs, audits, archived docs, active docs, and organized runbooks: no deletion is justified by lack of inbound links alone.
- The standard is incomplete for active evidence indexes: it says evidence indexes stay active while routing readers, but this task also prohibits editing anything under `evidence/`. `evidence/indexes/evidence_catalog.md` has stale current-doc references, so a future policy decision should clarify whether indexes are maintainable evidence metadata or fully append-only.
- The migration-runbook lifecycle trigger is met, but the optional move is blocked in practice by immutable evidence references and validator exact-path allowlists. The standard is not wrong; the repository has chosen reference stability over tidiness.
- `docs/presentations/` contradicts the documentation model if it is intended to be canonical: docs and a feature plan point there, but `.gitignore` excludes the whole directory.

## Recommended Order Of Operations

1. Lowest risk: correct active non-evidence references to the removed migration status doc in `governance/runbooks/operations/workspace_cutover_rollback.md`. Run `make doctor`.
2. Low-medium risk: decide the `docs/presentations/` ownership model. Either track the canonical template and narrow `.gitignore` to `node_modules/` and `dist/`, or revise the feature plan/docs so presentations are explicitly local-only. This requires `make doctor` and likely presentation build checks.
3. Medium risk: reduce GPS repeated status prose by making `.ai/current.md` a shorter pointer and keeping detailed operational/architecture claims in the two docs. This is a docs/.ai change requiring `make doctor`.
4. Medium-high risk: clarify evidence-index lifecycle before changing `evidence/indexes/evidence_catalog.md`. If approved, update stale status-doc links with dated rationale and run `make doctor`.
5. High risk: do not move migration runbooks now. If Ahmed still wants a migration-history bundle, first create a no-move index, then separately update `.ai`, docs, `validate_structure.sh`, and every mutable governance reference. Evidence reports would remain pinned to old paths, so the old paths would need permanent redirects or retained files.
6. High risk: do not archive `governance/runbooks/features/test_suite_migration/` while current docs and evidence reports point at it. A future cleanup should add successor pointers, not move the evidence-addressed files.

## Orphan Grep Proof

No tracked Markdown file is classified as `Orphan`, so no per-orphan grep proof is required. The conservative rule used here is: if the file is evidence, an ADR, an audit, an archived doc, a directory README, an active doc, or a runbook still tied to code/docs/evidence, it is not an orphan even with zero literal inbound path references.

## Check Log

| Check | Command | Result |
| --- | --- | --- |
| Owned tracked Markdown count | `git ls-files '*.md' \| rg -v '^(src/ardupilot/\|src/ardupilot_gazebo/\|src/SITL_Models/\|env/\|docs/presentations/node_modules/\|var/\|\.private/)' \| sort \| wc -l` | 229 |
| Untracked/ignored presentation Markdown | `find docs/presentations -path '*/node_modules' -prune -o -type f -name '*.md' -print \| sort` | 10 Markdown files, all ignored by .gitignore line 25 |
| Presentations tracked node_modules | `git ls-files 'docs/presentations/node_modules/**' \| wc -l` | 0 |
| Presentations ignore rule | `git check-ignore -v docs/presentations/README.md docs/presentations/package.json docs/presentations/reveal_md_template/slides.md` | .gitignore:25 ignores docs/presentations/ as a whole |
| Removed migration status path | `find . -path './.git' -prune -o -path './src/ardupilot' -prune -o -path './src/ardupilot_gazebo' -prune -o -path './src/SITL_Models' -prune -o -path './env' -prune -o -path './docs/presentations/node_modules' -prune -o -name 'migration_status.md' -print` | no file found |
| Current non-evidence migration_status references | `rg -n --fixed-strings 'docs/operations/migration_status.md' docs .ai governance scripts Makefile -g '*.md' -g '*.sh' -g 'Makefile' -g '!governance/audits/2026-08-10_document_inventory.md'` | five governance runbook references remain: active rollback lines 63 and 76, plus historical migration runbooks phase_0, phase_7, and phase_8 |
| Evidence migration_status references | `rg -n --fixed-strings 'docs/operations/migration_status.md' evidence -g '*.md'` | historical evidence/report/index references; accepted reports are not edited |
| Migration runbook references | `rg -n --fixed-strings 'governance/runbooks/migration/' docs .ai governance scripts Makefile evidence -g '*.md' -g '*.sh' -g 'Makefile'` | .ai, docs, governance, scripts validator, and evidence still reference this home |
| test_suite migration references | `rg -n --fixed-strings 'governance/runbooks/features/test_suite_migration' docs .ai governance scripts Makefile evidence -g '*.md' -g '*.sh' -g 'Makefile'` | docs/.ai/governance/evidence still reference this completed feature runbook |
| README removed-structure scan | `git ls-files -z '*README.md' \| xargs -0 rg -n 'compat_scripts\|migration_status\|src/SIM_ARD_GAW\|docs/operations/migration_status.md\|node_modules\|removed\|retired\|superseded'` | tracked README hits are historical archive/evidence references or retirement wording; no tracked README presents compat_scripts as live |
| Audit filename/content scan | `for f in $(git ls-files 'governance/audits/**/*.md' 'governance/audits/*.md' \| sort); do printf '%s \| ' "$f"; sed -n '1s/^# //p' "$f"; done` | no audit filename found that materially misdescribes its heading/content; raw uppercase files are imported provenance |
| Structure/evidence validation | `make doctor` | PASS. This differs from the task's expected baseline note of one pre-existing `.private` failure; no such failure appeared on 2026-08-10. |
| Requested test command | `pytest tests/unit tests/integration -q` | Blocked in this shell: `pytest` command not found. |
| Workspace virtualenv test command | `env/bin/python3 -m pytest tests/unit tests/integration -q` | PASS: 553 passed, 6 warnings, 506 subtests passed in 77.88s. |

The initial worktree was already dirty/staged before this audit (`.ai/entrypoint.md`, `.ai/index.md`, three lane docs, and `governance/standards/lane_documentation.md`), so the requested final `git status` invariant cannot literally show only this new file unless pre-existing user changes are set aside.
