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
and, through Phase 3A, still retains wind-specific legacy delegation for
parts of the attempt lifecycle so the existing campaign log schema and
runtime ordering are preserved.

That legacy path is wind-specific. The framework cannot honestly claim
generic readiness while the first plugin still depends on a wind-specific
legacy body for its attempt lifecycle. A second plugin before the wind
plugin is proven as a real staged plugin would be architecture theater:
it would demonstrate that a second directory can exist, not that the
framework boundary is generic.

See `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md` for the
detailed layering, lifecycle, and risk register.

2026-08-06 cleanup note: the plan below is historical. The live
attempt-strategy flag/config field and delegate strategy scaffolding described
in Phase 3 have been retired; current operator guidance lives in
`docs/campaigns/wind_matrix.md` and current architecture in
`src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`.

## Current architecture (as of 2026-05-29)

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
│   │   ├── manifest.py               # sensor-agnostic Manifest contract + generic view
│   │   ├── scheduler.py              # SequentialScheduler, RoundRobinScheduler
│   │   ├── attempt_runner.py         # AttemptRunner + Legacy/Staged strategies
│   │   ├── suite_runner.py           # SuiteRunner
│   └── plugins/wind_matrix/          # first plugin (Phase 1 wrap + Phase 3A staged opt-in)
│       ├── plugin.py                 # build_plugin + Legacy delegate body
│       ├── case_generator.py
│       ├── defaults.py              # wind defaults, combo keys, path helpers
│       ├── environment.py
│       ├── legacy.py                # lazy legacy runner shim for retained wind mode/helpers
│       ├── manifest.py              # wind-compatible manifest implementation
│       ├── monitor.py               # wind/square completion monitor
│       ├── stimulus.py              # Phase 3A staged wind stimulus adapter
│       ├── analyzers.py             # Phase 3A staged analysis/verdict adapter
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
- ArchitectureMD "Stage 3 — split run_one into plugin pieces" now maps to
  feature **Phase 3A** through **Phase 3G**:
  - **Phase 3A**: split wind logic into opt-in staged plugin/core pieces
    while retaining the legacy delegate fallback.
  - **Phase 3B**: audit and prove the current staged path is not enough:
    it avoids `run_one.run_one(...)` but still depends on legacy helper code.
  - **Phase 3C**: build test-suite-owned defaults, paths, case generation,
    manifest, and CLI bootstrap so staged construction does not import legacy
    runner modules.
  - **Phase 3D**: build test-suite-owned runtime/environment launch,
    process cleanup, world writing, plugin diagnostics, and timeout helpers.
  - **Phase 3E**: build test-suite-owned MAVLink readiness, mission upload,
    arm/mode control, and mission monitor behavior.
  - **Phase 3F**: build test-suite-owned wind stimulus, BIN collection,
    analysis invocation, run-summary, and artifact handling.
  - **Phase 3G**: prove the zero-legacy staged wind system live, side-by-side
    with the retained legacy mode.
- ArchitectureMD "Stage 4 — second plugin" == feature **Phase 4**, blocked
  until Phase 3G is accepted.
- ArchitectureMD "Stage 5 — retire legacy scripts" == feature **Phase 5**,
  blocked until Phase 4 is accepted.

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

### Phase 3A — split run_one into staged plugin/core pieces (accepted as opt-in static/unit proof 2026-05-25)

Move wind/CTE logic out of `run_one.run_one`:

- `inject_wind`, `preloaded_wind_artifact`, `parse_wind_echo`,
  `start_wind_echo` → `plugins/wind_matrix/stimulus.py`.
- `run_analysis`, wind/CTE summary fields →
  `plugins/wind_matrix/analyzers.py`.
- Mission upload, arming, mode → `core/control.py`.
- `monitor_until_disarm` → `plugins/wind_matrix/monitor.py`.
- Generic manifest contract/view → `core/manifest.py`.
- Wind-compatible manifest implementation → `plugins/wind_matrix/manifest.py`.

Add a real `StagedStrategy` path and framework-driven
`AttemptRunner.run` that calls each stage adapter. The legacy delegate
remains the default behavior until live SITL/Gazebo parity proves the
staged path for the runtime scope being claimed.

Details: `phase_3_staged_attempt_runner.md`.

Phase 3A is complete only as an opt-in staged implementation with static,
unit, integration, and CLI-help evidence. It is staged behind the legacy
fallback. It does not prove the framework is generic, because the wind plugin
still retains wind-specific legacy helper delegation and has no accepted live
staged wind case.

