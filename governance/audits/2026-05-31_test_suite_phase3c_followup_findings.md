# test_suite Phase 3C Follow-up Review Findings (H-1 .. H-7)

Date/time: 2026-05-31, Africa/Cairo / EEST (+03:00)

## Scope

This audit records a second review pass against the feature Phase 3C
`test_suite` staged wind-matrix work, raised after the
`2026-05-31_test_suite_phase3c_review_findings.md` (C-1 .. C-4) pass. It
covers the attempt-directory contract, plugin-owned analysis/BIN/summary
ownership, manifest read caching, mission item counting, CLI flag parity
coverage, and staged-path test fidelity.

It also records two correctness defects introduced by the in-progress fix
work itself (broken f-string test bodies, and unit tests that patched the
retired legacy module instead of the plugin-owned helpers).

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.

## Findings And Resolution

| ID | Finding | Resolution |
| --- | --- | --- |
| H-1 | `attempt_dir_factory` returned the combo `runs/` directory, and `ctx.attempt_dir` was mutated mid-attempt by the stimulus stage, so an exception before the stimulus stage left a non-canonical attempt directory in the terminal/running manifest rows. The framework also documented attempt-directory layout as core-owned while it was plugin-mutated. | `attempt_dir_factory` returns the full `attempt_NNN` path (already corrected). `build_wind_matrix_running_record` and `build_wind_matrix_error_fields` now re-derive the canonical `attempt_NNN` directory from the attempt index and set `ctx.attempt_dir` so running and terminal rows always record the same canonical path, regardless of the directory handed to `AttemptRunner.run`. A staged stimulus/control/monitor failure test passes the combo `runs/` parent and asserts the canonical `attempt_001` row. |
| H-2 | `WindMatrixStimulus._ensure_attempt_dir()` used legacy `run_one.combo_runs_dir` / `attempt_key` instead of the identical plugin-owned `defaults` helpers, creating a silent duplicate-source coupling. | Resolved with the Phase 3C C-3 stimulus rework: `_ensure_attempt_dir()` now uses `defaults.attempt_dir(...)`. No `run_one` path helpers remain in stimulus directory/run-config creation. |
| H-3 | `WindMatrixManifest.accepted_count` / `next_attempt_index` were described as reading `manifest.json` from disk on every scheduler call. | The plugin manifest caches the reconciled manifest (`_reconciled_manifest()` with `_cache` / `_cache_reconciled`); repeated `accepted_count` / `next_attempt_index` calls within a scheduler decision read the cache, and the cache is refreshed on `load()` / invalidated implicitly after writes. |
| H-4 | `defaults.mission_item_count` was described as line-counting, which could disagree by one with `run_one.mission_item_count` (which uses `mavwp.MAVWPLoader().count()`). | `defaults.mission_item_count` now uses `mavwp.MAVWPLoader().count()`, identical to the legacy implementation. The round-robin slot budget calculation therefore matches the legacy runner. |
| H-5 | No test asserted that `run_suite` does not adopt `run_round_robin`-only flags such as `--require-analysis`. | `tests/parity/test_phase1_parity.py::test_suite_cli_does_not_adopt_round_robin_require_analysis_flag` asserts `--require-analysis` is absent from `run_suite` and present in `run_round_robin`, alongside the existing legacy flag-surface diff. |
| H-6 | The staged `WindMatrixAnalyzer` invoked many `run_one.*` analysis/BIN/summary helpers, and the staged lifecycle tests only patched those helpers on the imported `run_one` module, so no test proved the staged analyzer runtime could run with legacy runner imports blocked. | The staged analyzer is now plugin-owned: `analyzers.py` imports `collect_bin_log`, `run_analysis`, `build_run_summary`, `cleanup_stack_for_analysis`, `clamp_timeout_to_slot`, and `ensure_run_alias_link` from `plugins/wind_matrix/analysis_helpers.py` (no `run_one` import). The Phase 3C import-blocker hard test now executes `WindMatrixAnalyzer.analyze()` to success with the three legacy runner modules blocked. |
| H-7 | The staged `run_config.json` was described as using `run_one.*` constants and omitting `sitl_launch_command` / `gazebo_launch_command`, and as using a divergent `wind_injection_source` string. | `_write_run_config()` uses `defaults.*` constants and writes `sitl_launch_command` and `gazebo_launch_command`. `wind_injection_source` uses the plugin-owned `defaults.wind_injection_source(...)` helper, which preserves the legacy text for comparator-dataset compatibility. The Phase 3C hard test asserts these `run_config.json` fields. |
| H-8 | (Defect introduced by in-progress fix work) Two unit-test files built subprocess/inline code via `textwrap.dedent(f"""...""")` with unescaped single-brace dict literals (`return_value={}`, `extra[...] = { ... }`), raising `SyntaxError` / `ValueError` at module import or runtime. | Single-brace literals inside the f-string code blocks are escaped (`{{ ... }}`). Both files compile and run. |
| H-9 | (Defect introduced by in-progress fix work) The staged-attempt and Phase 3C tests mocked `run_one.<fn>` / `analysis_helpers.<fn>` while the analyzer looks up those names in the `plugins/wind_matrix/analyzers` namespace (`from .analysis_helpers import ...`), so the mocks did not take effect and the real analysis ran. | All analysis helper mocks now patch `test_suite.plugins.wind_matrix.analyzers.<fn>` (the namespace the analyzer actually uses). |

## What This Changes In The Phase Map

The Phase 3F analysis substage (BIN collection, `run_analysis`, `build_run_summary`,
analysis cleanup, run-alias linking, slot-timeout helper) is now test-suite-owned
in `plugins/wind_matrix/analysis_helpers.py`. The following staged-runtime legacy
dependencies still remain and are unchanged by this pass:

- `WindMatrixEnvironment` launch/readiness/cleanup -> `run_matrix.*` / `run_one.*` (Phase 3D).
- `_LazyLegacyAutoMissionControl` mission upload/arm/mode -> `run_one.*` (Phase 3E).
- `_LazyLegacyDisarmMonitor` -> `run_one.monitor_until_disarm` (Phase 3E).
- `WindMatrixStimulus` runtime wind injection -> `run_one.inject_wind` / `run_one.preloaded_wind_artifact` (Phase 3F wind-injection substage).
- `_legacy_run_one_body` -> `run_one.run_one` (legacy-mode-only delegate; correct).

This is not a Phase 3G claim: no live SITL/Gazebo staged wind case was run, and
the auto control/monitor execute-time paths still import `run_one`.

## Verification Record

The associated evidence report is
`evidence/reports/features/2026-05-31_test_suite_phase3c_followup_fixes.md`.

## Residual Risk

Phase 3D-3G still must remove staged execution dependencies on legacy runner
helpers for environment launch/readiness/cleanup, MAVLink control/monitoring,
and runtime wind injection before Phase 4 can start. The staged auto
control/monitor paths remain unexercised with legacy imports blocked because
they still depend on `run_one` at execute time.
