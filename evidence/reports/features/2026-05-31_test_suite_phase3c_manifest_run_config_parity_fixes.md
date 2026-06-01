# test_suite Phase 3C Strict-Audit High Findings Fixes

Date/time: 2026-05-31T23:10:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature remediation evidence

Conclusion: PASS for the two scoped strict-audit high findings implemented in
this change only:

1. plugin-owned wind-matrix manifest reconciliation parity behavior; and
2. staged `run_config.json` schema/value parity for the migrated fields.

This report does **not** claim live SITL/Gazebo simulation proof, full staged
runtime zero-legacy proof, full migration completion, or Phase 4 readiness.

## Scope

- Implemented plugin-owned reconciliation in
  `plugins/wind_matrix/manifest.py` without importing/calling `run_one.py`
  reconciliation logic.
- Implemented staged `run_config.json` parity updates in
  `plugins/wind_matrix/stimulus.py` and `plugins/wind_matrix/defaults.py`.
- Added strict unit coverage for the required manifest and run-config parity
  checks in `tests/unit/test_test_suite_phase3_staged_attempt.py`.
- Updated adjacent non-live test fixtures only where they depended on
  underspecified legacy manifest rows that now fail the stricter reconciliation
  contract.

## Key Corrections Delivered

- Manifest reconciliation now enforces duplicate and missing-record guards,
  stale-running recovery, legacy terminal analysis-status normalization
  (`""`/`pending` -> `not_run`) while preserving terminal statuses, success
  record validation, run-alias normalization to `run_##`, alias repair, and
  stale alias cleanup in combo `runs/` directories.
- Staged `run_config.json` now restores legacy fields:
  `sitl_wipe_eeprom_expected`, `local_param_override_present`,
  `auto_arm_to_auto_settle_s`, `auto_wind_injection_min_relalt_m`,
  `auto_wind_injection_alt_timeout_s`, and
  `entry_waypoint_max_pass_distance_m`.
- Staged `run_config.json` no longer writes `attempt_strategy`.
- `gazebo_plugin_runtime` now uses the legacy nested schema keys:
  `policy`, `gz_sim_system_plugin_path`,
  `gz_sim_system_plugin_path_entries`, and
  `known_ardupilot_plugin_binaries`, and excludes `known_plugins`.
- Schema assertions use production `defaults.gazebo_plugin_diagnostics()` (no
  test-only fake in the strict schema test).

The following audit findings were also addressed in this change set:

**Finding 1 — Artificial "real staged wind" test renamed and augmented:**
- `test_real_staged_wind_path_does_not_call_legacy_run_one_body` renamed to
  `test_staged_orchestration_shell_does_not_call_legacy_run_one_body` to
  accurately describe that it proves only orchestration-shell avoidance of
  `run_one.run_one`, not real adapter semantics.
