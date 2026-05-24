# Automated Test Suite Blueprint

This document is the blueprint for turning the current legacy runner stack into
a reusable automated test-suite framework for multiple experiment lanes:

- wind / CTE robustness
- GPS failure or degradation
- airspeed failure or degradation
- other future SITL/Gazebo sensor or subsystem campaigns

The intended split is:

- **main framework code** owns lifecycle, bookkeeping, scheduling, artifacts,
  log collection, deadlines, retries, and durable records
- **experiment plugins** own the meaning of the test: the lane being exercised,
  parameter space, stimulus/fault injection, scenario expectations, analyzers,
  and verdict rules

This blueprint is deliberately strict. The current `scripts/test_suite/`
implementation has the right direction, but it is not yet a real plugin
architecture. It is currently a partial wrapper around the legacy scripts.

## Files In Scope

Legacy reference scripts:

- `src/SIM_ARD_GAW/scripts/run_one.py`
- `src/SIM_ARD_GAW/scripts/run_matrix.py`
- `src/SIM_ARD_GAW/scripts/run_matrix_round_robin.py`
- `src/SIM_ARD_GAW/scripts/run_one_og.py`

Current framework scaffold:

- `src/SIM_ARD_GAW/scripts/test_suite/`

The legacy scripts remain the source of truth for current behavior until their
responsibilities are explicitly extracted.

## Executive Reality Check

The current codebase contains the raw ingredients of a reusable framework, but
the framework boundary is not implemented yet.

`run_one.py` is not only a single-attempt runner. It still owns nearly
everything:

- attempt identity
- manifest writes
- campaign summary writes
- attempt directory creation
- run config writing
- wind stimulus application
- MAVLink heartbeat/readiness checks
- mission upload and verification
- arm and AUTO mode control
- mission-progress monitoring
- BIN log collection
- success classification
- analysis execution
- run summary generation
- final manifest update

That is too much for one function if the goal is reusable plugins.

`run_matrix.py` and `run_matrix_round_robin.py` also contain important behavior
that is not just "looping":

- SITL launch details
- Gazebo launch details
- parameter file stack resolution
- generated per-attempt world files
- wind-world modes
- cleanup policy
- isolated SITL state dirs
- BIN snapshot strategy
- round-robin wall-clock budgets
- analysis-required acceptance behavior

Therefore the current `scripts/test_suite/` package should be treated as a
**Phase-1 scaffold**, not as proof that the architecture goal has been reached.

## Current State Of `scripts/test_suite`

The current `scripts/test_suite/` implementation has useful pieces:

- generic data models in `core/models.py`
- lifecycle shell in `core/attempt_runner.py`
- suite loop in `core/suite_runner.py`
- sequential and round-robin scheduler classes
- lazy imports of legacy modules through `core/_legacy.py`
- a `wind_matrix` plugin directory
- CLI entry points for `run_case`, `run_suite`, and `run_round_robin`

But Phase 1 is mostly a wrapper:

- `LegacyDelegateStrategy` calls `run_one.run_one(...)` as one opaque body
- `LegacyManifest.append_attempt()` is intentionally a no-op because
  `run_one` still writes the manifest itself
- the wind plugin does not yet own wind behavior cleanly
- the framework does not yet own attempt bookkeeping cleanly
- the framework does not yet own BIN collection cleanly
- the round-robin deadline exists in the framework scheduler, but is not fully
  propagated through the legacy delegate path

The architecture direction is right. The implementation is not yet close enough
to claim that future GPS, airspeed, or other plugins can be added without
touching legacy wind-specific logic.

## Known Drift Between `test_suite` And Legacy Scripts

The current `test_suite` CLIs and plugin wrapper are out of sync with the
current legacy scripts.

### `run_case` drift from `run_one.py`

Legacy `run_one.py` exposes:

- `--auto-wind-phase`
- `--preloaded-wind-world`
- `--no-preloaded-wind-refresh`

Current `test_suite.cli.run_case` does not expose those flags.

### `run_suite` drift from `run_matrix.py`

Legacy `run_matrix.py` exposes:

- `--auto-wind-phase`
- `--wind-world-mode`
- `--param-base`
- `--param-airspeed`
- `--param-local`
- `--no-param-local`

Current `test_suite.cli.run_suite` does not expose those flags.

