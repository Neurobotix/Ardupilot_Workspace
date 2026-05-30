# Phase 1 — Wrapper Parity And Baseline Hardening

Scope: feature-level Phase 1 of the `test_suite` migration. This is the
"Stage 1 — wrap" phase from
`src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md` treated as a
governed feature phase.

## What Phase 1 does

1. Locks down the current `test_suite/` implementation under
   `src/sim_ard_gaw/campaigns/test_suite/` as the baseline.
2. Confirms the wrapper-only compatibility boundary in
   `src/sim_ard_gaw/compat_scripts/`.
3. Confirms three CLI surfaces and the legacy script wrappers all
   produce help output.
4. Confirms scheduler determinism, manifest acceptance counting, and
   cleanup-in-`finally` properties through focused tests already in
   `tests/parity/test_phase1_parity.py`,
   `tests/unit/test_campaign_*`, and
   `tests/integration/test_phase5_wrapper_manifest_flow.py`.
5. Removes disposable Python build artifacts from active source.
6. Produces the feature runbook bundle and a dated Phase 1 evidence
   report.

## What Phase 1 does NOT do

- Does not modify `run_one.run_one(...)` or split the legacy body.
- Does not retire any compatibility wrapper.
- Does not add a second plugin.
- Does not claim full live SITL/Gazebo runtime parity beyond what
  governance Phase 5 (`evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`)
  and Phase 8 (`evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`)
  already recorded.
- Does not change the manifest schema. At Phase 1, `LegacyManifest`
  delegated to `run_one.load_manifest` / `save_manifest`; Phase 3C later
  moved the wind-compatible implementation to `WindMatrixManifest`.
- Does not modify the deprecated fallback/reference workspace
  named in `.ai/current.md` and ADR-0005.

## Inventory

### Implemented (already present before this pass)

**Framework core under `src/sim_ard_gaw/campaigns/test_suite/core/`:**

- `models.py` — `TestCase`, `AttemptContext`, `AttemptRecord`,
  `AttemptStatus`, `Verdict`, `VerdictClass`, `MonitorResult`,
  `AnalysisResult`.
- `case_generator.py` — `CaseGenerator` protocol.
- `environment.py` — `EnvironmentAdapter` protocol.
- `stimulus.py` — `StimulusAdapter` protocol.
- `control.py` — `ControlStrategy` protocol.
- `monitor.py` — `CompletionMonitor` protocol.
- `artifacts.py` — `ArtifactStore` protocol.
- `analysis.py` — `AnalyzerChain` protocol.
- `verdicts.py` — `VerdictPolicy` protocol.
- `manifest.py` — `Manifest` ABC and, at Phase 1, `LegacyManifest`
  delegating to owned `run_one.load_manifest` /
  `save_manifest` / `combo_successes` / `next_attempt_index`. Phase 3C later
  moved this wind-specific implementation to `plugins/wind_matrix/manifest.py`.
- `scheduler.py` — `SchedulerPolicy` ABC, `SchedulerDecision`,
  `SequentialScheduler` (matches `run_matrix.main`),
  `RoundRobinScheduler` (bounded slot fairness).
- `attempt_runner.py` — `AttemptRunner`, `AttemptStrategy`,
  `StagedStrategy` (canonical), `LegacyDelegateStrategy` (Phase-1
  escape hatch).
- `suite_runner.py` — `SuiteRunner` with `SuiteRunSettings`.
- `_legacy.py` — lazy import shim resolving owned
  `sim_ard_gaw.campaigns.wind_matrix.*` runner modules.

**Plugin `plugins/wind_matrix/`:**

- `__init__.py` — exposes `build_plugin`.
- `config.py` — `WindMatrixConfig` dataclass.
- `case_generator.py` — emits one `TestCase` per (x_wind, y_wind)
  using legacy `combo_key()`.
- `environment.py` — `WindMatrixEnvironment` adapter wrapping
  `run_matrix.launch_sitl` / `launch_gazebo` / `cleanup_stack` and
  the static wind world preload.
- `plugin.py` — `WindMatrixPlugin`, `_legacy_run_one_body` mapping
  legacy `run_one.run_one(...)` into `AttemptRecord`, status
  translation tables.

**CLI under `cli/`:**

- `run_case.py` — `python -m test_suite.cli.run_case`.
- `run_suite.py` — `python -m test_suite.cli.run_suite`.
- `run_round_robin.py` — `python -m test_suite.cli.run_round_robin`.
- `_registry.py` — Phase-1 flat `PLUGINS` dict mapping
  `wind_matrix` to its factory.

**Tests:**

