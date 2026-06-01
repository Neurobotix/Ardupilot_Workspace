# test_suite Migration — Feature Phase 1 (Wrapper Parity)

Date/time: 2026-05-24T17:00:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase governance evidence (no new runtime output)

Conclusion: PASS

Feature runbook: `governance/runbooks/features/test_suite_migration/`

## Scope

This report records the feature-level Phase 1 ("Stage 1 — wrap")
pass for the `test_suite` migration. The goal is to lock the
current wrapper layer down as a baseline, prove that the
compatibility boundary is wrapper-only, prove the CLI surfaces
work, review scheduler/manifest safety, and create the governed
feature-runbook bundle and routing pointers.

Phase 1 explicitly does not:

- modify `run_one.run_one(...)` or split the legacy body;
- retire any compatibility wrapper;
- add a second plugin;
- claim full live SITL/Gazebo runtime parity beyond what governance
  Phase 5 (`evidence/reports/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`)
  and Phase 8 (`evidence/reports/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`)
  already recorded;
- change the manifest schema.

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.

## Files changed in this pass

Created:

- `governance/runbooks/features/test_suite_migration/plan.md`
- `governance/runbooks/features/test_suite_migration/phase_1_wrapper_parity.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `evidence/reports/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md` (this file)

Updated (documentation + routing):

- `.ai/index.md` — added pointers to the feature runbook and this
  evidence report.
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md` — added a
  pointer to the feature runbook, the Stage ↔ feature-phase mapping,
  and corrected the stale validation path to
  `tests/parity/test_phase1_parity.py`.
- `evidence/indexes/evidence_catalog.md` — added the
  `test-suite-migration-phase1-20260524` entry.

Updated (post-review remediation, see "Post-review remediation"
below):

- `src/sim_ard_gaw/campaigns/test_suite/core/manifest.py` —
  `LegacyManifest` is now policy-aware: `accept_square_only=False`
  (default) excludes `success_square_only` rows from acceptance.
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/plugin.py` —
  forwards `WindMatrixConfig.accept_square_only` into the manifest.
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_suite.py` and
  `cli/run_round_robin.py` — module docstrings softened from
  "behaviorally equivalent" to "mirrors the flag surface" /
  "delegates through the legacy ... call path" with an explicit
  reminder that live SITL/Gazebo parity is still required.
- `tests/parity/test_phase1_parity.py` — added two tests covering
  both branches of the new policy.

Cleaned (disposable, never git-tracked, already covered by
`.gitignore`):

- `__pycache__/` directories and `*.pyc` files under
  `src/sim_ard_gaw/campaigns/test_suite/` (all subpackages).

## Inventory summary

See
`governance/runbooks/features/test_suite_migration/phase_1_wrapper_parity.md`
for the full list. High-level:

| Bucket | Items |
| --- | --- |
| Implemented (pre-existing) | core/ framework (12 modules), plugins/wind_matrix/ (4 modules), cli/ (3 entry points + registry), 6 parity tests, 20 unit tests, 3 integration tests, wrapper-only `compat_scripts/test_suite/`, 3 compat script wrappers. |
| Missing — intentionally deferred | Phase 2 generic manifest fields; Phase 3 real `StagedStrategy` adapters; Phase 4 second plugin and plugin-registry redesign; Phase 5 deletion of legacy `run_one.py` etc.; live single-attempt diff against legacy `run_one.py`. |
| Intentionally deferred housekeeping | Empty `src/sim_ard_gaw/campaigns/test_suite/tests/` directory placeholder. |
| Retained compatibility surface | `compat_scripts/test_suite/__init__.py` namespace shim; `compat_scripts/run_one.py` / `run_matrix.py` / `run_matrix_round_robin.py` thin wrappers. |

## What was already implemented before this pass

The entire wrapper-parity surface was already implemented and tested
under governance Phase 5 (`evidence/reports/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`)
and Phase 8 (`evidence/reports/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`).
Phase 1 here is the governed *feature*-phase recognition of that
state plus the missing runbook bundle and the cleanup pass below.

## What was fixed / added in this pass

- Created the feature runbook bundle under
  `governance/runbooks/features/test_suite_migration/` (required by
  the change-control standard for features large enough to plan).
- Recorded the Stage ↔ feature-phase mapping in ARCHITECTURE.md so
  agents reading the architecture file know which governance bundle
  drives migration phasing.
- Linked the feature runbook and this report from `.ai/index.md` so
  agent routing picks them up.