### Phase 3B — staged dependency audit and negative proof

Audit the current staged implementation and record the uncomfortable truth:
it is modular in lifecycle shape, but not independent in implementation.
Phase 3B proves staged mode does not call the whole `run_one.run_one(...)`
body, and also records every remaining dependency on `run_one.py`,
`run_matrix.py`, and `run_matrix_round_robin.py`.

Phase 3B acceptance requires:

- staged orchestration-shell order tests (whole adapters may be faked) plus, where available, boundary-mocked adapter coverage;
- cleanup tests on success, failure, and interrupt-like paths;
- verdict and acceptance tests for full, partial, failed, error, interrupted,
  and analysis-failure outcomes;
- manifest compatibility tests proving legacy wind fields and generic fields
  remain additive and readable;
- CLI tests for the retained legacy default and explicit staged path;
- at least one bounded live wind case through the staged path, or an explicit
  dated blocker explaining why live staged wind proof is not yet available;
- a review statement that helper reuse is **not** sufficient for the final
  architecture and that staged mode still depends on legacy runner modules.

Do not start Phase 4 after Phase 3B. Phase 3B is a boundary audit and negative
proof, not the full replacement system.

### Phase 3C — legacy-runner import blocker / staged foundation

Status as of 2026-05-29: implemented for no-SITL foundation construction.
This proves the legacy-runner import blocker and the current core/plugin
foundation boundary only. A 2026-05-30 correction removed remaining
wind-legacy status decoding from `core/attempt_runner.py`. A second
2026-05-30 correction made default staged auto construction use the supported
`before-arm` wind phase and aligned campaign summary accepted counts with the
manifest `accept_square_only` policy. A 2026-05-31 correction restored
plugin manifest atomic writes, staged `running`/terminal manifest persistence,
stale-running reconciliation, and plugin-owned stimulus run-config/path
helpers. This does not prove zero-legacy staged runtime.

Create test-suite-owned replacements for construction-time and data-model
dependencies so `attempt_strategy="staged"` can be built without importing
legacy runner modules.

Scope:

- move wind defaults out of `run_one.py` / `run_matrix.py` dependencies and
  into plugin-owned constants/defaults;
- move combo key/order and case generation helpers into plugin-owned modules;
- move attempt IDs, attempt directories, run aliases, BIN names, and path
  helpers into plugin-owned modules;
- add a plugin-owned `WindMatrixManifest` entry point and remove legacy runner
  imports from manifest load/save/accepted-count/next-attempt behavior used by
  staged foundation setup;
- keep the generic `core.Manifest` contract clean and sensor-agnostic;
- change CLI bootstrap so staged mode does not use `_legacy` for defaults,
  validation, manifest setup, or logging.

Acceptance:

- constructing `WindMatrixConfig(attempt_strategy="staged")`,
  `build_plugin(...)`, and `plugin.attempt_runner()` does not import
  `run_one.py`, `run_matrix.py`, or `run_matrix_round_robin.py`;
- staged auto construction defaults to `auto_wind_phase="before-arm"`;
  explicit staged `after-takeoff` remains fail-closed;
- staged no-SITL foundation tests pass while legacy runner imports are blocked;
- legacy mode remains available and may still use the retained legacy
  delegate path.

Evidence: `evidence/reports/features/2026-05-29_test_suite_migration_phase_3c.md`.

### Phase 3D — zero-legacy runtime/environment stage

Create test-suite-owned runtime and environment modules for the staged path.

Scope:

- runtime environment construction and workspace Gazebo plugin enforcement;
- SITL launch command construction and process launch;
- Gazebo world writing and Gazebo launch;
- process-alive checks, tail logging, and stack cleanup;
- isolated SITL state / BIN directory discovery;
- timeout/deadline helpers and timestamp helpers;
- plugin diagnostics currently reached through `run_one`.

Acceptance:

- `WindMatrixEnvironment` in staged mode does not import or call
  `run_matrix.*` or `run_one.*`;
- environment unit tests cover launch command construction, cleanup, fail
  closed plugin selection, world writing, and timeout behavior;
- legacy runtime path remains unchanged.

### Phase 3E — zero-legacy MAVLink control and monitor stages

