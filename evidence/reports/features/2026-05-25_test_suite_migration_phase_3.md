# test_suite Migration - Feature Phase 3 (Staged Attempt Runner)

Date/time: 2026-05-25T02:57:15+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase implementation evidence (no new runtime output)

Conclusion: PASS after review remediation, with staged runtime cutover
explicitly deferred

Feature runbook:
`governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`

## Scope

This report records feature-level Phase 3 of the `test_suite` migration:
splitting the wind-matrix attempt lifecycle into framework/plugin stages while
preserving the legacy delegate as the default runtime path.

Phase 3 does not retire wrappers, delete `run_one.py`, create a second plugin,
switch campaign defaults to staged mode, or claim live staged SITL/Gazebo
parity.

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.

## Files Changed

This pass builds on the accepted Phase 2 files that were already present in
the worktree.

- `src/sim_ard_gaw/campaigns/test_suite/core/attempt_runner.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/control.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/monitor.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/manifest.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/models.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/plugin.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/config.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/environment.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/stimulus.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/analyzers.py`
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_case.py`
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_suite.py`
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_round_robin.py`
- `tests/unit/test_test_suite_phase3_staged_attempt.py`
- `tests/parity/test_phase1_parity.py`
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- `docs/campaigns/wind_matrix.md`
- `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`
- `governance/runbooks/features/test_suite_migration/plan.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `evidence/indexes/evidence_catalog.md`
- this report

## Extraction Map Summary

| Legacy responsibility | Phase 3 owner |
| --- | --- |
| Wind injection and preloaded-world artifact | `plugins/wind_matrix/stimulus.py` |
| Mission upload, arm, settle, AUTO mode | `core/control.py` |
| Manual operator prompt | `core/control.py` |
| Heartbeat/readiness for staged mode | `plugins/wind_matrix/environment.py` |
| Disarm/waypoint completion monitor | `core/monitor.py` |
| BIN collection, legacy analysis helpers, run summary, wind verdict fields | `plugins/wind_matrix/analyzers.py` |
| Stage ordering and cleanup contract | `core/attempt_runner.py` |
| Generic + legacy manifest additivity | `core/manifest.py` |

## Staged Strategy Behavior

The wind plugin now accepts `WindMatrixConfig.attempt_strategy` and the new CLI
flag `--attempt-strategy {legacy,staged}`.

`legacy` is the default and still delegates to `run_one.run_one(...)`.

`staged` wires:

- `WindMatrixStimulus`
- `ManualMissionControl` or `MavlinkAutoMissionControl`
- `DisarmCompletionMonitor`
- `WindMatrixAnalyzer`
- `WindMatrixVerdictPolicy`

through `StagedStrategy`. The staged path intentionally blocks
`auto_wind_phase=after-takeoff` during plugin construction because the generic
stage order applies stimulus before control while the legacy behavior applies
wind after AUTO takeoff altitude.

## Review Remediation

Post-review Phase 3 blockers were fixed before acceptance:

- Staged BIN finalization now mirrors the legacy square-loiter early cleanup
  path and `BIN_FLUSH_DELAY_S` wait before `collect_bin_log()`.
- `WindMatrixAnalyzer` now catches terminal analyzer failures before generic
  manifest persistence and writes legacy-compatible plugin fields for error
  rows.
- Staged wind-matrix stimulus, control, and monitor failures now use the
  plugin's staged exception hook to persist legacy-compatible error rows
  before returning from `AttemptRunner.run()`.
- Unsupported `attempt_strategy=staged`, `auto_control=True`,
  `auto_wind_phase=after-takeoff` is rejected during plugin construction,
  before environment launch/readiness.

## Compatibility/Fallback Behavior

The legacy delegate path remains available and default. Existing CLI calls keep
their runtime behavior unless the operator explicitly passes
`--attempt-strategy staged`.

`run_one.py`, `run_matrix.py`, `run_matrix_round_robin.py`, and the
`compat_scripts/` wrappers were not retired or moved. No implementation logic
was added to `compat_scripts/`.

## Manifest Compatibility Proof

- Phase 2 generic fields remain additive.
- Existing legacy rows are updated only with additive generic fields.
- New staged rows can include legacy wind fields plus generic fields.
- Legacy wind fields round-trip unchanged in focused tests.
- `success_square_only` remains partial.
- `failed`, `error`, and `interrupted` do not count as accepted.

## Cleanup Proof

Focused Phase 3 tests cover cleanup on:

- success;
- ordinary failure;
- interrupt-like `KeyboardInterrupt`.

The implementation still calls cleanup from `AttemptRunner.run()` in `finally`.

## Commands Run

- `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests/unit/test_test_suite_phase3_staged_attempt.py`
- `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`
- `git status --short`
- `git diff --stat`
- `git diff --check`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `env/bin/python3 -m unittest discover -s tests/integration`
- `make test-parity`
- `make doctor`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m test_suite.cli.run_case --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m test_suite.cli.run_suite --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m test_suite.cli.run_round_robin --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_case --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_suite --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_round_robin --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 src/sim_ard_gaw/compat_scripts/run_one.py --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 src/sim_ard_gaw/compat_scripts/run_matrix.py --help`
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 src/sim_ard_gaw/compat_scripts/run_matrix_round_robin.py --help`

## Test Results

| Command | Result |
| --- | --- |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py` | PASS: 15 tests |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py` | PASS: 7 tests |
| `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py` | PASS: 8 tests |
| `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests` | PASS |
| `env/bin/python3 -m unittest discover -s tests/unit` | PASS: 42 tests |
| `env/bin/python3 -m unittest discover -s tests/integration` | PASS: 3 tests |
| `make test-parity` | PASS |
| `make doctor` | PASS |
| CLI help smoke | PASS |

## What Was Not Implemented

- Phase 4 second plugin.
- Phase 5 compatibility retirement.
- Staged mode as the default.
- Staged `auto_wind_phase=after-takeoff`.
- Live staged SITL/Gazebo campaign parity.

## Residual Risk

- Staged mode is structurally tested but not live-runtime proven.
- The staged analyzer delegates to legacy heavy analysis helpers; this reduces
  semantic drift but does not replace live campaign evidence.
- Direct legacy invocations still write legacy-only rows until a framework path
  appends generic fields. This is intentional compatibility behavior from
  Phase 2.

## Strict Self-Review

- `run_one.py` remains callable.
- Compatibility wrappers remain wrapper-only.
- Staged execution preserves the framework cleanup `finally` contract.
- Partial/fail/error/interrupted semantics remain correct in tests.
- Manifest compatibility survived focused and Phase 2 tests.
- Existing CLI help paths still work.
- No code landed in the wrong home.
- Docs, runbooks, evidence, and indexes reflect the opt-in staged truth.
- Phase 4 and Phase 5 were not implemented.

## Old-Workspace Modification Statement

The old workspace `/home/ahmed/ardupilot_workspace` was not modified during
this Phase 3 pass.
