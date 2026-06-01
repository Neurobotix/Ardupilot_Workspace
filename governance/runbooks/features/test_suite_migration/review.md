# Feature Runbook: test_suite Migration — Review

Status as of 2026-06-01: **Phases 3A–3G are accepted. The staged wind_matrix
path is fully zero-legacy and live-proven against the retained legacy tool, and
Phase 4 (second plugin) is now unblocked.** Phases 3D (environment), 3E (MAVLink
control/monitor), and 3F (wind injection) moved every staged runtime stage into
plugin-owned modules; the only remaining `run_one` use is the intended
legacy-strategy delegate. Phase 3G ran the staged path live and compared it
against `compat_scripts/run_matrix.py` invoked directly (no `test_suite` code in
that baseline): both `success_full`, flight metrics within SITL noise, schema
and shared manifest fields matching. Evidence:
`evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md`.
Phase 5 (legacy retirement) still requires Phase 4 acceptance.

Earlier status (2026-05-29): Phase 3C was accepted for the legacy-runner import
blocker and core/plugin foundation boundary only; staged foundation no longer
imported legacy runner modules during config, case generation, manifest, plugin
construction, or CLI parser/bootstrap setup, while runtime stages remained
Phase 3D-3G work. That sequence is now complete.

2026-05-30 correction: a stricter review found `core/attempt_runner.py`
decoded wind legacy status strings (`success_full`, `success_square_only`).
That was a Phase 3C boundary failure. The decoder is now removed; status comes
from framework verdicts or an explicit framework `AttemptStatus` supplied by a
plugin.

2026-05-30 correction: default staged auto construction now resolves
`auto_wind_phase` to `before-arm` instead of inheriting the legacy-only
`after-takeoff` default. Explicit staged `after-takeoff` remains fail-closed.
Campaign summary accepted counts now respect `accept_square_only`.

2026-05-31 correction: review findings closed three Phase 3C regressions:
plugin-owned wind manifest writes are temp-file-rename atomic again, staged
attempts persist a `running` row before environment/runtime work and
terminalize ordinary failures, and `WindMatrixStimulus` no longer uses legacy
runner constants/path/provenance helpers for attempt directories or
`run_config.json`. This does not change the Phase 3C boundary: executing the
staged environment, wind injection, MAVLink control/monitor, artifact,
analysis, or summary path still has legacy runner dependencies assigned to
Phase 3D-3G.

2026-05-31 follow-up review (H-1 .. H-9): the staged analyzer was migrated to
plugin-owned `plugins/wind_matrix/analysis_helpers.py` (BIN collection,
`run_analysis`, `build_run_summary`, analysis cleanup, run-alias linking,
slot-timeout clamp), so the analysis substage of Phase 3F no longer imports
`run_one`; the Phase 3C import-blocker hard test now executes
`WindMatrixAnalyzer.analyze()` to success. Staged running/terminal manifest
rows now record the canonical `attempt_NNN` directory (H-1). Two test defects
introduced during in-progress fix work (unescaped f-string braces; analysis
mocks aimed at the wrong namespace) were corrected. Runtime wind injection,
environment launch/readiness, and MAVLink control/monitor execution still reach
legacy runner helpers and remain Phase 3D/3E/3F work. Evidence:
`evidence/reports/features/2026-05-31_test_suite_phase3c_followup_fixes.md`;
audit: `governance/audits/2026-05-31_test_suite_phase3c_followup_findings.md`.

2026-05-31 strict-audit correction: the prior H-7 wording overclaimed exact
staged `run_config.json` parity. Exact migrated-field schema/value parity and
manifest-reconciliation strict fixes are evidenced in
`evidence/reports/features/2026-05-31_test_suite_phase3c_manifest_run_config_parity_fixes.md`.