Status as of 2026-06-01: implemented for no-SITL MAVLink control/monitor
ownership. Staged `assert_ready`, `WindMatrixAutoMissionControl`, and
`WindMatrixDisarmMonitor` call plugin-owned `mavlink_control.*` only. The
only remaining staged legacy dependency after Phase 3E is `WindMatrixStimulus`
runtime wind injection (`run_one.inject_wind` / `preloaded_wind_artifact`),
owned by Phase 3F.

Create test-suite-owned MAVLink readiness, mission-control, and monitor
implementation for staged mode.

Scope:

- heartbeat wait;
- vehicle readiness checks;
- mission parsing/upload/verification;
- arm, post-arm settle, AUTO mode switch;
- passive mission monitor and disarm/timeout classification;
- `auto_wind_phase=before-arm` support first;
- `auto_wind_phase=after-takeoff` either implemented with explicit staged
  ordering or remains fail-closed with evidence.

Acceptance:

- staged control and monitor do not inject or call `run_one` helper functions;
- unit tests cover successful control order, readiness failures, monitor
  terminal states, timeout behavior, and interrupt cleanup;
- live proof is still not claimed until Phase 3G.

Evidence: `evidence/reports/features/2026-06-01_test_suite_migration_phase_3e.md`.

### Phase 3F — zero-legacy stimulus, artifacts, analysis, and summary stages

Create test-suite-owned wind stimulus, BIN/artifact handling, analysis
invocation, and run-summary implementation for staged mode.

Scope:

- Gazebo wind topic injection and echo verification;
- preloaded-world artifact handling;
- run config writing and parameter/mission provenance;
- BIN flush wait, BIN discovery, copy, naming, and raw-log artifact recording;
- analysis command invocation and analysis status classification;
- run-summary creation;
- terminal error-row creation and exception text formatting.

Acceptance:

- staged stimulus and analyzer code does not import or call legacy runner
  modules;
- tests cover full, partial, failed, error, interrupted, and analysis-failure
  manifest rows without legacy helpers;
- analysis output remains compatible with existing campaign evidence readers.

### Phase 3G — full zero-legacy staged wind proof in parallel with legacy

Run the full staged wind system beside the retained legacy system and prove the
replacement path with evidence.

Acceptance:

- hard test: when `attempt_strategy="staged"`, imports/calls to
  `run_one.py`, `run_matrix.py`, and `run_matrix_round_robin.py` are blocked
  and the no-SITL staged suite still passes;
- at least one bounded live staged wind case completes through SITL/Gazebo;
- matching legacy live case is run for comparison;
- staged and legacy manifests/artifacts are compared with documented accepted
  differences;
- staged remains opt-in unless the evidence explicitly supports changing the
  default;
- no second plugin is added;
- no legacy script is retired.

### Phase 4 — second plugin proof, blocked until Phase 3G acceptance

Stand up one additional non-wind plugin (recommended candidates: a
no-stimulus airspeed validation bench, or a GPS dropout injector).
Requires zero framework-core edits. If a `core/` edit is needed, the
abstractions are still wrong.

Phase 4 is authorized only after Phase 3G evidence shows `wind_matrix` has a
full zero-legacy staged implementation that runs in parallel with legacy and
has live proof. A second plugin proves nothing if the first plugin is still
secretly implemented by wind-specific legacy runner modules.

### Phase 5 — compatibility retirement, blocked until Phase 4 acceptance

Retire the legacy `run_one.py` / `run_matrix.py` /
`run_matrix_round_robin.py` only after Phase 4 proves generality with
evidence-backed replacement paths. Legacy
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
- `WindMatrixManifest.append_attempt()` writes generic fields additively to
  the matching attempt row and does not overwrite legacy wind fields.
- Older manifests with no generic fields normalize without crashing.
- `success_square_only` remains a generic `partial` verdict and does
  not count as strict full success by default.
- Focused Phase 2 tests, unit tests, integration tests, Phase 1 parity,
  `make test-parity`, and `make doctor` pass.

## Phase 3A success criteria

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

## Phase 3B success criteria

- `wind_matrix` no longer depends on `run_one.run_one(...)` or equivalent
  wind-specific legacy delegation for its attempt lifecycle.
- Remaining legacy helper calls are fully inventoried and treated as blockers
  for Phase 3G, not as final architecture.
- Stage-order, cleanup, verdict/acceptance, manifest compatibility, and CLI
  tests pass for the staged wind plugin.
- At least one bounded live staged wind case exists, or a dated blocker
  explicitly records why live proof is unavailable.