It also has different defaults:

- legacy `run_matrix.py`: `max_attempts_per_combo = 20`
- current `test_suite.cli.run_suite`: `max_attempts_per_combo = 12`
- legacy `run_matrix.py`: `stack_settle_s = 3.0`, `retry_delay_s = 2.0`
- current `WindMatrixConfig`: `stack_settle_s = 5.0`, `retry_delay_s = 3.0`

### `run_round_robin` drift from `run_matrix_round_robin.py`

Legacy `run_matrix_round_robin.py` exposes:

- `--slot-minutes`
- `--monitor-minutes`
- `--max-passes`
- `--auto-wind-phase`
- `--wind-world-mode`
- `--require-analysis`
- `--no-wipe-eeprom`
- `--rebuild`
- `--focus-combo`
- parameter stack flags

Current `test_suite.cli.run_round_robin` exposes a simpler
`--per-attempt-budget` surface and omits most of that behavior.

### Plugin delegate drift

The wind plugin delegate currently calls `run_one.run_one(...)` without passing
several newer parameters that matter for parity:

- `preloaded_wind_refresh`
- `auto_wind_phase`
- `require_analysis`
- `before_bin_names`
- `sitl_log_dir`
- `slot_deadline_monotonic`
- `param_file_stack`

This means the wrapper is not a faithful replacement for the current legacy
matrix runners.

## Target Ownership Model

The framework/plugin split must be based on ownership, not on file names.

### Framework Owns Lifecycle And Evidence Handling

The framework should own:

- attempt ID allocation
- target run index allocation
- attempt directory creation
- atomic manifest writes
- manifest repair/reconciliation
- campaign summary writes
- retry accounting
- scheduler policies
- slot deadlines and timeout clamping
- lifecycle ordering
- cleanup guarantees
- standard run configuration snapshot
- standard artifact registry
- raw log collection interface
- final durable attempt record

For ArduPilot SITL campaigns, the framework may also provide reusable helpers
for:

- MAVLink connection setup
- heartbeat wait
- generic mission upload
- generic arm/mode control
- `.BIN` discovery and copying
- SITL/Gazebo process supervision

Those helpers must not encode one experiment's success semantics.

### Plugin Owns Experiment Meaning

Each plugin should own:

- lane name, e.g. `wind_matrix`, `gps_failure`, `airspeed_failure`
- case generation and parameter space
- scenario and mission profile selection
- stimulus or fault injection method
- parameter overlay files required for the lane
- world/model generation when it is lane-specific
- monitor interpretation rules
- mission completion expectations
- analyzer list
- analyzer configuration
- verdict policy
- sensor-specific summary fields

For wind/CTE, that means the wind plugin owns:

- `x_wind_mps` / `y_wind_mps`
- Gazebo wind topic behavior
- preloaded wind SDF behavior
- wind frame notes
- square/loiter waypoint semantics
- CTE/square/loiter analyzers
- `success_full` versus `success_square_only` meaning

For GPS failure, a future plugin should own:

- dropout/degradation parameter space
- GPS fault injection mechanism
- GPS/EKF-specific analyzers
- GPS/EKF verdict thresholds

For airspeed failure, a future plugin should own:

- airspeed sensor fault profile
- pitot/airspeed parameter overlays
- airspeed tracking analyzers
- airspeed health verdict rules

## Required Package Shape

Keep the package where it currently lives unless there is a separate reason to
move it:

```text
src/SIM_ARD_GAW/scripts/test_suite/
  core/
    models.py
    manifest.py
    artifacts.py
    environment.py
    control.py
    monitor.py
    analysis.py
    verdicts.py
    scheduler.py
    suite_runner.py
    attempt_runner.py
    ardupilot_logs.py
    mavlink_control.py
  plugins/
    wind_matrix/
      config.py
      case_generator.py
      environment.py
      stimulus.py
      mission_profile.py
      analyzers.py
      verdicts.py
    gps_failure/
      config.py
      case_generator.py
      stimulus.py
      analyzers.py
      verdicts.py
    airspeed_failure/
      config.py
      case_generator.py
      stimulus.py
      analyzers.py
      verdicts.py
  cli/
    run_case.py
    run_suite.py
    run_round_robin.py
```

Compatibility wrappers can remain at:

