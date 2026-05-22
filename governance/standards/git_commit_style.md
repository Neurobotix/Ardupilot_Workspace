# Git Commit Style Standard

This standard is the canonical commit-message policy for
`ardupilot_workspace_next`. It is team/workspace policy, not private agent
memory.

Before making any commit, and before pushing any branch that includes new
commits, read this file and apply it automatically. Do not ask the user to
repeat the style.

## Subject Format

Use one exact prefix, a colon, a space, and a concise lowercase description:

```text
<Prefix>: <description>
```

Keep the subject descriptive and short enough to scan in history. Prefer the
component or file name when it makes the change clearer.

Examples:

```text
Add: fixed-harness CTE comparator evidence
Update: matrix runners parameter stack controls
Fixed: Gazebo world path resolution
Docs: agent commit workflow
Config: copter rangefinder parameters
```

## Canonical Prefixes

| Prefix | Use when |
| --- | --- |
| `Finished:` | A complete feature, phase, or major work item is finished. |
| `Fixed:` | A bug, incorrect behavior, broken path, or bad claim is corrected. |
| `Add:` | A new file, feature, test, report, asset, or capability is added. |
| `Update:` | Existing code, docs, governance, evidence, or config is changed. |
| `Remove:` | Files, features, compatibility paths, or stale records are removed. |
| `Refactor:` | Structure changes without intended behavior change. |
| `Test Results(<component>):` | A commit records test outcome evidence. |
| `Docs:` | Documentation-only or mostly documentation changes. |
| `Config:` | Shared configuration, parameters, or asset metadata changes. |
| `Merge:` | A merge commit. |
| `Revert:` | A revert commit. |

The legacy private guide mixed `Added:`, `Updated:`, and `Refactored:` in a
table with `Add:`, `Update:`, and `Refactor:` in examples. This workspace uses
the shorter exact prefixes above because they match the examples and are easier
to enforce mechanically. Do not use the past-tense variants for new commits.

## Body Format

Use a body when the subject cannot carry the important context. A body is useful
for multi-area changes, evidence provenance, test details, or limitations.

```text
Update: agent commit and push workflow

- Added canonical commit-style governance.
- Routed commit and push requests through the agent entrypoint.
- Recorded make doctor validation in dated evidence.
```

## Commit Workflow

Before committing:

1. Read `AGENTS.md`, `.ai/entrypoint.md`, and this standard.
2. Check `git status --short`.
3. Stage only files that belong to the requested change.
4. Inspect `git diff --staged`.
5. Choose one canonical prefix from this standard.
6. Commit with a valid subject and a body when useful.

Before pushing:

1. Re-read this standard if the branch contains new local commits.
2. Check branch and status.
3. Confirm the staged/committed scope excludes unrelated workspace changes.
4. Run required checks or record blockers honestly.
5. Push only when the user has authorized pushing.

## Anti-Patterns

Do not use vague or throwaway subjects:

```text
update
fix
changes
misc
wip
stuff
final version
working now
```

Do not commit broad untracked workspace contents just because they exist. In
this bootstrap workspace, the root repository may have many untracked files; a
commit must still be scoped to the user's requested change.
