# Wind-Matrix Legacy Attempt-Strategy Retirement

Date/time: 2026-06-30
Conclusion: PASS (with accepted-risk note on campaign-scale parity)

## Scope

Retire the `legacy` attempt strategy from the wind_matrix (CTE / Lane 1)
plugin and make the extracted `staged` adapters the only supported attempt
path. This follows the compat_scripts wrapper-layer removal
(`PHASE_8_COMPAT_FINAL_REMOVAL_AUDIT_2026-06-30.md`).

The standalone operator/campaign runners (`run_one.py`, `run_matrix.py`,
`run_matrix_round_robin.py` under `src/sim_ard_gaw/campaigns/wind_matrix/`)
are NOT deleted — see "Retained" below.

## Changes

- `WindMatrixConfig.attempt_strategy` default: `legacy` -> `staged`.
- CLI defaults (`run_case`, `run_suite`, `run_round_robin`) and the interactive
  helper: default `staged`; `legacy` removed from `--attempt-strategy` choices.
- `plugins/wind_matrix/plugin.py`: removed `_legacy_run_one_body`,
  `_legacy_body_unavailable`, the `legacy_body` field, and the `legacy`
  branch. `build_plugin`/`attempt_runner` now reject `attempt_strategy != staged`
  with a clear retirement error.
- Deleted `plugins/wind_matrix/legacy.py` (the run_one import bridge).
- Deleted the orphaned `campaigns/wind_matrix/run_one_og.py` (1276-line
  backup; referenced only by historical docs, no code/tests/ops).
- Kept the generic `LegacyDelegateStrategy` in `core/attempt_runner.py`
  (not wind_matrix-specific) and `_record_from_legacy` (manifest-record
  translator still used by tests).
- Updated tests: legacy-contrast tests now assert retirement (build raises,
  CLI choice rejected); zero-legacy-foundation tests patch the owned
  run_one/run_matrix entry points instead of the deleted bridge.

## Retained (with reason)

`run_one.py` / `run_matrix.py` / `run_matrix_round_robin.py` remain because:
- `launch/launch.sh` uses `run_one.py` as the operator `RUN_ONE_ENTRYPOINT`
  (the direct human launch path for the CTE lane);
- ~11 tests import monolith utility functions (`collect_bin_log`,
  `save_manifest`, `mission_item_count`, wind injection) as their real home.

Deleting them requires a separate effort: migrate the operator entrypoint to
a staged CLI and extract those utilities into owned modules. Not done here.

## Accepted-risk note

Staged became the default on the strength of the Phase 3F/3G SINGLE-COMBO
live staged-vs-legacy parity comparison
(`evidence/curated_logs/test_suite_phase3f_staged_live_20260601`,
`..._phase3g_legacy_compare_20260601`). Campaign-scale (multi-combo /
round-robin) staged-vs-legacy parity is NOT separately evidenced. This
cutover proceeds on accepted risk; CLI docstrings were updated to state this
honestly rather than claim full parity.

## Validation

- Full test suite: 160 tests + 258 subtests PASS (`PYTHONPATH=src`).
- `compileall` PASS; `make doctor` PASS.
- No `test_suite` framework/plugin code imports the run_one/run_matrix
  monolith.