- Added the catalog entry in
  `evidence/indexes/evidence_catalog.md`.
- Removed disposable `__pycache__` and `*.pyc` artifacts from the
  active source tree under
  `src/sim_ard_gaw/campaigns/test_suite/`. These were never
  git-tracked (the workspace has no root commit) but were polluting
  the active source tree. `.gitignore` already covers them.

No code-behavior changes. No manifest or schema changes.

## What remains deferred

- Phase 2: additive generic manifest fields.
- Phase 3: real `StagedStrategy` adapters (stimulus, control,
  monitor, analyzers, verdict) without going through
  `run_one.run_one(...)`.
- Phase 3 entry gate: a live SITL/Gazebo single-attempt diff
  between `python -m test_suite.cli.run_case ...` and
  `src/sim_ard_gaw/compat_scripts/run_one.py ...` to validate the
  wrapper-delegate property empirically.
- Phase 4: a second non-wind plugin and a real plugin registry.
- Phase 5: deletion / wrapper-ification of legacy
  `run_one.py` / `run_matrix.py` / `run_matrix_round_robin.py`.
- Housekeeping: removal of the empty
  `src/sim_ard_gaw/campaigns/test_suite/tests/` placeholder.

## Commands run

CLI help / import smoke (executed from the workspace root with
`PYTHONPATH=src:src/sim_ard_gaw/compat_scripts`):

- `env/bin/python3 -m test_suite.cli.run_case --help`
- `env/bin/python3 -m test_suite.cli.run_suite --help`
- `env/bin/python3 -m test_suite.cli.run_round_robin --help`
- `env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_case --help`
- `env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_suite --help`
- `env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_round_robin --help`
- `env/bin/python3 src/sim_ard_gaw/compat_scripts/run_one.py --help`
- `env/bin/python3 src/sim_ard_gaw/compat_scripts/run_matrix.py --help`
- `env/bin/python3 src/sim_ard_gaw/compat_scripts/run_matrix_round_robin.py --help`

Disposable-artifact cleanup:

- `find src/sim_ard_gaw/campaigns/test_suite -name '__pycache__' -type d -exec rm -rf {} +`
- `find src/sim_ard_gaw/campaigns/test_suite -name '*.pyc' -delete`
- `find src/sim_ard_gaw/campaigns/test_suite -name '__pycache__' -o -name '*.pyc'` (verifies empty result)

Tests:

- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests`
- `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `env/bin/python3 -m unittest discover -s tests/integration`
- `make test-parity`
- `make doctor`

Git status:

- `git status --short`

## Test results

| Command | Result |
| --- | --- |
| `compileall` of `src/sim_ard_gaw/campaigns/test_suite` and `tests` | PASS (no errors) |
| `unittest tests/parity/test_phase1_parity.py` | PASS: 8 tests (6 original + 2 added in the post-review remediation) |
| `unittest discover -s tests/unit` | PASS: 20 tests |
| `unittest discover -s tests/integration` | PASS: 3 tests |
| `make test-parity` | PASS: 8 tests |
| `make doctor` (structure validator + evidence validator) | PASS |
| Each of the nine CLI help invocations above | PASS (exit code 0, expected usage text) |

## Scheduler / manifest safety review

Inspected `core/scheduler.py`, `core/suite_runner.py`,
`core/attempt_runner.py`, `core/manifest.py`, and
`plugins/wind_matrix/plugin.py`:

- `RoundRobinScheduler` advances a pointer over a fixed
  `_pass_cases` list per pass and skips cases already at
  acceptance, matching the legacy round-robin semantics. The
  parity test `test_round_robin_snapshots_one_pass_in_legacy_order`
  freezes the expected order.
- `LegacyManifest.accepted_count` defers to the legacy
  `run_one.combo_successes(...)`. Only `success_full` (and
  `success_square_only` when `accept_square_only` is set) becomes
  an accepted success; `failed`, `failed_analysis`, `error`, and
  `interrupted` are not accepted.
  *(2026-06-01 errata: the sentence above describes the initial Phase 1
  state before the post-review remediation in this same report. The
  post-review High finding (see "Post-review remediation" below) added
  the `accept_square_only` policy argument so that `success_square_only`
  is excluded by default — a post-legacy stricter safety policy, not
  retained legacy parity. Legacy `run_one.combo_successes` counts both
  `success_full` and `success_square_only` unconditionally; the
  policy-aware implementation intentionally diverges from that. Running
  the new suite/round-robin logic over an old campaign root may retry or
  renumber rows that legacy would have accepted as square-only success.
  In Phase 3C this wind-compatible manifest behavior moved entirely to
  `plugins/wind_matrix/manifest.py`.)*
