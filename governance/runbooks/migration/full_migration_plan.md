# Full Migration Plan

Goal: promote `ardupilot_workspace_next` to the internal production workspace
and make `/home/ahmed/ardupilot_workspace` a deprecated reference/archive.

This is not only a file migration. Every change must obey the new workspace
rules: correct home, updated references, human docs, agent pointers, evidence,
governance, and tests/runbooks where relevant.

## Operating Principles

- Production source stays read-only until cutover.
- `workspace_next` becomes trusted only through evidence, not optimism.
- Runtime compatibility is allowed, but it must shrink over time.
- Raw simulator output stays in `var/`; curated proof goes to `evidence/`.
- `.private/` never becomes a hidden source of truth.
- `.ai/` points to canonical sources; it does not duplicate them.
- Every phase ends with a dated evidence report.

## Phase Index

| Phase | Name | Purpose | Exit gate |
| --- | --- | --- | --- |
| 0 | Foundation Freeze | Lock source truth and baseline inventory | Baseline report exists |
| 1 | Structure Hardening | Make workspace rules enforceable | Doctor, ignore, path checks pass |
| 2 | Runtime Parity | Prove launches and scripts still behave | Shadow parity smoke passes |
| 3 | Documentation Rebuild | Replace archived docs with trusted docs | Canonical docs have no stale refs |
| 4 | Config/Asset Normalization | Remove hidden config and path ambiguity | Param stacks and assets are indexed |
| 5 | Campaign/Test Migration | Move wind matrix/test suite toward new architecture | Tiny campaign parity passes |
| 6 | Evidence And Operations | Establish report/evidence promotion workflow | Evidence catalog and runbooks used |
| 7 | Cutover And Deprecation | Make `workspace_next` production | Old workspace marked deprecated |
| 8 | Compatibility Retirement | Remove legacy compatibility paths safely | No runtime depends on `src/SIM_ARD_GAW` |

## Global Definition Of Done

Each phase must update:

- `governance/runbooks/migration/phase_*.md` status and checklist.
- `evidence/reports/` with dated validation results.
- `docs/` for human-facing behavior.
- `.ai/current.md` for active state.
- `.ai/issues/open.md` for remaining blockers.
- `governance/decisions/` if a durable choice is made.
- `governance/standards/` if a rule changes.

## Promotion Policy

`ardupilot_workspace_next` may become production only after:

1. `make doctor` passes.
2. `make test-parity` passes.
3. `scripts/ops/launch.sh help` is correct.
4. Core SITL/Gazebo launch smoke passes.
5. LiDAR bridge smoke passes.
6. Wind/CTE single-case parity passes.
7. Tiny matrix parity passes.
8. Evidence/report generation writes to the correct homes.
9. `.private/` is proven non-essential for shared operation except documented local overlays.
10. A cutover decision ADR is accepted.

## Deprecation Policy For Old Workspace

The old workspace becomes deprecated in stages:

1. **Reference**: read-only source of truth for parity comparison.
2. **Fallback**: used only if `workspace_next` fails a production run.
3. **Archive**: no new work starts there.
4. **Retired**: retained only for historical recovery.

No stage change is allowed without an evidence report.
