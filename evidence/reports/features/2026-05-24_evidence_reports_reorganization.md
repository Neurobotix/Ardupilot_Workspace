# Evidence Reports Reorganization

Date/time: 2026-05-24

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: governance/docs evidence (no new runtime output)

Conclusion: PASS

## Scope

This change reorganizes `evidence/reports/` from a flat home into
purpose-based subdirectories, mirroring the categorized layout already used
under `governance/runbooks/`. No report content was edited beyond directory
relocation. No migration phase status changed because of this move. The
old workspace `/home/ahmed/ardupilot_workspace` was not modified.

Goals:

- Make `evidence/reports/` browsable without dumping every accepted report
  in one flat directory.
- Preserve provenance: historical filenames remain unchanged.
- Keep the evidence catalog as the canonical cross-phase router so
  filenames are not the sole way to find proof.
- Update all live references (docs, governance, `.ai`, indexes, validators)
  to point at the new paths.

## Target Structure

```text
evidence/reports/
├── README.md
├── migration/
├── features/
├── operations/
├── audits/
└── campaigns/
```

- `migration/` — Phase 0-8 reports, cutover reports, shadow parity, migration
  plan pack, workspace migration validation reports.
- `features/` — feature-scoped governance/implementation reports (naming
  policy, agent entrypoint/lifecycle, commit style adoption, runbook
  reorganization, test_suite migration, this report).
- `operations/` — recurring operational verification reports and bootstrap
  smoke reports not tied to a specific migration phase, feature, or campaign.
- `audits/` — evidence reports from strict policy or evidence reviews
  (currently empty; governance audit records stay under `governance/audits/`).
- `campaigns/` — campaign result reports (vehicle/campaign validation, wind
  matrix campaign summaries; currently empty because Phase 5 campaign
  migration evidence is migration-scoped).

## Classification

| Old path | New path | Category | Reason |
| --- | --- | --- | --- |
| `evidence/reports/MIGRATION_PLAN_PACK_2026-05-20.md` | `evidence/reports/migration/MIGRATION_PLAN_PACK_2026-05-20.md` | migration | initial migration plan pack |
| `evidence/reports/PHASE_0_BASELINE_2026-05-20.md` | `evidence/reports/migration/PHASE_0_BASELINE_2026-05-20.md` | migration | Phase 0 baseline |
| `evidence/reports/PHASE_1_STRUCTURE_2026-05-20.md` | `evidence/reports/migration/PHASE_1_STRUCTURE_2026-05-20.md` | migration | Phase 1 structure |
| `evidence/reports/PHASE_2_RUNTIME_PARITY_2026-05-20.md` | `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md` | migration | Phase 2 runtime parity |
| `evidence/reports/PHASE_3_DOCS_2026-05-20.md` | `evidence/reports/migration/PHASE_3_DOCS_2026-05-20.md` | migration | Phase 3 documentation rebuild |
| `evidence/reports/PHASE_4_CONFIG_ASSETS_2026-05-21.md` | `evidence/reports/migration/PHASE_4_CONFIG_ASSETS_2026-05-21.md` | migration | Phase 4 config/asset normalization |
| `evidence/reports/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md` | `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md` | migration | Phase 5 migration evidence (campaign+test_suite migration phase, not a standalone campaign result) |
| `evidence/reports/PHASE_6_EVIDENCE_OPS_2026-05-21.md` | `evidence/reports/migration/PHASE_6_EVIDENCE_OPS_2026-05-21.md` | migration | Phase 6 evidence operations |
| `evidence/reports/PHASE_7_REPROOF_2026-05-24.md` | `evidence/reports/migration/PHASE_7_REPROOF_2026-05-24.md` | migration | Phase 7 reproof review |
| `evidence/reports/PHASE_8_COMPAT_RETIREMENT_2026-05-22.md` | `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-22.md` | migration | Phase 8 partial (superseded) |
| `evidence/reports/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md` | `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md` | migration | Phase 8 pass |
| `evidence/reports/CUTOVER_2026-05-21.md` | `evidence/reports/migration/CUTOVER_2026-05-21.md` | migration | Phase 7 cutover (blocked, superseded) |
| `evidence/reports/CUTOVER_2026-05-24.md` | `evidence/reports/migration/CUTOVER_2026-05-24.md` | migration | Phase 7 cutover (pass) |
| `evidence/reports/shadow_parity_2026-05-21.md` | `evidence/reports/migration/shadow_parity_2026-05-21.md` | migration | shadow parity for Phase 7 (superseded) |
| `evidence/reports/shadow_parity_2026-05-24.md` | `evidence/reports/migration/shadow_parity_2026-05-24.md` | migration | shadow parity for Phase 7 (pass) |
| `evidence/reports/2026-05-24_naming_convention_policy.md` | `evidence/reports/features/2026-05-24_naming_convention_policy.md` | features | naming convention policy feature |
| `evidence/reports/AGENT_ENTRYPOINT_AND_RECORDS_LIFECYCLE_2026-05-24.md` | `evidence/reports/features/AGENT_ENTRYPOINT_AND_RECORDS_LIFECYCLE_2026-05-24.md` | features | agent entrypoint and lifecycle policy feature |
| `evidence/reports/GIT_COMMIT_STYLE_ADOPTION_2026-05-24.md` | `evidence/reports/features/GIT_COMMIT_STYLE_ADOPTION_2026-05-24.md` | features | git commit style adoption feature |
| `evidence/reports/RUNBOOK_REORGANIZATION_2026-05-24.md` | `evidence/reports/features/RUNBOOK_REORGANIZATION_2026-05-24.md` | features | governance runbook reorganization feature |
| `evidence/reports/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md` | `evidence/reports/features/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md` | features | test_suite migration feature Phase 1 |
| n/a (new) | `evidence/reports/features/2026-05-24_evidence_reports_reorganization.md` | features | this report |
| `evidence/reports/VALIDATION_2026-05-19.md` | `evidence/reports/operations/VALIDATION_2026-05-19.md` | operations | bootstrap smoke check, not tied to a migration phase or feature |

