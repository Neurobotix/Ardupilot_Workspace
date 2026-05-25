# Feature Runbook: test_suite Migration — Plan

## Why this feature exists

The legacy wind-matrix campaign code in
`src/sim_ard_gaw/campaigns/wind_matrix/` (owned home for `run_one.py`,
`run_matrix.py`, `run_matrix_round_robin.py`) is a working but
sensor-coupled monolith. `run_one.run_one(...)` is ~400 lines that mix
stack readiness, wind stimulus injection, mission upload, arm/mode
transitions, monitoring, log selection, analysis, and manifest writing
in one ordering-sensitive body. Adding any other sensor or campaign
(GPS dropouts, airspeed validation bench, lidar return capture) by
copying that monolith is not sustainable.

`src/sim_ard_gaw/campaigns/test_suite/` is the new generic test-suite
framework. It splits responsibility along a clean boundary: a
sensor-agnostic `core/`, plus per-sensor `plugins/<family>/`, plus a
thin CLI layer in `cli/`. The wind_matrix plugin is the first plugin
and currently delegates back into the legacy modules so the existing
campaign log schema and runtime ordering are preserved.

See `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md` for the
detailed layering, lifecycle, and risk register.

## Current architecture (as of 2026-05-24)

```
src/sim_ard_gaw/campaigns/
├── test_suite/                       # owned new framework
│   ├── ARCHITECTURE.md
│   ├── cli/                          # python -m test_suite.cli.*
│   │   ├── run_case.py               # mirrors run_one.py flags
│   │   ├── run_suite.py              # mirrors run_matrix.py flags
│   │   ├── run_round_robin.py        # mirrors run_matrix_round_robin.py flags
│   │   └── _registry.py              # Phase-1 plugin registry
│   ├── core/                         # sensor-agnostic framework
│   │   ├── models.py                 # TestCase, AttemptContext, AttemptRecord, Verdict
│   │   ├── case_generator.py         # CaseGenerator protocol
│   │   ├── environment.py            # EnvironmentAdapter protocol
│   │   ├── stimulus.py               # StimulusAdapter protocol
│   │   ├── control.py                # ControlStrategy protocol
│   │   ├── monitor.py                # CompletionMonitor protocol
│   │   ├── artifacts.py              # ArtifactStore protocol
│   │   ├── analysis.py               # AnalyzerChain protocol
│   │   ├── verdicts.py               # VerdictPolicy protocol
│   │   ├── manifest.py               # Manifest contract + LegacyManifest
│   │   ├── scheduler.py              # SequentialScheduler, RoundRobinScheduler
│   │   ├── attempt_runner.py         # AttemptRunner + Legacy/Staged strategies
│   │   ├── suite_runner.py           # SuiteRunner
│   │   └── _legacy.py                # lazy import shim to owned wind_matrix modules
│   └── plugins/wind_matrix/          # first plugin (Stage-1 wrap)
│       ├── plugin.py                 # build_plugin + Legacy delegate body
│       ├── case_generator.py
│       ├── environment.py
│       └── config.py
├── wind_matrix/                      # legacy runner ownership (Phase 8 destination)
│   ├── run_one.py
│   ├── run_one_og.py
│   ├── run_matrix.py
│   └── run_matrix_round_robin.py
└── (manifest_safety.py, mission_contract.py, provenance.py,
    status.py, wind_world.py)        # shared campaign hardening helpers
```

`src/sim_ard_gaw/compat_scripts/` keeps wrapper-only entry points
(`run_one.py`, `run_matrix.py`, `run_matrix_round_robin.py`, and the
`test_suite/` namespace shim) so old import paths and direct script
calls still work.

## Phase breakdown

The phase numbering used here is the **feature-level** phase numbering
for this migration. It is independent of the workspace-wide governance
phase numbering (Phase 5 / 7 / 8). The mapping is:

- ArchitectureMD "Stage 1 — wrap" == feature **Phase 1**.
- ArchitectureMD "Stage 2 — generic data model" == feature **Phase 2**.
- ArchitectureMD "Stage 3 — split run_one into plugin pieces" == feature **Phase 3**.
- ArchitectureMD "Stage 4 — second plugin" == feature **Phase 4**.
- ArchitectureMD "Stage 5 — retire legacy scripts" == feature **Phase 5**.

### Phase 1 — wrapper parity and baseline hardening

Goals:

- Lock down the current `test_suite` state under
  `src/sim_ard_gaw/campaigns/test_suite/`.
- Complete any missing wrapper-parity pieces.
- Prove the wrapper layer is safe before any later phase touches
  the monolith.
- Create the feature runbook bundle, evidence report, and routing
  pointers.

Phase 1 does **not** split `run_one.py`, retire compatibility
wrappers, claim full live-runtime parity, or stand up a second plugin.

### Phase 2 — generic manifest / data model (accepted 2026-05-25)

Add framework-level fields (`case_id`, `suite_name`, `parameters`,
`stimulus_result`, `analysis_results`, `verdict`, `artifacts`,
`attempt_id`, `started_at`, `finished_at`, and `schema_version`) to a
generic manifest view, written additively next to the existing
wind-specific fields for attempts created through the framework path.
Add a reader that exposes both views. No rename of existing fields.
Phase 2 preserves campaign log history for fixed-harness comparator
datasets under `evidence/curated_logs/017_*` and `018_*`.

Details: `phase_2_generic_manifest.md`.

### Phase 3 — split run_one into plugin pieces (implemented as opt-in staged mode 2026-05-25)

Move wind/CTE logic out of `run_one.run_one`:

