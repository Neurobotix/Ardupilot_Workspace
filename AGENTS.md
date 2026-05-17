# Agent Entry Point

This is the fixed starting point for AI agents working in this workspace.

Read this file first, then follow `.ai/entrypoint.md` for the specific task.

## Required First Reads

1. `AGENTS.md`
2. `.ai/entrypoint.md`
3. `.ai/current.md`
4. `.ai/index.md`
5. `governance/standards/change_control.md`
6. `governance/standards/naming.md`

## Non-Negotiable Rules

- Work in `/home/ahmed/ardupilot_workspace_next`.
- Treat `/home/ahmed/ardupilot_workspace` as read-only production/reference
  unless the user explicitly authorizes otherwise.
- Do not use `docs/archive/` as current truth. Archived docs are historical and
  may contain stale commands, paths, or contradictions.
- Do not make status, parity, vehicle, campaign, or cutover claims without dated
  evidence.
- Runtime output goes under `var/`.
- Curated proof goes under `evidence/`.
- Local-only overlays, secrets, machine notes, and personal notes go under
  `.private/`.
- Every change must update its designated homes: code, tests, docs, `.ai`,
  evidence, governance, config, assets, or indexes as applicable.
- Before creating or renaming files, check the nearest directory `README.md`
  or naming guidance plus `governance/standards/naming.md`.
- Before any commit or push, read
  `governance/standards/git_commit_style.md` and apply that commit-message
  style automatically. Do not rely on private or old-workspace memory for
  commit policy.

## Task Router

Use `.ai/entrypoint.md` to choose the correct read set and completion checklist
for simulation runs, feature work, documentation changes, campaign work,
configuration changes, evidence work, and compatibility retirement.

## Minimum Completion Rule

Run the checks required by `.ai/entrypoint.md`. For any structure, docs,
governance, evidence, runtime-path, or local-overlay-policy change, run:

```bash
make doctor
```

If a required check cannot run, record the blocker in the final report and do
not imply that the check passed.