2026-06-01 Phase 3E implementation: staged `assert_ready`,
`WindMatrixAutoMissionControl`, and `WindMatrixDisarmMonitor` no longer call
or inject any `run_one.*` helper. They call plugin-owned `mavlink_control.*`
only. The Phase 3C import-blocker hard test extended with a Phase 3E block.
The only remaining staged legacy dependency is `WindMatrixStimulus` runtime
wind injection (`run_one.inject_wind` / `preloaded_wind_artifact`), owned by
Phase 3F. `_legacy_run_one_body` / `LegacyDelegateStrategy` are the legacy
strategy path and are unchanged. Evidence:
`evidence/reports/features/2026-06-01_test_suite_migration_phase_3e.md`.

2026-06-01 strict-audit correction (H-A, H-B, H-C):

- H-A (manifest reconciliation legacy parity): the plugin
  `_reconcile_manifest_bookkeeping()` incorrectly raised `RuntimeError` for
  success rows lacking `attempt_index >= 1`. Legacy `reconcile_manifest_bookkeeping`
  imposes no such requirement on success rows. The strict guard is removed;
  success-row handling now matches legacy exactly. Regression test
  `test_manifest_reconcile_success_row_with_missing_attempt_index_does_not_raise`
  added to `tests/unit/test_test_suite_phase3_staged_attempt.py`, asserting no
  raise and parity against the legacy reconciler on the same fixture.

- H-B (analysis substage executing coverage): the prior wording implied
  `run_analysis` and `build_run_summary` were verified only via mocked tests.
  Executing tests have now been added in
  `tests/unit/test_wind_matrix_analysis_helpers.py`:
  `TestCollectBinLogBehavior` covers `collect_bin_log` pure-filesystem behavior
  (strict single/multiple new BIN, mtime-fallback, empty/missing dir) with
  parity assertions against the legacy `run_one.collect_bin_log`;
  `TestAnalysisHelperRealLog.test_build_run_summary_is_byte_equal_to_legacy_on_real_log`
  runs both legacy and migrated analysis paths on the same real flight log
  (`var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/wind_x_04_y_04/runs/run_01/wind_x_04_y_04__rep_01__attempt_002.BIN`,
  sha256 `771fa52785154b215e9650adfd3971f2077299a8fc1dbbfa9aedf8cfd62b5711`) and
  asserts the `build_run_summary` dicts are deeply equal to legacy. The test is
  skipped when the log is absent (clean checkout). Evidence:
  `evidence/reports/features/2026-05-31_test_suite_phase3c_manifest_run_config_parity_fixes.md`
  (4th correction entry).

- H-C (accept_square_only divergence documentation): see the clarification note
  added to the Phase 3B acceptance table and to `plan.md`.

## Phase 3G acceptance review — gate accepted, Phase 4 unblocked

Date: 2026-06-01

| Criterion | Result | Evidence |
| --- | --- | --- |
| Hard no-legacy staged tests pass (no-SITL) | PASS | Import-blocker suite (Phase 3C–3F blocks); 100 unit tests. |
| Bounded live staged wind case completes | PASS | `wind_x_04_y_04` → `success_full`; `evidence/curated_logs/test_suite_phase3f_staged_live_20260601/`. |
| Matching live legacy case via the legacy tool directly | PASS | `compat_scripts/run_matrix.py` → `run_one.run_one`; `success_full`; `evidence/curated_logs/test_suite_phase3g_legacy_compare_20260601/`. No `test_suite` code in this baseline. |
| Staged/legacy flight metrics agree within SITL noise | PASS | square RMS 58.71 vs 58.57 (Δ0.14 m), p95 Δ0.96 m, max Δ0.65 m, 20 vs 20 segments. |
| `run_config.json` schema parity | PASS | Identical key set; only `sitl_bin_dir`/`sitl_use_dir` differ (different campaign-root paths). |
| Shared manifest legacy fields match | PASS | status/combo/wind/target_run_index/attempt_index/success_class/flags/analysis_status/run_alias all equal. |
| Differences documented as intended | PASS | Additive generic fields; `mission_contract`/`param_file_provenance` placement; `accept_square_only` policy; `wind_injection_source` value. See the 3G report. |
| Staged remains opt-in; legacy default unchanged; no second plugin; no legacy retirement | PASS | `WindMatrixConfig().attempt_strategy == "legacy"`; only plugin files touched. |

