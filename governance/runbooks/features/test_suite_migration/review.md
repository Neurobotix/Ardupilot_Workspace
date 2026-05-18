# Feature Runbook: test_suite Migration — Review

Status as of 2026-05-24: **Phase 1 (wrapper parity) — accepted after
remediation pass.**

## Phase 1 remediation (2026-05-24, post-review)

Initial Phase 1 was marked PASS but a follow-up review flagged four
issues. All were addressed:

| Severity | Issue | Resolution |
| --- | --- | --- |
| High | `LegacyManifest.accepted_count` delegated to `run_one.combo_successes`, which counts `success_square_only` regardless of caller policy. A historical square-only row could silently satisfy acceptance for a new strict full-mission run. | `LegacyManifest` is now policy-aware via an `accept_square_only` constructor argument (default `False`). The `wind_matrix` plugin forwards `WindMatrixConfig.accept_square_only`. Two new parity tests prove both branches. |
| Low | Stale `scripts/test_suite/tests/test_phase1_parity.py` path in `ARCHITECTURE.md`. | Updated to the canonical `tests/parity/test_phase1_parity.py`. |
| Low | `cli/run_suite.py` docstring claimed "behaviorally equivalent" to legacy `run_matrix.py`, overstating Phase 1 evidence. | Reworded to "mirrors the flag surface" and "delegates through the legacy `run_one.run_one(...)` call path", and explicitly notes that live SITL/Gazebo parity is still required. The same softening was applied to `cli/run_round_robin.py`. |
| Low | (Same wording check) `cli/run_round_robin.py` docstring. | Reworded as above. |

All eight parity tests, twenty unit tests, three integration tests,
`make test-parity`, and `make doctor` pass after the remediation.

## Phase 1 acceptance review

| Criterion | Result | Evidence |
| --- | --- | --- |
| Feature runbook bundle exists | PASS | this directory |
| Phase 1 scope documented and bounded | PASS | `plan.md`, `phase_1_wrapper_parity.md` |
| Wrapper-only `compat_scripts/` | PASS | inspection (see `phase_1_wrapper_parity.md`) |
| `test_suite.core._legacy` resolves owned runners | PASS | `_legacy.py` imports `sim_ard_gaw.campaigns.wind_matrix.*` |
| Three CLI module paths plus three legacy scripts produce help | PASS | manual invocations recorded in evidence report |
| Parity tests pass | PASS | `make test-parity` (6 tests) |
| Unit / integration tests pass | PASS | `unittest discover` |
| `make doctor` passes | PASS | structure + evidence validators |
| Disposable build artifacts removed and ignored | PASS | `__pycache__` removed; `.gitignore` covers both |
| Evidence report dated | PASS | `evidence/reports/features/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md` |
| Old workspace untouched | PASS | no edits to the deprecated fallback/reference workspace named in ADR-0005 |

## Residual risk after Phase 1

- Live SITL/Gazebo single-attempt parity is not re-proven at this
  phase. The wrapper-delegate property keeps the legacy body in the
  call path, so structural equivalence to the legacy run is implied
  but not empirically diffed at runtime. A diff between a fresh
  `python -m test_suite.cli.run_case` attempt and a fresh
  `compat_scripts/run_one.py` attempt is still useful before Phase 3
  starts changing the strategy body. That is out of scope for Phase 1
  and is recorded as a follow-up for the Phase 3 entry gate.
- The Phase-1 plugin registry hard-codes `wind_matrix`. A non-Phase-1
  plugin cannot be selected via `--plugin`. This is the expected
  Phase-1 state; the registry redesign is part of Phase 4.

## Rollback notes

Phase 1 only added documentation and removed disposable build
artifacts. There is nothing to roll back at the runtime layer. If the
feature runbook or evidence report needs to be retracted, the affected
files are:

- `governance/runbooks/features/test_suite_migration/plan.md`
- `governance/runbooks/features/test_suite_migration/phase_1_wrapper_parity.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `evidence/reports/features/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md`
- `.ai/index.md` (pointer line)

Removing the runbook does not affect runtime behavior or the existing
governance Phase 5 / Phase 8 evidence.

## Successor

The next planned step is Phase 2 (generic manifest / data model). It
has not started. When it starts, create
`phase_2_generic_data_model.md` in this directory and link it from
`plan.md`.
