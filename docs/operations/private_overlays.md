# Private Overlays

`.private/` is local-only and ignored by git.

Allowed:

- `.private/config/*.local.parm`
- `.private/env/*.local`
- `.private/notes/` for personal reminders only
- `.private/backups/`

Not allowed:

- Duplicate operator docs
- Duplicate launch scripts
- Canonical runtime code
- Required configuration values
- Required environment variables
- Shared test procedures
- Troubleshooting facts needed for normal operation

If a note contains operational knowledge that another operator or agent needs,
promote it to a canonical tracked home first:

- runtime procedure: `docs/operations/`
- setup and install behavior: `docs/onboarding/` or `src/external/DEPENDENCIES.md`
- shared parameters: `config/`
- durable policy: `governance/standards/`