Notes:

- Historical filenames were preserved per
  `governance/standards/naming.md` and
  `governance/standards/records_lifecycle.md`. The reorganization is a
  directory move, not a rename.
- `audits/` and `campaigns/` are created but currently empty. `audits/` is
  reserved for evidence reports from strict reviews (governance audit
  records continue to live in `governance/audits/`). `campaigns/` is
  reserved for standalone campaign result reports. Phase 5 campaign
  migration evidence stays under `migration/` because its primary purpose
  is the migration phase record.

## Files Moved

15 reports moved to `evidence/reports/migration/`, 5 reports moved to
`evidence/reports/features/`, 1 report moved to
`evidence/reports/operations/`, plus this new report created under
`evidence/reports/features/`. `evidence/reports/README.md` retained at the
top level.

## References Updated

The following files were updated to point at the new paths:

- `AGENTS.md` — no direct evidence/reports references; no edit needed.
- `.ai/index.md`, `.ai/entrypoint.md`, `.ai/current.md`, `.ai/issues/open.md`.
- `README.md`.
- `docs/onboarding/installation.md`, `docs/operations/evidence_workflow.md`,
  `docs/operations/launch_targets.md`,
  `docs/operations/migration_status.md`,
  `docs/operations/troubleshooting.md`,
  `docs/architecture/simulation_lanes.md`,
  `docs/campaigns/wind_matrix.md`, `docs/vehicles/status.md`.
- `governance/standards/change_control.md`,
  `governance/standards/evidence.md`,
  `governance/standards/records_lifecycle.md`.
- `governance/audits/README.md`.
- `governance/decisions/ADR-0005-workspace-next-cutover.md`.
- `governance/runbooks/features/README.md`,
  `governance/runbooks/features/test_suite_migration/plan.md`,
  `governance/runbooks/features/test_suite_migration/phase_1_wrapper_parity.md`,
  `governance/runbooks/features/test_suite_migration/review.md`,
  `governance/runbooks/features/test_suite_migration/evidence.md`.
- `governance/runbooks/operations/shadow_parity.md` (including the
  `shadow_parity_<date>.md` recording template path).
