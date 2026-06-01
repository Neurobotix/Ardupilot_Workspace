# test_suite Migration — Feature Phase 3E

Date/time: 2026-06-01T00:00:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase implementation evidence

Conclusion: PASS for no-SITL Phase 3E MAVLink-control/monitor-ownership proof.
Staged `assert_ready`, `WindMatrixAutoMissionControl`, and
`WindMatrixDisarmMonitor` no longer call or inject any `run_one.*` function.
They call plugin-owned `mavlink_control.*` helpers only. This is not live
proof. Phase 4 remains blocked until Phase 3G accepts a full zero-legacy staged
wind system with live proof.

Feature runbook:
`governance/runbooks/features/test_suite_migration/plan.md`

## Scope

Phase 3E moves MAVLink heartbeat readiness, vehicle-readiness checks, mission
upload, mission verification, arm, post-arm settle, AUTO mode control, and
mission completion monitoring from legacy runner delegation into test-suite-owned
plugin code:

In scope (now test-suite-owned, in `mavlink_control.py`; signatures are
verbatim ports of `run_one` — same names, parameters, and return shapes):

- `wait_for_heartbeat(mavlink_addr, timeout)` — connect, wait for first
  heartbeat or raise; returns the `mavutil` connection
- `wait_for_vehicle_ready(master, timeout, *, force_arm)` — wait for AUTO
  availability, GPS/EKF readiness, and `READY_HEARTBEATS_REQUIRED` clear beats
- `settle_after_arm_before_auto(master, settle_s)` — timed post-arm settle loop
- `wait_for_relative_altitude(master, min_relalt_m, timeout)` — altitude wait
- `mission_item_count(mission_file)` — load the QGC-WPL file and return its count
- `mission_item_int(wp, target_system, target_component)` — convert a loaded
  waypoint to a `MISSION_ITEM_INT` message
- `upload_mission(master, mission_file, timeout)` — upload the mission;
  returns the list of uploaded `MISSION_ITEM_INT` messages
- `verify_mission(master, uploaded_items, timeout)` — download and compare the
  vehicle mission item-by-item; raises on mismatch
- `arm_vehicle(master, timeout, force_arm)` — arm and await ARMED heartbeat
- `set_auto_mode(master, timeout)` — switch to AUTO and confirm via heartbeat
- `monitor_until_disarm(master, monitor_log, timeout_s, *, mission_pre_loaded,
  stop_on_square_loiter)` — passive monitor to disarm/timeout; returns the
  mission-progress state `dict` (same keys as `run_one`)

Constants added to `defaults.py` (verbatim copies of `run_one` values):

- `FORCE_ARM_MAGIC = 21196.0`
- `READY_HEARTBEATS_REQUIRED = 2`
- `PASSED_WAYPOINT_RE` (compiled regex)

Helper added to `defaults.py`:

- `coerce_int(val)` — coerce float/int/str to int (identical logic to run_one)

Slot-timeout source: `analysis_helpers.clamp_timeout_to_slot` is the single
source for staged readiness, control, and monitor slot clamping.

Out of scope (no change in this phase):

- `WindMatrixStimulus` runtime wind injection (`run_one.inject_wind` /
  `preloaded_wind_artifact`) → Phase 3F wind-injection substage.
- `_legacy_run_one_body` → legacy-mode-only delegate; correct and intended.
- `run_one.py`, `run_matrix.py`, `run_matrix_round_robin.py` → unmodified.

## Files Changed

- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/mavlink_control.py`
  (created — verbatim ports of eleven functions from `run_one`; no legacy
  import; constants/helpers from `defaults` + mission contract)
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/defaults.py`
  (added `FORCE_ARM_MAGIC`, `READY_HEARTBEATS_REQUIRED`, `PASSED_WAYPOINT_RE`,
  `coerce_int`)
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/environment.py`
  (`assert_ready` staged path now uses `mavlink_control.*` +
  `analysis_helpers.clamp_timeout_to_slot` + `defaults.utc_now()`; the
  `from . import legacy` import was removed from `assert_ready`; legacy-mode
  `assert_ready` still returns early as before; launch/cleanup from Phase 3D
  unchanged)
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/plugin.py`
  (`_LazyLegacyAutoMissionControl` renamed to `WindMatrixAutoMissionControl`;
  `_LazyLegacyDisarmMonitor` renamed to `WindMatrixDisarmMonitor`; both now
  inject `mavlink_control.*` + `analysis_helpers.clamp_timeout_to_slot` instead
  of `run_one`; `_legacy_run_one_body` / `LegacyDelegateStrategy` unchanged)
