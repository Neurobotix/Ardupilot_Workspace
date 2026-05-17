# Phase 8 Compatibility Retirement

Date/time: 2026-05-24T14:00:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Conclusion: PASS

## Scope

This report records the Phase 8 follow-up ownership pass after Phase 7 cutover.
It addresses the remaining Phase 8 compatibility blockers from
`evidence/reports/PHASE_8_COMPAT_RETIREMENT_2026-05-22.md`:

- real implementations still owned by `src/sim_ard_gaw/compat_scripts/`;
- symlink-backed organized launch, bridge, analysis, wind-matrix, and
  `test_suite` views;
- `test_suite` legacy import chokepoint into top-level runner modules.

The old workspace was not modified.

This report does not claim `copter-lidar` obstacle-return proof, non-core launch
target runtime smokes, or full wind-matrix evidence.

## Ownership Changes

Real implementation ownership now lives in organized homes:

| Area | Owned home after this pass |
| --- | --- |
| launch and cleanup | `src/sim_ard_gaw/launch/` |
| bridge and wind publisher scripts | `src/sim_ard_gaw/bridges/` |
| analysis, logging, and probe helpers | `src/sim_ard_gaw/analysis/` |
| wind-matrix runners | `src/sim_ard_gaw/campaigns/wind_matrix/` |
| campaign test-suite package | `src/sim_ard_gaw/campaigns/test_suite/` |

`src/sim_ard_gaw/compat_scripts/` remains as a thin compatibility-wrapper layer
for old imports and script paths. It delegates into the owned homes through
`_owned_wrapper.py` or shell `exec` wrappers. Do not add implementation logic
there.

## Compatibility State

Removed:

- organized symlinks under `src/sim_ard_gaw/launch/`;
- organized symlinks under `src/sim_ard_gaw/bridges/`;
- organized symlinks under `src/sim_ard_gaw/analysis/`;
- organized symlinks under `src/sim_ard_gaw/campaigns/wind_matrix/`;
- `src/sim_ard_gaw/campaigns/test_suite` symlink.

Retained:

- wrapper-only files under `src/sim_ard_gaw/compat_scripts/`;
- top-level `test_suite.*` compatibility import path when
  `src/sim_ard_gaw/compat_scripts` is on `PYTHONPATH`;
- old direct script paths such as `src/sim_ard_gaw/compat_scripts/run_one.py`.

`src/SIM_ARD_GAW` still exists: NO.

`compat_scripts/` still exists: YES, wrapper-only.

## Import And Path Fixes

- Owned `run_one.py` and `run_one_og.py` now derive the workspace root correctly
  from the deeper `campaigns/wind_matrix/` home when `ARDUPILOT_WORKSPACE` is
  not set.
- Owned `run_matrix.py` and `run_matrix_round_robin.py` support both package
  imports and direct script execution.
- Owned `compare_campaign_mission_window.py` supports both package import and
  direct script execution for its square/loiter metrics dependency.
- `test_suite.core._legacy` now imports owned
  `sim_ard_gaw.campaigns.wind_matrix.*` modules instead of top-level
  compatibility runner modules.

## Commands Run

Inspection and verification:

- `find src/sim_ard_gaw -maxdepth 4 -type l -print`
- import smoke for compatibility and owned runner/module paths
- `scripts/ops/launch.sh help`
- `env PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 -m test_suite.cli.run_round_robin --help`
- `env PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 src/sim_ard_gaw/compat_scripts/run_matrix.py --help`
- `bash -n src/sim_ard_gaw/launch/launch.sh src/sim_ard_gaw/launch/cleanup.sh src/sim_ard_gaw/compat_scripts/launch.sh src/sim_ard_gaw/compat_scripts/cleanup.sh`
- `env/bin/python3 -m unittest tests/unit/test_phase8_runtime_paths.py tests/unit/test_wind_world_safety.py tests/parity/test_phase1_parity.py tests/integration/test_phase5_wrapper_manifest_flow.py`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw tests`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `env/bin/python3 -m unittest discover -s tests/integration`
- `make test-parity`
- `pyright tests/unit/test_phase8_runtime_paths.py tests/unit/test_wind_world_safety.py`
- `make doctor`

## Validation Results

| Check | Result |
| --- | --- |
| organized symlink scan | PASS: no symlinks remain under `src/sim_ard_gaw` at max depth 4 |
| compatibility import smoke | PASS: top-level wrapper imports route to owned modules |
| owned import smoke | PASS: `sim_ard_gaw.campaigns.wind_matrix.run_one` resolves owned paths |
| launch help | PASS |
| test-suite CLI help through wrapper path | PASS |
| compatibility `run_matrix.py --help` | PASS |
| shell syntax | PASS |
| focused unit/parity/integration tests | PASS: 19 tests |
| compileall | PASS |
| unit discovery | PASS: 20 tests |
| integration discovery | PASS: 3 tests |
| `make test-parity` | PASS: 6 tests |
| focused pyright | PASS: 0 errors |
| `make doctor` | PASS: structure and evidence validators passed |

## Retained Wrapper Boundary

The remaining compatibility layer is intentionally small and wrapper-only. It is
safe to keep while old commands and tests still exercise legacy script names.
Remove it only after a separate compatibility-removal pass proves those old
paths are no longer needed.

## Conclusion

Phase 8 implementation ownership is retired from `compat_scripts/`. The old
root bridge is gone, organized runtime homes are real files/packages, and
compatibility is reduced to wrappers.
