# Phase 1 Structure Hardening

Date/time: 2026-05-20T13:53:15+03:00

Timezone: Africa/Cairo

## Scope

Phase 1 makes `/home/ahmed/ardupilot_workspace_next` structure rules
enforceable before runtime parity or deeper migration work. This report covers
top-level homes, structure validation, symlinks, raw log leakage, nested private
state, `.private/` policy, gitignore coverage, stale canonical references, and
required migration-plan links.

This report was revised after audit feedback found that the initial
stale-reference and migration-link gates were too narrow. The current evidence
uses the strengthened validator with blocklists, exact file/label/text
allowlist entries, printed allowlist reasons, and entry-point reference checks.

No edits were made to `/home/ahmed/ardupilot_workspace`.

## Files Changed

- `README.md`
- `.ai/current.md`
- `.ai/index.md`
- `.ai/issues/open.md`
- `docs/architecture/workspace_map.md`
- `docs/onboarding/quick_start.md`
- `docs/operations/launch_targets.md`
- `docs/operations/migration_status.md`
- `governance/runbooks/phase_1_structure_hardening.md`
- `governance/runbooks/phase_3_documentation_rebuild.md`
- `governance/standards/change_control.md`
- `scripts/maintenance/README.md`
- `scripts/maintenance/validate_structure.sh`
- `scripts/ops/doctor.sh`
- `evidence/reports/PHASE_1_STRUCTURE_2026-05-20.md`

## Commands Run

- `scripts/maintenance/validate_structure.sh`
- `make doctor`
- `find -L . -type l -print`
- `find . -type f \( -iname '*.bin' -o -name '*.tlog' -o -name '*.tlog.raw' \) -print | sort`
- `find config -path '*/.private' -print -o -path '*/.private/*' -print | sort`
- `find assets config docs evidence governance scripts src tests .ai -path '*/.private' -print -o -path '*/.private/*' -print | sort`
- `find .private -type f -print | sort`
- `find .private -type f \( -perm -111 -o -name '*.sh' -o -name '*.py' -o -name '*.pl' -o -name '*.rb' -o -name '*.js' -o -name '*.ts' -o -name 'Makefile' \) -print | sort`
- `git check-ignore -v .private/config/plane_params.local.parm var/logs/example.BIN var/runs/example.tlog`
- strengthened stale-reference blocklist and allowlist scan inside
  `scripts/maintenance/validate_structure.sh`
- strengthened migration-plan target and entry-point reference scan inside
  `scripts/maintenance/validate_structure.sh`

## `make doctor` Result

Result: PASS.

Summary output:

```text
PASS: all required top-level homes exist
PASS: no broken symlinks
PASS: no raw .BIN/.bin/.tlog/.tlog.raw files outside allowed ignored/runtime areas
PASS: no nested .private directories under active homes
PASS: .private contains only allowed local pointer notes and no runnable logic
PASS: required runtime, private, and external dependency paths are ignored
PASS: no disallowed stale canonical references in non-archive docs/governance/AI
PASS: required migration-plan targets and entry-point references exist
STRUCTURE VALIDATION PASSED
```

## Structure Validator Result

Result: PASS.

`scripts/maintenance/validate_structure.sh` produced the same pass summary as
`make doctor`, because `scripts/ops/doctor.sh` now delegates to the maintenance
validator.

## Broken Symlink Check Result

Command: `find -L . -type l -print`

Result: PASS. No output; no broken symlinks found.

## Raw Log Leakage Check Result

Command: `find . -type f \( -iname '*.bin' -o -name '*.tlog' -o -name '*.tlog.raw' \) -print | sort`

Result: PASS. No output; no raw `.BIN`, `.bin`, `.tlog`, or `.tlog.raw` files
were found in the workspace.

## Nested `.private` Check Result

Command: `find assets config docs evidence governance scripts src tests .ai -path '*/.private' -print -o -path '*/.private/*' -print | sort`

Result: PASS. No output; no nested `.private` directories or files exist under
active homes.

The required active `config/` scan also passed with no output:

```text
find config -path '*/.private' -print -o -path '*/.private/*' -print | sort
```

## `.private` Policy Check Result

Result: PASS.

Observed local-only files:

```text
.private/README.md
.private/backups/backup.log
.private/config/plane_params.local.parm
.private/notes/local_notes.md
.private/notes/root_local_notes_legacy.md
```

Runnable-logic scan result: no output.

Policy assertions passed:

- no `.private/docs`,
- no `.private/scripts`,
- Markdown only in `.private/README.md` and `.private/notes/*.md`,
- no duplicate canonical headings,
- no command-like procedures in private notes,
- canonical-home links in private notes are marked as pointers,
- no canonical runnable logic.

## Gitignore Check Result

Result: PASS.

```text
.gitignore:12:.private/ .private/config/plane_params.local.parm
.gitignore:2:var/       var/logs/example.BIN
.gitignore:2:var/       var/runs/example.tlog
```