- `tests/unit/test_wind_matrix_mavlink_control.py` (new — parity tests for
  `mission_item_count`, `mission_item_int`, and `monitor_until_disarm`)
- `tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py` (extended
  with Phase 3E in-subprocess block and non-subprocess ownership class)
- `tests/unit/test_test_suite_phase3_staged_attempt.py` (updated for renamed
  ownership adapters)

Legacy runner scripts (`run_matrix.py`, `run_one.py`, `run_matrix_round_robin.py`,
`run_one_og.py`) were not modified.

## Why Phase 3E Exists

Phase 3D proved the staged environment launch and cleanup no longer call
`run_matrix.*` or `run_one.*`. But `WindMatrixEnvironment.assert_ready()` still
resolved `legacy.run_one_module()` for heartbeat, vehicle-readiness, and
slot-timeout, and `_LazyLegacyAutoMissionControl` / `_LazyLegacyDisarmMonitor`
still lazily imported `run_one` at execute time for mission upload/arm/mode and
`monitor_until_disarm`. Phase 3E removes those dependencies by porting the
eleven control/monitor/readiness helpers into plugin-owned `mavlink_control.py`
and rewiring `environment.py` and `plugin.py`.

## Dependency Audit

| Dependency | Phase 3E classification | Result |
| --- | --- | --- |
| `WindMatrixEnvironment.assert_ready()` calling `legacy.run_one_module()` for `wait_for_heartbeat` | Phase 3E blocker | Removed. `assert_ready` now calls `mavlink_control.wait_for_heartbeat`. |
| `WindMatrixEnvironment.assert_ready()` calling `legacy.run_one_module()` for `wait_for_vehicle_ready` | Phase 3E blocker | Removed. `assert_ready` now calls `mavlink_control.wait_for_vehicle_ready`. |
| `WindMatrixEnvironment.assert_ready()` calling `legacy.run_one_module()` for slot-timeout clamp | Phase 3E blocker | Removed. `analysis_helpers.clamp_timeout_to_slot` is used directly. |
| `_LazyLegacyAutoMissionControl` lazy `run_one` import for `upload_mission`, `verify_mission`, `arm_vehicle`, `set_auto_mode`, settle, altitude wait | Phase 3E blocker | Removed. `WindMatrixAutoMissionControl` now calls `mavlink_control.*`. |
| `_LazyLegacyDisarmMonitor` lazy `run_one` import for `monitor_until_disarm` | Phase 3E blocker | Removed. `WindMatrixDisarmMonitor` now calls `mavlink_control.monitor_until_disarm`. |
| `FORCE_ARM_MAGIC`, `READY_HEARTBEATS_REQUIRED`, `PASSED_WAYPOINT_RE`, `coerce_int` from `run_one` | Phase 3E blockers | Added to `defaults.py` with values verified equal to `run_one`. |
| `WindMatrixStimulus` runtime wind injection (`inject_wind` / `preloaded_wind_artifact`) | later-phase blocker | Unchanged. Phase 3F wind-injection substage owns this. |
| `_legacy_run_one_body` → `run_one.run_one` | legacy-mode-only delegate | Unchanged. Correct. |

## Phase 4 Core-Promotion Candidates

`mavlink_control.py` carries a note identifying candidates for future promotion
to `core/mavlink` once a second plugin validates the seam:

- `wait_for_heartbeat` — generic MAVLink protocol; no wind semantics.
- `mission_item_count` / `mission_item_int` — generic mission protocol helpers.
- Generic command-ack loop patterns used in `arm_vehicle` / `set_auto_mode`.

These remain plugin-owned until Phase 4 acceptance:

- `monitor_until_disarm` — wind-specific status classification and
  `success_square_only` / `success_full` semantics.
- `verify_mission` — wind-specific command special-cases.
- `wait_for_vehicle_ready` — wind-specific `READY_HEARTBEATS_REQUIRED` and
  arming check.
- `settle_after_arm_before_auto` — wind-specific settle loop.

Promotion decisions are Phase 4 work and are recorded here only as intent, not
as committed architecture.

## Commands Run

```
cd /home/ahmed/ardupilot_workspace_next

# focused new test
env/bin/python3 -m unittest tests/unit/test_wind_matrix_mavlink_control.py

# phase 3C/3D/3E zero-legacy foundation test
env/bin/python3 -m unittest tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py

# full unit suite
env/bin/python3 -m unittest discover -s tests/unit

# parity
env/bin/python3 -m unittest tests/parity/test_phase1_parity.py
make test-parity

# structure + evidence
make doctor
```

