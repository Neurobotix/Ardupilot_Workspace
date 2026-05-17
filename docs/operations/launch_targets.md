# Launch Targets

Source of truth for executable target names is:

```bash
scripts/ops/launch.sh help
```

Phase 2 runtime parity evidence:

- Latest report:
  `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`
- Production reference command:
  `/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help`
- New workspace command: `scripts/ops/launch.sh help`
- Result: target names match production except for the intentional
  `wind-check-altitude` behavior change described below.

Known policy:

- Phase 7 cutover passed on 2026-05-24 for the governed core workflows. See
  `evidence/reports/migration/CUTOVER_2026-05-24.md`,
  `evidence/reports/migration/shadow_parity_2026-05-24.md`, and
  `governance/decisions/ADR-0005-workspace-next-cutover.md`.
- `wind-check-altitude` is retired in this workspace because production
  referenced a missing altitude-wind log validator. The target remains visible
  in help for operator awareness, but it exits with a retired-target error
  instead of claiming validation.
- Logger output goes to `var/logs/flight_logger/`.
- Campaign runtime output remains under `var/`: current wind-matrix defaults
  route directly into `var/logs/`, and explicit Phase 5 campaign roots used
  `var/runs/`. Promote only reviewed campaign proof into `evidence/` through
  `docs/operations/evidence_workflow.md`.
- Launch and campaign entrypoints own the active simulator stack for the run
  and perform broad clean-run cleanup before new work.
- Gazebo runtime uses the workspace plugin build at
  `build/ardupilot_gazebo/libArduPilotPlugin.so`; installed plugin fallback is
  forbidden and entrypoints fail closed when that build output is missing.

## Parameter Stacks

The launcher resolves owned paths directly: worlds and missions come from
`assets/`, shared vehicle config is under `config/vehicles/`, overlays are
under `config/overlays/`, campaign lane config is under `config/campaigns/`,
and runtime output is under `var/`. The current wind-matrix runners remain a
compatibility layer, but their default path constants no longer route through
the retired root bridge. `.private/config/plane_params.local.parm` is an
optional local-only final overlay when a plane lane names it below.

`config/vehicles/plane_base.parm` is intentionally sensor-neutral. It contains
generic `AIRSPEED_*` defaults while keeping `ARSPD_TYPE` disabled. Gazebo
airspeed sensor enablement and lane-specific or high-wind airspeed overrides
come from `config/overlays/plane_airspeed.parm` or campaign lane files.

| Target or caller | Shared stack in applied order | Local override behavior |
| --- | --- | --- |
| `plane` | `config/vehicles/plane_base.parm` | Compatibility launcher appends `.private/config/plane_params.local.parm` only when it exists. |
| `plane-cte` / `plane-airspeed` | `config/vehicles/plane_base.parm` -> `config/overlays/plane_airspeed.parm` | Same optional local final overlay; `plane-cte` wipes EEPROM. |
| `plane-lidar` | `config/vehicles/plane_base.parm` -> `config/overlays/plane_lidar.parm` | Same optional local final overlay. |
| `plane-staircase` | `config/vehicles/plane_base.parm` -> `config/overlays/plane_lidar.parm` -> `config/overlays/staircase_plane_params.parm` | Same optional local final overlay. |
| `plane-airspeed-lidar` | `config/vehicles/plane_base.parm` -> `config/campaigns/mini_talon_airspeed_lidar/plane_full.parm` | Same optional local final overlay; the integrated target remains not yet tested in current evidence. |
| `plane-altitude-wind` | `config/vehicles/plane_base.parm` -> `config/campaigns/mini_talon_altitude_wind/plane_full.parm` | Same optional local final overlay; the altitude-wind target remains not yet tested in current evidence. |
| `plane-rebuild` | `config/vehicles/plane_params_rebuild.parm` | Launcher deliberately skips the local plane override. |
| `copter` / `copter-lidar` | `config/vehicles/copter_params.parm` | No `.private` config is appended by the launcher. |
| CTE `run_one.py` / `run_matrix.py` and current suite wrappers | `config/vehicles/plane_base.parm` -> `config/overlays/plane_airspeed.parm` | Default campaign callers append the local plane override when present unless `--no-param-local` or an explicit param stack says otherwise. |
| Legacy CTE `run_one_og.py` caller | `config/vehicles/plane_base.parm` -> `config/overlays/plane_airspeed.parm` | Retained legacy peer still appends the local plane override when invoked. |

