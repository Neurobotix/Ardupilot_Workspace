# Phase 3A - Staged Attempt Runner

Scope: feature-level Phase 3A of the `test_suite` migration. This is the
first half of the old "Stage 3 - split run_one into plugin pieces" phase from
`src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`.

Status as of 2026-06-01: Phase 3A is complete as an opt-in staged
implementation. Phase 3B proves the staged wind lifecycle is not hidden behind
`run_one.run_one(...)`, but it also records that staged mode still depends on
legacy runner helper code. Phase 3C is complete for staged foundation only:
config/defaults, case generation, plugin-owned wind manifest/monitor
foundation, plugin construction, and CLI parser/bootstrap no longer import
legacy runner modules. Generic `core/manifest.py` and `core/monitor.py` no
longer carry wind-matrix fallback behavior. Phase 3D is complete: environment
launch/cleanup are plugin-owned via `runtime.py`. Phase 3E is complete: staged
`assert_ready`, `WindMatrixAutoMissionControl`, and `WindMatrixDisarmMonitor`
now call plugin-owned `mavlink_control.*` only. Phase 3F is complete: staged
wind injection is plugin-owned in `wind_injection.py` and `stimulus.py` no
longer imports `legacy`, so the staged attempt path is now fully zero-legacy.
A first live completed staged run (`success_full`, strict gz echo verified) was
captured. Phase 3G is still required: a matched live legacy comparison run
beside the staged live run. Phase 4 remains blocked until Phase 3G.

## Objective

Split the wind-matrix attempt lifecycle into framework/plugin-owned stages
without cutting over the campaign default. The legacy delegate remains the
default strategy until a live SITL/Gazebo parity run proves the staged path is
runtime-equivalent for the campaign scope being claimed.

Because the legacy path is wind-specific, this phase cannot authorize a second
plugin proof by itself. `test_suite` is not generic until `wind_matrix` is a
real staged plugin with evidence, or until any retained legacy wind pieces are
explicitly isolated and evidence-backed.

## Extraction Map

| Legacy function/block | New owner | Reason | Test coverage | Risk |
| --- | --- | --- | --- | --- |
| `run_one.inject_wind`, `preloaded_wind_artifact`, wind echo parsing/capture | `plugins/wind_matrix/stimulus.py` via `WindMatrixStimulus` | Wind is plugin-specific stimulus, not framework lifecycle. | `test_wind_plugin_can_build_staged_strategy_without_compat_wrappers`; compile/import coverage. | Runtime topic echo behavior still delegates to legacy helpers; live parity not yet proven. |
| Mission upload, mission verification, arm, settle, AUTO mode | `core/control.py` via `MavlinkAutoMissionControl` with injected MAVLink helpers | Mission control is a reusable lifecycle stage while helper functions remain injectable. | Staged order tests exercise control call placement. | The staged opt-in does not yet support `auto_wind_phase=after-takeoff`; legacy remains default. |
| Manual operator prompt | `core/control.py` via `ManualMissionControl` | Manual runs are a control strategy with no MAVLink commands. | Staged build test covers manual staged assembly. | Operator-facing text is preserved in shape, but live manual staged parity is not claimed. |
| Heartbeat and vehicle readiness | `plugins/wind_matrix/environment.py` for staged mode | Readiness must happen after launch and before stimulus/control. | Compile/import coverage; staged strategy build test. | Uses legacy readiness helpers; no live staged run yet. |
| `monitor_until_disarm` | `plugins/wind_matrix/monitor.py` via `WindMatrixDisarmCompletionMonitor` | Wind/square mission completion is plugin-specific monitor behavior. | Staged order test verifies monitor position. | Uses legacy monitor helper when executed; live timeout/disarm behavior not re-proven. |
| BIN finalization, BIN collection, `run_analysis`, `build_run_summary`, wind success classification | `plugins/wind_matrix/analyzers.py` via `WindMatrixAnalyzer` and `WindMatrixVerdictPolicy` | Analysis and wind verdict semantics are plugin-owned. | Cleanup/flush ordering, partial verdict, non-accepted failure statuses, and staged manifest tests. | Analyzer still delegates to legacy helpers; heavy analysis is not unit-executed. |
| Generic staged orchestration | `core/attempt_runner.py` `StagedStrategy` | Framework owns stage ordering and cleanup in `finally`. | `test_staged_strategy_calls_stages_in_expected_order`; cleanup success/failure/interrupt tests. | Strategy order is generic; wind after-takeoff remains blocked in staged mode. |
| Legacy manifest additive writes | `plugins/wind_matrix/manifest.py` `WindMatrixManifest.append_attempt()` | Generic fields remain additive; plugin legacy fields can be appended for new staged rows. | Phase 2 generic tests plus Phase 3 plugin-manifest tests. | Direct legacy scripts still write legacy-only rows by design. |
| `run_one.run_one(...)` full body | Retained in `campaigns/wind_matrix/run_one.py`; used by `LegacyDelegateStrategy` | Proven compatibility fallback and default runtime path. | `test_legacy_delegate_path_remains_available`; Phase 1 parity tests. | Full staged cutover is intentionally deferred. |