- `tests/parity/test_phase1_parity.py` — eight tests covering:
  - CLI flag-surface parity (`run_one.py` ↔ `run_case`,
    `run_matrix.py` ↔ `run_suite`, `run_matrix_round_robin.py` ↔
    `run_round_robin`).
  - Legacy default propagation through `WindMatrixConfig`.
  - Deterministic round-robin pass ordering.
  - Static wind world round-trip (SDF write + parse).
  - Workspace-plugin-only enforcement (`runtime_env`).
  - Square-only acceptance policy: a legacy `success_square_only`
    row counts toward acceptance only when
    `accept_square_only=True`.
  - Partial-only manifest under strict policy yields zero accepted
    runs (failed / failed_analysis are never counted).
- `tests/unit/test_campaign_manifest_safety.py` and
  `tests/unit/test_campaign_contracts.py` — manifest locking,
  terminal taxonomy, mission contract, wind world safety.
- `tests/unit/test_phase8_runtime_paths.py` — owned runtime path
  resolution.
- `tests/integration/test_phase5_wrapper_manifest_flow.py` — wrapper
  manifest flow.

**Compatibility wrappers:**

- `src/sim_ard_gaw/compat_scripts/test_suite/__init__.py` — namespace
  shim that points `test_suite.*` at the owned
  `sim_ard_gaw.campaigns.test_suite` package.
- `src/sim_ard_gaw/compat_scripts/run_one.py`,
  `run_matrix.py`, `run_matrix_round_robin.py` — thin script
  wrappers using `_owned_wrapper.run_owned_script` / `export_owned_module`.

### Missing (intentionally deferred to later feature phases)

- Phase 2: additive generic manifest fields and a generic-view
  reader.
- Phase 3: real `StagedStrategy` adapters (stimulus, control,
  monitor, analyzers, verdict) that don't go through
  `run_one.run_one(...)`.
- Phase 4: a second plugin under
  `plugins/<non_wind_family>/`.
- Phase 4: real plugin registry (entry points or package iteration).
- Phase 5: deletion / wrapper-ification of legacy `run_one.py` etc.
- Live SITL/Gazebo single-attempt diff between new CLI and legacy
  `run_one.py` (ARCHITECTURE.md validation step 3) — deferred to
  later runtime work; the wrapper-delegate property makes the
  output equivalence structural rather than empirical at this phase.

### Intentionally deferred

- A `tests/` package under
  `src/sim_ard_gaw/campaigns/test_suite/tests/` exists as an empty
  directory placeholder from earlier work. Workspace tests live
  under top-level `tests/`. The placeholder is harmless and is left
  alone; deletion is a follow-up housekeeping item, not a Phase 1
  blocker.

### Retained compatibility surface

- `src/sim_ard_gaw/compat_scripts/test_suite/__init__.py` namespace
  shim so callers that put `compat_scripts/` on `PYTHONPATH` can
  still `import test_suite.*`. The shim sets
  `__path__ = [owned_package_dir]` and adds `src/` to `sys.path`;
  it contains no implementation logic.
- `src/sim_ard_gaw/compat_scripts/run_one.py`,
  `run_matrix.py`, `run_matrix_round_robin.py` — thin script
  wrappers via `_owned_wrapper.run_owned_script`. Implementation
  ownership lives in `campaigns/wind_matrix/`.

## Wrapper-only boundary verification

| Check | Result |
| --- | --- |
| `compat_scripts/test_suite/__init__.py` contains only namespace forwarding | PASS |
| `compat_scripts/run_one.py` only calls `run_owned_script` / `export_owned_module` | PASS |
| `compat_scripts/run_matrix.py` only calls `run_owned_script` / `export_owned_module` | PASS |
| `compat_scripts/run_matrix_round_robin.py` only calls `run_owned_script` / `export_owned_module` | PASS |
| `test_suite/core/_legacy.py` resolves owned `sim_ard_gaw.campaigns.wind_matrix.*` modules, not top-level wrappers | PASS at Phase 1; superseded in Phase 3C by `plugins/wind_matrix/legacy.py` |
| No new implementation logic added to `compat_scripts/` during Phase 1 | PASS |

## CLI parity surfaces verified

The Phase 1 pass executed each of these and confirmed exit code 0
plus expected usage output. Commands use the canonical
`PYTHONPATH=src:src/sim_ard_gaw/compat_scripts`.

- `env/bin/python3 -m test_suite.cli.run_case --help`
- `env/bin/python3 -m test_suite.cli.run_suite --help`
- `env/bin/python3 -m test_suite.cli.run_round_robin --help`
- `env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_case --help`
- `env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_suite --help`
- `env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_round_robin --help`
- `env/bin/python3 src/sim_ard_gaw/compat_scripts/run_one.py --help`
- `env/bin/python3 src/sim_ard_gaw/compat_scripts/run_matrix.py --help`
- `env/bin/python3 src/sim_ard_gaw/compat_scripts/run_matrix_round_robin.py --help`

