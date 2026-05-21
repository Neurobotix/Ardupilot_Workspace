# Feature Runbooks

This directory holds per-feature runbook bundles. Each feature large enough to
need planning, implementation notes, or a structured review gets its own
dedicated subdirectory here.

## Naming

- Use a stable `<feature_slug>` in lower snake case that names the feature, not
  the date or the assignee.
- Examples: `lidar_obstacle_capture/`, `wind_matrix_full_campaign/`,
  `copter_lidar_return_capture/`.
- Do not start a slug with `phase_`. Migration phase work lives under
  `migration/`, not here.
- Stable feature files use `plan.md`, `implementation.md`, `review.md`, and
  optional `evidence.md`.
- Phased feature files may use `phase_<n>_<short_slug>.md`.
- Date prefixes are not required for stable feature runbook files. Dated
  evidence reports belong under `evidence/reports/`.
- Follow `governance/standards/naming.md` for exceptions and historical files.

## Contents

A feature directory should contain only the files it actually needs. The
common shape is:

```text
features/<feature_slug>/
├── plan.md            # scope, motivation, success criteria, risks
├── implementation.md  # design notes, code routing, test plan
├── review.md          # acceptance review, residuals, rollback notes
└── evidence.md        # optional: link to dated evidence reports for this feature
```

Rules:

1. Create `plan.md` first. A feature directory with no plan is not a real
   runbook bundle; it is a placeholder and should be removed.
2. Add `implementation.md` when the work goes beyond a trivial change.
3. Add `review.md` when the feature is accepted, blocked, or retired. Record
   the decision and link to the dated evidence report under
   `evidence/reports/`.
4. `evidence.md` is optional and is a *pointer* to evidence, not a duplicate of
   it. Raw evidence stays in `evidence/`.
5. ADRs still belong in `governance/decisions/`. Audits still belong in
   `governance/audits/`. Only feature-scoped runbook material lives here.

## When To Create A Feature Directory

Create a `features/<feature_slug>/` directory when at least one of these is
true:

- The work needs a written plan agreed on before implementation.
- The work spans multiple files, multiple commits, or multiple sessions.
- The work has a review gate, residual risk, or rollback path that must be
  recorded.
- A non-trivial follow-up will need the same context months later.

For a one-line bug fix or a routine doc tweak, do not create a feature
directory. Use a focused commit and, if needed, an evidence report under
`evidence/reports/`.

## Lifecycle

- A feature directory stays until the feature is fully accepted or retired and
  the surrounding code, docs, and evidence no longer benefit from its
  context.
- Do not delete a feature directory just because the feature shipped. Move it
  to an archive bundle only when no canonical doc or evidence report still
  points at it.
- A feature that is superseded by a later feature should keep its directory
  and add a note in `review.md` pointing to the successor.
