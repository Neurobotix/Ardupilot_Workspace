# Governance Runbooks

This directory holds operational procedures, migration phase plans, and
feature-scoped runbooks. It is organized so the top level stays readable: a
flat dumping ground of every runbook ever written is not acceptable.

## Layout

```text
governance/runbooks/
├── README.md           # this file
├── migration/          # one-time migration phase runbooks
├── operations/         # active cross-cutting operational runbooks
└── features/           # per-feature runbook directories (see features/README.md)
```

## Rules

1. Every major feature, workstream, or operational domain gets its own
   dedicated directory. Do not add new top-level runbooks.
2. The top level is reserved for this README and the three category
   subdirectories.
3. Completed migration-phase runbooks stay under `migration/`. They are
   historical record and are not deleted just because the phase is done. The
   records lifecycle rule for moving them to a migration-history bundle is in
   `governance/standards/records_lifecycle.md`.
4. Cross-cutting operational runbooks (rollback procedures, shadow parity,
   on-call procedures, recurring drills) belong under `operations/`. These are
   reusable and not tied to a single feature or phase.
5. New feature work that is large enough to need planning, implementation
   notes, or review structure must get a `features/<feature_slug>/` directory.
   See `features/README.md` for the naming and contents convention.
6. A runbook never belongs in two places at once. If a runbook's purpose
   changes from migration to operations or to a feature, move it deliberately
   and update every reference in the same change.
7. Do not put ADRs, audits, or evidence reports here. Those have their own
   homes under `governance/decisions/`, `governance/audits/`, and `evidence/`.

## Naming

- Migration and operational runbook files use `lower_snake_case.md`.
- Migration phase runbooks may use `phase_<n>_<short_slug>.md` when the phase
  number is part of the durable identity.
- Feature runbook directories use lower snake case and follow
  `features/README.md`.
- Date prefixes are not required for stable runbooks. Use date-first names only
  for event records such as audits, incidents, and evidence reports in their
  own homes.
- Existing historical runbook names are preserved unless a deliberate move or
  rename updates every reference.

See `governance/standards/naming.md` for the workspace-wide policy.

## Where Things Live Now

- Migration plan and Phase 0 through Phase 8 runbooks: `migration/`.
- Shadow parity proof gate (used by Phase 2 and Phase 7): `operations/shadow_parity.md`.
- Workspace cutover rollback guidance: `operations/workspace_cutover_rollback.md`.
- Future feature runbook directories: `features/<feature_slug>/`.

## Adding A New Runbook

1. Decide the category: `migration/`, `operations/`, or
   `features/<feature_slug>/`. If none fit, propose a new category in this
   README before adding files.
2. Place the runbook in that directory. Do not create a new top-level file.
3. Check `governance/standards/naming.md` and this README before naming the
   file.
4. Update `.ai/index.md` if the runbook is an agent-facing entry point.
5. Update `governance/standards/change_control.md` only if the runbook
   introduces a durable policy or routing change.
6. Add the runbook to the relevant doc cross-links (`docs/`, the matching
   evidence report, or `AGENTS.md`) so humans and agents can find it.