Full comparison: `evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md`.

Gate decision: **Phase 4 (one second non-wind plugin, zero framework-core
edits) is authorized.** Phase 5 (legacy retirement) remains blocked until
Phase 4 acceptance.

## Phase 3F acceptance review

Date: 2026-06-01

| Criterion | Result | Evidence |
| --- | --- | --- |
| Staged `WindMatrixStimulus.apply()` calls no `run_one.*` / `run_matrix.*` | PASS | `stimulus.py` now calls `wind_injection.inject_wind` / `preloaded_wind_artifact`; `from . import legacy` removed. |
| `wind_injection.py` reproduces legacy behavior (parity test) | PASS | `test_wind_matrix_wind_injection`: `parse_wind_echo` / `wind_echo_matches` parity; `inject_wind` success + retry parity (subprocess patched); `parse_sdf_world_wind` / `preloaded_wind_artifact` parity (refresh off and on). |
| Phase 3F in-subprocess import-blocker exercises staged stimulus with legacy blocked | PASS | `test_test_suite_phase3c_zero_legacy_foundation` Phase 3F block runs `WindMatrixStimulus.apply()` and writes `wind_injection.json` with `run_one`/`run_matrix` imports blocked. |
| Non-subprocess ownership test verifies stimulus wiring | PASS | `Phase3FWindInjectionOwnershipTests` patches `legacy.run_one_module` to raise and runs `apply()` through `wind_injection.*` without it. |
| Staged path is fully zero-legacy | PASS | The only live `legacy.run_one_module()` call in the plugin is `_legacy_run_one_body` (legacy strategy). Environment (3D), MAVLink (3E), and wind injection (3F) are all plugin-owned. |
| Misleading `wind_injection_source` provenance corrected | PASS | Value changed from `run_one.py ...` to `test_suite staged ...`; run_config schema (key set) unchanged. Intentional value-only divergence from legacy, recorded in the 3F report. |
| First live completed staged run captured | PASS | `wind_x_04_y_04` → `success_full`, `analysis_status=done`, `run_alias=run_01`, strict gz echo verified `{x:4.0,y:4.0,z:0.0}`. Curated: `evidence/curated_logs/test_suite_phase3f_staged_live_20260601/`. |
| Matched live legacy comparison | NOT DONE / Phase 3G | Phase 3F captured the staged live half only; the matching legacy run is Phase 3G. |
| Legacy runner scripts unmodified | PASS | Only plugin files touched. |
| No Phase 4 / second-plugin work | PASS | Phase 4 remains blocked until Phase 3G. |

Remaining legacy dependencies after Phase 3F (later-phase blockers):

- `_legacy_run_one_body` → `run_one.run_one`. **Legacy-mode-only delegate; correct and intended.** No staged-path legacy dependency remains.

## Phase 3E acceptance review

Date: 2026-06-01