- Review records that `test_suite` is not treated as generic or replacement
  ready after Phase 3B.

## Phase 3C success criteria

- Staged config/default creation does not import legacy runner modules.
- Staged case generation and combo-key naming do not import legacy runner
  modules.
- Staged manifest load/save/additive generic fields and accepted-count logic do
  not import legacy runner modules.
- Generic `core/manifest.py` and `core/monitor.py` contain no wind-matrix
  case fields, combo-key logic, summary generation, or wind/square monitor
  assumptions.
- Generic core contains no wind legacy status-string decoding; plugins provide
  framework verdicts or explicit framework `AttemptStatus` values.
- `build_plugin(... attempt_strategy="staged")`, `plugin.attempt_runner()`,
  and CLI parser/bootstrap foundation behavior work while imports of
  `run_one.py`, `run_matrix.py`, and `run_matrix_round_robin.py` are blocked.
- Campaign summaries respect `accept_square_only` the same way
  `WindMatrixManifest.accepted_count()` does.
- Legacy mode remains the default and stays available.
- No live runtime proof, second plugin, Phase 4 work, or legacy script
  retirement is claimed.

**Manifest Compatibility Contract — accept_square_only (H-C, 2026-06-01):**
The strict `accept_square_only` gate in `WindMatrixManifest.accepted_count()` is
a property of the new orchestrator and applies to **both** `legacy` and `staged`
attempt strategies when a campaign is run through `test_suite.cli.*`. Running the
new CLIs in `--attempt-strategy legacy` mode over an existing campaign root that
contains `success_square_only` rows will renumber/retry those combos; the legacy
`run_matrix.py` tool would have counted those rows as complete. This is an
intentional stricter safety policy, not a legacy parity bug, but operators
resuming campaigns via the new CLIs must account for it. See `review.md`
(Post-legacy acceptance policy note and H-C clarification) for detail.

## Phase 3D-3G success criteria

- Staged runtime, control, monitor, stimulus, artifact, analysis, summary, and
  remaining runtime manifest/error-row code do not import or call the legacy
  runner modules.
- Legacy mode remains available as the side-by-side fallback and comparison
  path.
- A hard no-legacy test blocks `run_one.py`, `run_matrix.py`, and
  `run_matrix_round_robin.py` imports/calls for full staged mode.
- A bounded live staged wind case passes.
- A matching legacy case is run and compared.
- Only after this evidence may Phase 4 begin.

## Phase 4 gate — OPEN (Phase 3G accepted 2026-06-01)

Phase 3G is accepted: `wind_matrix` is a full zero-legacy staged system proven
live against the legacy tool run directly
(`evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md`).
Phase 4 is therefore authorized. The Phase 4 second plugin must test general
framework boundaries with **zero framework-core edits** (if a `core/` edit is
needed, the abstractions are still wrong). It must not be used to distract from
the wind plugin's correctness, which is now evidence-backed.

## Phase 5 gate

Do not start Phase 5 until Phase 4 is accepted. Legacy wind-specific scripts
and wrappers are retained until replacement paths are evidence-backed.

## Out of scope for Phase 2

- Splitting `run_one.py`.
- Retiring legacy wrappers.
- Creating the second plugin.
- Claiming Phase 3 / Phase 4 / Phase 5 completion.
- Changing live runtime behavior except additive generic manifest/view
  recording.
- Adding implementation logic to `compat_scripts/`.

## Out of scope for Phase 3A

- Switching all campaign runtime behavior to staged mode by default.
- Claiming live staged SITL/Gazebo parity.
- Supporting staged `auto_wind_phase=after-takeoff`.
- Retiring legacy wrappers or deleting `run_one.py`.
- Creating the second plugin.
- Claiming `test_suite` generic framework readiness.

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
- Architecture theater: treating a second plugin as proof of generality while
  the first plugin still hides a wind-specific legacy lifecycle. Mitigated by
  the Phase 3B gate and the explicit Phase 4 block.

## Pointers

- Architecture: `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- Phase 1 details: `phase_1_wrapper_parity.md` (this directory)
- Review: `review.md`
- Evidence pointers: `evidence.md`
- Governance phase 5 (the workspace-wide campaign/test phase that
  put the wrappers in place): `governance/runbooks/migration/phase_5_campaign_test_migration.md`
- Governance phase 8 (which moved the runner ownership):
  `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`
