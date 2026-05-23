# Phase 0: Foundation Freeze

Purpose: establish the old workspace as read-only production reference and
record the exact baseline that `workspace_next` must match.

## Status

Completed on 2026-05-20.

Evidence: `evidence/reports/migration/PHASE_0_BASELINE_2026-05-20.md`

## Tasks

- [x] Record current git status for old and new workspaces.
- [x] Record commit IDs for root workspace, nested `src/ardupilot`, and plugin source.
- [x] Record `UNKNOWN` for any expected commit, dependency, or value that cannot be
  discovered, including the command or reason.
- [x] Record current directory sizes for logs, assets, dependencies, and configs.
- [x] Record external dependency presence or absence in both workspaces.
- [x] Confirm raw logs are not copied into `workspace_next`.
- [x] Confirm migration inventory exists and is reviewable.
- [x] Run basic structural checks in `workspace_next`:
  - `make doctor`
  - broken symlink scan
  - raw `.BIN`, `.tlog`, and `.tlog.raw` scan outside ignored runtime and
    external dependency areas
  - active `config/` nested `.private` scan
  - `.private/` policy check, including content review for hidden operational
    truth
- [x] Re-check old workspace git status after Phase 0 work and compare it to the
  initial observed status before claiming production was not modified.
- [x] Record exact nested production dirty-state output or hashes, not only
  status counts.
- [x] Create a baseline evidence report under `evidence/reports/`.

## Required Updates

- `src/external/DEPENDENCIES.md`: dependency pins or explicit unknowns.
- `governance/audits/migration_inventory.csv`: regenerate if inventory changes.
- `.ai/current.md`: mark baseline complete when done.
- `.ai/issues/open.md`: add any baseline blockers.
- `docs/operations/migration_status.md`: link the baseline report when Phase 0
  status changes.

## Exit Gate

Create `evidence/reports/migration/PHASE_0_BASELINE_<date>.md` with:

- date/time and timezone,
- scope,
- commands run,
- old workspace git status,
- new workspace git status,
- root commit IDs,
- dependency commits,
- important directory sizes,
- inventory count,
- raw log migration status,
- `.private` status,
- known dirty/private state,
- risks/blockers,
- pass/fail conclusion,
- and explicit statement that production was not modified.