- `scripts/run_one.py`
- `scripts/run_matrix.py`
- `scripts/run_matrix_round_robin.py`

But the end state should be that those wrappers call the framework, not the
other way around.

## Core Interfaces

### `TestCase`

Generic representation of one logical case.

Required fields:

- `suite_name`
- `case_id`
- `parameters`
- `scenario_name`
- `stimulus_name`
- `mission_file`
- `acceptance_target_runs`
- `tags`

The framework must treat `parameters` as opaque plugin-owned data.

### `AttemptContext`

Mutable object shared through one attempt.

Required fields:

- `case`
- `campaign_root`
- `attempt_dir`
- `attempt_index`
- `target_run_index`
- `start_wall_s`
- `start_monotonic_s`
- `slot_deadline_monotonic_s`
- `artifacts`
- `process_handles`
- `log_paths`
- `extra`

### `AttemptRecord`

Durable record written by the framework.

Required generic fields:

- `attempt_id`
- `suite_name`
- `case_id`
- `target_run_index`
- `attempt_index`
- `status`
- `verdict`
- `analysis_status`
- `start_time_utc`
- `end_time_utc`
- `duration_wall_s`
- `parameters`
- `stimulus_result`
- `artifacts`
- `notes`

Wind-specific fields may be preserved during migration for backward
compatibility, but new framework code should not depend on top-level
`x_wind_mps` or `y_wind_mps`.

### `CaseGenerator`

```text
iter_cases() -> Iterable[TestCase]
```

Plugin-owned.

### `EnvironmentAdapter`

```text
prepare_case(case)
launch(case, ctx)
assert_ready(case, ctx)
cleanup(case, ctx)
```

Usually plugin-owned, but can reuse framework helpers for SITL/Gazebo process
management.

### `StimulusAdapter`

```text
apply(case, ctx) -> dict
verify(case, ctx) -> dict
```

Plugin-owned.

### `ControlStrategy`

```text
execute(case, ctx)
```

Framework should provide generic manual, auto, and passive strategies. Plugins
may customize prompts, mission choices, or preconditions.

### `CompletionMonitor`

```text
run(case, ctx) -> MonitorResult
```

Shared MAVLink message-reading machinery can be framework-owned. The meaning of
mission progress is plugin-owned through a mission profile or completion
policy.

### `Analyzer`

```text
analyze(case, ctx) -> AnalysisResult
```

Plugin-owned.

### `VerdictPolicy`

```text
classify(case, monitor_result, analysis_results) -> Verdict
```

Plugin-owned.

### `SchedulerPolicy`

```text
initial_pending(cases, manifest) -> list[TestCase]
next_case(pending, manifest) -> SchedulerDecision
```

Framework-owned.

## Correct Attempt Lifecycle

The final framework lifecycle should be:

1. load and reconcile manifest
2. select case through scheduler
3. reserve attempt index and target run index
4. create attempt directory
5. write initial `running` attempt record
6. write generic `run_config.json`
7. ask plugin/environment to prepare and launch
8. verify environment readiness
9. apply plugin stimulus or preconditions
10. execute control strategy
11. monitor completion
12. collect raw evidence, including `.BIN` where applicable
13. run plugin analyzers
14. classify verdict
15. update accepted-run alias if accepted
16. write run summary
17. write final manifest and campaign summary
18. cleanup in `finally`

The current legacy `run_one.run_one()` performs most of these steps internally.
The migration is not complete until the framework owns this ordering.

## What Must Be Extracted From `run_one.py`

### Framework extraction

Move or reimplement as framework-owned:

- manifest load/save/reconcile primitives
- attempt numbering
- alias symlink management
- campaign summary writing
- timeout/deadline helpers
- `.BIN` log collection
- generic run config writer
- generic analysis runner orchestration
- cleanup-on-finally contract

### Shared ArduPilot/SITL helpers

Move to reusable core helpers:

- `wait_for_heartbeat`
- generic readiness checks where not lane-specific
- mission upload
- mission verification
- arm command
- AUTO mode command
- post-arm settle

These helpers should be usable by wind, GPS, and airspeed plugins.

### Wind plugin extraction

Move to `plugins/wind_matrix/`:

- `inject_wind`
- wind echo parsing and verification
- wind info capture
- preloaded wind world validation
- wind-specific run config fields
- square/loiter mission profile constants
- square/loiter completion interpretation
- wind/CTE analyzer selection
- wind/CTE run summary fields
- wind verdict policy

