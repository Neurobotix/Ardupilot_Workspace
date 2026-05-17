# Workspace Cutover Rollback

Use this runbook after a governed production promotion if
`workspace_next` cannot safely support the run that was cut over. A blocked
Phase 7 decision does not activate rollback; it keeps the old workspace as the
production reference.

Phase 7 passed on 2026-05-24 under
`governance/decisions/ADR-0005-workspace-next-cutover.md`. After that decision,
`/home/ahmed/ardupilot_workspace` is deprecated fallback/reference, not active
production. It may be used for governed rollback or historical comparison and
must not be edited without explicit operator authorization.

## When To Fall Back

Fall back to the old workspace when a promoted production run shows a safety,
runtime, evidence, or operator-doc failure that:

- breaks a launch or campaign workflow required by the cutover ADR;
- changes outputs or parameter/plugin provenance outside the accepted risks;
- writes raw runtime output outside the documented homes;
- shows governed clean-run cleanup was bypassed or another simulator session
  was unintentionally exposed to a production run;
- makes operators unable to reproduce the promoted entrypoint from the cutover
  docs.

Do not improvise compatibility retirement during rollback. Phase 8 still owns
compatibility-path removal.

## Recognize Cutover Failure

Treat these as rollback signals:

- `make doctor`, `make test-parity`, or the cutover ADR validation set fails
  after promotion;
- final shadow-parity workflows no longer reproduce the dated cutover evidence;
- a vehicle or campaign status doc makes a production claim the run cannot
  reproduce;
- required runtime output or curated evidence cannot be located through the
  report/catalog path;
- a production run needs an undocumented local overlay, installed-plugin
  fallback, or manual cleanup action outside the accepted risks.

## Capture Before Rollback

Before switching the operator back to the old workspace, capture:

1. date/time and timezone;
2. failing command path, environment setup, parameters/config/assets, plugin
   path selection, and relevant hashes;
3. raw output paths under `var/` or retained archive locations;
4. the failing console summary, process state, and cleanup result;
5. the cutover ADR/report references that the failure contradicts;
6. whether the old workspace was read only or a fallback run was started.

Record the failure in a dated report or governance audit before updating the
status docs when practical. Do not promote raw runtime trees blindly.

## Fallback Steps

1. Stop the failing `workspace_next` run without editing the old workspace.
2. Preserve the proof above and mark the production claim as under rollback
   review in `.ai/current.md` and `docs/operations/migration_status.md`.
3. Use the old workspace only for the bounded production fallback run needed to
   restore service.
4. Keep `workspace_next` evidence and runtime output in their governed homes so
   the cutover failure can be diagnosed.
5. Reopen or update `.ai/issues/open.md` with the blocker and remediation owner.

## Status After Rollback

After fallback, update:

- the cutover ADR status or a superseding decision record;
- the cutover evidence report or a new rollback report;
- `docs/operations/migration_status.md`;
- `.ai/current.md` and `.ai/issues/open.md`;
- any README, onboarding, launch-target, vehicle, or campaign status page that
  named the rolled-back production truth.

The old workspace remains reference/fallback material until a later explicit
retirement decision says otherwise.
