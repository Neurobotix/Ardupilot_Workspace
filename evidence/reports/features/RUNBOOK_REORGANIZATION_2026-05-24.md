# Runbook Reorganization — 2026-05-24

Date/time: 2026-05-24 13:59 EEST (UTC+3)
Scope: reorganize `governance/runbooks/` into categorized subdirectories and
codify the new layout as the permanent workspace norm. No runbook content was
edited beyond cross-link path updates. No phase status was changed by this
move.

## Decision

`governance/runbooks/` is no longer a flat directory. It now has three
categories:

- `migration/` — one-time migration phase runbooks plus `full_migration_plan.md`.
- `operations/` — cross-cutting active operational runbooks (shadow parity,
  cutover rollback, future on-call/drill procedures).
- `features/<feature_slug>/` — per-feature runbook bundles for future feature
  work. Currently contains only `features/README.md`.

A top-level `README.md` documents the layout and the rule that no new flat
runbook files are added at the top level.

## File Moves

All moves preserved file contents byte-for-byte. The repository has no root
commit yet, so `git mv` and `mv` are equivalent for history; plain `mv` was
used.

| From | To |
|---|---|
| `governance/runbooks/full_migration_plan.md` | `governance/runbooks/migration/full_migration_plan.md` |
| `governance/runbooks/phase_0_foundation_freeze.md` | `governance/runbooks/migration/phase_0_foundation_freeze.md` |
| `governance/runbooks/phase_1_structure_hardening.md` | `governance/runbooks/migration/phase_1_structure_hardening.md` |
| `governance/runbooks/phase_2_runtime_parity.md` | `governance/runbooks/migration/phase_2_runtime_parity.md` |
| `governance/runbooks/phase_3_documentation_rebuild.md` | `governance/runbooks/migration/phase_3_documentation_rebuild.md` |
| `governance/runbooks/phase_4_config_asset_normalization.md` | `governance/runbooks/migration/phase_4_config_asset_normalization.md` |
| `governance/runbooks/phase_5_campaign_test_migration.md` | `governance/runbooks/migration/phase_5_campaign_test_migration.md` |
| `governance/runbooks/phase_6_evidence_operations.md` | `governance/runbooks/migration/phase_6_evidence_operations.md` |
| `governance/runbooks/phase_7_cutover_deprecation.md` | `governance/runbooks/migration/phase_7_cutover_deprecation.md` |
| `governance/runbooks/phase_8_compatibility_retirement.md` | `governance/runbooks/migration/phase_8_compatibility_retirement.md` |
| `governance/runbooks/shadow_parity.md` | `governance/runbooks/operations/shadow_parity.md` |
| `governance/runbooks/workspace_cutover_rollback.md` | `governance/runbooks/operations/workspace_cutover_rollback.md` |

Filename note: the original Phase 4 runbook is
`phase_4_config_asset_normalization.md` (not `phase_4_config_asset_migration.md`).
The original filename was preserved to keep the existing evidence and
internal-reference text accurate.

## Files Added

- `governance/runbooks/README.md` — layout, rules, and where things live now.
- `governance/runbooks/features/README.md` — per-feature runbook bundle
  contract (`plan.md`, `implementation.md`, `review.md`, optional
  `evidence.md`).
- `evidence/reports/RUNBOOK_REORGANIZATION_2026-05-24.md` — this report.

## Governance Standards Updated

- `governance/standards/records_lifecycle.md`:
  - Record-home table now distinguishes active operational runbooks under
    `operations/`, migration phase runbooks under `migration/`, and feature
    runbooks under `features/<feature_slug>/`.
  - New section "Runbook Directory Norm" makes categorized subdirectories the
    permanent layout; top-level flat runbook files are not allowed.
  - "Completed Runbooks" section rewritten to point at the new homes.
- `governance/standards/change_control.md`:
  - Required-routing table now has three runbook rows (migration,
    operational, feature) with explicit homes.
  - New "Feature Runbook Rule" requires a dedicated
    `features/<feature_slug>/` directory for any feature large enough to need
    planning or review, with `plan.md` as the minimum contract.
- `governance/standards/documentation.md`: notes the categorized layout and
  points to `governance/runbooks/README.md`.

## Live Cross-References Updated

Only live navigational references were updated. Dated evidence reports under
`evidence/reports/` were intentionally left as-is so they remain accurate
historical records of the workspace state at their report dates. Readers
following an old evidence report to find a runbook should map the path
through the table above.