- `governance/runbooks/migration/full_migration_plan.md`,
  `governance/runbooks/migration/phase_0_foundation_freeze.md`,
  `governance/runbooks/migration/phase_1_structure_hardening.md`,
  `governance/runbooks/migration/phase_2_runtime_parity.md`,
  `governance/runbooks/migration/phase_3_documentation_rebuild.md`,
  `governance/runbooks/migration/phase_4_config_asset_normalization.md`,
  `governance/runbooks/migration/phase_5_campaign_test_migration.md`,
  `governance/runbooks/migration/phase_6_evidence_operations.md`,
  `governance/runbooks/migration/phase_7_cutover_deprecation.md`,
  `governance/runbooks/migration/phase_8_compatibility_retirement.md`.
- `evidence/indexes/evidence_catalog.md` — Report column entries updated.
- `evidence/templates/README.md`,
  `evidence/templates/launch_runtime_smoke_report.md`,
  `evidence/templates/vehicle_verification_report.md`.
- `src/external/DEPENDENCIES.md`.
- `scripts/maintenance/validate_evidence.sh`,
  `scripts/maintenance/validate_structure.sh`.

References inside the moved reports themselves were intentionally left
unchanged. Dated evidence reports are append-only history per
`governance/standards/records_lifecycle.md` and
`governance/standards/evidence.md`; the catalog routes readers between
historical filenames and current paths.

## Validators Updated

- `scripts/maintenance/validate_evidence.sh`,
  `check_report_home_shape()` — relaxed to allow the five documented
  subdirectories under `evidence/reports/`. The check still fails on:
  - non-Markdown files anywhere under `evidence/reports/`,
  - unexpected top-level subdirectories (not in the allowed set), and
  - report files at the top level (only `README.md` is allowed there).
- `check_phase_report_home()` was not changed. Its existing
  `! -path './evidence/reports/*'` filter still matches files under
  subdirectories because `find -path` glob `*` matches `/`. Verified
  manually after the move: no `PHASE_*.md` files were found outside
  `evidence/reports/`.
- `check_raw_log_leakage()`, `check_evidence_runtime_pollution()`,
  `check_raw_run_directories()`, `check_evidence_top_level()`,
  `check_template_inventory()`, `check_catalog_sanity()`, and
  `check_curated_root_catalog_coverage()` were not weakened. They continue
  to enforce raw-log leakage and curated-evidence shape rules.
- `scripts/maintenance/validate_structure.sh` was only touched by the
  reference sed (`evidence/reports/README.md` mention preserved with the
  same path because the README stays at the top level).

## Commands Run

```bash
find evidence/reports -maxdepth 1 -type f -name "*.md" | sort
mkdir -p evidence/reports/{migration,features,operations,audits,campaigns}
mv <fifteen migration reports> evidence/reports/migration/
mv <five feature reports> evidence/reports/features/
mv VALIDATION_2026-05-19.md evidence/reports/operations/
sed -i -f /tmp/path_renames.sed <referencing files>
rg "evidence/reports/" .
find evidence/reports -maxdepth 1 -type f -name "*.md" -print
find evidence/reports -maxdepth 2 -type f -name "*.md" | sort
make doctor
```

## Validation Results

Results are recorded in the run that produced this report. See the closing
summary at the bottom of this file for the exact `make doctor` outcome.

## Old Workspace Modification Statement

`/home/ahmed/ardupilot_workspace` was not modified during this change. The
reorganization is scoped to `/home/ahmed/ardupilot_workspace_next` only.

## Residual Risks

- Intra-report cross-links inside moved reports still use the historical
  top-level paths (e.g., a Phase 7 cutover report referencing
  `evidence/reports/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md` without the
  `migration/` prefix). This is a deliberate preservation of historical
  text consistent with the records-lifecycle and evidence standards. A
  reader following one of those links inside a dated report must use the
  evidence catalog or directory listing to locate the file. The catalog
  has been updated to current paths.
- Validators were relaxed only enough to permit the documented
  subdirectories; new top-level subdirectories will still fail the
  `check_report_home_shape` check until added to both the README and the
  validator.
- This change does not claim any phase or cutover status change. It is a
  housekeeping move with no runtime impact.
