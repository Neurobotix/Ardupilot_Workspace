# test_suite Migration - Feature Phase 3B

Date/time: 2026-05-29T15:49:25+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase audit evidence with live blocker

Conclusion: PASS for proving staged mode does not call `run_one.run_one(...)`;
BLOCKED as a replacement architecture because staged mode still depends on
legacy runner helper code. Phase 3C-3G are required before Phase 4.

Feature runbook:
`governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`

## Scope

This report records feature-level Phase 3B of the `test_suite` migration:
auditing the current staged `wind_matrix` path. It proves staged mode is not
hidden behind the single `run_one.run_one(...)` lifecycle body, and it records
that staged mode is still not a replacement system because it depends on
legacy runner helper code.

This is not Phase 4. No second plugin was added. Legacy wrappers and legacy
wind runners were not retired or deleted. This report does not accept generic
runtime readiness.

## Why Phase 3B Was Needed

Phase 3A added an opt-in staged path, but the default path remained the
wind-specific legacy delegate and the staged path still reused wind-specific
helpers. A second plugin would not prove generic framework readiness while the
first plugin still hid lifecycle delegation behind legacy wind code.

Phase 3B therefore separated three questions:

- Does staged `wind_matrix` secretly call `run_one.run_one(...)`? No.
- Does staged `wind_matrix` avoid legacy runner helper dependencies? No.
- Is staged `wind_matrix` live SITL/Gazebo proven? No, live proof is not
  accepted.

## Files Changed

- `tests/unit/test_test_suite_phase3_staged_attempt.py`
- `tests/parity/test_phase1_parity.py`
- `governance/runbooks/features/test_suite_migration/phase_3_staged_attempt_runner.md`
- `governance/runbooks/features/test_suite_migration/plan.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- `evidence/indexes/evidence_catalog.md`
- `.ai/index.md`
- this report

## Legacy-Delegation Audit

| Legacy call | Phase 3B classification |
| --- | --- |
| `run_one.run_one(...)` | Removed from staged lifecycle. Retained only by `LegacyDelegateStrategy`, which remains the default fallback. |
| `run_one.inject_wind` | Retained as a narrow stimulus helper behind `WindMatrixStimulus`. |
| `run_one.preloaded_wind_artifact` and wind echo helpers | Retained as narrow stimulus helpers behind `WindMatrixStimulus`. |
| `run_one.wait_for_heartbeat`, `wait_for_vehicle_ready` | Retained as readiness helpers behind `WindMatrixEnvironment.assert_ready`. |
| `run_one.upload_mission`, `verify_mission`, `arm_vehicle`, `set_auto_mode`, timeout helpers | Retained as injected MAVLink helpers behind `MavlinkAutoMissionControl`. |
| `run_one.monitor_until_disarm` | Retained as an injected helper behind `DisarmCompletionMonitor`. |
| `run_one.cleanup_stack_for_analysis`, `collect_bin_log`, `run_analysis`, `build_run_summary` | Retained as analyzer helpers behind `WindMatrixAnalyzer`. |
| `run_matrix.launch_sitl`, `launch_gazebo`, `cleanup_stack` | Retained as environment launch/cleanup helpers behind `WindMatrixEnvironment`. |

Follow-up self-review found additional legacy dependencies:

- staged plugin construction still builds the legacy delegate closure;
- `WindMatrixConfig` default factories import legacy runner modules;
- `WindMatrixCaseGenerator` imports legacy for combo-key formatting;
- generic `core.LegacyManifest` imports wind legacy;
- CLI parsing and bootstrap import legacy runner modules for defaults,
  validation, manifest setup, and logging.

## What Was Removed Vs Retained

Removed from staged lifecycle:

- hidden lifecycle delegation through `run_one.run_one(...)`;
- unstated reliance on the legacy body for staged stage order.

Retained, and now classified as blockers for the replacement architecture:

- legacy wind protocol helpers where they provide narrow behavior under
  plugin-owned staged adapters;
- default legacy fallback for compatibility.

## Retained Helper Justification

Helper reuse was useful for Phase 3A/3B learning, but it is not the final
architecture. Under the corrected goal, staged mode must not import or call
`run_one.py`, `run_matrix.py`, or `run_matrix_round_robin.py`. Phase 3C-3G
must replace these helpers with test-suite-owned modules while keeping legacy
mode available as the side-by-side fallback and comparison path.

## Test Coverage

Added or strengthened coverage for:

- staged orchestration-shell order without `run_one.run_one(...)`; later
  2026-05-31 strict-fix evidence adds boundary-mocked real-adapter coverage
  (`test_real_staged_wind_adapters_run_with_boundary_mocks`); no live staged
  wind proof; no full zero-legacy staged runtime proof; retained helper
  dependencies remain explicit blockers;
- cleanup on success, failure, and interrupt-like paths;
- terminal error rows on stimulus/control/monitor/analyzer failures;
- full, partial, failed, error, interrupted, and analysis-failure verdict and
  acceptance behavior;
- additive generic manifest fields with unchanged legacy wind fields;
- CLI default legacy behavior, explicit staged selection, and documented
  staged fail-closed behavior.

## Live Staged Wind Result Or Blocker

Live staged wind proof is not accepted.

Attempted commands:

```bash
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts timeout 300s env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_suite --attempt-strategy staged --auto-wind-phase before-arm --x-values 0 --y-values 0 --runs-per-combo 1 --max-attempts-per-combo 1 --campaign-root var/runs/test_suite_phase3b_staged_live_20260529 --wind-world-mode calm-runtime --no-param-local --wipe-eeprom --stack-settle-s 2 --retry-delay-s 0 --heartbeat-timeout 45 --ready-timeout 45 --mission-timeout 120 --upload-timeout 30 --arm-timeout 30 --mode-timeout 20
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts timeout 300s env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_suite --attempt-strategy staged --auto-wind-phase before-arm --x-values 0 --y-values 0 --runs-per-combo 1 --max-attempts-per-combo 1 --campaign-root var/runs/test_suite_phase3b_staged_live_20260529_no_wipe --wind-world-mode calm-runtime --no-param-local --stack-settle-s 2 --retry-delay-s 0 --heartbeat-timeout 45 --ready-timeout 45 --mission-timeout 120 --upload-timeout 30 --arm-timeout 30 --mode-timeout 20
```

Both recorded attempts failed during `WindMatrixEnvironment.launch()` before
Gazebo launch and before staged stimulus/control/monitor execution.
`sim_vehicle.py` started ArduPlane and MAVProxy, then exited before heartbeat
with `SIM_VEHICLE: MAVProxy exited`. The SITL log also recorded
`WARNING: no config for frame (JSON)`.

A later operator-run command with longer settle time reached heartbeat,
readiness, wind injection, mission upload, arm, AUTO mode, and waypoint 8, but
timed out before mission completion/disarm because the proof command used a
3-minute monitor timeout for a 30-item mission. That run is partial runtime
diagnostic evidence, not campaign success and not zero-legacy proof.

Raw runtime output:

- `var/runs/test_suite_phase3b_staged_live_20260529/`
- `var/runs/test_suite_phase3b_staged_live_20260529_no_wipe/`

Evidence still missing:

- one bounded staged wind attempt that reaches heartbeat/readiness;
- staged wind stimulus/control/monitor/analyzer completion under live
  SITL/Gazebo;
- an accepted staged wind manifest row from live runtime.
- zero-legacy staged implementation proof with legacy runner imports/calls
  blocked.

## Commands Run

- `date --iso-8601=seconds`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py`
- `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests/unit/test_test_suite_phase3_staged_attempt.py tests/parity/test_phase1_parity.py`
- the two bounded live staged commands above
- `PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 - <<'PY' ... run_matrix.cleanup_stack() ... PY`
- `command -v gz`
- `test -f build/ardupilot_gazebo/libArduPilotPlugin.so`
- `test -x src/ardupilot/Tools/autotest/sim_vehicle.py`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `env/bin/python3 -m unittest discover -s tests/integration`
- `make test-parity`
- `rg "Phase 3B|architecture theater|second plugin|legacy.*wind|wind-specific|generic" governance/runbooks/features/test_suite_migration src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md .ai evidence/indexes/evidence_catalog.md`
- `git diff --check`
- `make doctor`
- CLI help smoke for `test_suite.cli.run_case`, `test_suite.cli.run_suite`,
  `test_suite.cli.run_round_robin`, and the three owned
  `sim_ard_gaw.campaigns.test_suite.cli.*` module paths.