| Criterion | Result | Evidence |
| --- | --- | --- |
| `assert_ready` (staged) calls no `run_one.*` / `run_matrix.*` | PASS | `environment.py` staged path calls `mavlink_control.wait_for_heartbeat`, `mavlink_control.wait_for_vehicle_ready`, and `analysis_helpers.clamp_timeout_to_slot`. The `from . import legacy` import is absent from the `assert_ready` body. |
| `WindMatrixAutoMissionControl.execute()` calls no `run_one.*` | PASS | `plugin.py` `WindMatrixAutoMissionControl` injects and calls `mavlink_control.*` (upload, verify, arm, settle, set_auto). No lazy `run_one` import. |
| `WindMatrixDisarmMonitor.run()` calls no `run_one.*` | PASS | `plugin.py` `WindMatrixDisarmMonitor` injects and calls `mavlink_control.monitor_until_disarm`. No lazy `run_one` import. |
| `mavlink_control.py` reproduces legacy behavior (parity test) | PASS | `test_wind_matrix_mavlink_control`: `mission_item_count` / `mission_item_int` parity on the real mission file; `monitor_until_disarm` parity via scripted fake-master streams for full-mission, square+loiter early stop, invalid_start_reason, and timeout. |
| Phase 3E in-subprocess import-blocker exercises staged assert_ready + control + monitor with legacy blocked | PASS | `test_test_suite_phase3c_zero_legacy_foundation` Phase 3E block runs `assert_ready`, `WindMatrixAutoMissionControl.execute()`, and `WindMatrixDisarmMonitor.run()` inside the subprocess import-blocker; any `run_one`/`run_matrix` import raises `AssertionError`. |
| Non-subprocess ownership test verifies adapter construction/wiring | PASS | `Phase3EControlMonitorOwnershipTests` in `test_test_suite_phase3c_zero_legacy_foundation` verifies `WindMatrixAutoMissionControl` and `WindMatrixDisarmMonitor` call only `mavlink_control.*`, not `run_one.*`. |
| Legacy mode remains default and unchanged | PASS | `WindMatrixConfig().attempt_strategy == "legacy"`; `_legacy_run_one_body` / `LegacyDelegateStrategy` unmodified. |
| Legacy-mode `assert_ready` is unchanged (no-op early return) | PASS | Legacy branch of `assert_ready` returns early; no `mavlink_control` calls in the legacy branch. |
| No live SITL/Gazebo run | PASS | All tests run with mocked or fake-master MAVLink message streams. |
| No Phase 3F/3G/4 work | PASS | Wind injection, BIN/artifacts, analysis, summary, and second-plugin work untouched. |
| Legacy runner scripts (`run_matrix.py`, `run_one.py`) unmodified | PASS | Only plugin files touched. |

Remaining legacy dependencies after Phase 3E (later-phase blockers):

- `WindMatrixStimulus` runtime wind injection still calls `run_one.inject_wind` / `preloaded_wind_artifact`. **Phase 3F wind-injection substage owns this.**
- `_legacy_run_one_body` → `run_one.run_one`. **Legacy-mode-only delegate; correct and intended.**

## Phase 3D acceptance review

Date: 2026-05-31

| Criterion | Result | Evidence |
| --- | --- | --- |
| `WindMatrixEnvironment.launch()` calls no `run_matrix.*` / `run_one.*` | PASS | `environment.py` now imports and calls `runtime.*`; `legacy.run_matrix_module()` / `legacy.run_one_module()` are not called in `launch()`. |
| `WindMatrixEnvironment.cleanup()` calls no `run_matrix.*` / `run_one.*` | PASS | `cleanup()` calls `runtime.cleanup_stack()` directly; no legacy module resolve. |
| `assert_ready()` is unchanged and still uses `legacy.run_one_module()` | PASS | Phase 3E boundary intact; `assert_ready` body unmodified. |
| `runtime.py` reproduces legacy behavior byte-for-byte | PASS | All seven functions and three constants ported from `run_matrix.py`/`run_one.py` with identical subprocess commands, env, flag order, and world-writing branches. |
| In-subprocess import-blocker test exercises `env.launch()+cleanup()` with legacy blocked | PASS | `test_staged_foundation_constructs_with_legacy_runner_imports_blocked` now includes Phase 3D env.launch()/cleanup() block with runtime mocked. Any `run_one`/`run_matrix` import raises `AssertionError`. |
| Non-subprocess unit test verifies owned-runtime path | PASS | `Phase3DEnvironmentOwnershipTests.test_phase3d_environment_launch_uses_owned_runtime_not_legacy` patches `legacy.run_matrix_module` and `.run_one_module` to raise, patches runtime.* and time.sleep, calls launch()+cleanup(), asserts success and legacy never called. |
| Legacy mode remains default and unchanged | PASS | `WindMatrixConfig().attempt_strategy == "legacy"`; legacy delegate path unmodified. |
| No live SITL/Gazebo run | PASS | All tests run with mocked runtime functions. |
| No Phase 3E/3F/3G/4 work | PASS | `assert_ready`, stimulus, control/monitor, analyzer, legacy scripts unchanged. |
| Legacy runner scripts (`run_matrix.py`, `run_one.py`) unmodified | PASS | Only plugin files touched. |

