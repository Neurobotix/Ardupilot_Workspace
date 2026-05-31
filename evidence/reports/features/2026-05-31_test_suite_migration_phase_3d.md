# test_suite Migration — Feature Phase 3D

Date/time: 2026-05-31T12:21:53+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase implementation evidence

Conclusion: PASS for no-SITL Phase 3D environment-ownership proof.
`WindMatrixEnvironment.launch()` and `.cleanup()` no longer call any
`run_matrix.*` or `run_one.*` function. They call plugin-owned `runtime.py`
helpers only. This is not live proof. Phase 4 remains blocked until
Phase 3G accepts a full zero-legacy staged wind system with live proof.

Feature runbook:
`governance/runbooks/features/test_suite_migration/plan.md`

## Scope

Phase 3D moves SITL/Gazebo process launch, static wind-world writing,
process-liveness checking, tail logging, and stack cleanup from legacy runner
delegation into test-suite-owned plugin code:

In scope (now test-suite-owned):

- `cleanup_stack()` — subprocess call to `launch.sh cleanup`
- `tail_text(path, max_chars=800)`
- `ensure_process_alive(name, proc, log_path)`
- `launch_process(cmd, cwd, log_path)` — `subprocess.Popen` wrapper
- `launch_sitl(log_path, no_rebuild, wipe_eeprom, *, use_dir, param_files)`
- `launch_gazebo(log_path, *, world_path)`
- `write_static_wind_world(x_wind, y_wind, output_path)`
- `preferred_python()` added to `defaults.py`
- Constants `SIM_VEHICLE`, `PLANE_WIND_WORLD`, `STACK_CLEANUP_TIMEOUT_S`

Out of scope (no change in this phase):

- `assert_ready()` heartbeat/vehicle-readiness/slot-timeout → Phase 3E.
- `_LazyLegacyAutoMissionControl` mission upload/arm/mode → Phase 3E.
- `_LazyLegacyDisarmMonitor` → Phase 3E.
- `WindMatrixStimulus` runtime wind injection → Phase 3F wind-injection substage.
- `_legacy_run_one_body` → legacy-mode-only delegate; correct and intended.

## Files Changed

- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/runtime.py` (created)
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/defaults.py` (added `preferred_python()`)
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/environment.py` (rewired `launch()`/`cleanup()`)
- `tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py` (Phase 3D in-subprocess + unit test)
- `governance/runbooks/features/test_suite_migration/review.md` (Phase 3D acceptance table)
- `governance/runbooks/features/test_suite_migration/evidence.md` (Phase 3D pointer)
- `evidence/reports/features/2026-05-29_test_suite_migration_phase_3c.md` (dependency-audit row split)
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md` (Stage 3D implemented note)
- `evidence/indexes/evidence_catalog.md` (new row)
- `.ai/index.md` (Phase 3D pointer)

Legacy runner scripts (`run_matrix.py`, `run_one.py`, `run_matrix_round_robin.py`,
`run_one_og.py`) were not modified.

## Why Phase 3D Exists

Phase 3C proved the staged foundation (config, case generation, manifest,
plugin construction, CLI bootstrap) could be constructed with legacy runner
imports blocked. But `WindMatrixEnvironment.launch()` and `.cleanup()` still
called `legacy.run_matrix_module()` at runtime, making the staged runtime path
not zero-legacy. Phase 3D removes that dependency by porting the seven launch/
cleanup helpers into plugin-owned `runtime.py` and rewiring `environment.py`.

## Dependency Audit

