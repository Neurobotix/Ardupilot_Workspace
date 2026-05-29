# test_suite Migration Plan Correction

Date/time: 2026-05-29T15:35:33+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature planning/governance correction

Conclusion: PASS

Feature runbook:
`governance/runbooks/features/test_suite_migration/`

## Why the correction was needed

The old plan let Phase 4 become "second plugin proof" immediately after the
2026-05-25 staged attempt runner work. That was logically premature.

Phase 3 was accepted as an opt-in staged path behind the legacy fallback, with
static/unit/integration/CLI evidence and no live staged wind proof. The default
runtime path still delegates to wind-specific legacy code, and staged wind
still reuses wind-specific legacy helpers. Because the legacy path is
wind-specific, `test_suite` cannot claim generic framework readiness until
`wind_matrix` is proven as a real staged first plugin.

A second plugin before that proof would be architecture theater. It would show
that a second plugin can be added, not that the framework boundary is generic.

## Files changed

- `governance/runbooks/features/test_suite_migration/plan.md`
- `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- `evidence/indexes/evidence_catalog.md`
- this report

## Old flawed phase logic

- Phase 1: wrapper parity around legacy wind runners.
- Phase 2: additive generic manifest/data model.
- Phase 3: staged attempt runner.
- Phase 4: second plugin proof.
- Phase 5: retire legacy scripts after two plugins are stable.

The flaw was the jump from Phase 3 to Phase 4. The accepted Phase 3 evidence
did not prove the first plugin had escaped wind-specific legacy delegation.

## Corrected phase logic

- Phase 1: wrapper parity around legacy wind runners.
- Phase 2: additive generic manifest/data model.
- Phase 3A: split wind-specific logic out of `run_one.py` into opt-in
  staged plugin/core pieces while retaining the legacy fallback.
- Phase 3B: prove `wind_matrix` is complete enough to be a real first plugin,
  not just a wrapper around wind-specific legacy delegation.
- Phase 4: second plugin proof, only after Phase 3B is accepted.
- Phase 5: retire legacy wind-specific scripts/wrappers only after Phase 4
  proves generality and replacement paths are evidence-backed.

## Phase 3B gate

Phase 3B requires:

- stage-order tests;
- cleanup tests;
- verdict/acceptance tests;
- manifest compatibility tests;
- CLI tests;
- at least one bounded live staged wind case, or a dated blocker explaining
  why live proof is not yet available;
- review that retained legacy helper calls are isolated behind plugin-owned
  staged boundaries and do not conceal lifecycle delegation through
  `run_one.run_one(...)`.

## Phase 4 blocked-until condition

Do not start Phase 4 until Phase 3B is accepted.

Phase 4 begins only after `wind_matrix` no longer depends on wind-specific
legacy delegation for its attempt lifecycle, or after any retained legacy
pieces are explicitly isolated and evidence-backed. A second plugin proves
nothing if the first plugin is still secretly a wind-specific legacy wrapper.

## Runtime implementation statement

No runtime implementation was changed. No `test_suite` code was refactored. No
second plugin was added. No legacy wrapper was retired.

## Old workspace statement

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.

## Commands run

- `date --iso-8601=seconds`
- `rg "Phase 3B|architecture theater|second plugin|legacy.*wind|wind-specific|generic" governance/runbooks/features/test_suite_migration src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md .ai evidence/indexes/evidence_catalog.md`
- `git diff --check`
- `make doctor`

## Test results

| Command | Result |
| --- | --- |
| `rg "Phase 3B|architecture theater|second plugin|legacy.*wind|wind-specific|generic" governance/runbooks/features/test_suite_migration src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md .ai evidence/indexes/evidence_catalog.md` | PASS |
| `git diff --check` | PASS |
| `make doctor` | PASS |

## Residual risk

- Phase 3B evidence is not yet available.
- Phase 4 remains blocked until Phase 3B is accepted.
- Phase 5 remains blocked until Phase 4 is accepted.