Remaining legacy dependencies after Phase 3D (superseded by Phase 3E):

- `WindMatrixEnvironment.assert_ready()` called `legacy.run_one_module()` for heartbeat, vehicle-readiness, slot-timeout. **Resolved in Phase 3E.**
- `_LazyLegacyAutoMissionControl` and `_LazyLegacyDisarmMonitor` lazily imported `run_one` at execute time. **Resolved in Phase 3E.**
- `WindMatrixStimulus` runtime wind injection still calls `run_one.inject_wind` / `preloaded_wind_artifact`. **Phase 3F wind-injection substage owns this.**
- `_legacy_run_one_body` → `run_one.run_one`. **Legacy-mode-only delegate; correct and intended.**

## Phase 3C acceptance review

| Criterion | Result | Evidence |
| --- | --- | --- |
| Staged config/default creation works with legacy runner imports blocked | PASS | `tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py` constructs `WindMatrixConfig(attempt_strategy="staged")` under an import blocker. |
| Staged case generation and combo-key naming work with imports blocked | PASS | Same hard test builds `WindMatrixCaseGenerator` and verifies `wind_x_00_y_04`. |
| Staged manifest creation and additive generic fields work with imports blocked | PASS | Same hard test appends via `WindMatrixManifest` and reads the generic view. |
| Default plugin staged bootstrap works with imports blocked | PASS | Same hard test constructs `WindMatrixConfig(attempt_strategy="staged")`, verifies staged auto defaults to `before-arm`, calls `build_plugin(...)` and `plugin.attempt_runner()`, and verifies `StagedStrategy` rather than `LegacyDelegateStrategy`. |
| CLI parser/bootstrap defaults are foundation-owned | PASS | Same hard test imports/parses `run_case`, `run_suite`, and `run_round_robin` under the blocker; staged suite/round-robin default to `before-arm`; `run_suite.main()` and `run_round_robin.main()` bootstrap with explicit `before-arm` while runtime execution is patched out. CLI help smoke also passes for owned module paths. |
| Generic core has no wind manifest/monitor/status fallback behavior | PASS | `test_core_has_no_wind_matrix_foundation_semantics` scans all `core/*.py` files for wind-matrix case fields, legacy runner names, combo keys, `success_full`, `success_square_only`, summary names, and wind/square monitor state. |
| Core does not interpret plugin legacy status strings | PASS | `test_core_staged_strategy_uses_framework_verdict_not_plugin_status` feeds a plugin manifest `status="success_full"` into `StagedStrategy` with a failed framework verdict and verifies the record stays `AttemptStatus.FAILED`. |
| Campaign summary respects strict square-only policy | PASS | `test_campaign_summary_respects_square_only_acceptance_policy` proves strict summaries do not count `success_square_only`, while `accept_square_only=True` summaries do. |
| Plugin wind manifest writes are atomic | PASS | 2026-05-31 focused regression test simulates a temp-file write failure and verifies the existing `manifest.json` remains intact. |
| Staged attempts write durable `running` and terminal rows | PASS | 2026-05-31 focused staged tests verify a `running` row exists before readiness and that launch failure updates that same row to terminal `error`. Stale `running` rows are reconciled as `interrupted` before later attempt allocation. |
| Stimulus config/path helpers avoid legacy runner imports | PASS within Phase 3C scope | 2026-05-31 import-blocker test executes `_ensure_attempt_dir()` and `_write_run_config()` with legacy runner imports blocked; wind injection itself remains Phase 3F legacy-helper work. |
| Legacy remains default | PASS | `WindMatrixConfig().attempt_strategy == "legacy"` and CLI parser defaults stay `legacy`. |
| Staged remains explicit | PASS | CLI parser tests require `--attempt-strategy staged` for staged mode. |
| Live zero-legacy runtime proof | NOT PROVEN | Phase 3C intentionally does not launch SITL/Gazebo, control MAVLink, inject wind, collect BIN logs, run analysis, or prove live campaign execution. |
| Staged runtime has no legacy dependencies | NOT PROVEN / OUT OF SCOPE | `WindMatrixEnvironment` still calls `run_matrix.*` / `run_one.*`; staged control/monitor and runtime wind injection still reach legacy runner helpers until Phase 3D-3F. The analysis/BIN/summary substage was migrated to plugin-owned `analysis_helpers.py` on 2026-05-31. |