## Runtime Behavior Preservation Contract

- `run_one.py` remains callable and is not deleted.
- `WindMatrixConfig.attempt_strategy` defaults to `legacy`.
- CLI paths accept `--attempt-strategy {legacy,staged}`. Existing invocations
  keep legacy delegate behavior unless they explicitly opt into `staged`.
- The staged path uses existing legacy helper functions for MAVLink protocol,
  wind echo verification, monitor state, BIN selection, analysis scripts, and
  summary building. This reduces behavior drift while creating stage owners.
- `auto_wind_phase=after-takeoff` is blocked during staged plugin
  construction. Use the legacy delegate for that mode until the wind
  stimulus/control ordering is split safely and proven with live evidence.

## Completion Status

Phase 3A is accepted for:

- opt-in staged runner construction;
- explicit stage ordering;
- cleanup in `finally`;
- manifest additivity and legacy field compatibility;
- verdict/acceptance safety;
- CLI flag/help coverage;
- retention of the default legacy delegate fallback.

Phase 3A remains blocked for:

- default staged runtime cutover;
- live staged SITL/Gazebo wind parity;
- staged `auto_wind_phase=after-takeoff`;
- any claim that `test_suite` is generic;
- any Phase 4 second-plugin work.

## Cleanup Contract

`AttemptRunner.run()` still wraps every strategy in `finally` and calls
`EnvironmentAdapter.cleanup(case, ctx)` on success, ordinary exceptions, and
interrupt-like `BaseException` paths. `WindMatrixEnvironment.cleanup()` still
calls the legacy `run_matrix.cleanup_stack()` kill path when it owns the
launched stack and then closes retained process handles.

## Manifest Compatibility Contract

- Existing wind manifest fields are not renamed or removed.
- Existing rows are updated only with additive generic fields.
- New staged rows can include plugin-owned legacy wind fields plus the Phase 2
  generic fields in the same row.
- `success_square_only` remains generic `partial` and does not count as a
  strict accepted run unless `accept_square_only=True` (post-legacy stricter
  safety policy). Running the new suite/round-robin logic over an old
  campaign root can therefore retry and renumber runs that legacy would have
  accepted via square-only success.
- `failed`, `error`, `interrupted`, and `failed_analysis` do not count as
  accepted.
- `WindMatrixManifest.generic_view()` remains backward-compatible with historical
  manifests that do not contain generic fields.

## Validation Plan

- Focused Phase 3 unit test:
  `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py`
- Phase 2 focused unit test:
  `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py`
- CLI help smoke for both owned and compatibility module paths.
- Required workspace checks:
  - `git status --short`
  - `git diff --stat`
  - `git diff --check`
  - `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests`
  - `env/bin/python3 -m unittest discover -s tests/unit`
  - `env/bin/python3 -m unittest discover -s tests/integration`
  - `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`
  - `make test-parity`
  - `make doctor`

