# Git Commit Style Adoption - 2026-05-24

Status: governance/docs update.

## Scope

Adopted the legacy commit-message guidance into canonical, team-visible
workspace governance so future agents route commit and push requests through the
same standard automatically.

## Source Reviewed

- Legacy read-only source:
  `/home/ahmed/ardupilot_workspace/.private/GIT_COMMIT_STYLE.md`

The old source was inspected but not copied blindly. The new standard removes
personal attribution, old-workspace-specific push examples, milestone tag
guidance, and private-memory framing.

## Files Changed

- `AGENTS.md`
- `.ai/entrypoint.md`
- `.ai/index.md`
- `governance/standards/change_control.md`
- `governance/standards/git_commit_style.md`
- `evidence/reports/GIT_COMMIT_STYLE_ADOPTION_2026-05-24.md`

## Normalization

The legacy guide mixed table prefixes such as `Added:`, `Updated:`, and
`Refactored:` with examples such as `Add:`, `Update:`, and `Refactor:`. The new
canonical standard chooses the shorter exact prefixes because they match the
examples and are easy for agents to enforce.

Canonical examples:

```text
Add: fixed-harness CTE comparator evidence
Update: matrix runners parameter stack controls
Fixed: Gazebo world path resolution
Docs: agent commit workflow
```

## Agent Routing Result

- `AGENTS.md` now tells agents to read the commit style before any commit or
  push.
- `.ai/entrypoint.md` now has a `Commit Or Push` workflow.
- `.ai/index.md` links the standard.
- `governance/standards/change_control.md` makes commit style and push
  authorization part of completion discipline.

## Checks

- `make doctor` on 2026-05-24: PASS

## Dry-Run Push Workflow Test

Pretend request: "push this."

Routing check:

- `AGENTS.md` points commit and push requests to
  `governance/standards/git_commit_style.md`.
- `.ai/entrypoint.md` has a `Commit Or Push` workflow that reads the commit
  style standard.
- `governance/standards/change_control.md` makes the standard part of commit
  and push discipline.

Git state observed:

- Current branch: `main`
- `git rev-parse --verify HEAD`: blocked with `fatal: Needed a single
  revision`; this root workspace still has no initial commit.
- `git diff --cached --name-only`: no staged files.
- `git status --short`: broad top-level untracked workspace contents are
  present, including `.ai/`, `AGENTS.md`, `docs/`, `evidence/`, `governance/`,
  `src/`, and `tests/`.

Dry-run result:

- Prefix that would be used for this adoption work: `Add:`
- Valid commit subject: `Add: canonical git commit style standard`
- Current tree safety: not safe for a broad automatic commit because there are
  no staged files and the bootstrap repository shows many unrelated top-level
  untracked homes.
- Push status: blocked pending explicit user push authorization and staging
  decisions.

## Workspace Boundary

The old production/reference workspace was read for the legacy style only and
was not modified.