For comparisons, record the effective parameter file list and content hashes
with the run evidence. Phase 5 wind-matrix evidence records that provenance in
the per-attempt run config and manifest record.

## Phase 2 Runtime Status

Phase 2 runtime parity is PASS. Phase 7 accepted this workspace as production
for the governed core cutover scope on 2026-05-24 with accepted residuals for
non-core target evidence. Every required
Phase 2 runtime smoke target was run in
concurrent operator terminals (SITL + Gazebo, plus the bridge for the LiDAR
lanes) and captured direct SITL/Gazebo/MAVLink handshake evidence. See
`evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md` and the per-target
curated captures in `evidence/curated_logs/phase_2_runtime_2026-05-20/`.

Two runtime defects were found and fixed during Phase 2:

- `copter` / `copter-lidar` would not arm (`Check frame class and type`). The
  copter launchers now load `config/vehicles/copter_params.parm`
  (`FRAME_CLASS`/`FRAME_TYPE`) with `--wipe-eeprom`.
- `bridge-plane` produced no observable output because Python block-buffers
  piped stdout. Bridge launchers now run `python3 -u`.

| Target | Phase 2 status | Evidence |
| --- | --- | --- |
| `copter` | PASS | 201 HEARTBEATs, EKF3 + GPS, in-flight yaw alignment, `takeoff 10` reached 10.0 m. `copter_evidence.txt`. |
| `copter-lidar` | PASS | 793 HEARTBEATs, EKF3 + GPS, armed, flew to 4.04 m. `bridge-copter` connected and streamed 922 `DISTANCE_SENSOR` messages. Caveat: forward LiDAR captured no obstacle return (copter flew above the obstacle band). |
| `plane` | PASS | 256 HEARTBEATs, EKF3 + GPS, `Throttle armed`, groundspeed 17.3 m/s. `plane_evidence.txt`. |
| `plane-lidar` | PASS | 199 HEARTBEATs, EKF3 + GPS, `Armed AUTO`, climbed to 52.5 m. `plane-lidar_evidence.txt`. |
| `plane-cte` | PASS | 126 HEARTBEATs, EKF3 + GPS, `Armed AUTO`, climbed to 46.9 m. `plane-cte_evidence.txt`. |
| `gazebo-plane` | PASS | Mini Talon runway world loaded; SITL `plane` connected and flew. |
| `gazebo-plane-cte` | PASS | Wind runway world loaded; SITL `plane-cte` connected and flew. |
| `gazebo-plane-lidar` | PASS | LiDAR runway world loaded; SITL `plane-lidar` connected and flew; LiDAR fed the bridge. |
| `gazebo-copter` | PASS | Iris runway world loaded; SITL `copter` connected, armed, and climbed. |
| `bridge-plane` | PASS | `Connected to system 1`, `Subscribed to /lidar`; 46 `AGL` readings tracked the climb (1.83 m -> 35.6 m). `bridge-plane_console.txt`. |
| `logger` | PASS | Connected to a live `plane` SITL MAVLink source on udp 14551, captured telemetry, and wrote a 48 KB flight log to `var/logs/flight_logger/`. |
| `cleanup` | PASS | Command completed and process scan found no remaining sim processes. |
| `wind-check-altitude` | PASS for retired behavior | Exits with code 2 and explains the target is retired. |