## Acceptance Criteria

- Staged strategy calls stages in the expected order.
- Cleanup runs on success, failure, and interrupt-like errors.
- Square-loiter early completion runs the legacy analysis cleanup path before
  BIN flush wait and collection.
- BIN collection failure writes a legacy-compatible terminal manifest row.
- Stimulus, control, and monitor exceptions before analyzer completion write
  legacy-compatible terminal manifest rows.
- Unsupported staged `auto_wind_phase=after-takeoff` fails before environment
  launch.
- Partial verdicts remain partial.
- Failed/error/interrupted attempts do not count as accepted.
- Generic manifest fields remain additive.
- Legacy wind manifest fields round-trip unchanged.
- Wind plugin can build a staged strategy.
- Legacy delegate path remains available and default.
- CLI help paths still work.
- No implementation logic lands in `compat_scripts/`.
- Phase 4 second plugin and Phase 5 wrapper retirement are not implemented.

## Phase 3B Audit Result

Phase 3B no-SITL proof is recorded in
`evidence/reports/features/2026-05-29_test_suite_migration_phase_3b.md`.
It adds:

- `test_staged_orchestration_shell_does_not_call_legacy_run_one_body` and
  `test_real_staged_wind_adapters_run_with_boundary_mocks`;
- verdict/acceptance coverage for full, partial, failed, error, interrupted,
  and analysis-failure statuses;
- CLI default/staged/fail-closed tests;
- analysis-failure persistence proof.

The retained legacy helper audit is now treated as a blocker list for the
replacement system:

| Helper | Phase 3B classification |
| --- | --- |
| `run_one.run_one(...)` | Removed from the staged lifecycle; retained only by the default legacy strategy. |
| `run_one.inject_wind`, `preloaded_wind_artifact`, wind echo helpers | Retained as plugin-owned stimulus helpers behind `WindMatrixStimulus`. |
| `run_one.wait_for_heartbeat`, `wait_for_vehicle_ready` | Retained as staged environment readiness helpers behind `WindMatrixEnvironment`. |
| `run_one.upload_mission`, `verify_mission`, `arm_vehicle`, `set_auto_mode`, timeout helpers | Retained as injected MAVLink helpers behind `MavlinkAutoMissionControl`. |
| `run_one.monitor_until_disarm` | Retained as an injected monitor helper behind `WindMatrixDisarmCompletionMonitor`. |
| `run_one.collect_bin_log`, `cleanup_stack_for_analysis`, `run_analysis`, `build_run_summary` | Retained as plugin-owned analyzer helpers behind `WindMatrixAnalyzer`. |
| `run_matrix.launch_sitl`, `launch_gazebo`, `cleanup_stack` | Retained as environment launch/cleanup helpers behind `WindMatrixEnvironment`. |

These retained calls are not the final architecture. They remain wind-specific
legacy runner dependencies behind explicit staged boundaries and must be
removed from staged mode before replacement readiness.

Additional Phase 3B self-review blockers:

- staged plugin construction still builds a legacy delegate closure;
- `WindMatrixConfig` defaults still import legacy runner modules;
- `WindMatrixCaseGenerator` still imports legacy for combo keys;
- generic `core.LegacyManifest` still imports wind legacy (resolved in Phase
  3C by moving wind-compatible manifest behavior to
  `plugins/wind_matrix/manifest.py`);
- CLI bootstrap still imports legacy for defaults, manifest setup, validation,
  and logging.

The live staged wind gate is blocked. Attempts under
`var/runs/test_suite_phase3b_staged_live_20260529/` and
`var/runs/test_suite_phase3b_staged_live_20260529_no_wipe/` failed during SITL
launch before heartbeat with `SIM_VEHICLE: MAVProxy exited`. The manifest has
no accepted staged attempt. Phase 3B live proof is not accepted.

The complete Phase 3B gate requires:

- stage-order tests that exercise real staged adapters with boundary mocks,
  plus the orchestration-shell order test;