- `AttemptRunner.run` wraps the strategy body in `try/finally` so
  `EnvironmentAdapter.cleanup` always runs even when the body
  raises. `WindMatrixEnvironment.cleanup` always calls
  `run_matrix.cleanup_stack()` then closes any retained process
  handles.
- `RoundRobinScheduler` populates `slot_deadline_monotonic_s` and
  `slot_budget_s` metadata; `_legacy_run_one_body` propagates the
  deadline into `run_one.run_one(...)` after subtracting
  `slot_deadline_margin_s` so cleanup has time to run inside the
  budget.
- Manifest writes use the legacy `run_one.save_manifest`
  atomic-write path (governance Phase 5 hardening). The CLI
  pre-amble in `run_suite.py` and `run_round_robin.py` is wrapped
  in `run_one.campaign_manifest_lock`.

No new tests were needed to cover a Phase 1 gap.

## Post-review remediation

The initial Phase 1 PASS was returned with four findings (one High,
three Low). All were addressed in the same dated pass:

1. **High — partial `success_square_only` could count as accepted.**
   `LegacyManifest.accepted_count` delegated to
   `run_one.combo_successes`, which counts both `success_full` and
   `success_square_only` rows regardless of caller policy. A
   historical square-only manifest row could silently satisfy
   acceptance for a strict full-mission run.

   Fix: `LegacyManifest` gained an `accept_square_only` constructor
   argument (default `False`). When `False`, `accepted_count`
   filters out attempts whose `status == "success_square_only"`. The
   `wind_matrix` plugin in `plugin.py` forwards
   `WindMatrixConfig.accept_square_only`.

   Tests: `tests/parity/test_phase1_parity.py::test_legacy_manifest_does_not_accept_square_only_by_default`
   builds a manifest with one `success_full` and one
   `success_square_only` row, then asserts `accepted_count == 1`
   under the strict policy and `== 2` under `accept_square_only=True`.
   `test_legacy_manifest_partial_alone_is_not_accepted_under_strict_policy`
   builds a manifest with only one `success_square_only` plus
   `failed` and `failed_analysis` rows, then asserts `accepted_count
   == 0` under the strict policy and `== 1` under
   `accept_square_only=True`.

2. **Low — stale validation path in ARCHITECTURE.md.** The
   "Validation steps" section pointed at
   `scripts/test_suite/tests/test_phase1_parity.py`, which does not
   exist. Fixed to the canonical
   `tests/parity/test_phase1_parity.py` and the test list updated
   to match the actual eight tests.

3. **Low — `cli/run_suite.py` docstring overstated runtime
   equivalence.** It said "behaviorally equivalent to the legacy
   `run_matrix.py`". Reworded to "mirrors the flag surface" /
   "delegates through the legacy `run_one.run_one(...)` call path"
   with an explicit reminder that a live SITL/Gazebo diff is still
   required.

4. **Low — same wording check applied to `cli/run_round_robin.py`.**
   The same softening was applied so the operator-visible
   description matches the static-only evidence at this phase.

The flag-surface parity test
(`test_cli_flag_surfaces_match_legacy`) was unaffected — the
description-line wording is not part of the `--flag` regex it
diffs.

## Honest blockers / residual risk

- Phase 1 does not include a live SITL/Gazebo single-attempt diff
  between the new CLI and legacy `run_one.py`. The wrapper-delegate
  property keeps the legacy body in the call path, so equivalence
  is structural rather than empirical at this phase. Treating the
  current `test_suite.cli.*` paths as wrapper-equivalent to the
  legacy scripts is safe; treating them as independently runtime-proven
  is not. The Phase 3 entry gate requires this diff.
- The Phase-1 plugin registry hard-codes `wind_matrix`. A non-Phase-1
  plugin cannot be selected via `--plugin`. This is the expected
  Phase-1 state; the registry redesign is part of Phase 4.

## Old-workspace modification statement

The old workspace `/home/ahmed/ardupilot_workspace` was not modified
during this Phase 1 pass.

## Phase 1 conclusion

PASS. The wrapper-parity baseline is locked down, the governed
feature-runbook bundle exists, agent routing points at it,
disposable build artifacts are gone, and every parity/unit/integration
test plus `make doctor` passes.
