# Automated Test Suite — Architecture

This lane is the compatibility implementation of the automated test-suite
blueprint. Its active migration state is governed by
`governance/runbooks/migration/phase_5_campaign_test_migration.md`. The
feature-level migration plan and per-phase notes live under
`governance/runbooks/features/test_suite_migration/`; the
ArchitectureMD "Stage" labels below map onto the feature phases there
(`Stage 1` ↔ feature Phase 1, ..., `Stage 5` ↔ feature Phase 5).

It sits **alongside** the legacy runners. Phase 5 hardens shared campaign
behavior in `run_one.py`, `run_matrix.py`, `run_matrix_round_robin.py`, and the
wrapper CLIs without cutting over or retiring those compatibility entrypoints.
New CLI entry points (`test_suite/cli/*.py`) build a plugin and feed it through
the framework.

## Layered model

```
┌─────────────────────────────────────────────────────────────┐
│ Campaign config layer — argparse / YAML / env vars          │
│   (which mission, which cases, how many runs, scheduler)    │
├─────────────────────────────────────────────────────────────┤
│ Plugin layer — knows the sensor/test family                 │
│   plugins/wind_matrix/, plugins/<future_sensor>/            │
│   - case generator                                          │
│   - environment adapter                                     │
│   - stimulus adapter                                        │
│   - analyzers + verdict policy                              │
├─────────────────────────────────────────────────────────────┤
│ Framework layer — sensor-agnostic                           │
│   core/                                                     │
│   - lifecycle (AttemptRunner, SuiteRunner)                  │
│   - manifesting + artifacts                                 │
│   - scheduling policies                                     │
│   - control strategies (manual / auto / passive)            │
└─────────────────────────────────────────────────────────────┘
```

The core never imports from `plugins/`. Plugins never reach into other
plugins. The CLI binds a plugin to the core for a given run.

## Lifecycle (per attempt)

`AttemptRunner.run(case)` walks these stages in order; each stage is a
plugin-overridable adapter:

1. `EnvironmentAdapter.prepare_case(case)` — per-case scaffolding
2. `EnvironmentAdapter.launch(case, ctx)` — bring up sim/SITL/etc.
3. `EnvironmentAdapter.assert_ready(case, ctx)` — process supervision
4. `StimulusAdapter.apply(case, ctx)` — inject the test condition
5. `StimulusAdapter.verify(case, ctx)` — confirm it took effect
6. `ControlStrategy.execute(case, ctx)` — drive the subject
   (manual prompts / auto upload+arm+mode / passive observe)
7. `CompletionMonitor.run(case, ctx)` — block until done; capture log
8. `ArtifactStore.collect(case, ctx)` — pull raw evidence into attempt dir
9. `AnalyzerChain.analyze(case, ctx)` — run analyzers, collect outputs
10. `VerdictPolicy.classify(case, monitor, analyses)` — pass/partial/fail
11. `Manifest.persist(attempt_record)` — atomic manifest update
12. `EnvironmentAdapter.cleanup(case, ctx)` — always runs in `finally`

`SuiteRunner` loops over a `SchedulerPolicy` (sequential, round-robin, etc.),
calling `AttemptRunner` for each chosen case until acceptance counts are met
or budgets are exhausted.

## Generic vs. plugin-owned

| Concern                           | Owner    |
|-----------------------------------|----------|
| Attempt id / numbering            | core     |
| Manifest read/write/atomicity     | core     |
| Artifact directory layout         | core     |
| Slot deadlines / retry counting   | core     |
| Process supervision plumbing      | core     |
| Control-mode plumbing             | core     |
| Scheduler policies                | core     |
| Case enumeration                  | plugin   |
| Scenario / mission selection      | plugin   |
| Stimulus injection mechanics      | plugin   |
| Environment launch commands       | plugin   |
| Analyzer scripts and parsing      | plugin   |
| Verdict thresholds                | plugin   |
| Case-specific summary fields      | plugin   |

If a new sensor needs framework edits to ship, the abstractions are leaking.

## Phase-1 wind_matrix plugin

Phase 1 targets wrapper parity with the legacy wind runners. The wind_matrix
adapters are thin wrappers that delegate into the legacy modules:

| Adapter                          | Delegates to                           |
|----------------------------------|----------------------------------------|
| `WindMatrixCaseGenerator`        | `run_matrix.combo_order` + manifest    |
| `WindMatrixEnvironment.launch`   | `run_matrix.launch_sitl` + `launch_gazebo` |
| `WindMatrixEnvironment.cleanup`  | `run_matrix.cleanup_stack`             |
| `WindMatrixStimulus.apply`       | preloaded world via `run_matrix.write_static_wind_world` (auto) or `run_one.inject_wind` (manual) |
| `AutoControl` / `ManualControl`  | branches inside `run_one.run_one`      |
| `WindMatrixMonitor`              | `run_one.monitor_until_disarm`         |
| `WindMatrixAnalyzers`            | `run_one.run_analysis`                 |
| `WindMatrixVerdict`              | success classes from `run_one.run_one` |
| `LegacyManifest`                 | `run_one.load_manifest` / `save_manifest`, plus additive generic view fields |

