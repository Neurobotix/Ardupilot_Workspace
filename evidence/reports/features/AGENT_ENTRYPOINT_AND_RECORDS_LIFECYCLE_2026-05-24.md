# Agent Entrypoint And Records Lifecycle - 2026-05-24

Status: governance/docs update.

## Scope

This update adds a fixed AI agent entry point and makes archive/runbook lifecycle
rules explicit.

## Files Changed

- `AGENTS.md`
- `.ai/entrypoint.md`
- `.ai/README.md`
- `.ai/index.md`
- `governance/standards/documentation.md`
- `governance/standards/records_lifecycle.md`
- `README.md`

## Result

Agents now have one fixed starting file: `AGENTS.md`.

Detailed task routing lives in `.ai/entrypoint.md`, with required read sets,
rules, and minimum checks for simulation runs, feature work, campaign work,
config/asset changes, docs/governance work, and compatibility refactors.

Archived docs are explicitly non-canonical. They are historical records and may
contain stale commands, deprecated paths, or contradictions. The Phase 3 errata
record remains the disposition source for archived source docs.

Completed phase runbooks remain in `governance/runbooks/` while cutover,
rollback, shadow parity, and compatibility retirement are still relevant. After
final cutover and compatibility retirement, one-time phase runbooks may move to
a migration-history bundle only when evidence reports exist, `.ai/current.md`
does not point to them as active work, and canonical docs no longer depend on
them as current instructions.

The old production/reference workspace was not modified.
