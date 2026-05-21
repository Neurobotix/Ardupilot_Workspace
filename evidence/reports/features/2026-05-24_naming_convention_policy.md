# Naming Convention Policy

Date/time: 2026-05-24

Timezone: Africa/Cairo

Status: pass

## Scope

Implemented workspace-wide naming policy and directory-level guidance for new
files in `/home/ahmed/ardupilot_workspace_next`.

This was not a mass rename project. The work added forward-looking policy,
agent routing, directory guidance, lightweight validator support, and this
evidence record.

## Files Changed

- `AGENTS.md`
- `.ai/README.md`
- `.ai/entrypoint.md`
- `.ai/index.md`
- `docs/README.md`
- `evidence/indexes/README.md`
- `evidence/indexes/evidence_catalog.md`
- `evidence/reports/README.md`
- `evidence/reports/2026-05-24_naming_convention_policy.md`
- `evidence/templates/README.md`
- `governance/audits/README.md`
- `governance/runbooks/README.md`
- `governance/runbooks/features/README.md`
- `governance/standards/change_control.md`
- `governance/standards/documentation.md`
- `governance/standards/evidence.md`
- `governance/standards/naming.md`
- `governance/standards/records_lifecycle.md`
- `scripts/README.md`
- `scripts/maintenance/README.md`
- `scripts/maintenance/validate_structure.sh`
- `tests/README.md`

## Naming Policy Summary

- Stable living docs use `lower_snake_case.md`.
- Stable feature runbooks use `plan.md`, `implementation.md`, `review.md`, and
  optional `evidence.md`.
- Phased feature files may use `phase_<n>_<short_slug>.md`.
- Historical/event records use `YYYY-MM-DD_lower_snake_case.md`.
- ADRs keep the existing `ADR-0001-short-slug.md` style.
- Root exceptions remain `README.md`, `CHANGELOG.md`, `AGENTS.md`, and
  `Makefile`.
- Code, script, config, test, and asset names follow lower snake case unless an
  external tool or provenance reason requires a different name.
- Files are named for clarity. Use modified-time sorting or reverse lexical
  sorting for timeline views instead of forcing date prefixes onto stable docs.

## Inventory Summary

Read-only inventory covered root, `docs/`, `governance/`,
`governance/runbooks/`, `governance/runbooks/features/`,
`evidence/reports/`, `evidence/templates/`, `evidence/indexes/`, `.ai/`,
`scripts/`, `tests/`, `config/`, `assets/`, and `src/sim_ard_gaw/`.

Findings:

- Root already uses conventional exceptions and tool names.
- Current docs mostly already use stable lower snake case.
- Governance standards and runbooks mostly already use lower snake case, with
  ADRs using the established ADR style.
- Feature runbooks already use stable names, with one phased feature file
  matching the new `phase_<n>_<short_slug>.md` allowance.
- Evidence reports contain older uppercase phase and cutover names plus newer
  date-bearing names. These were treated as accepted historical records.
- Templates and active indexes already use stable lower snake case, except
  historical/imported index names preserved for provenance.
- Scripts, tests, config, and owned Python modules generally follow lower
  snake case; tool-required model files such as `model.sdf` and `model.config`
  remain valid exceptions.
- Assets contain imported media names with spaces and copy suffixes. They were
  not renamed because they are simulator/model assets and references were not
  audited for this policy change.

## Intentionally Not Renamed

- Accepted evidence reports with older names, including phase and cutover
  reports.
- ADR files under `governance/decisions/`.
- Files under `docs/archive/`.
- Imported raw audit package files under
  `governance/audits/2026-05-13_truth_audit/raw/`.
- Imported curated evidence package names and legacy report names.
- Simulator/model assets and media whose names may be tool- or reference-bound.
- Code, config, scripts, and tests that already satisfy the policy or need a
  separate reference audit before renaming.

No files were renamed.

## Validator And Check Results

Commands run:

```bash
rg "naming.md|naming convention|YYYY-MM-DD|lower_snake_case" AGENTS.md .ai governance docs evidence scripts tests README.md
make doctor
git status --short
git diff --stat
git diff --check
git ls-files | sed -n '1,20p'
```

Results:

- The `rg` policy scan found the new naming standard, agent routing, directory
  guidance, and evidence/report naming references.
- `make doctor` passed.
- `scripts/maintenance/validate_structure.sh` now checks that
  `governance/standards/naming.md` and required directory guidance files exist.
- The validator check is intentionally narrow and does not fail historical
  names.
- `git status --short` shows the full workspace tree as untracked because this
  bootstrap repository has no tracked baseline.
- `git diff --stat` and `git diff --check` returned no output. `git ls-files`
  also returned no tracked files, so those diff commands had no tracked
  baseline to inspect.

## Residual Risks

- Historical evidence names remain mixed by design; readers should use
  `evidence/indexes/evidence_catalog.md`.
- No strict repository-wide filename validator exists yet. Future enforcement
  should start with new files or narrowly scoped homes to avoid breaking
  historical provenance.
- Imported asset/media names were not audited for reference safety.
- Existing links were not exhaustively crawled beyond the requested scans and
  `make doctor`.

## Old Workspace Modification Statement

`/home/ahmed/ardupilot_workspace` was not modified. All work was performed in
`/home/ahmed/ardupilot_workspace_next`.
