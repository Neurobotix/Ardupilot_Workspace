# Agent Protocol

This `.ai` tree is intentionally small. Do not duplicate operator docs here.

Start every session by reading:

1. `AGENTS.md`
2. `.ai/entrypoint.md`
3. `.ai/index.md`
4. `.ai/current.md`
5. `governance/standards/documentation.md`
6. `governance/standards/naming.md`
7. `governance/runbooks/operations/shadow_parity.md` if validating migration

Canonical human docs live in `docs/`. Durable decisions live in
`governance/decisions/`. Audit records live in `governance/audits/`.

## Naming

- Stable agent protocol files use `lower_snake_case.md`.
- Examples: `entrypoint.md`, `current.md`, `index.md`.
- Date prefixes are not required for active agent routing files.
- Historical session or audit records may use date-first names when retained as
  event records.

Before creating new agent-facing files, check
`governance/standards/naming.md` and keep `.ai/` as pointers and protocol, not
duplicate human documentation.
