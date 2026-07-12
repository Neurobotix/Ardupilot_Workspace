# Agent Index

- Fixed agent entry point: `AGENTS.md`
- Detailed agent task router: `.ai/entrypoint.md`
- Workspace map: `docs/architecture/workspace_map.md`
- Full migration plan: `governance/runbooks/migration/full_migration_plan.md`
- Change control standard: `governance/standards/change_control.md`
- Git commit style standard: `governance/standards/git_commit_style.md`
- Naming standard: `governance/standards/naming.md`
- Structure standard: `governance/standards/workspace_structure.md`
- Evidence standard: `governance/standards/evidence.md`
- Records lifecycle standard: `governance/standards/records_lifecycle.md`
- Human evidence workflow: `docs/operations/evidence_workflow.md`
- Presentation template: `docs/presentations/README.md`
- Evidence catalog: `evidence/indexes/evidence_catalog.md`
- Evidence report templates: `evidence/templates/`
- Runbook layout overview: `governance/runbooks/README.md`
- Shadow parity: `governance/runbooks/operations/shadow_parity.md`
- Phase 7 cutover runbook:
  `governance/runbooks/migration/phase_7_cutover_deprecation.md`
- Cutover rollback guidance:
  `governance/runbooks/operations/workspace_cutover_rollback.md`
- Phase 7 cutover report:
  `evidence/reports/migration/CUTOVER_2026-05-24.md`
- Phase 7 shadow parity report:
  `evidence/reports/migration/shadow_parity_2026-05-24.md`
- Phase 7 cutover decision:
  `governance/decisions/ADR-0005-workspace-next-cutover.md`
- Superseded Phase 7 blocked cutover report:
  `evidence/reports/migration/CUTOVER_2026-05-21.md`
- Superseded Phase 7 shadow parity report:
  `evidence/reports/migration/shadow_parity_2026-05-21.md`
- Phase 8 compatibility-retirement runbook:
  `governance/runbooks/migration/phase_8_compatibility_retirement.md`
- Phase 8 compatibility-retirement evidence:
  `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`
- Unified test-suite interactive CLI: `src/sim_ard_gaw/campaigns/test_suite/cli/run.py`
  and `src/sim_ard_gaw/campaigns/test_suite/cli/interactive.py`
- test_suite migration feature runbook:
  `governance/runbooks/features/test_suite_migration/`
- Airspeed failure behavior feature runbook (historical headwind Phase 2 raw
  measurement smoke accepted 2026-06-06; tailwind healthy gate and corrected
  two-attempt P130 pulse interpretation recorded through 2026-06-23):
  `governance/runbooks/features/airspeed_failure_behavior/`
- GPS failure behavior feature runbook (Phase 0 design lock accepted 2026-07-06;
  Phase 1 no-SITL foundation Chunks 1-2 implemented and under repair/hardening;
  Chunk 3 mission/overlay integration is implemented pending review; full
  Phase 1 remains open; no live SITL, readback, mechanism gate, BIN parsing,
  campaign execution, or evidence claim exists):
  `governance/runbooks/features/gps_failure_behavior/`
- GPS failure behavior design decisions (Proposed 2026-07-06; full reasoning in
  `governance/runbooks/features/gps_failure_behavior/design_adrs.md` and
  `design_research.md`):
  `governance/decisions/ADR-0017-gps-failure-fault-catalog.md`,
  `ADR-0018-gps-failure-knee-and-classification.md`,
  `ADR-0019-gps-failure-sweep-design.md`,
  `ADR-0020-gps-failure-mission-and-trigger.md`,
  `ADR-0021-gps-failure-parameter-overlay.md`
- Airspeed failure behavior technical analysis (2026-06-11; sweep + pulse ladder
  + stepped ramps; later accepted for bounded Phase 4A on 2026-06-14):
  `evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`;
  curated: `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/`