## What Must Be Extracted From `run_matrix.py`

Framework/shared extraction:

- process launch wrapper
- process liveness check
- cleanup call contract
- sequential suite runner behavior
- retry policy

Wind plugin extraction:

- wind combo order
- wind value validation
- generated wind SDF rendering
- `wind_world_mode`

SITL/Gazebo environment extraction:

- `launch_sitl`
- `launch_gazebo`
- parameter stack application
- local param override policy

Parameter stack behavior is important. It must not disappear behind a generic
interface, because airspeed/GPS/failure plugins will likely need their own
overlay stacks.

## What Must Be Extracted From `run_matrix_round_robin.py`

Framework extraction:

- round-robin scheduler
- slot budget model
- max pass handling
- focus-case filtering if kept generically
- deadline propagation into every blocking phase

Wind/current-lane extraction:

- accepted count by wind combo
- wind combo key parsing

Important: round-robin is not correct unless the slot deadline reaches the
attempt body. A scheduler that computes a deadline but does not pass it into
heartbeat/upload/monitor/analysis is only cosmetic.

## Migration Phases

### Phase 0. Document and freeze current behavior

Before moving logic, document the current legacy behavior and parity surface.

Required outputs:

- exact legacy CLI flag table
- exact manifest schema table
- exact artifact tree description
- exact status/analysis-status meanings
- exact matrix and round-robin acceptance rules

No behavior change should be made in this phase.

### Phase 1. Correct wrapper parity

Goal: make `scripts/test_suite` a faithful wrapper before extraction.

Required fixes:

- expose all current legacy CLI flags in `run_case`
- expose all current `run_matrix.py` flags in `run_suite`
- expose all current `run_matrix_round_robin.py` flags in `run_round_robin`
- align defaults with legacy scripts
- pass all relevant `run_one.run_one()` parameters through the wind plugin
- propagate `slot_deadline_monotonic`
- propagate `before_bin_names` and `sitl_log_dir`
- propagate param file stacks
- propagate `require_analysis`
- support current `wind_world_mode`

Acceptance gate:

- for a small wind campaign, legacy CLI and `test_suite` CLI produce equivalent
  manifest behavior and artifact layout, allowing only timestamp/PID/log-order
  differences

Phase 1 still uses `run_one.run_one(...)` as a delegate. That is acceptable
only as a temporary compatibility stage.

### Phase 2. Move bookkeeping into the framework

Goal: stop relying on `run_one` to write attempts.

Required changes:

- framework creates attempt dirs
- framework appends initial `running` attempt records
- framework writes final terminal attempt records
- framework owns campaign summary writes
- framework owns accepted-run alias handling
- legacy wind fields remain additive for compatibility

Acceptance gate:

- `LegacyManifest.append_attempt()` is no longer a no-op
- `run_one` compatibility wrapper no longer directly owns manifest writes

### Phase 3. Split `run_one` attempt body into stages

Goal: replace `LegacyDelegateStrategy` with real staged execution.

Required extractions:

- wind stimulus adapter
- generic/manual/auto control strategies
- completion monitor with plugin mission profile
- raw evidence collector
- analyzer chain
- verdict policy

Acceptance gate:

- `wind_matrix` plugin no longer calls `run_one.run_one(...)`
- `run_one.py` becomes a thin compatibility wrapper around `test_suite`

### Phase 4. Prove the boundary with a second plugin

Goal: add one non-wind plugin without changing core lifecycle code.

Good candidates:

- GPS failure/degradation
- airspeed failure/degradation
- no-stimulus airspeed validation bench

Acceptance gate:

- second plugin has its own case generator, stimulus/analyzers/verdicts
- no wind-specific imports are needed outside `plugins/wind_matrix`
- no core lifecycle changes are required for ordinary plugin behavior

### Phase 5. Retire legacy implementation ownership

Goal: keep old entry points but remove old ownership.

Required changes:

- `run_one.py` calls `test_suite.cli.run_case`
- `run_matrix.py` calls `test_suite.cli.run_suite`
- `run_matrix_round_robin.py` calls `test_suite.cli.run_round_robin`
- old internal helper code is deleted or moved to framework/plugin modules