Phase 3C removed these staged-foundation blockers from Phase 3B:

- `WindMatrixConfig` no longer imports legacy runner modules for defaults.
- `WindMatrixCaseGenerator` no longer imports legacy runner modules for
  combo-key formatting.
- staged plugin construction no longer builds the legacy delegate closure.
- staged `plugin.attempt_runner()` no longer imports legacy runner modules for
  control/monitor object construction.
- default staged auto construction no longer inherits the unsupported
  after-takeoff wind phase.
- CLI parser/bootstrap no longer imports legacy runner modules for defaults,
  wind-value validation, manifest setup, parameter stack resolution, or
  logging.
- manifest load/save/accepted-count/next-attempt behavior used by staged
  foundation no longer imports legacy runner modules and lives in
  `plugins/wind_matrix/manifest.py`.
- wind/square mission monitor behavior no longer lives in generic
  `core/monitor.py`; it lives in `plugins/wind_matrix/monitor.py`.
- wind legacy status-string mapping no longer lives in
  `core/attempt_runner.py`; framework status is verdict-derived or explicitly
  supplied as `AttemptStatus`.
- campaign summaries now use the same `accept_square_only` policy as manifest
  acceptance counting.

Remaining legacy dependencies are later-phase blockers, not Phase 3C failures:

- `WindMatrixEnvironment` still imports/calls `run_matrix.*` and `run_one.*`
  during staged runtime launch/readiness/cleanup. Phase 3D owns this.
- staged auto control and monitor still lazily import `run_one` when executed.
  Phase 3E owns this.
- `WindMatrixStimulus` still imports/calls `run_one` during runtime wind
  injection (`inject_wind` / `preloaded_wind_artifact`). Run-config and path
  helpers were already moved to plugin-owned defaults in the C-3 fix; only
  runtime injection remains. Phase 3F wind-injection substage owns this.
- `WindMatrixAnalyzer` BIN/analysis/summary work was migrated to plugin-owned
  `analysis_helpers.py` on 2026-05-31 and no longer imports `run_one`; the
  terminal error-row builder re-derives the canonical attempt directory from
  the attempt index.

No second plugin was added. Phase 4 was not started. Legacy scripts were not
retired or deleted. The old workspace was not modified.

## Phase 3B acceptance review