| Dependency | Phase 3D classification | Result |
| --- | --- | --- |
| `WindMatrixEnvironment.launch()` calling `legacy.run_matrix_module()` for `launch_sitl`, `launch_gazebo`, `cleanup_stack`, `write_static_wind_world`, `ensure_process_alive` | Phase 3D blocker | Removed. All calls now go through `runtime.*`. |
| `WindMatrixEnvironment.launch()` calling `legacy.run_one_module()` for `sitl_bin_dir` | Phase 3D blocker | Removed. `defaults.sitl_bin_dir(...)` is used directly. |
| `WindMatrixEnvironment.cleanup()` calling `legacy.run_matrix_module().cleanup_stack()` | Phase 3D blocker | Removed. `runtime.cleanup_stack()` is called directly. |
| `preferred_python()` from `run_one` | Phase 3D blocker | Added as `defaults.preferred_python()`. |
| `run_matrix.CLEANUP_TIMEOUT_S` (30.0) | Phase 3D blocker | Now `runtime.STACK_CLEANUP_TIMEOUT_S = 30.0`. |
| `run_matrix.SIM_VEHICLE` / `PLANE_WIND_WORLD` | Phase 3D blocker | Now `runtime.SIM_VEHICLE` / `runtime.PLANE_WIND_WORLD`. |
| `WindMatrixEnvironment.assert_ready()` calling `legacy.run_one_module()` | later-phase blocker | Unchanged. Phase 3E owns this. |
| `_LazyLegacyAutoMissionControl` lazy `run_one` import at execute time | later-phase blocker | Unchanged. Phase 3E owns this. |
| `_LazyLegacyDisarmMonitor` lazy `run_one` import at execute time | later-phase blocker | Unchanged. Phase 3E owns this. |
| `WindMatrixStimulus` runtime wind injection (`inject_wind` / `preloaded_wind_artifact`) | later-phase blocker | Unchanged. Phase 3F wind-injection substage owns this. |
| `_legacy_run_one_body` | legacy-mode-only delegate | Unchanged. Correct. |

## Commands Run

```
cd /home/ahmed/ardupilot_workspace_next

# compile check
env/bin/python3 -m py_compile tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py
env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests

# focused tests
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m unittest \
  tests.unit.test_test_suite_phase3c_zero_legacy_foundation -v

PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m unittest \
  tests.unit.test_test_suite_phase3_staged_attempt -v

# full test suites
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m unittest \
  discover -s tests/unit

PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m unittest \
  discover -s tests/integration

# parity and CLI
make test-parity

for m in run_case run_suite run_round_robin; do
  PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 \
    -m sim_ard_gaw.campaigns.test_suite.cli.$m --help >/dev/null && echo "$m OK"
done

# pyright (modulo pymavlink pre-existing env artifact)
/home/ahmed/.local/bin/pyright \
  src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/runtime.py \
  src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/environment.py \
  src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/defaults.py

make doctor
```

## Validation Results

| Check | Result |
| --- | --- |
| `py_compile` test file | PASS |
| `compileall` test_suite + tests | PASS |
| `test_test_suite_phase3c_zero_legacy_foundation` (4 tests, incl. Phase 3D) | PASS |
| `test_test_suite_phase3_staged_attempt` (23 tests) | PASS |
| `unittest discover -s tests/unit` (56 tests) | PASS |
| `unittest discover -s tests/integration` (3 tests) | PASS |
| `make test-parity` (9 tests) | PASS |
| `run_case --help` | PASS |
| `run_suite --help` | PASS |
| `run_round_robin --help` | PASS |
| pyright runtime.py + environment.py + defaults.py | PASS (1 pre-existing `pymavlink` error) |
| `make doctor` | PASS |

## Residual Risk

- This is no-SITL Phase 3D environment-ownership proof, not live proof.
- Phase 3E, 3F, 3G remain required before any live zero-legacy staged wind
  case can be run.
- `assert_ready()` heartbeat / vehicle-readiness / slot-timeout still call
  `legacy.run_one_module()` and are blocked until Phase 3E.
- Runtime wind injection still calls `run_one.inject_wind` /
  `preloaded_wind_artifact` and is blocked until Phase 3F.
- MAVLink control/monitor still lazily import `run_one` at execute time and
  are blocked until Phase 3E.
- Phase 4 second-plugin proof is blocked until Phase 3G is accepted.

## Phase 4 / wrapper / workspace statements

- Phase 4 was not started.
- No second plugin was added.
- Legacy runner scripts (`run_matrix.py`, `run_one.py`,
  `run_matrix_round_robin.py`, `run_one_og.py`) were not modified.
- The old workspace `/home/ahmed/ardupilot_workspace` was not modified.
