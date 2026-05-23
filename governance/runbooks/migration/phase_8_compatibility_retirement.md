# Phase 8: Compatibility Retirement

Purpose: remove migration bridges only after their replacements are proven.
Phase 8 is a subsystem-by-subsystem retirement phase, not permission to delete
every bridge at once. Work only in `/home/ahmed/ardupilot_workspace_next`; the
old workspace may be read as historical reference but must not be edited.

## Status Semantics

- `PASS`: every active compatibility surface in scope has a proven replacement,
  required validation passes, and the evidence report states the retired state.
- `PARTIAL PASS WITH RETAINED COMPATIBILITY`: the retired slices pass but one or
  more remaining bridges have named blockers and exit conditions.
- `BLOCKED`: a required replacement, validation result, or governance boundary
  prevents a safe retirement slice from completing.
- `FAIL`: a retirement change breaks behavior or structure validation.

## Pre-Edit Audit

Before runtime edits:

1. Inventory `src/SIM_ARD_GAW/{config,models,worlds,missions,scripts,logs}`,
   `src/sim_ard_gaw/compat_scripts/`, and organized symlink views under
   `src/sim_ard_gaw/{launch,bridges,campaigns,analysis}`.
2. Search code, tests, docs, AI pointers, and governance for old runtime-path
   dependencies: `src/SIM_ARD_GAW`, `SIM_ARD_GAW_DIR`, `compat_scripts`,
   hardcoded old workspace roots, old asset/config/log assumptions, and old
   runner entrypoints.
3. Classify each dependency as `retire now`, `refactor first`, or `retain with
   blocker and exit condition`.
4. Record the audit and the actual retirement order in the Phase 8 evidence
   report or a durable governance audit before claiming removal.

## Retirement Order

Default order:

1. Refactor launch/runtime path discovery to use the workspace root,
   `assets/`, `config/`, `var/`, and `evidence/` homes directly.
2. Move launch, bridge, and analysis implementations out of compatibility
   ownership when their command paths can stay stable.
3. Review campaign and `test_suite` runners one by one. Keep thin wrappers or
   compatibility owners only when replacement ownership is not yet proven.
4. Update imports, tests, docs, AI pointers, governance, and evidence for each
   retired slice.
5. Remove organized symlink views after the real owned files exist.
6. Remove `src/SIM_ARD_GAW` compatibility links only when no runtime code,
   tests, canonical docs, or operator command depends on them.
7. Shrink or remove `compat_scripts/` only after owned replacements and parity
   checks prove there is no competing implementation.

If implementation order changes, the evidence report must explain why.

## Runtime Ownership Rules

- Workspace discovery uses `ARDUPILOT_WORKSPACE` when supplied or robust root
  discovery from the current owned module/script.
- Models, worlds, and missions resolve through `assets/`.
- Shared runtime parameters resolve through `config/vehicles/`,
  `config/overlays/`, and `config/campaigns/`.
- Raw runtime output resolves through `var/`; curated proof lives under
  `evidence/`.
- A retained fallback must be explicit, documented, tracked with an exit
  condition, and covered by evidence. Silent legacy fallback is not allowed.

## Removal Rules

Do not remove a bridge until its users are identified, replacements are
implemented, relevant tests pass, docs are updated, and evidence records the
decision.

`src/SIM_ARD_GAW` may be removed only when:

- runtime code no longer needs its paths;
- tests no longer need its paths;
- canonical docs do not present it as active architecture;
- operator entrypoints remain valid; and
- validation and parity checks pass without it.

`compat_scripts/` may be removed only after its code has real ownership homes,
imports and CLI wrappers no longer require it, and docs/tests/evidence have been
updated. If that gate is not met, reduce it where safe and document what stays.

## Required Updates

- `src/sim_ard_gaw/`: real owned implementations replace retireable symlink
  views and direct old-path constants.
- `tests/`: cover new import paths, launch/path routing, retained wrappers, and
  removed compatibility dependencies.
- `docs/architecture/workspace_map.md`,
  `docs/operations/launch_targets.md`,
  `docs/operations/migration_status.md`, `docs/campaigns/wind_matrix.md`, and
  `README.md`: state final ownership paths and retained compatibility honestly.
- `.ai/index.md`, `.ai/current.md`, and `.ai/issues/open.md`: point at the
  current Phase 8 state and blockers.
- `governance/audits/` or `governance/decisions/` when a finding or durable
  compatibility policy needs a long-lived record.
- `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_<date>.md`: record the audit,
  commands, removals, retained blockers, and conclusion.

## Minimum Validation

- `make doctor`
- `scripts/maintenance/validate_structure.sh`
- `make test-parity`
- relevant unit and integration tests
- relevant CLI help and import checks
- `find -L . -type l -print`
- raw-log leakage scan
- remaining compatibility-reference scan for `src/SIM_ARD_GAW`,
  `SIM_ARD_GAW_DIR`, `compat_scripts`, and hardcoded old workspace roots
- docs/AI/governance consistency scan for compatibility claims

Run bounded runtime smoke only when a retirement slice changes material runtime
behavior and record the result.

## Exit Gate

Re-read this runbook and the Phase 8 evidence report after validation. The
report must include date/time and timezone, prior Phase 7 state, audit results,
retirement order, files changed, commands run, compatibility before/after,
owned code before/after, tests and structure checks, broken-symlink and stale
reference scans, removed and retained surfaces, blockers with exit conditions,
the old-workspace modification statement, whether `src/SIM_ARD_GAW` still
exists, whether `compat_scripts/` still exists, and one conclusion:

- `PASS`
- `FAIL`
- `BLOCKED`
- `PARTIAL PASS WITH RETAINED COMPATIBILITY`

## 2026-05-24 Closure

The implementation-ownership blockers named in the 2026-05-22 partial report
were closed in `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`.
Organized launch, bridge, analysis, wind-matrix, and campaign test-suite homes
are real files/packages. `src/sim_ard_gaw/compat_scripts/` remains only as a
thin wrapper layer for old import and script paths.