Acceptance gate:

- users can keep old commands
- implementation lives in framework and plugins

## Validation Requirements

### Static validation

- import all CLIs
- run all `--help` surfaces
- compare legacy and new CLI flags
- run focused unit tests for scheduler, manifest, artifact path generation, and
  verdict mapping

### No-SITL parity validation

- test manifest reconciliation on fixture manifests
- test attempt numbering on fixture artifact trees
- test generated wind world rendering
- test BIN selection logic with fixture directories
- test deadline clamping with fake monotonic clocks

### SITL parity validation

Run only after static/no-SITL checks pass:

- one manual wind case
- one automated wind case
- one sequential mini-matrix
- one round-robin mini-matrix
- one analysis-required retry scenario

For each, compare:

- manifest status transitions
- accepted count
- attempt directory layout
- run alias behavior
- `run_config.json`
- `wind_injection.json`
- copied `.BIN`
- analyzer outputs
- `run_summary.json`

## Design Rules

### Rule 1. Core must not know wind dimensions

No framework module should assume:

- `x_wind`
- `y_wind`
- known wind values
- wind combo key format
- square/loiter waypoint ranges

Those belong to the wind plugin.

### Rule 2. Core must own durable bookkeeping

If a plugin can bypass manifest writes, attempt numbering, or final status
updates, the architecture is not reusable.

### Rule 3. Plugins own meaning, not lifecycle

Plugins may decide what a failure means. They should not reimplement:

- attempt loops
- scheduler loops
- atomic manifest writes
- retry accounting
- cleanup guarantees

### Rule 4. Deadlines must be enforced inside blocking phases

Round-robin only matters if every long-running phase obeys the slot:

- heartbeat
- readiness
- upload
- verification
- arm
- mode switch
- monitor
- log flush
- analysis

### Rule 5. Raw evidence must survive failed verdicts

A failed, timed-out, or analysis-failed attempt should still preserve all
available raw evidence and logs.

### Rule 6. Backward compatibility is a gate, not a slogan

If a new CLI claims to mirror a legacy CLI, it must expose the same current
flags or explicitly document unsupported differences.

## Suggested Deliverables

1. Legacy behavior reference table.
2. CLI parity tests.
3. Manifest/artifact fixture tests.
4. Correct Phase-1 wrapper parity.
5. Framework-owned manifest and artifact layer.
6. Extracted wind plugin stages.
7. One second plugin proving generality.
8. Thin compatibility wrappers for old commands.

## Bottom Line

The plan behind `scripts/test_suite` is the right direction, but the current
implementation does not yet achieve the stated goal.

It is close only at the interface-sketch level. The hard ownership split has
not happened yet.

The next approved work should be judged by this question:

**Does this change move ownership out of `run_one` and into either the generic
framework or the correct experiment plugin?**

If the answer is no, the change may improve the scripts, but it does not
advance the reusable automated test-suite architecture.

## Reusable Implementation Prompt

Use this prompt for another AI agent or implementation pass:

```text
Read and preserve current behavior from:

- src/SIM_ARD_GAW/scripts/run_one.py
- src/SIM_ARD_GAW/scripts/run_matrix.py
- src/SIM_ARD_GAW/scripts/run_matrix_round_robin.py
- src/SIM_ARD_GAW/scripts/run_one_og.py
- src/SIM_ARD_GAW/scripts/test_suite/

Goal:
Turn the legacy wind/CTE runner stack into a reusable automated test-suite
framework where core owns lifecycle/bookkeeping/artifacts/scheduling and
plugins own experiment meaning.

Be strict:
- Do not claim plugin architecture is complete while run_one.run_one remains
  the opaque attempt body.
- First make test_suite wrappers exactly match current legacy behavior.
- Then move manifest, artifact, BIN collection, config writing, deadlines, and
  scheduler behavior into core.
- Move wind stimulus, wind world modes, square/loiter semantics, CTE analyzers,
  and wind verdicts into plugins/wind_matrix.
- Keep legacy CLIs usable as compatibility wrappers.
- Add a second plugin, such as GPS failure or airspeed failure, to prove the
  boundary.

Output:
- exact ownership map
- migration phases with acceptance gates
- files/functions to move
- CLI parity checklist
- manifest/artifact parity checklist
- risks and validation steps
```
