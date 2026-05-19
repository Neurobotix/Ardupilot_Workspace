# Change Control Standard

Every change in `ardupilot_workspace_next` must update all affected homes. A
change is incomplete if code moved but docs, evidence, or governance still point
to the old truth.

## Required Routing

| Change type | Primary home | Required secondary updates |
| --- | --- | --- |
| Runtime code | `src/sim_ard_gaw/` | `tests/`, `docs/operations/` when user-facing, `.ai/current.md` if active work changes |
| Simulator asset | `assets/` | `docs/architecture/` or `docs/operations/` if referenced, parity/evidence if verified |
| Shared parameter/config | `config/` | `docs/operations/`, `docs/vehicles/` or `docs/campaigns/`, evidence hash/report |
| Local override | `.private/` | No canonical docs unless the override becomes shared config |
| Runtime output | `var/` | Promote only selected summaries/manifests/reports to `evidence/` |
| Evidence/result | `evidence/` | Link from relevant docs and `.ai/current.md` if it changes active status |
| Decision/policy | `governance/decisions/` or `governance/standards/` | Link from `.ai/index.md`; update affected docs |
| Migration phase runbook | `governance/runbooks/migration/` | Link from `.ai/index.md` when active; cross-link from the matching evidence report |
| Operational runbook | `governance/runbooks/operations/` | Link from docs or `.ai/index.md` when operationally relevant |
| Feature runbook | `governance/runbooks/features/<feature_slug>/` | Required for any feature large enough to need planning or review; link from `.ai/current.md` while active |
| Human documentation | `docs/` | Update `.ai/index.md` if it becomes a canonical entry point |
| Agent working state | `.ai/` | Must point to canonical homes, not duplicate them |
| Commit/push policy | `governance/standards/git_commit_style.md` | Link from `AGENTS.md` and `.ai/entrypoint.md`; apply before commits or pushes |
| Naming policy | `governance/standards/naming.md` | Check before creating or renaming files; update directory README guidance when a home needs local rules |

## Definition Of Done

Before a change is considered complete:

1. The file lives in the correct primary home.
2. All references to old paths are updated or intentionally archived.
3. The related human doc is updated if humans run, configure, or interpret it.
4. `.ai/current.md` is updated if the active migration state changed.
5. Governance is updated if the change creates or modifies a durable rule.
6. Evidence is added if the change claims something works.
7. Tests or runbook checks are added/updated for non-trivial behavior.
8. Raw runtime output remains under `var/` and out of git.
9. New files comply with `governance/standards/naming.md` and the nearest
   directory README, or the exception is documented.
10. `make doctor` passes after any change to structure, docs, governance,
   ignore policy, runtime paths, or local overlay policy.
11. Any commit created for the change follows
    `governance/standards/git_commit_style.md`; any push is explicitly
    authorized by the user.

## Commit And Push Rule

Commit-message style is shared workspace policy. Before creating a commit or
pushing local commits, agents must read
`governance/standards/git_commit_style.md` and use one exact canonical prefix.

Do not stage unrelated untracked workspace contents just to satisfy a commit or
push request. If no safe scoped change is staged or committable, report that the
commit or push is blocked pending staging decisions.

## Evidence Rule

Do not write `WORKING`, `VERIFIED`, or `READY FOR CUTOVER` without a dated
evidence file under `evidence/reports/` or a linked curated manifest/report under
`evidence/`.

## Compatibility Rule

Compatibility paths are allowed only while they are named and tracked as
migration bridges. Any compatibility path must have:

- an owner,
- an exit condition,
- a parity check,
- and a removal phase in the migration plan.

## Feature Runbook Rule

Any new feature, workstream, or operational domain large enough to need
planning, implementation notes, or a structured review must get a dedicated
runbook directory under `governance/runbooks/features/<feature_slug>/`. A
one-line fix or a trivial doc tweak does not need a runbook directory.

The minimum contract is `plan.md` before implementation begins; add
`implementation.md`, `review.md`, and optional `evidence.md` as the work
progresses. See `governance/runbooks/features/README.md` for the contents and
naming convention. Phased feature files may use `phase_<n>_<short_slug>.md`.

Do not add new flat runbook files at the top level of `governance/runbooks/`.
Migration runbooks belong under `migration/`, cross-cutting operational
runbooks belong under `operations/`, and feature work belongs under
`features/<feature_slug>/`.

## Structure Validation Rule

`scripts/maintenance/validate_structure.sh` is the canonical Phase 1 structure
validator and is called by `make doctor`. It enforces required top-level homes,
broken symlink checks, raw log leakage checks, nested `.private` checks,
`.private/` policy checks, gitignore coverage, stale canonical reference scans,
and required migration-plan links.

`.private/` may contain local overlays, notes, backups, and local environment
files. It must not contain `.private/docs`, `.private/scripts`, duplicate
canonical docs, command-like operational procedures, or canonical runnable
logic. Private notes may point to canonical tracked homes only when clearly
marked as pointers.

Canonical docs, governance, and AI pointers must not use legacy paths as
current truth. Any remaining legacy workspace path, compatibility path, retired
target, or production-status wording must be explicitly allowlisted by
`scripts/maintenance/validate_structure.sh` with an exact file, label, and
matched text rule. The validator must print the reason and matched text for each
allowed exception.

## Naming Rule

Any change that creates files must check `governance/standards/naming.md` and
the nearest directory README before choosing names. Do not rename accepted
historical evidence, ADRs, or archive material only for aesthetics. Use new
date-first names for new historical/event records and stable lower snake case
for living docs, code, tests, scripts, config, and active indexes.
