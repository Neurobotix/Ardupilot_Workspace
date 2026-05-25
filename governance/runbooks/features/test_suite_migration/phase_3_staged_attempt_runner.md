# Phase 3 - Staged Attempt Runner

Scope: feature-level Phase 3 of the `test_suite` migration. This is the
"Stage 3 - split run_one into plugin pieces" phase from
`src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`.

## Objective

Split the wind-matrix attempt lifecycle into framework/plugin-owned stages
without cutting over the campaign default. The legacy delegate remains the
default strategy until a live SITL/Gazebo parity run proves the staged path is
runtime-equivalent for the campaign scope being claimed.

## Extraction Map

| Legacy function/block | New owner | Reason | Test coverage | Risk |
| --- | --- | --- | --- | --- |
| `run_one.inject_wind`, `preloaded_wind_artifact`, wind echo parsing/capture | `plugins/wind_matrix/stimulus.py` via `WindMatrixStimulus` | Wind is plugin-specific stimulus, not framework lifecycle. | `test_wind_plugin_can_build_staged_strategy_without_compat_wrappers`; compile/import coverage. | Runtime topic echo behavior still delegates to legacy helpers; live parity not yet proven. |
| Mission upload, mission verification, arm, settle, AUTO mode | `core/control.py` via `MavlinkAutoMissionControl` with injected MAVLink helpers | Mission control is a reusable lifecycle stage while helper functions remain injectable. | Staged order tests exercise control call placement. | The staged opt-in does not yet support `auto_wind_phase=after-takeoff`; legacy remains default. |
| Manual operator prompt | `core/control.py` via `ManualMissionControl` | Manual runs are a control strategy with no MAVLink commands. | Staged build test covers manual staged assembly. | Operator-facing text is preserved in shape, but live manual staged parity is not claimed. |
| Heartbeat and vehicle readiness | `plugins/wind_matrix/environment.py` for staged mode | Readiness must happen after launch and before stimulus/control. | Compile/import coverage; staged strategy build test. | Uses legacy readiness helpers; no live staged run yet. |
| `monitor_until_disarm` | `core/monitor.py` via `DisarmCompletionMonitor` | Completion monitoring is a framework stage with plugin thresholds. | Staged order test verifies monitor position. | Uses legacy monitor helper; live timeout/disarm behavior not re-proven. |
| BIN finalization, BIN collection, `run_analysis`, `build_run_summary`, wind success classification | `plugins/wind_matrix/analyzers.py` via `WindMatrixAnalyzer` and `WindMatrixVerdictPolicy` | Analysis and wind verdict semantics are plugin-owned. | Cleanup/flush ordering, partial verdict, non-accepted failure statuses, and staged manifest tests. | Analyzer still delegates to legacy helpers; heavy analysis is not unit-executed. |
| Generic staged orchestration | `core/attempt_runner.py` `StagedStrategy` | Framework owns stage ordering and cleanup in `finally`. | `test_staged_strategy_calls_stages_in_expected_order`; cleanup success/failure/interrupt tests. | Strategy order is generic; wind after-takeoff remains blocked in staged mode. |
| Legacy manifest additive writes | `core/manifest.py` `LegacyManifest.append_attempt()` | Generic fields remain additive; plugin legacy fields can be appended for new staged rows. | Phase 2 generic tests plus Phase 3 plugin-manifest tests. | Direct legacy scripts still write legacy-only rows by design. |
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
  strict accepted run unless `accept_square_only=True`.
- `failed`, `error`, `interrupted`, and `failed_analysis` do not count as
  accepted.
- `LegacyManifest.generic_view()` remains backward-compatible with historical
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

## Out Of Scope

- Making staged mode the default runtime path.
- Live SITL/Gazebo parity claims for staged mode.
- Supporting staged `auto_wind_phase=after-takeoff`.
- Creating a second plugin.
- Retiring or deleting legacy wrappers.
- Changing accepted/partial/fail manifest semantics.

## Rollback Plan

Set or leave `--attempt-strategy legacy` and the runtime path returns to the
Phase 2 behavior. To remove the staged opt-in, revert the Phase 3 adapter
files and the `attempt_strategy` wiring while keeping Phase 2 generic manifest
support intact. No historical manifests require migration for rollback because
the new fields are additive and old rows remain readable.
