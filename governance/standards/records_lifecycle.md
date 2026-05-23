# Records Lifecycle Standard

Do not delete records just because a phase finished. Move or archive records
only when their role changes.

## Record Homes

| Record type | Home | Lifecycle rule |
| --- | --- | --- |
| Canonical human docs | `docs/` | Stay active while current; move to `docs/archive/` when superseded. |
| Archived source docs | `docs/archive/` | Historical only; never current truth unless rewritten and verified into canonical docs. |
| Standards | `governance/standards/` | Stay active until replaced by a newer standard or ADR. |
| ADRs | `governance/decisions/` | Append-only durable decisions; do not move casually. |
| Audits, incidents, errata | `governance/audits/` | Retain while referenced by decisions, docs, evidence, or migration history. |
| Active operational runbooks | `governance/runbooks/operations/` | Cross-cutting procedures (rollback, parity gates, drills). Stay while they guide current or future work. |
| Migration phase runbooks | `governance/runbooks/migration/` | Stay until final cutover and compatibility retirement are complete; then may move to a migration-history bundle. Do not delete just because a phase finished. |
| Feature runbooks | `governance/runbooks/features/<feature_slug>/` | One directory per feature large enough to need a plan, implementation notes, or review. Stay while related code, docs, or evidence still rely on the context. |
| Evidence reports | `evidence/reports/` | Append-only proof; do not delete accepted reports. |
| Evidence indexes | `evidence/indexes/` | Stay active while they route readers to current proof. |
| Agent current state | `.ai/current.md` | Keep current only; old state belongs in `.ai/sessions/` if worth preserving. |

Stable living docs, standards, active indexes, and agent pointers use
`lower_snake_case.md`. Historical/event records use
`YYYY-MM-DD_lower_snake_case.md` when created after
`governance/standards/naming.md`. ADRs keep `ADR-0001-short-slug.md`.

## Archived Docs

Archived docs are not guaranteed to be free of stale commands,
deprecated paths, or contradictions. Their disposition is tracked in
`governance/audits/2026-05-20_phase3_docs_errata.md`.

Use archived docs only as historical reference. If archived material becomes
useful again, rewrite it into the current doc model and attach fresh evidence.

## Runbook Directory Norm

`governance/runbooks/` is organized, not flat. Every runbook lives in one of
three category directories:

- `governance/runbooks/migration/` for one-time migration phase runbooks and
  the full migration plan.
- `governance/runbooks/operations/` for cross-cutting active operational
  runbooks (rollback, parity gates, recurring drills).
- `governance/runbooks/features/<feature_slug>/` for per-feature runbook
  bundles (`plan.md`, `implementation.md`, `review.md`, optional
  `evidence.md`).

Top-level files under `governance/runbooks/` are reserved for the directory
README. Do not add new flat runbook files at the top level.

See `governance/runbooks/README.md` for the routing rules and
`governance/runbooks/features/README.md` for the per-feature contract.

## Completed Runbooks

Migration phase runbooks remain under `governance/runbooks/migration/` while
migration, cutover, rollback, shadow parity, or compatibility retirement work
is still relevant.

After final cutover and compatibility retirement:

1. Keep operational runbooks active under `governance/runbooks/operations/`.
2. Move migration phase runbooks to a clearly indexed migration-history
   bundle only after their evidence reports exist, `.ai/current.md` no longer
   points to them as active work, and canonical docs no longer rely on them as
   current instructions. Do not delete them.
3. Feature runbook directories stay until the related code, docs, and
   evidence no longer need their context. Superseded feature runbooks should
   keep their directory and add a `review.md` pointer to the successor.
4. Do not move ADRs, audits, or evidence reports simply because a runbook
   moved.

## Deletion Policy

Allowed deletion candidates:

- duplicate drafts with no unique history
- scratch output
- raw runtime artifacts that are already ignored or superseded by curated
  evidence
- unreferenced temporary records created during a failed attempt

Do not delete:

- accepted evidence reports
- ADRs
- incident audits
- cutover or rollback records
- phase reports that justify current migration status
- archived docs before their replacement and disposition are clear

## Naming And Provenance

Naming cleanup is not a reason to delete or mass rename records. Preserve
accepted evidence reports, ADRs, incident audits, imported raw audit packages,
and archive material when their names are part of provenance or are already
referenced. Use indexes, README guidance, and new-policy names going forward.
