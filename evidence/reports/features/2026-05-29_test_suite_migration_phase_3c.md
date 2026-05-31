# test_suite Migration - Feature Phase 3C

Date/time: 2026-05-29T20:43:50+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase implementation evidence

Conclusion: PASS only for the Phase 3C no-SITL legacy-runner import blocker
and current core/plugin foundation boundary. It does not prove staged runtime
independence: the execution path still reaches legacy runner helpers during
environment launch/readiness, MAVLink control/monitoring, wind injection,
artifacts, analysis, summary, and terminal-row helpers until Phase 3D-3G
replace those pieces.

Correction on 2026-05-30: the first Phase 3C correction still left generic
core decoding wind legacy status strings in `core/attempt_runner.py`. That was
a boundary failure. The status decoder is now removed; staged core status comes
from framework verdicts or an explicit framework `AttemptStatus` supplied by
the plugin, not from plugin legacy manifest strings.

Second correction on 2026-05-30: default staged wind construction previously
failed because the generic staged opt-in inherited the legacy-only
`auto_wind_phase="after-takeoff"` default. Staged auto construction now
defaults to `before-arm`; explicit staged `after-takeoff` remains fail-closed.
Campaign summaries now use the same `accept_square_only` policy as
`WindMatrixManifest.accepted_count()`.

Third correction on 2026-05-31: follow-up review found that the plugin-owned
wind manifest had lost the legacy temp-file-rename atomic write behavior, the
staged runner did not prewrite a durable `running` record before
environment/runtime work, and `WindMatrixStimulus._write_run_config()` still
used avoidable legacy constants and path helpers. The follow-up fix restores
atomic writes for the plugin manifest/summary outputs, prewrites and
terminalizes staged manifest rows for ordinary failures before and during
runtime execution, reconciles stale `running` rows as `interrupted` before
later attempts allocate indices, and moves stimulus config/path/provenance
helpers to plugin-owned defaults/shared campaign helpers. Runtime wind
injection itself remains Phase 3F legacy-helper work.

Fourth correction on 2026-05-31 (follow-up review H-1 .. H-9): the staged
analyzer was migrated to plugin-owned `plugins/wind_matrix/analysis_helpers.py`
(BIN collection, analysis, run summary, analysis cleanup, run-alias linking,
slot-timeout clamp), so the analysis substage of Phase 3F no longer imports
`run_one`; the Phase 3C import-blocker hard test now executes
`WindMatrixAnalyzer.analyze()` to success under the blocker. Staged
running/terminal manifest rows now record the canonical `attempt_NNN`
directory. Runtime wind injection (stimulus), environment launch/readiness, and
MAVLink control/monitor execution still reach legacy runner helpers and remain
Phase 3D/3E/3F work. See
`evidence/reports/features/2026-05-31_test_suite_phase3c_followup_fixes.md` and
`governance/audits/2026-05-31_test_suite_phase3c_followup_findings.md`.

Feature runbook:
`governance/runbooks/features/test_suite_migration/plan.md`

## Scope

Phase 3C removes legacy runner-module imports from staged foundation setup
only:

- config/defaults;
- case naming/generation;
- manifest creation, additive generic fields, accepted-count, and
  next-attempt bookkeeping;
- plugin construction/bootstrap and `plugin.attempt_runner()`;
- CLI argument parsing/bootstrap;
- the flagged wind-matrix manifest and wind/square monitor behavior in
  generic core.

The staged runtime path is still not zero-legacy. The Phase 3C PASS label must
not be read as a claim that executing `WindMatrixEnvironment`,
`WindMatrixStimulus`, control/monitor adapters, or analyzers can run with
legacy runner modules blocked.

Out of scope:

- SITL/Gazebo launch;
- MAVLink readiness/control/monitor execution;
- wind injection;
- BIN/artifact collection;
- analysis and run-summary generation;
- live campaign proof.

## Why Phase 3C Exists

Phase 3B proved staged mode did not call the monolithic
`run_one.run_one(...)` body, but it also found staged construction still
depended on legacy runner modules. A follow-up review also found that generic
core still contained wind-matrix manifest and monitor behavior. Phase 3C is
the first cleanup step toward a real staged system: staged foundation setup
must be constructible while imports of these legacy runner modules are blocked:

- `sim_ard_gaw.campaigns.wind_matrix.run_one`
- `sim_ard_gaw.campaigns.wind_matrix.run_matrix`
- `sim_ard_gaw.campaigns.wind_matrix.run_matrix_round_robin`

## Files Changed

- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/defaults.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/legacy.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/manifest.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/monitor.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/config.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/case_generator.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/plugin.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/environment.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/stimulus.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/analyzers.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/manifest.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/monitor.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/attempt_runner.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/models.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/control.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/scheduler.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/stimulus.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/_legacy.py` deleted
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_case.py`
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_suite.py`
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_round_robin.py`
- `tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py`
- `tests/unit/test_test_suite_phase3_staged_attempt.py`
- `tests/unit/test_test_suite_manifest_generic_view.py`
- `tests/parity/test_phase1_parity.py`
- `tests/integration/test_phase5_wrapper_manifest_flow.py`
- `governance/runbooks/features/test_suite_migration/plan.md`
- `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- `evidence/indexes/evidence_catalog.md`
- `.ai/index.md`
- this report

## Dependency Audit

| Dependency | Phase 3C classification | Result |
| --- | --- | --- |
| `WindMatrixConfig` default factories importing `run_one` / `run_matrix` | should move into test_suite-owned code | Moved to `plugins/wind_matrix/defaults.py`. |
| `WindMatrixCaseGenerator` importing `run_one.combo_key` | should move into test_suite-owned code | Moved to plugin-owned `combo_key()` and `combo_order()`. |
| `core.LegacyManifest` importing `run_one.load_manifest`, `save_manifest`, `combo_successes`, and `next_attempt_index` | blocker | Removed from generic core. Replaced by plugin-owned `WindMatrixManifest`. |
| `core/manifest.py` hardcoding wind fields, combo keys, CSV fields, summaries, and wind-specific generic fallback behavior | blocker | Removed from generic core. Wind-compatible behavior lives in `plugins/wind_matrix/manifest.py`. |
| `core/monitor.py` writing `wind_monitor_state` and checking square/loiter mission fields | blocker | Removed from generic core. Wind/square completion behavior lives in `plugins/wind_matrix/monitor.py`. |
| `core/attempt_runner.py` decoding `success_full` and `success_square_only` from plugin manifest fields | blocker | Removed from generic core. Staged framework status now comes from the framework verdict or explicit plugin-supplied `AttemptStatus`; wind legacy mappings remain plugin-owned. |
| core docstrings modeling framework abstractions after wind legacy runners | blocker | Rewritten so core docstrings describe generic framework contracts instead of wind runner provenance. |
| CLI parsers importing legacy modules for defaults and validation | should move into test_suite-owned code | Replaced with plugin-owned defaults and validation. |
| CLI bootstrap importing legacy modules for manifest setup, param stack resolution, mission item count, and logging | should move into test_suite-owned code | Replaced with shared mission-contract validation, plugin-owned defaults/helpers, and `WindMatrixManifest`. |
| staged `build_plugin(...)` constructing `_legacy_run_one_body(config)` | blocker for Phase 3C | Removed from staged construction; legacy delegate closure is built only for `attempt_strategy="legacy"`. |
| staged `plugin.attempt_runner()` importing `run_one` for control/monitor construction | blocker for Phase 3C | Replaced with lazy runtime adapters; no import occurs during foundation construction. |
| default staged config inheriting legacy-only `auto_wind_phase="after-takeoff"` | blocker | Staged auto defaults now resolve to `before-arm`; explicit staged `after-takeoff` still fails closed. |
| campaign summary counting `success_square_only` under strict acceptance | blocker | Summary generation now respects `accept_square_only`, matching `WindMatrixManifest.accepted_count()`. |
| plugin-owned `WindMatrixManifest` non-atomic `manifest.json` / CSV writes | blocker found in 2026-05-31 review | Fixed with temp-file-rename writes for plugin manifest and summary outputs. |
| staged `AttemptRunner.run()` writing only after `strategy.execute(...)` returns | blocker found in 2026-05-31 review | Fixed for staged mode: a `running` row is persisted before environment work, ordinary failures are terminalized, and later allocation reconciles stale `running` rows as `interrupted`. |
| `WindMatrixStimulus._write_run_config()` and `_ensure_attempt_dir()` using legacy constants/path/provenance helpers | blocker found in 2026-05-31 review | Avoidable constants, path helpers, run-config JSON writing, mission validation, parameter provenance, SITL BIN path, and plugin diagnostics now use plugin-owned defaults or shared campaign helpers. |
| `WindMatrixEnvironment` runtime launch/readiness/cleanup helpers | later-phase blocker, outside Phase 3C foundation | Still imports/calls legacy modules when runtime methods execute. Phase 3D owns removal. |
| staged MAVLink control and monitor execution helpers | later-phase blocker, outside Phase 3C foundation | Still lazy-import `run_one` when executed. Phase 3E owns removal. |
| `WindMatrixStimulus` wind injection | later-phase blocker, outside Phase 3C foundation | Runtime wind injection still imports/calls `run_one.inject_wind` / `preloaded_wind_artifact` when executed. Phase 3F wind-injection substage owns removal. |
| `WindMatrixAnalyzer` BIN/analysis/summary helpers | migrated 2026-05-31 (Phase 3F analysis substage) | The staged analyzer now imports BIN collection, analysis, summary, cleanup, run-alias, and slot-timeout helpers from plugin-owned `plugins/wind_matrix/analysis_helpers.py`; it no longer imports `run_one`. The Phase 3C hard test executes `WindMatrixAnalyzer.analyze()` to success with legacy runner imports blocked. See `evidence/reports/features/2026-05-31_test_suite_phase3c_followup_fixes.md`. |
| Staged terminal error-row builder using `ctx.attempt_dir` | corrected 2026-05-31 (H-1) | `build_wind_matrix_error_fields` and `build_wind_matrix_running_record` re-derive the canonical `attempt_NNN` directory from the attempt index. |
| `plugins/wind_matrix/legacy.py` shim and legacy delegate body | legacy-only and acceptable | Retained for default legacy mode and retained staged runtime helpers assigned to later phases. |

## What Was Removed From Staged Foundation

- legacy-runner imports from staged config/default construction;
- legacy-runner imports from staged case generation;
- legacy-runner imports from staged manifest creation and bookkeeping;
- legacy-runner imports from CLI parser/bootstrap defaults;
- eager legacy delegate construction during staged plugin build;
- eager legacy control/monitor helper imports during staged
  `plugin.attempt_runner()` construction;
- legacy-only after-takeoff default from staged auto construction;
- wind-matrix manifest implementation, CSV/summary generation, combo-key
  logic, and wind-specific generic fallbacks from `core/manifest.py`;
- wind/square mission completion assumptions from `core/monitor.py`;
- wind legacy status-string decoding from `core/attempt_runner.py`;
- wind legacy runner provenance wording from core docstrings.

## What Remains For Later Phases

- Phase 3D: replace staged environment/runtime launch, world writing, cleanup,
  diagnostics, and timeout helpers.
- Phase 3E: replace staged MAVLink readiness/control/monitor execution.
- Phase 3F: replace staged wind stimulus, BIN/artifacts, analysis, summary,
  and terminal error-row behavior.
- Phase 3G: prove the full zero-legacy staged wind system live beside the
  retained legacy mode.

## Tests Added

`tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py` runs an isolated
Python process with a meta-path import blocker for the three legacy runner
modules. It proves the narrow import-blocker claim:

- staged config creation works;
- staged case generation works;
- staged manifest creation and generic view work;
- default staged plugin construction and `plugin.attempt_runner()` work;
- CLI parsers keep legacy as default, staged as explicit opt-in, and staged
  auto defaults to `before-arm`;
- staged `run_suite.main()` and `run_round_robin.main()` bootstrap work with
  explicit `--auto-wind-phase before-arm` when runtime execution is patched
  out;
- no blocked legacy runner module is imported during staged foundation setup.

The same test file also scans every `core/*.py` file for the flagged
wind-matrix tokens, including `success_full` and `success_square_only`. It
also has a behavioral check proving `StagedStrategy` does not interpret a
plugin legacy manifest `status` string as the framework `AttemptStatus`.
Those checks prove only the named Phase 3C foundation violations were removed
from generic core; they do not prove live staged execution or full generic
runtime readiness.

## Commands Run

- `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_case --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_suite --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_round_robin --help`
- `rg "run_one|run_matrix|run_matrix_round_robin|Phase 3C|zero-legacy|legacy runner" src/sim_ard_gaw/campaigns/test_suite tests governance/runbooks/features/test_suite_migration evidence/reports/features`
- `git diff --check`
- `make doctor`
- `/home/ahmed/.local/bin/pyright src/sim_ard_gaw/campaigns/test_suite/core/attempt_runner.py src/sim_ard_gaw/campaigns/test_suite/core/models.py tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py`

## Validation Results

| Command | Result |
| --- | --- |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py` | PASS: 3 tests |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py` | PASS: 21 tests |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py` | PASS: 7 tests |
| `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests` | PASS |
| `env/bin/python3 -m unittest discover -s tests/unit` | PASS: 51 tests |
| CLI help smoke for `run_case`, `run_suite`, `run_round_robin` | PASS |
| required `rg` scan | PASS |
| `git diff --check` | PASS |
| `make doctor` | PASS |
| focused `pyright` diagnostic | PASS: 0 errors |

## Residual Risk

- Live zero-legacy runtime is not proven.
- Staged runtime methods still have legacy runner dependencies assigned to
  Phase 3D-3F.
- The full staged system is not replacement-ready until Phase 3G has hard
  no-legacy tests plus bounded live staged wind proof and matching legacy
  comparison.
- The Phase 3C tests prove blocked imports during foundation setup, default
  staged construction, explicit staged CLI bootstrap for the supported
  `before-arm` path, absence of flagged wind tokens in generic core files, and
  no core decoding of plugin legacy status strings. They do not prove that all
  future plugin types can ship without framework changes.

## Phase 4 / Wrapper / Workspace Statements

- Phase 4 was not started.
- No second plugin was added.
- Legacy scripts were not retired.
- `run_one.py`, `run_matrix.py`, and `run_matrix_round_robin.py` were not
  deleted.
- The old workspace `/home/ahmed/ardupilot_workspace` was not modified.