| Criterion | Result | Evidence |
| --- | --- | --- |
| Staged wind does not call `run_one.run_one(...)` | PASS | `test_staged_orchestration_shell_does_not_call_legacy_run_one_body` plus `test_real_staged_wind_adapters_run_with_boundary_mocks` both block `run_one.run_one` while staged execution persists a row. |
| Staged adapter lifecycle order (boundary-mocked) | PASS | `test_real_staged_wind_adapters_run_with_boundary_mocks`; `test_staged_strategy_calls_stages_in_expected_order` |
| Cleanup on success/failure/interrupt-like paths | PASS | `test_cleanup_runs_on_success`; `test_cleanup_runs_on_failure`; `test_cleanup_runs_on_interrupt_like_error` |
| Terminal error persistence | PASS | `test_collect_bin_failure_persists_legacy_compatible_error_row`; `test_staged_stimulus_failure_persists_legacy_error_row_and_cleans_up`; `test_staged_control_and_monitor_failures_persist_legacy_error_rows` |
| Verdict/acceptance matrix | PASS | `test_wind_verdict_and_acceptance_matrix_covers_terminal_outcomes`; `test_analysis_failure_persists_failed_analysis_and_is_not_accepted` |
| Manifest compatibility | PASS | `test_plugin_manifest_fields_are_additive_for_new_staged_rows`; `test_legacy_manifest_fields_round_trip_unchanged`; `tests/unit/test_test_suite_manifest_generic_view.py` |
| CLI default and explicit staged selection | PASS | `test_cli_attempt_strategy_defaults_and_explicit_selection`; Phase 1 parity flag tests |
| Unsupported staged mode fails closed | PASS | `test_cli_staged_after_takeoff_mode_fails_closed`; `test_staged_after_takeoff_rejected_before_environment_launch` |
| Bounded live staged wind case | BLOCKED | Two bounded `run_suite --attempt-strategy staged --auto-wind-phase before-arm` attempts exited during SITL launch before heartbeat. Raw output: `var/runs/test_suite_phase3b_staged_live_20260529/` and `var/runs/test_suite_phase3b_staged_live_20260529_no_wipe/`. |

Post-legacy acceptance policy note: staged and legacy-compatible manifests now
apply a stricter safety policy by default, excluding `success_square_only`
from accepted counts unless `accept_square_only=True`. This intentionally
diverges from legacy `combo_successes` behavior, so running the new
suite/round-robin logic over an old campaign root can trigger retries and
renumbering where legacy would have counted square-only success as accepted.

**H-C clarification (2026-06-01):** the strict `accept_square_only` gate is a
property of the new orchestrator's `WindMatrixManifest.accepted_count()` and
applies to **both** `legacy` and `staged` attempt strategies when the campaign
is run through `test_suite.cli.*` (`run_case`, `run_suite`, `run_round_robin`).
Running these CLIs in `--attempt-strategy legacy` mode over an existing campaign
root that contains `success_square_only` rows will renumber/retry those combos
that `run_matrix.py` would have counted as complete. This is an intentional
stricter safety policy divergence, not a bug; but operators resuming an existing
campaign through the new CLIs must be aware that square-only successes recorded
by `run_matrix.py` do not satisfy the strict acceptance gate by default. See
`plan.md` (Phase 3C success criteria) for the corresponding contract note.

Phase 3B proves only that the staged wind attempt lifecycle is not hidden
behind the single `run_one.run_one(...)` body. It also proves the current
staged path is **not** the final architecture, because it still depends on
legacy runner helper code:

- `run_matrix.launch_sitl`, `run_matrix.launch_gazebo`, and
  `run_matrix.cleanup_stack` remain in `WindMatrixEnvironment`.
- `run_one.wait_for_heartbeat` and `wait_for_vehicle_ready` remain in
  `WindMatrixEnvironment.assert_ready`.
- `run_one.inject_wind` and `preloaded_wind_artifact` remain in
  `WindMatrixStimulus`.
- MAVLink upload/arm/mode helper functions are injected into
  `MavlinkAutoMissionControl` by the wind plugin.
- `run_one.monitor_until_disarm` is injected into
  `WindMatrixDisarmCompletionMonitor`.
- BIN collection, `run_analysis`, and `build_run_summary` remain in
  `WindMatrixAnalyzer`.

Additional dependency found during self-review:

- `build_plugin(... attempt_strategy="staged")` still constructs a legacy
  delegate closure through `_legacy_run_one_body(config)`.
- `WindMatrixConfig` default factories import legacy runner modules.
- `WindMatrixCaseGenerator` imports legacy for combo-key formatting.
- `core.LegacyManifest` was wind-specific and imported legacy runner modules
  from generic core. Phase 3C resolved this by moving wind-compatible manifest
  behavior to `plugins/wind_matrix/manifest.py`.
- CLI parsing/bootstrap imports legacy runner modules for defaults,
  validation, manifest setup, and logging.

These dependencies are blockers for the real replacement system. Live staged
wind proof is also **not accepted**. Do not claim generic runtime readiness
from this Phase 3B pass.

