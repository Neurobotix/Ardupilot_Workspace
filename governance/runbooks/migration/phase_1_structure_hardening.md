# Phase 1: Structure Hardening

Purpose: make the new workspace rules enforceable before deeper migration work.

Phase 1 does not prove SITL/Gazebo runtime parity. It hardens the workspace
boundary so later migration work cannot silently recreate legacy path sprawl,
private source-of-truth drift, or raw log leakage.

## Tasks

- Expand `scripts/ops/doctor.sh` to validate all required top-level homes:
  `README.md`, `setup.bash`, `governance/`, `docs/`, `.ai/`, `src/`,
  `assets/`, `config/`, `tests/`, `evidence/`, `scripts/`, `var/`, and
  `.private/`.
- Add `scripts/maintenance/validate_structure.sh` as the reusable path and
  reference validator, and have `scripts/ops/doctor.sh` call it.
- Add checks for broken symlinks, raw log leakage, nested `.private`, private
  policy violations, stale canonical refs, gitignore rules, and required
  migration-plan links.
- Confirm `.gitignore` blocks raw logs, runtime output, caches, local overlays, and external dependencies.
- Confirm `.private/` contains no canonical docs or runnable logic.
- Confirm `var/` is disposable and ignored.

## Required Checks

`scripts/maintenance/validate_structure.sh` must fail on:

- missing top-level homes,
- broken symlinks,
- raw `.BIN`, `.bin`, `.tlog`, or `.tlog.raw` files outside ignored/runtime
  areas,
- nested `.private` directories under active tracked homes,
- `.private/docs` or `.private/scripts`,
- private Markdown files outside `.private/README.md` and
  `.private/notes/*.md`,
- private notes that contain command-like procedures, duplicate canonical
  headings, or canonical-home links without pointer wording,
- runnable source or executable logic under `.private/`,
- disallowed stale canonical references in non-archive docs, governance, or AI
  pointers, using a blocklist plus exact file/label/text allowlist entries,
- missing migration-plan link targets or missing required entry-point
  references,
- missing gitignore coverage for `.private/`, `var/logs/*.BIN`, and
  `var/runs/*.tlog`.

## Required Updates

- `governance/standards/change_control.md`: update if any new rule appears.
- `docs/onboarding/quick_start.md`: add any required setup command.
- `docs/architecture/workspace_map.md`: update if structure changes.
- `.ai/index.md`: link new validation scripts if created.
- `evidence/reports/`: record validation output.

## Exit Gate

Create `evidence/reports/migration/PHASE_1_STRUCTURE_<date>.md` showing:

- doctor check passed,
- broken symlink check passed,
- raw log scan passed,
- nested `.private` scan passed,
- `.private` policy check passed,
- gitignore checks passed,
- stale canonical reference scan passed,
- migration-plan link check passed,
- stale-reference allowlist exceptions are reported separately with matched
  text and reason,
- unresolved blockers are explicitly listed,
- final conclusion is pass or fail.

Phase 1 may be marked passed only when the evidence report proves every item in
this exit gate.