- `inject_wind`, `preloaded_wind_artifact`, `parse_wind_echo`,
  `start_wind_echo` → `plugins/wind_matrix/stimulus.py`.
- `run_analysis`, wind/CTE summary fields →
  `plugins/wind_matrix/analyzers.py`.
- Mission upload, arming, mode → `core/control.py`.
- `monitor_until_disarm` → `core/monitor.py`.
- Manifest helpers → `core/manifest.py`.

Add a real `StagedStrategy` path and framework-driven
`AttemptRunner.run` that calls each stage adapter. The legacy delegate
remains the default behavior until live SITL/Gazebo parity proves the
staged path for the runtime scope being claimed.

Details: `phase_3_staged_attempt_runner.md`.

### Phase 4 — second plugin (proof of generality)

Stand up one additional non-wind plugin (recommended candidates: a
no-stimulus airspeed validation bench, or a GPS dropout injector).
Requires zero framework-core edits. If a `core/` edit is needed, the
abstractions are still wrong.

### Phase 5 — compatibility retirement

Retire the legacy `run_one.py` / `run_matrix.py` /
`run_matrix_round_robin.py` once two plugins are stable. Legacy
modules become thin wrappers that import and call
`test_suite/cli/*.py`; eventually they can be removed along with the
`compat_scripts/` shims.

## Phase 1 success criteria

- Inventory of implemented / missing / intentionally-deferred /
  retained compatibility pieces, recorded in
  `phase_1_wrapper_parity.md`.
- Wrapper-only boundary in `compat_scripts/` confirmed (no
  implementation logic in `compat_scripts/`).
- Three module-style CLI paths (`-m test_suite.cli.*` via the
  compat namespace, and the owned `-m sim_ard_gaw.campaigns.test_suite.cli.*`
  path) plus the three legacy compat scripts all produce help output.
- `tests/parity/test_phase1_parity.py` passes.
- Tests in `tests/unit/` and `tests/integration/` pass.
- `make test-parity` and `make doctor` pass.
- Disposable Python artifacts (`__pycache__`, `*.pyc`) are absent
  from active source and covered by `.gitignore`.
- Dated evidence report exists under `evidence/reports/`.

## Phase 2 success criteria

- `Manifest.generic_view()` exposes the generic attempt contract with
  schema version `test_suite.generic_manifest.v1`.
- `Manifest.legacy_view()` keeps the wind-specific manifest shape.
- `LegacyManifest.append_attempt()` writes generic fields additively to
  the matching attempt row and does not overwrite legacy wind fields.
- Older manifests with no generic fields normalize without crashing.
- `success_square_only` remains a generic `partial` verdict and does
  not count as strict full success by default.
- Focused Phase 2 tests, unit tests, integration tests, Phase 1 parity,
  `make test-parity`, and `make doctor` pass.

## Phase 3 success criteria

- `--attempt-strategy legacy` remains the default and keeps the legacy
  delegate path available.
- `--attempt-strategy staged` builds wind-matrix staged adapters for
  stimulus, control, monitor, analysis, and verdict.
- Staged strategy order and cleanup behavior are covered by unit tests.
- Manifest writes remain additive and legacy wind fields round-trip
  unchanged.
- Failed/error/interrupted statuses do not count as accepted.
- CLI help paths still work.
- No Phase 4 second plugin or Phase 5 compatibility retirement occurs.

## Out of scope for Phase 2

- Splitting `run_one.py`.
- Retiring legacy wrappers.
- Creating the second plugin.
- Claiming Phase 3 / Phase 4 / Phase 5 completion.
- Changing live runtime behavior except additive generic manifest/view
  recording.
- Adding implementation logic to `compat_scripts/`.

## Out of scope for Phase 3

- Switching all campaign runtime behavior to staged mode by default.
- Claiming live staged SITL/Gazebo parity.
- Supporting staged `auto_wind_phase=after-takeoff`.
- Retiring legacy wrappers or deleting `run_one.py`.
- Creating the second plugin.

## Out of scope for Phase 1

- Live SITL/Gazebo single-attempt parity diff against the legacy
  `run_one.py` output. Architecture validation steps 3–6 still apply
  to Phase 3 / Phase 4 once the framework is split. Phase 1 does not
  re-prove the runtime parity beyond what Phase 5 (governance phase
  numbering) already recorded; it relies on the wrapper-delegate
  property that the legacy body is still called byte-for-byte.
- Schema rename or new manifest fields.
- Second-plugin proof of generality.
- Any change to `compat_scripts/` beyond confirming wrapper-only
  status.

## Risks

The architectural risk register lives in `ARCHITECTURE.md` ("Risks").
The Phase-1-specific risks are:

- Drift between the new CLI flag surface and the legacy script
  flags. Mitigated by `tests/parity/test_phase1_parity.py` which
  diffs the help output, allowing only the new `--plugin` flag.
- Silent acceptance of partial/failed attempts as full successes if
  the legacy-status → framework-status mapping in `plugin.py` is
  wrong. Inspected in this phase; existing mapping treats
  `success_full` only as `SUCCESS` and `success_square_only` as
  `PARTIAL`, with all others (`failed`, `failed_analysis`, `error`,
  `interrupted`) blocked from acceptance via
  `legacy_analysis_succeeded`.

## Pointers

- Architecture: `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- Phase 1 details: `phase_1_wrapper_parity.md` (this directory)
- Review: `review.md`
- Evidence pointers: `evidence.md`
- Governance phase 5 (the workspace-wide campaign/test phase that
  put the wrappers in place): `governance/runbooks/migration/phase_5_campaign_test_migration.md`
- Governance phase 8 (which moved the runner ownership):
  `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`