- Airspeed failure behavior Phase 4A bounded acceptance (2026-06-14; ratio
  sweep + pulse ladder + stepped ramps accepted, fixed-case Phase 4B open):
  `evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`
- Tailwind P130 pulse evaluator correction and two-attempt additive reanalysis
  (2026-06-23; raw manifests preserved):
  `evidence/reports/features/2026-06-23_tailwind_pulse_evaluator_correction.md`
- test_suite migration Phase 1 (wrapper parity) evidence:
  `evidence/reports/features/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md`
- test_suite migration Phase 2 (generic manifest) evidence:
  `evidence/reports/features/2026-05-25_test_suite_migration_phase_2.md`
- test_suite migration Phase 3 (staged attempt runner) evidence:
  `evidence/reports/features/2026-05-25_test_suite_migration_phase_3.md`
- test_suite migration Phase 3B (staged-boundary audit / negative proof;
  Phase 3C-3G now required for zero-legacy staged system) evidence:
  `evidence/reports/features/2026-05-29_test_suite_migration_phase_3b.md`
- test_suite migration Phase 3C (legacy-runner import blocker / staged
  foundation boundary; no live zero-legacy runtime proof) evidence:
  `evidence/reports/features/2026-05-29_test_suite_migration_phase_3c.md`
- test_suite migration Phase 3C review fixes (atomic manifests, staged
  running/terminal rows, stimulus run-config boundary) evidence:
  `evidence/reports/features/2026-05-31_test_suite_phase3c_review_fixes.md`
- test_suite migration Phase 3C review findings audit:
  `governance/audits/2026-05-31_test_suite_phase3c_review_findings.md`
- test_suite migration Phase 3C follow-up fixes (H-1..H-9; Phase 3F analysis
  substage now plugin-owned, canonical staged attempt dirs, run_suite flag
  parity guard) evidence:
  `evidence/reports/features/2026-05-31_test_suite_phase3c_followup_fixes.md`
- test_suite migration Phase 3D (zero-legacy runtime/environment; launch/cleanup
  now plugin-owned via runtime.py; assert_ready readiness remains Phase 3E)
  evidence:
  `evidence/reports/features/2026-05-31_test_suite_migration_phase_3d.md`
- test_suite migration Phase 3E (zero-legacy MAVLink control/monitor; staged
  assert_ready + WindMatrixAutoMissionControl + WindMatrixDisarmMonitor now
  call plugin-owned mavlink_control.*; only WindMatrixStimulus wind injection
  remains Phase 3F) evidence:
  `evidence/reports/features/2026-06-01_test_suite_migration_phase_3e.md`
- test_suite migration Phase 3F (zero-legacy wind injection; staged path now
  fully zero-legacy; first live completed staged run `success_full`) evidence:
  `evidence/reports/features/2026-06-01_test_suite_migration_phase_3f.md`;
  curated: `evidence/curated_logs/test_suite_phase3f_staged_live_20260601/`
- test_suite migration Phase 3G (live staged-vs-legacy comparison; GATE
  ACCEPTED, Phase 4 unblocked; staged matches legacy-direct within SITL noise)
  evidence:
  `evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md`;
  curated legacy baseline:
  `evidence/curated_logs/test_suite_phase3g_legacy_compare_20260601/`
- test_suite migration Phase 3C follow-up review findings audit:
  `governance/audits/2026-05-31_test_suite_phase3c_followup_findings.md`
- test_suite migration Phase 3C strict high-finding fixes (manifest
  reconciliation parity + staged run-config exact migrated-field parity)
  evidence:
  `evidence/reports/features/2026-05-31_test_suite_phase3c_manifest_run_config_parity_fixes.md`
- CTE wind-envelope platform-briefing result package (production-like 017
  campaign, corrected 020 source, no live reruns) evidence:
  `evidence/reports/features/2026-06-02_cte_wind_envelope_result.md`
- CTE wind-envelope curated analysis package:
  `evidence/curated_logs/cte_wind_envelope_017_20260602/`