Updated:

- `README.md` — migration plan link and a pointer to the runbook README.
- `.ai/index.md` — full migration plan, Phase 5/6/7/8 runbook links, shadow
  parity, rollback runbook, plus a new pointer to the runbook README.
- `.ai/current.md` — active-plan link and rollback runbook link.
- `.ai/entrypoint.md` — Phase 5 and Phase 8 runbook links.
- `docs/onboarding/quick_start.md` — migration plan link.
- `docs/operations/migration_status.md` — migration plan, shadow parity, and
  rollback runbook links.
- `governance/runbooks/migration/full_migration_plan.md` — internal
  reference to `phase_*` runbooks now points under `migration/`.
- `governance/runbooks/migration/phase_7_cutover_deprecation.md` — three
  references to `shadow_parity.md` and the required-updates list now point
  under the categorized layout.
- `governance/runbooks/operations/shadow_parity.md` — pointer to the full
  migration plan now uses the new path.
- `governance/decisions/ADR-0005-workspace-next-cutover.md` — rollback
  runbook pointer.
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md` — Phase 5 runbook
  pointer.
- `evidence/indexes/evidence_catalog.md` — two `workspace_cutover_rollback.md`
  pointers (live cross-phase index, not a dated report).
- `scripts/maintenance/validate_structure.sh` — every hardcoded runbook
  allowlist entry and the `check_migration_links` target list updated to the
  new paths. The validator was updated intentionally to match the new norm,
  not weakened.

Not updated (intentional):

- All dated reports under `evidence/reports/` (e.g.,
  `MIGRATION_PLAN_PACK_2026-05-20.md`, `PHASE_*_2026-05-*.md`,
  `CUTOVER_*.md`). These are historical proof and were not rewritten. The
  paths recorded inside them describe the workspace as it existed on the
  report date; this report is the cross-reference point for the move.

## Phase Status Statement

This change moves files and updates cross-links only. It does not alter the
status of any migration phase:

- Phase 7 cutover remains PASS as of 2026-05-24 under
  `evidence/reports/CUTOVER_2026-05-24.md` and
  `governance/decisions/ADR-0005-workspace-next-cutover.md`.
- Phase 8 compatibility retirement remains as recorded in
  `evidence/reports/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md` (implementation
  ownership pass; `compat_scripts/` retained as wrapper-only).
- No new claim of Phase 7 or Phase 8 completion is made here beyond what
  dated evidence already records.

## Validation

Commands run:

- `rg "governance/runbooks/" .` — every active surface points at the
  categorized layout. Remaining matches outside `evidence/reports/`,
  `governance/runbooks/migration/`, and `governance/runbooks/operations/`
  live only in this report and in the new `governance/runbooks/README.md`
  documentation. Dated reports under `evidence/reports/` still reference the
  pre-move paths and are intentionally untouched.
- `make doctor` — runs `validate_structure.sh` and `validate_evidence.sh`.
  Result and any blockers are recorded below.

## make doctor Result

`make doctor` ran end-to-end and reported:

- `STRUCTURE VALIDATION PASSED`:
  - required top-level homes present;
  - no broken symlinks;
  - no raw log leakage;
  - no nested `.private/` content;
  - `.private/` policy clean;
  - gitignore coverage intact;
  - stale-reference scan: every match in the moved runbook files
    (`governance/runbooks/migration/phase_2_runtime_parity.md`,
    `governance/runbooks/migration/phase_8_compatibility_retirement.md`,
    `governance/runbooks/operations/workspace_cutover_rollback.md`) was
    correctly attributed by the updated allowlist; no disallowed references;
  - migration-plan link gate passed against the new
    `governance/runbooks/migration/full_migration_plan.md` target from
    `README.md`, `.ai/index.md`, `.ai/current.md`,
    `docs/onboarding/quick_start.md`, and `docs/operations/migration_status.md`.
- `EVIDENCE VALIDATION PASSED`:
  - no raw log leakage;
  - no unallowlisted raw runtime signatures in tracked evidence homes;
  - no raw run directories under evidence;
  - evidence top-level homes shape clean;
  - report-home shape clean;
  - dated phase reports stay under `evidence/reports/`;
  - all required evidence templates present;
  - catalog sanity markers and statuses present;
  - curated-root catalog coverage complete.

No structure or evidence check failed as a result of the move.

## Old Workspace

The old workspace at `/home/ahmed/ardupilot_workspace` was not modified by
this reorganization.