- New test `test_real_staged_wind_adapters_run_with_boundary_mocks` added:
  exercises real `WindMatrixStimulus`, real environment adapter, real
  `WindMatrixAnalyzer` chain, and real `WindMatrixManifest`, mocking only
  external boundary calls (`inject_wind`, `upload_mission`, `arm_vehicle`,
  `monitor_until_disarm`, `collect_bin_log`, etc.) in the namespaces the
  adapters actually use. `run_one.run_one` is blocked and raises if called.
  The test was fixed from a `SyntaxError: too many statically nested blocks`
  (23 context managers exceeded CPython's limit) by converting the patch block
  to `contextlib.ExitStack`.
- `review.md` and `phase_3_staged_attempt_runner.md` updated to reference both
  tests with accurate scope language.

**Finding 2 — Post-legacy acceptance policy explicitly labeled:**
- `test_wind_verdict_and_acceptance_matrix_covers_terminal_outcomes` locks the
  strict/lenient `accepted_count` matrix: `success_square_only` counts 0 by
  default and 1 with `accept_square_only=True`.
- `test_campaign_summary_uses_post_legacy_acceptance_policy` locks campaign
  summary `accepted_runs`/`remaining_runs` under both the strict and lenient
  policies.
- `review.md` and `phase_3_staged_attempt_runner.md` carry explicit notes that
  this is an intentional post-legacy stricter safety policy divergence, not
  legacy parity.

## 2026-06-01 Strict-Audit Follow-up (H-A, H-B, H-C)

Three additional high findings were addressed in a follow-up change on 2026-06-01:

**4th correction — H-A (manifest reconciliation legacy parity):**
Plugin `_reconcile_manifest_bookkeeping()` raised `RuntimeError` for any success
row where `attempt_index` was absent or less than 1. Legacy
`reconcile_manifest_bookkeeping` in `run_one.py` imposes no such requirement on
success rows: only `target_run_index`, `run_alias`, and `attempt_dir` existence are
validated. The strict guard was removed from `manifest.py`. Success-row handling
now matches legacy semantics exactly. Regression test
`test_manifest_reconcile_success_row_with_missing_attempt_index_does_not_raise`
was added to `tests/unit/test_test_suite_phase3_staged_attempt.py`; it builds a
`success_full` row with a valid `combo_key`, `target_run_index`, existing
`attempt_dir`, but missing `attempt_index`, asserts neither plugin nor legacy
reconciler raises, and asserts the row is counted as accepted.

**5th correction — H-B (analysis substage executing coverage):**
Prior tests mocked `run_analysis` and `build_run_summary`; fidelity against
legacy was unproven. The following executing tests were added in
`tests/unit/test_wind_matrix_analysis_helpers.py`:

- `TestCollectBinLogBehavior`: six pure-filesystem tests covering
  `collect_bin_log` — strict single new BIN returns it; >1 new BINs raises
  "Multiple new"; strict with only old names returns None; non-strict mtime
  fallback within 2 s window returns newest; empty dir returns None; missing
  dir returns None. Each assertion is mirrored against `run_one.collect_bin_log`
  on the same fixture.
- `TestAnalysisHelperRealLog.test_build_run_summary_is_byte_equal_to_legacy_on_real_log`:
  runs both `run_one.run_analysis`/`run_one.build_run_summary` (legacy) and
  `analysis_helpers.run_analysis`/`analysis_helpers.build_run_summary` (migrated)
  on the same real flight log into separate temp dirs and asserts the summary
  dicts are deeply equal (artifact paths normalized to filenames to remove
  temp-dir variation). The test is skipped when the log is absent.

Real log used as parity anchor:
- Path: `var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/wind_x_04_y_04/runs/run_01/wind_x_04_y_04__rep_01__attempt_002.BIN`
- SHA256: `771fa52785154b215e9650adfd3971f2077299a8fc1dbbfa9aedf8cfd62b5711`
- Command: `env/bin/python3 -m unittest tests/unit/test_wind_matrix_analysis_helpers.py`
- Result: PASS — 7 tests, real-log test executed both analysis paths; `build_run_summary` dicts were byte-equal to legacy.

**6th correction — H-C (accept_square_only divergence documentation):**
Documentation-only fix. The strict `accept_square_only` gate in
`WindMatrixManifest.accepted_count()` applies when run through `test_suite.cli.*`
for **both** `legacy` and `staged` attempt strategies, not just staged. Existing
docs framed this as a "post-legacy" / staged-path property without warning that
legacy-mode runs launched via the new CLIs will renumber/retry square-only
campaigns differently than `run_matrix.py`. Clarification notes were added to
`review.md` (near the existing "Post-legacy acceptance policy note") and to
`plan.md` (Phase 3C success criteria / Manifest Compatibility Contract). No code
was changed.

## Files Changed (2026-06-01 follow-up)

H-A, H-B code changes:
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/manifest.py` (H-A: removed strict attempt_index guard)
- `tests/unit/test_test_suite_phase3_staged_attempt.py` (H-A: updated/added reconcile regression test)
- `tests/unit/test_wind_matrix_analysis_helpers.py` (H-B: new file — collect_bin_log + real-log parity tests)

H-C and reporting changes:
- `governance/runbooks/features/test_suite_migration/review.md` (H-A/H-B/H-C corrections)
- `governance/runbooks/features/test_suite_migration/plan.md` (H-C: accept_square_only clarification)
- this report (4th–6th correction entries)

## Files Changed (original 2026-05-31 change)

- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/manifest.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/stimulus.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/defaults.py`
- `tests/unit/test_test_suite_phase3_staged_attempt.py`
- `tests/unit/test_test_suite_manifest_generic_view.py`
- `tests/parity/test_phase1_parity.py`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `.ai/index.md`
- `evidence/indexes/evidence_catalog.md`

## Commands Run (2026-06-01)

- `env/bin/python3 -m unittest tests/unit/test_wind_matrix_analysis_helpers.py`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py -k manifest_reconcile`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`
- `make test-parity`
- `make doctor`

## Validation Results (2026-06-01)

| Command | Result |
| --- | --- |
| `test_wind_matrix_analysis_helpers.py` | PASS: 7 tests (incl. real-log parity) |
| `test_test_suite_phase3_staged_attempt.py -k manifest_reconcile` | PASS: 19 tests |
| `unittest discover -s tests/unit` | PASS: 85 tests |
| `test_phase1_parity.py` | PASS: 9 tests |
| `make test-parity` | PASS: 9 tests |
| `make doctor` | PASS: structure + evidence validation |

## Commands Run (original 2026-05-31)

- `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py`
- `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`

## Validation Results (original 2026-05-31)

| Command | Result |
| --- | --- |
| `tests/unit/test_test_suite_phase3_staged_attempt.py` | PASS: 46 tests |
| `tests/unit/test_test_suite_manifest_generic_view.py` | PASS: 9 tests |
| `tests/parity/test_phase1_parity.py` | PASS: 9 tests |

## Claim Boundaries

- No live simulation commands were run.
- No claim is made that staged runtime environment/control/monitor/wind-injection
  execution is legacy-independent.
- No claim is made that Phase 3D-3G are complete.