The validator also confirmed ignore coverage for `var/cache/`,
`src/ardupilot/`, and `src/SITL_Models/`.

## Stale Canonical Reference Scan Result

The strengthened validator scans canonical README/docs/governance/AI pointers,
excluding archives and audits, for:

- old absolute production workspace paths,
- legacy `src/SIM_ARD_GAW` references,
- old log homes,
- retired scripts and worlds,
- retired launch targets,
- deprecated production-status claims,
- obsolete parameter claims.

Result: PASS. No disallowed stale references were found.

Allowed exceptions reported by the validator with reason and matched text:

```text
.ai/current.md:33: old absolute production workspace path: records the Phase 0 production reference: - Production reference remains `/home/ahmed/ardupilot_workspace`.
.ai/issues/open.md:18: legacy compatibility path: tracks the named compatibility blocker: - Legacy compatibility path `src/SIM_ARD_GAW` still required by migrated scripts.
.ai/issues/open.md:19: retired launch target: tracks retired launch-target follow-up: - `wind-check-altitude` retired until a real validator is implemented.
.ai/issues/open.md:8: legacy compatibility path: records a Phase 0 production dirty-state blocker: - Production nested `src/SIM_ARD_GAW` is dirty with 115 status entries.
README.md:17: old absolute production workspace path: documents the read-only production reference: Production source: `/home/ahmed/ardupilot_workspace`.
README.md:36: deprecated production claim: explicitly says this workspace is not production: Do not treat this workspace as production until the shadow parity checklist in
docs/architecture/workspace_map.md:25: legacy compatibility path: documents the temporary compatibility bridge: `src/SIM_ARD_GAW/` is a temporary compatibility path made of symlinks for
docs/onboarding/quick_start.md:18: old absolute production workspace path: documents the temporary production virtualenv fallback: `/home/ahmed/ardupilot_workspace/env/bin/python3`.
docs/operations/launch_targets.md:11: retired launch target: documents retired target status: - `wind-check-altitude` is retired in this workspace because production
governance/runbooks/full_migration_plan.md:32: legacy compatibility path: defines the compatibility retirement exit gate: | 8 | Compatibility Retirement | Remove legacy compatibility paths safely | No runtime depends on `src/SIM_ARD_GAW` |
governance/runbooks/full_migration_plan.md:4: old absolute production workspace path: states the migration deprecation target: and make `/home/ahmed/ardupilot_workspace` a deprecated reference/archive.
governance/runbooks/phase_2_runtime_parity.md:9: retired launch target: Phase 2 parity task for retired target: - Verify `wind-check-altitude` is intentionally retired and documented.
governance/runbooks/phase_8_compatibility_retirement.md:26: legacy compatibility path: Phase 8 exit gate: - no runtime code depends on `src/SIM_ARD_GAW`,
governance/runbooks/phase_8_compatibility_retirement.md:7: legacy compatibility path: Phase 8 removal task: - Replace `src/SIM_ARD_GAW` symlink compatibility with direct new-path usage.
governance/standards/change_control.md:39: deprecated production claim: evidence rule preventing unsupported readiness claims: Do not write `WORKING`, `VERIFIED`, or `READY FOR CUTOVER` without a dated
```

Historical audit and archive paths are intentionally excluded from the canonical
scan.

## Migration-Plan Link Check Result

Result: PASS.

Required migration-plan targets exist:

- `governance/runbooks/full_migration_plan.md`
- `governance/standards/change_control.md`
- `docs/operations/migration_status.md`

Required entry-point references passed:

```text
README.md -> governance/runbooks/full_migration_plan.md
README.md -> governance/standards/change_control.md
README.md -> docs/operations/migration_status.md
.ai/index.md -> governance/runbooks/full_migration_plan.md
.ai/index.md -> governance/standards/change_control.md
.ai/index.md -> docs/operations/migration_status.md
.ai/current.md -> governance/runbooks/full_migration_plan.md
.ai/current.md -> governance/standards/change_control.md
.ai/current.md -> docs/operations/migration_status.md
docs/onboarding/quick_start.md -> governance/runbooks/full_migration_plan.md
docs/onboarding/quick_start.md -> governance/standards/change_control.md
docs/onboarding/quick_start.md -> docs/operations/migration_status.md
docs/operations/migration_status.md -> governance/runbooks/full_migration_plan.md
docs/operations/migration_status.md -> governance/standards/change_control.md
docs/operations/migration_status.md -> docs/operations/migration_status.md
```

## Unresolved Blockers

No Phase 1 structure-hardening blockers remain.

Existing non-Phase-1 migration blockers remain tracked in `.ai/issues/open.md`,
including runtime parity, external dependency setup, campaign hardening, and
cutover/deprecation work.

## Conclusion

PASS. Phase 1 Structure Hardening is complete. The workspace now has an
enforceable structure validator, `make doctor` passes, and every Phase 1 exit
gate item is proven by this report.