## Phase 3C-3G plan review

The corrected next work is not Phase 4. It is a sequence of Phase 3 follow-on
steps that build a full staged system in parallel with legacy mode:

| Phase | Purpose | Exit |
| --- | --- | --- |
| 3C | Own defaults, paths, case generation, manifest, and CLI bootstrap. | Staged construction works with legacy runner imports blocked. |
| 3D | Own runtime/environment launch, cleanup, worlds, diagnostics, and timeouts. | Staged environment no longer calls `run_matrix.*` / `run_one.*`. |
| 3E | Own MAVLink readiness, mission control, arm/mode, and monitor. | Staged control/monitor no longer inject legacy helpers. |
| 3F | Own wind stimulus, BIN/artifacts, analysis invocation, summary, and terminal rows. | Staged stimulus/analyzer no longer call legacy helpers. |
| 3G | Prove full zero-legacy staged wind live beside legacy mode. | Hard no-legacy staged test passes, live staged case passes, matching legacy comparison exists. |

Only after Phase 3G is accepted can Phase 4 begin.

## Phase 3A acceptance review

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

This acceptance was based on static/unit/integration tests and CLI help smoke.
It did not include a live staged wind run. Remaining live/runtime proof is a
Phase 3B requirement, not Phase 4 setup work.

Phase 4 is not authorized after this Phase 3B pass because the staged path is
still implemented with legacy runner helpers. A second plugin before Phase 3G
would still be architecture theater.

## Residual risk after Phase 3A

- Staged mode is not the campaign default and is not live-runtime parity
  evidence. The proven default path remains the legacy delegate.
- Staged `auto_wind_phase=after-takeoff` is intentionally blocked because
  the generic stage order applies stimulus before control while the legacy
  after-takeoff path applies wind after AUTO takeoff altitude.
- The staged analyzer delegates to legacy analysis helpers. Under the stricter
  replacement goal, that is a blocker, not an acceptable final boundary.
- `test_suite` is not generic-runtime-ready until staged `wind_matrix` has
  zero-legacy implementation and live SITL/Gazebo proof.

## Phase 2 acceptance review

| Criterion | Result | Evidence |
| --- | --- | --- |
| Generic manifest view exists | PASS | `Manifest.generic_view()` in `core/manifest.py` |
| Legacy manifest view remains available | PASS | `Manifest.legacy_view()` returns `load()` without normalization |
| Generic fields are additive | PASS | `WindMatrixManifest.append_attempt()` updates only generic fields on the matching row |
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
- The generic model is still exercised against wind_matrix only, and Phase 4
  remains blocked until Phase 3G accepts a zero-legacy staged wind system.

## Phase 1 remediation (2026-05-24, post-review)

Initial Phase 1 was marked PASS but a follow-up review flagged four
issues. All were addressed:

| Severity | Issue | Resolution |
| --- | --- | --- |
| High | `LegacyManifest.accepted_count` delegated to `run_one.combo_successes`, which counts `success_square_only` regardless of caller policy. A historical square-only row could silently satisfy acceptance for a new strict full-mission run. Follow-up review also found campaign summaries counted square-only under strict acceptance. | The manifest implementation was made policy-aware via an `accept_square_only` constructor argument (default `False`); in Phase 3C this behavior moved to `WindMatrixManifest`. The `wind_matrix` plugin forwards `WindMatrixConfig.accept_square_only`. Summary generation now uses the same policy. Tests cover strict and lenient counts. |
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
| `test_suite.core._legacy` resolves owned runners | PASS at Phase 1; superseded in Phase 3C | The lazy shim moved to `plugins/wind_matrix/legacy.py` so generic core no longer carries wind-runner imports. |
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

The next planned step is Phase 3C, not Phase 4 and not script deletion. Build
the staged foundation so `attempt_strategy="staged"` can construct and run
no-SITL tests with legacy runner imports blocked. Live proof comes later in
Phase 3G.
