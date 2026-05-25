# Feature Runbook: test_suite Migration — Review

Status as of 2026-05-25: **Phase 3 (staged attempt runner) implemented as
an opt-in path; legacy delegate remains the default.**

## Phase 3 acceptance review

| Criterion | Result | Evidence |
| --- | --- | --- |
| Legacy delegate remains default | PASS | `WindMatrixConfig.attempt_strategy = "legacy"` |
| Staged strategy can be built | PASS | `test_wind_plugin_can_build_staged_strategy_without_compat_wrappers` |
| Legacy delegate path remains available | PASS | `test_legacy_delegate_path_remains_available` |
| Stage order is explicit | PASS | `test_staged_strategy_calls_stages_in_expected_order` |
| Cleanup on success/failure/interrupt | PASS | Phase 3 focused cleanup tests |
| BIN finalization ordering matches legacy | PASS | `test_square_loiter_early_cleanup_and_flush_happen_before_bin_collection` |
| Analyzer failure writes legacy-compatible row | PASS | `test_collect_bin_failure_persists_legacy_compatible_error_row` |
| Pre-analyzer staged failures write legacy-compatible rows | PASS | `test_staged_stimulus_failure_persists_legacy_error_row_and_cleans_up`; `test_staged_control_and_monitor_failures_persist_legacy_error_rows` |
| Unsupported staged after-takeoff rejected before launch | PASS | `test_staged_after_takeoff_rejected_before_environment_launch` |
| Partial verdict remains partial | PASS | `test_partial_verdict_stays_partial` |
| Failed/error/interrupted not accepted | PASS | `test_failed_error_interrupted_do_not_count_as_accepted` |
| Generic manifest fields additive | PASS | Phase 2 tests plus `test_plugin_manifest_fields_are_additive_for_new_staged_rows` |
| Legacy manifest fields round-trip unchanged | PASS | `test_legacy_manifest_fields_round_trip_unchanged` |
| No Phase 4 / Phase 5 work | PASS | No second plugin; wrappers retained; `run_one.py` remains callable |

## Residual risk after Phase 3

- Staged mode is not the campaign default and is not live-runtime parity
  evidence. The proven default path remains the legacy delegate.
- Staged `auto_wind_phase=after-takeoff` is intentionally blocked because
  the generic stage order applies stimulus before control while the legacy
  after-takeoff path applies wind after AUTO takeoff altitude.
- The staged analyzer delegates to legacy analysis helpers; this reduces drift
  but means the heavy analysis path is still proven by unit shape and existing
  legacy evidence, not by a new live staged campaign.

## Phase 2 acceptance review

| Criterion | Result | Evidence |
| --- | --- | --- |
| Generic manifest view exists | PASS | `Manifest.generic_view()` in `core/manifest.py` |
| Legacy manifest view remains available | PASS | `Manifest.legacy_view()` returns `load()` without normalization |
| Generic fields are additive | PASS | `LegacyManifest.append_attempt()` updates only generic fields on the matching row |
| Additive append uses campaign manifest lock | PASS | `test_append_attempt_observes_campaign_manifest_lock` |
| Generic `finished_at` preserves legacy end time | PASS | `test_attempt_runner_preserves_legacy_end_time_for_generic_finished_at` |
| Old legacy manifests are readable | PASS | `tests/unit/test_test_suite_manifest_generic_view.py::test_old_legacy_wind_manifest_gets_generic_view_without_mutation` |
| Legacy wind fields round-trip unchanged | PASS | `test_append_attempt_writes_generic_fields_without_overwriting_legacy` |
| Wind-matrix attempt rows expose generic fields | PASS | `test_wind_matrix_attempt_record_exposes_generic_fields` |
| `success_square_only` remains partial | PASS | `test_square_only_generic_verdict_stays_partial_not_success` |
| Missing optional generic fields tolerated | PASS | `test_missing_optional_generic_fields_are_tolerated` |
| No `run_one.py` split, wrapper retirement, or second plugin | PASS | self-review recorded in `evidence/reports/features/2026-05-25_test_suite_migration_phase_2.md` |

Phase 2 schema marker: `test_suite.generic_manifest.v1`.

Post-review remediation on 2026-05-25 fixed two findings: the additive
append transaction is now wrapped in `campaign_manifest_lock()`, and
`AttemptRunner.run()` preserves a strategy-provided `end_time_utc` instead
of overwriting it before generic manifest persistence.

## Residual risk after Phase 2

- Direct legacy `run_one.py` / `run_matrix.py` invocations still write the
  legacy manifest shape only. This is intentional compatibility behavior;
  old rows are normalized through the reader, while `test_suite` framework
  attempts add generic fields after the delegated legacy body returns.
- The generic model is still exercised against wind_matrix only. A second
  plugin proof remains Phase 4.

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

The next planned step is Phase 4 (second plugin proof of generality).
Before any staged-mode runtime cutover claim, run a live SITL/Gazebo
single-attempt diff between `python -m test_suite.cli.run_case ...` and
the retained legacy `run_one.py` path.