`tests/parity/test_phase1_parity.py::test_cli_flag_surfaces_match_legacy`
also diffs the help flag sets between each legacy script and its
`test_suite.cli.*` counterpart, allowing only the new `--plugin` flag.

## Scheduler / manifest safety review

| Area | Behavior | Evidence |
| --- | --- | --- |
| Round-robin ordering | `RoundRobinScheduler.next_case` advances a pointer over a fixed `_pass_cases` list per pass; cases already at acceptance are skipped, not double-counted. | `tests/parity/test_phase1_parity.py::test_round_robin_snapshots_one_pass_in_legacy_order` |
| Acceptance counting (full success) | At Phase 1, `LegacyManifest.accepted_count` deferred to `run_one.combo_successes(manifest, key, require_analysis=...)`; Phase 3C moved this wind-compatible behavior to `WindMatrixManifest`. `failed` / `failed_analysis` / `error` / `interrupted` are not in the success set. | Translation tables in `plugins/wind_matrix/plugin.py`; `legacy_analysis_succeeded` helper. |
| Acceptance counting (square-only policy) | The wind-compatible manifest implementation is policy-aware: when `accept_square_only=False` (the default), legacy `success_square_only` attempts are treated as partial and do **not** contribute to the accepted count. A historical square-only row cannot silently satisfy a strict full-mission run. | `tests/parity/test_phase1_parity.py::test_legacy_manifest_does_not_accept_square_only_by_default` and `test_legacy_manifest_partial_alone_is_not_accepted_under_strict_policy`. |
| Attempt indexing | Phase 1 delegated attempt indexing to `run_one.next_attempt_index`; Phase 3C moved the test-suite-owned implementation to `WindMatrixManifest.next_attempt_index`. | Phase 1 manifest path unchanged from governance Phase 5; Phase 3C report records the move. |
| Cleanup in `finally` | `AttemptRunner.run` wraps the strategy body in `try/.../finally: env.cleanup(...)`. `WindMatrixEnvironment.cleanup` always calls `run_matrix.cleanup_stack()` then closes any retained process handles. | `attempt_runner.py:158-176`; `environment.py:115-128` |
| Slot deadline propagation | `RoundRobinScheduler.next_case` sets `slot_deadline_monotonic_s`. `_legacy_run_one_body` subtracts `slot_deadline_margin_s` before forwarding to `run_one.run_one`. | `scheduler.py:116-124`; `plugin.py:82-117` |
| Manifest writes | `run_one.save_manifest` is the legacy atomic write path; `campaign_manifest_lock` protects the cli pre-amble in `run_suite.py` / `run_round_robin.py`. | Inherited from governance Phase 5 hardening; covered by `tests/unit/test_campaign_manifest_safety.py`. |

No new unit tests were needed to fill a gap during this Phase 1 pass.
The above checks already exist.

## Artifacts removed during Phase 1

`__pycache__/` directories and `*.pyc` files under
`src/sim_ard_gaw/campaigns/test_suite/` were removed. They were never
git-tracked (the workspace has no root commit yet), but they polluted
the active source tree. `.gitignore` already covers `__pycache__/`
and `*.pyc`, so they cannot accidentally be tracked later.

No evidence files, no curated logs, and no governance records were
deleted.

## Phase 1 acceptance gate

- [x] Feature runbook bundle exists under
      `governance/runbooks/features/test_suite_migration/`.
- [x] Phase 1 scope documented; later phases listed.
- [x] Stage-1 wrapper architecture confirmed in code.
- [x] No duplicate implementation logic.
- [x] `compat_scripts/` is wrapper-only.
- [x] CLI/import parity tested (6 parity tests pass) plus the nine
      manual help invocations.
- [x] Scheduler / manifest behavior reviewed.
- [x] Evidence report
      `evidence/reports/features/TEST_SUITE_MIGRATION_PHASE_1_2026-05-24.md`
      exists.
- [x] `.ai/index.md` points to this feature runbook.
- [x] `make doctor` passes.
- [x] Old workspace not modified.

## Exit to Phase 2

Phase 2 (generic manifest / data model) is unblocked. Required input
for Phase 2:

- `core/manifest.py` `Manifest` contract is stable.
- Phase 1 inventory above lists every adapter site that will need a
  generic-view field.
- `evidence/curated_logs/017_*` and `018_*` campaign log shapes are
  the comparator datasets that Phase 2 must keep round-trip
  compatible.

No Phase 2 work has started. Do not pre-commit Phase 2 schema changes
in any Phase 1 follow-up.