- cleanup tests on success, failure, and interrupt-like paths;
- verdict and acceptance tests for full, partial, failed, error, interrupted,
  and analysis-failure outcomes;
- manifest compatibility tests for additive generic fields and unchanged
  legacy wind fields;
- CLI tests proving the legacy default remains available and the staged path
  is explicitly selectable;
- review confirmation that `wind_matrix` no longer hides wind-specific
  lifecycle delegation through `run_one.run_one(...)`;
- complete inventory of retained legacy runner helper dependencies, recorded
  as blockers for Phase 3C-3G;
- any live staged wind result or blocker recorded without claiming replacement
  readiness.

## Phase 3C-3G Completion Gate — ALL ACCEPTED (2026-06-01); Phase 4 unblocked

Phase 4 was blocked until all of these were accepted. As of 2026-06-01 all are
accepted and **Phase 4 is authorized**:

- **Phase 3C:** staged construction, defaults, paths, case generation,
  manifest, and CLI bootstrap are test-suite-owned and work with legacy runner
  imports blocked. Accepted on 2026-05-29 as no-SITL foundation proof only:
  `evidence/reports/features/2026-05-29_test_suite_migration_phase_3c.md`.
- **Phase 3D:** staged environment/runtime launch, world writing, cleanup,
  diagnostics, and timeouts are test-suite-owned. Accepted on 2026-05-31:
  `evidence/reports/features/2026-05-31_test_suite_migration_phase_3d.md`.
- **Phase 3E:** staged MAVLink readiness/control/monitor implementation is
  test-suite-owned. Accepted on 2026-06-01 as no-SITL control/monitor
  ownership proof only:
  `evidence/reports/features/2026-06-01_test_suite_migration_phase_3e.md`.
- **Phase 3F:** staged wind injection is test-suite-owned in
  `wind_injection.py`; `stimulus.py` no longer imports `legacy`, so the staged
  path is fully zero-legacy. A first live completed staged run was captured.
  Accepted on 2026-06-01:
  `evidence/reports/features/2026-06-01_test_suite_migration_phase_3f.md`
  (BIN/artifact/analysis/summary substage was already plugin-owned via
  `analysis_helpers.py` since the 2026-05-31 follow-up).
- **Phase 3G:** the full zero-legacy staged wind system passes no-SITL hard
  tests, completed a bounded live staged wind case, and was compared against a
  matching live legacy case run through the legacy tool directly
  (`compat_scripts/run_matrix.py` → `run_one.run_one`, no `test_suite` code).
  Both `success_full`; metrics within SITL noise; schema/shared-field parity.
  Accepted on 2026-06-01:
  `evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md`.

With Phase 3G accepted, the first plugin (`wind_matrix`) is a full zero-legacy
staged system proven live, so a second plugin is no longer architecture theater:
Phase 4 may now add one non-wind plugin with zero framework-core edits.

## Out Of Scope

- Making staged mode the default runtime path.
- Live SITL/Gazebo parity claims for staged mode.
- Supporting staged `auto_wind_phase=after-takeoff`.
- Creating a second plugin.
- Retiring or deleting legacy wrappers.
- Changing accepted/partial/fail manifest semantics.
- Claiming generic framework readiness.

## Residual Risk

- `test_suite` is not generic until `wind_matrix` is a zero-legacy staged
  plugin with live evidence.
- The current staged path still relies on wind-specific legacy helpers for
  construction, defaults, manifesting, launch, protocol behavior, wind echo
  handling, monitoring, BIN selection, and heavy analysis. Under the stricter
  replacement goal, this is a blocker, not an acceptable final boundary.
- The default runtime path remains the legacy delegate. That is the correct
  fallback, but it is not proof of generic framework readiness.

## Rollback Plan

Set or leave `--attempt-strategy legacy` and the runtime path returns to the
Phase 2 behavior. To remove the staged opt-in, revert the Phase 3 adapter
files and the `attempt_strategy` wiring while keeping Phase 2 generic manifest
support intact. No historical manifests require migration for rollback because
the new fields are additive and old rows remain readable.