## Validation Results

| Check | Result |
| --- | --- |
| `test_wind_matrix_mavlink_control` (6 tests) | PASS |
| `test_test_suite_phase3c_zero_legacy_foundation` (5 tests, incl. Phase 3E) | PASS |
| `unittest discover -s tests/unit` (93 tests) | PASS |
| `test_phase1_parity.py` (9 tests) | PASS |
| `make test-parity` (9 tests) | PASS |
| `make doctor` | PASS |

## Residual Risk

- This is no-SITL Phase 3E MAVLink control/monitor-ownership proof, not live
  proof.
- Phase 3F and 3G remain required before any live zero-legacy staged wind case
  can be run.
- Runtime wind injection still calls `run_one.inject_wind` /
  `preloaded_wind_artifact` and is blocked until Phase 3F.
- Phase 4 second-plugin proof is blocked until Phase 3G is accepted.

## Phase 3E Acceptance Review

Date: 2026-06-01

| Criterion | Result | Evidence |
| --- | --- | --- |
| `assert_ready` (staged) calls no `run_one.*` / `run_matrix.*` | PASS | `environment.py` staged path now calls `mavlink_control.wait_for_heartbeat`, `mavlink_control.wait_for_vehicle_ready`, and `analysis_helpers.clamp_timeout_to_slot`. The `from . import legacy` import is absent from the `assert_ready` body. |
| `WindMatrixAutoMissionControl.execute()` calls no `run_one.*` | PASS | `plugin.py` `WindMatrixAutoMissionControl` injects and calls `mavlink_control.*` (upload, verify, arm, settle, set_auto). No lazy `run_one` import. |
| `WindMatrixDisarmMonitor.run()` calls no `run_one.*` | PASS | `plugin.py` `WindMatrixDisarmMonitor` injects and calls `mavlink_control.monitor_until_disarm`. No lazy `run_one` import. |
| `mavlink_control.py` reproduces legacy behavior (parity test) | PASS | `test_wind_matrix_mavlink_control`: `mission_item_count` / `mission_item_int` parity on the real mission file; `monitor_until_disarm` parity via scripted fake-master message streams for full-mission, square+loiter early stop, invalid_start_reason, and timeout paths. |
| Phase 3E in-subprocess import-blocker exercises staged assert_ready + control + monitor with legacy blocked | PASS | `test_test_suite_phase3c_zero_legacy_foundation`: Phase 3E block runs `assert_ready`, `WindMatrixAutoMissionControl.execute()`, and `WindMatrixDisarmMonitor.run()` inside the subprocess import-blocker. Any `run_one`/`run_matrix` import raises `AssertionError`. |
| Non-subprocess ownership test verifies adapter construction/wiring | PASS | `Phase3EControlMonitorOwnershipTests` in `test_test_suite_phase3c_zero_legacy_foundation`: verifies `WindMatrixAutoMissionControl` and `WindMatrixDisarmMonitor` call only `mavlink_control.*`, not `run_one.*`, without a subprocess blocker. |
| Legacy mode remains default and unchanged | PASS | `WindMatrixConfig().attempt_strategy == "legacy"`; `_legacy_run_one_body` / `LegacyDelegateStrategy` unmodified. |
| Legacy-mode `assert_ready` is unchanged (no-op early return) | PASS | Legacy branch of `assert_ready` returns early; no `mavlink_control` calls in the legacy branch. |
| No live SITL/Gazebo run | PASS | All tests run with mocked or fake-master MAVLink message streams. No real SITL process was started. |
| No Phase 3F/3G/4 work | PASS | Wind injection, BIN/artifacts, analysis, summary, live proof, and second-plugin work are untouched. |
| Legacy runner scripts (`run_matrix.py`, `run_one.py`) unmodified | PASS | Only plugin files touched. |

Remaining legacy dependencies after Phase 3E (later-phase blockers):

- `WindMatrixStimulus` runtime wind injection still calls `run_one.inject_wind`
  / `preloaded_wind_artifact`. **Phase 3F wind-injection substage owns this.**
- `_legacy_run_one_body` → `run_one.run_one`. **Legacy-mode-only delegate;
  correct and intended.**

## Phase 4 / wrapper / workspace statements

- Phase 4 was not started.
- No second plugin was added.
- Legacy runner scripts (`run_matrix.py`, `run_one.py`,
  `run_matrix_round_robin.py`, `run_one_og.py`) were not modified.
- The old workspace `/home/ahmed/ardupilot_workspace` was not modified.