## Validation Results

| Command | Result |
| --- | --- |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py` | PASS: 20 tests |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py` | PASS: 7 tests |
| `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py` | PASS: 8 tests |
| focused `compileall` | PASS |
| full `compileall` | PASS |
| `env/bin/python3 -m unittest discover -s tests/unit` | PASS: 47 tests |
| `env/bin/python3 -m unittest discover -s tests/integration` | PASS: 3 tests |
| `make test-parity` | PASS: 8 tests |
| required `rg` scan | PASS |
| `git diff --check` | PASS |
| CLI help smoke | PASS |
| `make doctor` | PASS |
| bounded live staged wind, wipe EEPROM | BLOCKED: SITL/MAVProxy exited before heartbeat |
| bounded live staged wind, no wipe | BLOCKED: SITL/MAVProxy exited before heartbeat |
| cleanup after live attempts | PASS: `cleanup_stack complete` |

## Residual Risk

- Live staged wind proof is not accepted.
- Staged mode remains opt-in and must not become the default from this report.
- Retained legacy helpers still need live coverage before runtime readiness is
  claimed.
- Phase 3C-3G must remove staged dependencies on legacy runner code before
  replacement readiness is claimed.
- Phase 4 remains blocked because a second plugin cannot substitute for a
  zero-legacy first-plugin staged system.

## Phase 4 / Wrapper / Workspace Statements

- Phase 4 was not started.
- No second plugin was added.
- Legacy wrappers were not retired.
- `run_one.py`, `run_matrix.py`, and `run_matrix_round_robin.py` were not
  deleted.
- The old workspace `/home/ahmed/ardupilot_workspace` was not modified.