For Phase 1 the wind plugin uses a `LegacyDelegateAttemptStrategy` that calls
`run_one.run_one(...)` as the single body of stages 4–10. The intent is to keep
legacy behavior, manifest schema, and artifact layout unchanged while the new
entry points exercise the framework boundary. Live SITL/Gazebo parity still
needs to be validated with the checks below before this is treated as
runtime-proven.

## Blueprint Refactor Stages

These stage labels predate the workspace governance phase numbering. Governance
Phase 5 retained the compatibility runners; it did not execute the legacy-script
retirement stage below.

### Stage 1 — wrap
- Introduce `core/` interfaces and `SuiteRunner` / `AttemptRunner` shells.
- Implement `wind_matrix` plugin as wrappers around legacy functions.
- Add new CLI entry points that go through the framework while keeping the
  legacy `run_one.py` / `run_matrix.py` / `run_matrix_round_robin.py` CLIs
  fully functional.
- No changes to manifest schema or artifact layout.

### Stage 2 — generic data model
- Add framework-level `case_id`, `suite_name`, `parameters`,
  `stimulus_result`, `analysis_results`, `verdict`, `artifacts`,
  `attempt_id`, `started_at`, `finished_at`, and `schema_version` fields
  written **alongside** the existing wind-specific fields (additive, not
  breaking).
- Provide a manifest reader that exposes both views.

Implemented in feature Phase 2 on 2026-05-25. The generic view schema marker
is `test_suite.generic_manifest.v1`; `Manifest.legacy_view()` returns the
legacy/plugin shape and `Manifest.generic_view()` normalizes old and new rows
without mutating older manifests.

### Stage 3 — split run_one into plugin pieces
- Extract from `run_one.py`:
  - `inject_wind`, `preloaded_wind_artifact`, `parse_wind_echo`,
    `start_wind_echo` → `plugins/wind_matrix/stimulus.py`
  - `run_analysis`, `build_run_summary` (wind/CTE-tailored bits)
    → `plugins/wind_matrix/analyzers.py`
  - mission upload/arm/mode logic → `core/control.py`
  - `monitor_until_disarm` → `core/monitor.py` (waypoint-range knob is
    plugin config)
  - manifest helpers → `core/manifest.py`
- Add a real framework-driven staged path in `AttemptRunner.run` that calls
  each stage adapter. As of feature Phase 3 on 2026-05-25 this path is
  available only with `--attempt-strategy staged`; `legacy` remains the
  default until live SITL/Gazebo parity evidence exists. Staged
  `auto_wind_phase=after-takeoff` is blocked because the legacy behavior
  applies wind after AUTO takeoff altitude while the generic staged order
  applies stimulus before control.

### Stage 4 — second plugin (proof of generality)
- Stand up a second non-wind plugin (suggested: a no-stimulus airspeed
  validation bench, or a GPS dropout injector).
- If it requires editing `core/`, the boundaries are still wrong.

### Stage 5 — retire legacy scripts
- Once the two plugins are stable, the legacy `run_one.py` etc. become
  thin wrappers that import and call `test_suite/cli/*.py`. Eventually
  they can be removed.

## CLI compatibility

The new CLI entry points accept the legacy argparse flags so existing
scripted callers (`launch.sh` recipes, ops runbooks, README examples)
keep working when the entry point is swapped in:

| Legacy                           | New                                  |
|----------------------------------|--------------------------------------|
| `python run_one.py --x ... --y ... --rep ...` | `python -m test_suite.cli.run_case --x ... --y ...` |
| `python run_matrix.py --x-values ... --y-values ...` | `python -m test_suite.cli.run_suite --x-values ... --y-values ...` |
| `python run_matrix_round_robin.py ...`        | `python -m test_suite.cli.run_round_robin ...`      |

During Phase 1 these new entry points exist in addition to the legacy
ones, not in place of them.

Feature Phase 3 added `--attempt-strategy {legacy,staged}` to the new
`test_suite.cli.*` entry points. The default is `legacy`; `staged` is an
explicit opt-in for the extracted wind-matrix stage adapters.

## Risks

- **Hidden coupling in `run_one.run_one`.** The 400-line function has
  intricate ordering between stack-readiness, wind injection, mission
  upload, arm, monitor, and cleanup. Splitting it prematurely (Phase 3
  before the wrapper layer is well-exercised) risks regressions. Phase 1
  intentionally avoids touching it.
- **Manifest schema drift.** Adding generic fields in Phase 2 must be
  additive. Any rename of an existing field invalidates campaign log
  history for fixed-harness comparator datasets such as
  `logs/017_params_old_009_matrix_r3_plugin_fixed/`.
