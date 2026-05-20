# Evidence Reports

This directory holds reviewed evidence reports: dated conclusions, commands,
scope, output locations, limitations, and pass/fail/blocker statements.

Reports are organized into purpose-based subdirectories so the top level stays
readable. The top level holds only this README plus the category
subdirectories.

## Layout

```text
evidence/reports/
├── README.md
├── migration/    # one-time migration phase, cutover, shadow parity, plan pack reports
├── features/     # feature-scoped governance and implementation reports
├── operations/   # recurring operational verification and bootstrap smoke reports
├── audits/       # evidence reports from strict policy or evidence reviews
└── campaigns/    # campaign result reports (vehicle/campaign validation, wind matrix)
```

## Subdirectory Purpose

- `migration/`: migration plan packs, Phase 0-8 reports, cutover reports,
  shadow parity reports tied to a migration cutover, and workspace migration
  validation reports.
- `features/`: feature-specific implementation reports, such as the naming
  convention policy report, runbook reorganization report, test_suite
  migration reports, agent entrypoint/lifecycle policy report, and commit
  style adoption report.
- `operations/`: recurring operational verification reports and bootstrap or
  runtime smoke reports that are not tied to a specific migration phase,
  feature, or campaign.
- `audits/`: evidence report outputs from strict reviews or policy reviews,
  when they are evidence reports. Governance audit records remain under
  `governance/audits/` and are not duplicated here.
- `campaigns/`: campaign result reports such as vehicle/campaign validation
  reports and wind matrix campaign summaries. Phase-scoped campaign
  migration evidence (for example `PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`)
  stays under `migration/` because it is tied to the migration phase, not a
  standalone campaign result.

## Classifying A New Report

1. Decide which subdirectory matches the report's primary purpose using the
   rules above. If none fit, propose a new category in this README before
   adding files; do not drop the report at the top level.
2. Place the report in that subdirectory.
3. Update `evidence/indexes/evidence_catalog.md` with the new report path.
4. Cross-link the report from the relevant doc, `.ai/` pointer, or runbook
   so humans and agents can find it.

## Naming

- New evidence reports use `YYYY-MM-DD_lower_snake_case.md`.
- Examples: `2026-05-24_naming_convention_policy.md`,
  `2026-05-24_campaign_result_plane_lidar.md`.
- Date prefixes are required for new reports because reports are historical
  records.
- Existing accepted reports with older filenames are preserved for
  provenance even after the reorganization move. Route readers through
  `evidence/indexes/evidence_catalog.md` instead of renaming for aesthetics.
- See `governance/standards/naming.md` for the workspace-wide naming policy.

## Top-Level Rule

`evidence/reports/` top level may contain only:

- this `README.md`, and
- the category subdirectories listed above.

Do not add new report files at the top level. New top-level subdirectories
require a deliberate update to this README and the validator allowlist in
`scripts/maintenance/validate_evidence.sh`.

Do not place raw logs, `.BIN`, `.tlog`, simulator run trees, or unreviewed
analysis output here. Raw and working output belongs under `var/`; selected
proof belongs under the appropriate `evidence/` home.
