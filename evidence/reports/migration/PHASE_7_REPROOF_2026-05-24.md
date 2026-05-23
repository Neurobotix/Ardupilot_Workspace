# Phase 7 Reproof Review

Date/time: 2026-05-24T12:40:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Status: SUPERSEDED BY FINAL PHASE 7 CUTOVER PASS

## Scope

This report reviews the 2026-05-24 Phase 7 reproof logs under
`var/runs/phase7_reproof_20260524/` and the follow-up cleanup fix made after
Gazebo was observed to survive cleanup. It does not promote
`workspace_next`, does not deprecate the old workspace, and does not create a
cutover ADR.

The old workspace was not modified.

## Static Gate Results

The operator ran the static Phase 7 gate commands from a normal shell:

- `make doctor`: PASS.
- `make test-parity`: PASS, six parity tests.
- `scripts/ops/launch.sh help`: PASS.
- `env/bin/python3 -m unittest tests/unit/test_phase8_runtime_paths.py tests/parity/test_phase1_parity.py`: PASS, ten tests.
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/compat_scripts tests`: PASS.
- Runtime/import smoke for launch, bridge, analysis, wind-matrix, and
  `test_suite` modules: PASS with the known protobuf duplicate-descriptor
  warning noise.

After the cleanup patch in this pass, these validation commands were rerun:

- `bash -n src/sim_ard_gaw/compat_scripts/launch.sh`: PASS.
- `bash -n src/sim_ard_gaw/compat_scripts/cleanup.sh`: PASS.
- `env/bin/python3 -m unittest tests/unit/test_phase8_runtime_paths.py`: PASS,
  five tests including cleanup process-pattern coverage.
- `make test-parity`: PASS, six parity tests.
- `make doctor`: PASS.

## Workspace Plugin Proof

The workspace plugin exists and was selected as the only Gazebo plugin runtime:

- Plugin path: `build/ardupilot_gazebo/libArduPilotPlugin.so`.
- SHA-256:
  `1d4089bb6306ecc602e484e9b4e3e77dfb7ecf6649a4292ba872f6d420415fc0`.
- Size: `9395808` bytes.
- Runtime policy from `run_one.gazebo_plugin_diagnostics()`:
  `workspace_build_only`.
- Effective `GZ_SIM_SYSTEM_PLUGIN_PATH`:
  `/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo`.

## Representative Vehicle Proof

Representative vehicle proof is supported by the direct-shell plane smoke:

- SITL log: `var/runs/phase7_reproof_20260524/plane_smoke/plane.log`.
- Gazebo log: `var/runs/phase7_reproof_20260524/plane_smoke/gazebo-plane.log`.
- Cleanup log before the cleanup fix:
  `var/runs/phase7_reproof_20260524/plane_smoke/cleanup.log`.
- Working decoded summary:
  `var/working/runtime_capture/plane_capture_20260524T115831+0300.txt`.
- Raw tlog:
  `var/logs/mavproxy/plane/logs/2026-05-24/flight2/flight.tlog`.

The decoded summary records:

- 132 HEARTBEAT messages.
- GPS fix type 6 with 10 satellites visible.
- ArduPilot Ready, EKF3 initialisation, EKF3 GPS use, and AHRS EKF3 active.
- `Throttle armed` and `Armed AUTO`.
- Maximum relative altitude: 52.371 m.
- Maximum groundspeed: 22.339435577392578 m/s.

The Gazebo log records the workspace plugin search path as
`/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo`.

## Campaign / Evidence Workflow Result

The 2026-05-24 x=4, y=4 campaign attempt proves workspace-plugin wind
injection, but it does not close the representative campaign/evidence blocker
because the monitor budget expired before the mission disarmed.

Inputs and outputs:

- Console log: `var/runs/phase7_reproof_20260524/tiny_rr_console.log`.
- Campaign root: `var/runs/phase7_reproof_20260524/tiny_rr/`.
- Attempt directory:
  `var/runs/phase7_reproof_20260524/tiny_rr/wind_x_04_y_04/runs/attempt_001/`.
- Manifest: `var/runs/phase7_reproof_20260524/tiny_rr/manifest.json`.
- Attempt config:
  `var/runs/phase7_reproof_20260524/tiny_rr/wind_x_04_y_04/runs/attempt_001/run_config.json`.
- Wind injection record:
  `var/runs/phase7_reproof_20260524/tiny_rr/wind_x_04_y_04/runs/attempt_001/wind_injection.json`.

What it proves:

- The run used `config/vehicles/plane_base.parm` and
  `config/overlays/plane_airspeed.parm`.
- `local_param_override_present` was `false`.
- The attempt config records workspace-only Gazebo plugin diagnostics with the
  plugin SHA above.
- Wind injection requested x=4.0 m/s, y=4.0 m/s.
- Strict echo verification was enabled.
- `wind_injection.json` records `status: ok` and
  `verification: gz topic echo matched requested wind payload`.
- The parsed echo was x=4.0, y=4.0, z=0.0, `enable_wind: true`.
- The vehicle completed the square portion of the mission.

Why it does not close the campaign blocker:

- The manifest records `accepted_total: 0`.
- The harness attempt status is `failed` because the monitor timed out before
  disarm.
- `analysis_status` is `not_run`.
- The monitor timed out before vehicle disarm at `Mission: 23 LoitTurns`.
- `loiter_completed` and `mission_completed_full` are both `false`.

This is usable as wind-injection/plugin proof. It is not evidence of a
substantive wind-injection failure. It is also not, by the harness record, a
passing bounded campaign/evidence workflow; close that gate by rerunning with a
larger monitor/slot budget or by accepting square-only proof in governance.

## Cleanup Fix

During this review, the operator reported that cleanup did not kill Gazebo. The
pre-fix cleanup log only said `Cleanup complete`, which is not enough to prove
Gazebo process hygiene.

The cleanup implementation was updated in:

- `src/sim_ard_gaw/compat_scripts/launch.sh`;
- `src/sim_ard_gaw/compat_scripts/cleanup.sh`.

The fix adds targeted process-pattern cleanup for Gazebo Sim process shapes
that plain `pkill -x gz` can miss:

- `gz sim`;
- `gz-sim`;
- `ruby .../gz`;
- plus the existing ArduPilot, MAVProxy, `sim_vehicle.py`, and LiDAR bridge
classes.

The launcher cleanup now verifies that no matching simulator process remains
and returns failure if cleanup leaves a match.

At the time of this intermediate review, post-fix host-level cleanup proof had
not yet been run from a normal shell with a live Gazebo process. That gap was
closed later on 2026-05-24 by the final proof under
`var/runs/phase7_final_20260524/cleanup_proof/`.

## Files Changed By This Recovery Slice

- `evidence/indexes/evidence_catalog.md`
- `evidence/indexes/parameter_config_index.md`
- `src/sim_ard_gaw/compat_scripts/launch.sh`
- `src/sim_ard_gaw/compat_scripts/cleanup.sh`
- `tests/unit/test_phase8_runtime_paths.py`
- `docs/operations/sitl_gazebo_runtime.md`
- this report

## Intermediate Blockers Now Closed

At the time of this intermediate report, Phase 7 remained blocked by:

1. Post-fix host-level cleanup/process-hygiene proof.
2. A passing representative campaign/evidence workflow with enough monitor
   budget to reach the intended acceptance condition, or an explicit accepted
   governance decision that square-only campaign proof is sufficient for the
   Phase 7 cutover boundary.
3. A final shadow parity report after the cleanup fix and campaign decision.
4. An accepted cutover ADR, if and only if the final proof passes.

Those blockers are closed or explicitly accepted by
`governance/decisions/ADR-0005-workspace-next-cutover.md`.

## Conclusion

This pass fixes evidence truth alignment and the cleanup implementation gap at
the code/test/doc level. It also provides fresh representative plane proof and
workspace-plugin wind-injection proof. The campaign timeout is a proof-budget
issue, not a wind-injection failure. This intermediate report is superseded by
the final Phase 7 pass records below.

## 2026-05-24 Follow-Up Closure

The remaining cleanup and campaign proof gaps were closed by the final runtime
artifacts under `var/runs/phase7_final_20260524/`. The final decision is
recorded in:

- `evidence/reports/shadow_parity_2026-05-24.md`
- `evidence/reports/CUTOVER_2026-05-24.md`
- `governance/decisions/ADR-0005-workspace-next-cutover.md`