- **Process leaks across attempts.** The legacy `cleanup_stack()` is the
  authoritative kill path. The framework must never short-circuit it; the
  `finally` block in `AttemptRunner.run` is the contract.
- **Round-robin starvation.** The legacy round-robin uses bounded slot
  deadlines (`remaining_deadline_s`, `clamp_timeout_to_slot`). The
  scheduler policy must propagate these into `AttemptContext`, not each
  plugin.
- **Plugin discovery.** Phase 1 hard-wires the wind_matrix plugin in the
  CLI. Phase 4 should introduce a plugin registry (entry points or a
  simple `plugins/__init__.py` mapping). Premature dynamic discovery is
  out of scope.
- **Path assumptions.** Plugins must not hard-code workspace-relative
  paths inside the framework layer. All paths flow through plugin config
  so a new plugin can pick its own scenario and analyzers.

## Assumptions

- The `env/` venv layout, `WORKSPACE_ROOT` discovery, and `runtime_env()`
  are stable and shared by all current and near-future plugins.
- `gz`, `sim_vehicle.py`, and MAVProxy continue to be the launch surface
  for SITL+Gazebo plugins. Plugins that target a different simulator
  (e.g., pure SITL only, or a hardware-in-the-loop bench) will provide
  their own `EnvironmentAdapter`.
- Each attempt produces at most one `.BIN` log; the `collect_bin_log`
  contract (newest matching log after the attempt's wall-clock start)
  remains correct.
- The existing manifest is the source of truth for acceptance counts.

## Validation steps

Current no-SITL validation coverage lives in
`tests/parity/test_phase1_parity.py` and checks CLI flag parity,
legacy default propagation, round-robin pass ordering, static wind
world round-trip, workspace-plugin-only enforcement, and the
square-only acceptance policy. The SITL/Gazebo checks below are still
the runtime acceptance gate.

1. **Static smoke.** `python -c "import test_suite.cli.run_case"` and the
   matching imports for `run_suite` / `run_round_robin` succeed without
   side effects.
2. **CLI parity.** `python -m test_suite.cli.run_case --help` matches the
   flag surface of `run_one.py --help`. Same for the other two.
3. **Single-attempt parity (manual).** Run a single attempt through the
   new CLI on a known wind combo and diff the resulting attempt
   directory against an attempt produced by `run_one.py` for the same
   combo. Expect identical artifacts (allowing for timestamp/PID drift).
4. **Sequential matrix parity.** Run a tiny `--x-values 0 --y-values 0
   --runs-per-combo 1` campaign through `run_suite` and confirm the
   manifest acceptance count increments exactly as it does with
   `run_matrix.py`.
5. **Round-robin parity.** Run the same campaign through
   `run_round_robin` with a single `--slot-minutes` value and confirm
   bounded-slot behavior matches the legacy script.
6. **Cleanup contract.** Kill the new CLI mid-attempt with SIGINT and
   confirm `EnvironmentAdapter.cleanup` runs (look for the cleanup log
   marker and absence of orphaned `arducopter`/`gz`/MAVProxy procs).
7. **Plugin isolation.** Add a stub second plugin (e.g.,
   `plugins/example_noop/`) and prove it can run a one-attempt suite
   without touching wind_matrix files.

## Example: porting to a non-wind sensor

A GPS-dropout suite would override **only** the plugin layer:

```python
# plugins/gps_dropouts/case_generator.py
class GpsDropoutCaseGenerator(CaseGenerator):
    def iter_cases(self):
        for hz in (1, 2, 5):
            for window_s in (5, 10, 20):
                yield TestCase(
                    suite_name="gps_dropouts",
                    case_id=f"gps_dropout_{hz}hz_{window_s}s",
                    parameters={"dropout_rate_hz": hz, "dropout_window_s": window_s},
                    scenario_name="lane_hold_mission",
                    stimulus_name="gps_fault_injector",
                    acceptance_target_runs=3,
                )

# plugins/gps_dropouts/stimulus.py
class GpsFaultInjector(StimulusAdapter):
    def apply(self, case, ctx):
        # publish fault pattern over the SITL GPS injection interface
        ...

# plugins/gps_dropouts/analyzers.py
class EkfInnovationAnalyzer(Analyzer): ...
class HorizontalDriftAnalyzer(Analyzer): ...

# plugins/gps_dropouts/verdicts.py
class GpsDropoutVerdict(VerdictPolicy):
    def classify(self, case, monitor, analyses):
        # pass if drift_p95_m < 4.0 and no EKF lane switches recorded
        ...
```

Reused without change: `core/attempt_runner.py`, `core/suite_runner.py`,
`core/scheduler.py`, `core/manifest.py`, `core/artifacts.py`,
`core/control.py`, `cli/run_case.py` (with `--plugin gps_dropouts`).
