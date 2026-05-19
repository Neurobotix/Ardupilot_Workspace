# Documentation Standard

`docs/` is for humans operating and understanding the system. `.ai/` is for
agent protocol, active state, and links to canonical records. Durable decisions
belong in `governance/decisions/`. Audits and errata belong in
`governance/audits/`.

Canonical status claims require evidence: a path, command, hash, commit, dated
log, or explicit decision record.

Historical docs and completed phase records follow
`governance/standards/records_lifecycle.md`.

Stable living docs use `lower_snake_case.md`. Historical/event records such as
audits, incidents, evidence reports, and one-off reviews use
`YYYY-MM-DD_lower_snake_case.md` when created after the naming standard. See
`governance/standards/naming.md` before adding new docs or moving records.

Runbooks live under organized subdirectories of `governance/runbooks/`:
`migration/` for migration phase runbooks, `operations/` for cross-cutting
operational runbooks, and `features/<feature_slug>/` for per-feature runbook
bundles. Canonical docs should link runbooks by their organized path, not by
a legacy flat path. See `governance/runbooks/README.md`.