- Pillar A flight engineering and analysis results rollup:
  `evidence/reports/features/2026-06-02_pillar_a_flight_results.md`
- Pillar A curated rollup package:
  `evidence/curated_logs/pillar_a_flight_results_20260602/`
- Superseded Phase 8 partial-retirement evidence:
  `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-22.md`
- Human migration status: `docs/operations/migration_status.md`
- Installation guide: `docs/onboarding/installation.md`
- Quick start: `docs/onboarding/quick_start.md`
- Troubleshooting guide: `docs/operations/troubleshooting.md`
- Simulation lanes and flight modes: `docs/architecture/simulation_lanes.md`
- Airspeed failure behavior lane (behavior characterization; Phase 2 measurement smoke accepted 2026-06-06; Phase 4A ratio/ramp/pulse characterization accepted 2026-06-14; fixed-case Phase 4B remains open): `docs/architecture/airspeed_failure_lane.md`
- GPS failure behavior lane (behavior characterization under degraded/corrupted GPS; EKF innovation-gate "knee"; Phase 0 design lock accepted 2026-07-06; Chunk 3 implemented pending review; full Phase 1 open; live runs deferred): `docs/architecture/gps_failure_lane.md`
- Launch target status: `docs/operations/launch_targets.md`
- Airspeed failure behavior — verified no-SITL commands, stack, output paths, live-run gate: `docs/operations/airspeed_failure_runbook.md`
- GPS failure behavior — no-SITL stack/CLI and live-run gate; live validation deferred: `docs/operations/gps_failure_runbook.md`
- SITL/Gazebo runtime notes: `docs/operations/sitl_gazebo_runtime.md`
- Vehicle status: `docs/vehicles/status.md`
- Wind matrix campaign status: `docs/campaigns/wind_matrix.md`
- Phase 5 campaign/test runbook:
  `governance/runbooks/migration/phase_5_campaign_test_migration.md`
- Phase 5 campaign/test evidence:
  `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`
- Phase 5 campaign safety decision:
  `governance/decisions/ADR-0003-phase5-campaign-safety-contract.md`
- Clean-run and workspace-plugin decision:
  `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`
- Airspeed failure behavior design decisions (accepted 2026-06-03; full reasoning
  in `governance/runbooks/features/airspeed_failure_behavior/design_adrs.md` and
  `design_research.md`):
  `governance/decisions/ADR-0006-airspeed-failure-mission-design.md`,
  `ADR-0007-airspeed-failure-case-payloads-and-ratio-sweep.md`,
  `ADR-0008-airspeed-failure-reset-protocol.md`,
  `ADR-0009-airspeed-failure-injection-trigger.md`,
  `ADR-0010-airspeed-failure-reference-wind.md`,
  `ADR-0011-airspeed-failure-behavior-classification.md`
- Phase 5 Gazebo plugin fallback incident:
  `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`
- Phase 6 evidence/operations runbook:
  `governance/runbooks/migration/phase_6_evidence_operations.md`
- Phase 6 evidence/operations report:
  `evidence/reports/migration/PHASE_6_EVIDENCE_OPS_2026-05-21.md`
- Asset index: `evidence/indexes/asset_index.md`
- Parameter/config index: `evidence/indexes/parameter_config_index.md`
- Phase 4 config/asset evidence:
  `evidence/reports/migration/PHASE_4_CONFIG_ASSETS_2026-05-21.md`
- External dependency record: `src/external/DEPENDENCIES.md`
- Private overlay policy: `docs/operations/private_overlays.md`
- Structure validator: `scripts/maintenance/validate_structure.sh`
- Evidence validator: `scripts/maintenance/validate_evidence.sh`
- Maintenance scripts: `scripts/maintenance/README.md`
- Migration audit: `governance/audits/2026-05-19_migration_summary.md`
- Truth audit raw record: `governance/audits/2026-05-13_truth_audit/raw/`
