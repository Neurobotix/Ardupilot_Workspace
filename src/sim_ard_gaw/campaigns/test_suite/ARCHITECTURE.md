# Automated Test Suite Architecture

The automated test suite is the reusable campaign framework for the
fault-injection lanes. It binds a sensor-family plugin to a generic attempt
lifecycle, records each attempt in a manifest, and keeps raw runtime output
separate from promoted evidence.

Current plugin families:

- `wind_matrix`: CTE wind campaign attempts.
- `airspeed_failure`: degraded/corrupted airspeed behavior characterization.
- `gps_failure`: degraded/corrupted GPS behavior characterization.

The standalone wind-matrix operator runners under
`src/sim_ard_gaw/campaigns/wind_matrix/` remain live direct entry points. The
`test_suite` wind-matrix plugin uses the staged framework pipeline; the retired
`--attempt-strategy` option is only a deprecated CLI compatibility surface.

## Layered Model

```text
Campaign config layer
  argparse / YAML / env vars
  selects plugin, cases, run mode, timeouts, roots, and operator guards

Plugin layer
  plugins/<sensor_family>/
  owns cases, launch/environment details, stimulus mechanics, monitors,
  analyzers, verdict policy, and plugin-specific manifest fields

Framework layer
  core/
  owns attempt and suite lifecycle, scheduler policies, generic manifest view,
  artifact collection contract, and common model types
```

The core does not import plugins. Plugins do not import sibling plugins. CLI
entry points select a plugin by name through `cli/_registry.py` and pass it to
the framework.

## Attempt Pipeline

An attempt has five high-level phases:

1. **Prepare and launch:** create per-attempt scaffolding, start or attach to
   the simulator stack, and assert readiness.
2. **Apply and drive:** apply the stimulus, verify it took effect, and execute
   the selected control strategy.
3. **Observe:** monitor the vehicle until the lane's terminal condition or a
   guarded failure.
4. **Collect and analyze:** collect artifacts and run plugin-owned analyzers.
5. **Classify and persist:** classify the verdict, atomically update the
   manifest, and always run cleanup.

`AttemptRunner.run(case)` implements those phases through these adapters:

1. `EnvironmentAdapter.prepare_case(case)`
2. `EnvironmentAdapter.launch(case, ctx)`
3. `EnvironmentAdapter.assert_ready(case, ctx)`
4. `StimulusAdapter.apply(case, ctx)`
5. `StimulusAdapter.verify(case, ctx)`
6. `ControlStrategy.execute(case, ctx)`
7. `CompletionMonitor.run(case, ctx)`
8. `ArtifactStore.collect(case, ctx)`
9. `AnalyzerChain.analyze(case, ctx)`
10. `VerdictPolicy.classify(case, monitor, analyses)`
11. `Manifest.persist(attempt_record)`
12. `EnvironmentAdapter.cleanup(case, ctx)` in `finally`

`SuiteRunner` loops over a `SchedulerPolicy` (sequential, round-robin, or a
plugin-specific policy) until requested acceptance counts, budgets, or stop
conditions are reached.

## Ownership

| Concern | Owner |
| --- | --- |
| Attempt id / numbering | core |
| Generic manifest view and atomic persistence contract | core |
| Artifact directory root and collection contract | core |
| Slot deadlines and retry accounting | core |
| Control-mode plumbing | core |
| Scheduler policies | core |
| Case enumeration | plugin |
| Scenario, mission, and parameter stack selection | plugin |
| Environment launch commands and readiness semantics | plugin |
| Stimulus injection mechanics | plugin |
| Completion monitor and behavior-specific terminal state | plugin |
| Analyzer scripts and parsing | plugin |
| Verdict thresholds and accepted-observation rules | plugin |
| Plugin-specific manifest fields | plugin |

If a new sensor family needs framework edits to ship, treat that as a design
review trigger: either the framework is missing a real abstraction, or the
plugin is reaching across an ownership boundary.

## Manifest And Evidence Contract

The framework writes additive generic fields (`schema_version`, `case_id`,
`suite_name`, `parameters`, `stimulus_result`, `analysis_results`, `verdict`,
`artifacts`, `attempt_id`, `started_at`, `finished_at`) while preserving
plugin-specific views needed by existing evidence readers. The generic schema
marker is `test_suite.generic_manifest.v1`.

`Manifest.generic_view()` normalizes old and new rows without mutating older
manifests. `Manifest.legacy_view()` remains a compatibility API for reading
existing evidence bundles; renaming it is intentionally out of scope for
documentation cleanup.

Raw simulator output stays under `var/` or a campaign root. A result becomes a
workspace claim only after reviewed proof is promoted under `evidence/` with a
dated report, manifest or curated artifact, raw-output reference, and
limitations.

## Current Wind-Matrix Shape

The wind-matrix plugin owns framework-driven CTE attempts through these
modules:

- `case_generator.py`: wind combo ordering and case ids.
- `environment.py` and `runtime.py`: SITL/Gazebo stack ownership.
- `mavlink_control.py`: mission upload, arming, AUTO mode, and square monitor.
- `wind_injection.py` and `stimulus.py`: runtime wind-topic injection and SDF
  wind artifacts.
- `analysis_helpers.py` and `analyzers.py`: BIN collection, square/loiter
  analysis, summaries, and verdict inputs.
- `manifest.py`: wind-compatible manifest fields plus the generic view.

The direct wind-matrix runners (`run_one.py`, `run_matrix.py`, and
`run_matrix_round_robin.py`) are separate operator/campaign entry points. They
are not compatibility wrappers and are not removed by the test-suite
architecture.

## Current Risks

- **Framework boundaries:** promote helpers into `core/` only after more than
  one plugin needs them as real callers.
- **Manifest schema drift:** generic fields must stay additive. Existing
  evidence readers rely on older wind-specific fields.
- **Process ownership:** governed attempts must clean up the simulator stack so
  stale SITL, Gazebo, MAVProxy, bridge, or logger processes do not contaminate
  evidence.
- **Campaign-scale claims:** bounded live proof does not imply a full campaign
  matrix. Wider readiness claims require their own dated evidence.
- **Path assumptions:** framework code should not hard-code workspace-relative
  plugin paths. Paths flow through plugin config.

## Validation

Use focused unit and integration tests for code changes:

```bash
python -m pytest tests/unit -q
python -m pytest tests/integration -q
```

Use `make doctor` after documentation, governance, evidence, structure,
runtime-path, or local-overlay-policy changes.

## Historical Crosswalk

Older feature runbooks refer to architecture "Stage" labels. Those labels are
historical implementation milestones, not current operating modes:

| Historical label | Record home |
| --- | --- |
| Stage 1 — wrappers | `governance/runbooks/features/test_suite_migration/phase_1_wrapper_parity.md` |
| Stage 2 — generic manifest | `governance/runbooks/features/test_suite_migration/phase_2_generic_manifest.md` |
| Stage 3A-3G — staged wind extraction and proof | `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md` plus the Phase 3B-3G reports in `evidence/reports/features/` |
| Stage 4 — second plugin proof | Airspeed and GPS plugin runbooks under `governance/runbooks/features/` |
| Stage 5 — wind-matrix strategy retirement | `evidence/reports/migration/WIND_MATRIX_LEGACY_STRATEGY_RETIREMENT_2026-06-30.md` |

Stage 3G compared the staged framework path against the retained direct
wind-matrix runner path; the deleted `compat_scripts/` wrapper layer is not a
current comparison entry point.
