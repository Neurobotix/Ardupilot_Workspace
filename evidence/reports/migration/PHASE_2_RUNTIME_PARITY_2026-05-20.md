# Phase 2 Runtime Parity

Date/time: 2026-05-20T16:42:37+03:00

Correction revision: 2026-05-21T08:55:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

This report supersedes the earlier 2026-05-20T15:23 Phase 2 report, which
concluded `BLOCKED`. The runtime smoke targets were executed in concurrent
operator terminals (SITL + Gazebo + bridge running together) and captured
direct SITL/Gazebo/MAVLink handshake evidence.

The 2026-05-21 correction revision adds the `copter-lidar`, `bridge-copter`,
and `logger` runtime runs (which the original 2026-05-20 report had left
untested/blocked), reconciles the runtime-output count after those runs, and
adds `docs/operations/migration_status.md` to Files Changed. The original
report's "core proof set PASS" wording was a narrowed gate and is corrected
here: all runbook-required smoke targets now have direct evidence.

## Scope

Phase 2 tested whether `/home/ahmed/ardupilot_workspace_next` can reproduce the
production runtime launch surface before trust or cutover. Production
`/home/ahmed/ardupilot_workspace` was used only as a read-only production
reference.

This phase did not perform cutover, did not deprecate the old workspace, and
did not perform major refactors. Vehicle/bridge/logger statuses were promoted
only where direct command evidence was captured.

## Files Changed

- `.ai/current.md`
- `.ai/issues/open.md`
- `docs/operations/launch_targets.md`
- `docs/operations/migration_status.md` (2026-05-21 correction — was stale)
- `docs/vehicles/status.md`
- `docs/architecture/simulation_lanes.md` (2026-05-21 correction — copter-lidar status)
- `evidence/reports/PHASE_2_RUNTIME_PARITY_2026-05-20.md`
- `evidence/curated_logs/phase_2_runtime_2026-05-20/` (curated per-target evidence)
- `governance/runbooks/phase_2_runtime_parity.md`
- `scripts/ops/capture_round.sh` (new — tlog decode tool with explicit reviewed promotion mode)
- `src/sim_ard_gaw/compat_scripts/launch.sh` (copter param fix, bridge `-u`)

Ignored local runtime state remains provisioned under `env/`, `src/ardupilot/`,
and `src/SITL_Models/`.

## Commands Run

- `/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help`
- `scripts/ops/launch.sh help`
- `source setup.bash`
- `make doctor`
- `make test-parity`
- `scripts/maintenance/validate_structure.sh`
- `python -m compileall -q src/sim_ard_gaw/compat_scripts tests`
- direct static imports of `lidar_bridge_unified`, `log_flight_data`,
  `wind_publisher_altitude` with `PYTHONPATH=src/sim_ard_gaw/compat_scripts`
- `scripts/ops/launch.sh wind-check-altitude`
- `scripts/ops/launch.sh cleanup`
- concurrent operator-terminal smoke runs (SITL + Gazebo, plus bridge for
  the LiDAR round):
  - `scripts/ops/launch.sh gazebo-plane` + `scripts/ops/launch.sh plane`
  - `scripts/ops/launch.sh gazebo-plane-cte` + `scripts/ops/launch.sh plane-cte`
  - `scripts/ops/launch.sh gazebo-plane-lidar` +
    `scripts/ops/launch.sh plane-lidar` + `scripts/ops/launch.sh bridge-plane`
  - `scripts/ops/launch.sh gazebo-copter` + `scripts/ops/launch.sh copter`
  - `scripts/ops/launch.sh gazebo-copter-lidar` +
    `scripts/ops/launch.sh copter-lidar` + `scripts/ops/launch.sh bridge-copter`
    (run 2026-05-21)
  - `scripts/ops/launch.sh gazebo-plane` + `scripts/ops/launch.sh plane` +
    `scripts/ops/launch.sh logger` (run 2026-05-21)
- historical fixed-name promotion command used for these Phase 2 summaries:
  `scripts/ops/capture_round.sh --promote-reviewed {plane,plane-cte,plane-lidar,copter,copter-lidar}`;
  new reviewed promotions require `--evidence-id` and a versioned curated
  artifact path.
- process scans with `pgrep -af` before/after cleanup
- raw log leakage scan excluding `.git`, `var`, `.private`, `src/ardupilot`,
  `src/SITL_Models`, `src/ardupilot_gazebo`, `env`

## Production Launch Target Summary

Production help command succeeded. Production target names:

`bridge-copter`, `bridge-plane`, `cleanup`, `copter`, `copter-lidar`,
`gazebo-copter`, `gazebo-copter-lidar`, `gazebo-plane`,
`gazebo-plane-airspeed-lidar`, `gazebo-plane-altitude-wind`,
`gazebo-plane-bench`, `gazebo-plane-cte`, `gazebo-plane-lidar`,
`gazebo-plane-rebuild`, `gazebo-plane-rebuild-wind`, `gazebo-plane-staircase`,
`gazebo-plane-wind`, `gazebo-plane-wind-sea-level`, `help`, `logger`,
`logger-csv`, `plane`, `plane-airspeed`, `plane-airspeed-lidar`,
`plane-altitude-wind`, `plane-cte`, `plane-lidar`, `plane-rebuild`,
`plane-staircase`, `wind-check-altitude`, `wind-publisher-altitude`.

## New Workspace Launch Target Summary

New workspace help command succeeded and exposed the same target names.

## Launch Target Differences

- Only in production: none.
- Only in `workspace_next`: none.
- Intentional behavior difference: `wind-check-altitude` remains visible in
  help but is retired in `workspace_next`. `scripts/ops/launch.sh
  wind-check-altitude` exited with code 2 and printed that
  `wind_altitude_log_check.py` was not present in production.
- Expected path difference: the raw help `Usage:` line names the production
  launcher path in the old workspace and the `workspace_next` launcher path in
  the new workspace.

## Static Checks

| Check | Result | Evidence |
| --- | --- | --- |
| `source setup.bash` | PASS | Printed workspace, assets, runtime, logs, and cache homes. |
| Python compile | PASS | `compileall` of `compat_scripts` and `tests` completed. |
| Static imports | PASS | `lidar_bridge_unified`, `log_flight_data`, `wind_publisher_altitude` all imported. |
| `make doctor` | PASS | Structure validation passed (see note below). |
| `make test-parity` | PASS | `Ran 3 tests ... OK`. |
| `scripts/maintenance/validate_structure.sh` | PASS | Structure validation passed. |

### Tooling issue found and resolved: `make doctor` ripgrep dependency

On re-check, `make doctor` initially FAILED. Root cause: the canonical
structure validator `scripts/maintenance/validate_structure.sh` calls `rg`
(ripgrep) for its `.private` policy and migration-plan-link checks. `rg` was not
installed on this machine, so the validator treated every reference scan as
"missing" and failed. `ripgrep` was installed via `apt`, after which
`make doctor` passed. This dependency is now documented in
`governance/runbooks/phase_2_runtime_parity.md` as a required-setup item.

## `make doctor` Result

Result: PASS.

```text
PASS: all required top-level homes exist
PASS: no broken symlinks
PASS: no raw .BIN/.bin/.tlog/.tlog.raw files outside allowed ignored/runtime areas
PASS: no nested .private directories under active homes
PASS: .private contains only allowed local pointer notes and no runnable logic
PASS: required runtime, private, and external dependency paths are ignored
PASS: no disallowed stale canonical references in non-archive docs/governance/AI
PASS: required migration-plan targets and entry-point references exist
STRUCTURE VALIDATION PASSED
```

## `make test-parity` Result

Result: PASS. `Ran 3 tests ... OK`.

## Structure Validation Result

Result: PASS. `scripts/maintenance/validate_structure.sh` passed.

## Runtime Smoke Results

All required runtime smoke targets were run in concurrent operator terminals.
Each `flight.tlog` was decoded into a curated evidence file under
`evidence/curated_logs/phase_2_runtime_2026-05-20/`. Raw `.tlog`/`.tlog.raw` files
remain under `var/` (ignored, disposable). This bootstrap workspace still has no
root Git commit, so these evidence files are not yet Git-tracked.

| Command | Result | Reason / evidence |
| --- | --- | --- |
| `scripts/ops/launch.sh plane` + `gazebo-plane` | PASS | 256 HEARTBEATs; GPS fix_type 6, 10 sats; EKF3 origin set + using GPS; `AHRS: EKF3 active`; `Throttle armed`; groundspeed 17.3 m/s (Gazebo physics coupling). `plane_evidence.txt`. |
| `scripts/ops/launch.sh plane-cte` + `gazebo-plane-cte` | PASS | 126 HEARTBEATs; EKF3 + GPS; `Throttle armed` + `Armed AUTO`; climbed to 46.9 m; groundspeed 23.1 m/s. `plane-cte_evidence.txt`. |
| `scripts/ops/launch.sh plane-lidar` + `gazebo-plane-lidar` | PASS | 199 HEARTBEATs; EKF3 + GPS; `Armed AUTO`; climbed to 52.5 m; groundspeed 22.4 m/s. `plane-lidar_evidence.txt`. |
| `scripts/ops/launch.sh copter` + `gazebo-copter` | PASS | 201 HEARTBEATs; EKF3 + GPS; `EKF3 IMU0 MAG0 in-flight yaw alignment complete`; `takeoff 10` reached 10.0 m relative altitude. `copter_evidence.txt`. |
| `scripts/ops/launch.sh gazebo-plane` | PASS | Mini Talon runway world loaded; `ArduPilotPlugin` initialized; SITL `plane` connected and flew (see `plane` row). |
| `scripts/ops/launch.sh gazebo-plane-cte` | PASS | Wind runway world loaded; SITL `plane-cte` connected and flew. |
| `scripts/ops/launch.sh gazebo-plane-lidar` | PASS | LiDAR runway world loaded; SITL `plane-lidar` connected and flew; LiDAR fed the bridge. |
| `scripts/ops/launch.sh gazebo-copter` | PASS | Iris runway world loaded; SITL `copter` connected, armed, and climbed. |
| `scripts/ops/launch.sh copter-lidar` | PASS | Run 2026-05-21 with `gazebo-copter-lidar` + `bridge-copter`. 793 HEARTBEATs, GPS fix 6, EKF3 + using GPS, armed, took off, flew to 4.04 m (Gazebo physics coupling). `bridge-copter` connected (`Connected to system 1`) and streamed 922 `DISTANCE_SENSOR` messages to ArduPilot. Caveat: the forward LiDAR returned no obstacle hit because the copter flew above the 3 m obstacle band; the SITL/Gazebo/MAVLink/bridge handshake is proven, an obstacle-detection return is not. `copter-lidar_evidence.txt`, `bridge-copter_console.txt`. |
| `scripts/ops/launch.sh cleanup` | PASS | Printed `Cleanup complete`; post-cleanup process scan found no simulator processes. |
| `scripts/ops/launch.sh wind-check-altitude` | PASS for retired behavior | Exited code 2 with retired-target message; not a runtime validation pass. |

### Runtime fixes made during Phase 2

Two real runtime defects were found and fixed in
`src/sim_ard_gaw/compat_scripts/launch.sh`:

1. **`copter` / `copter-lidar` would not arm** — `Arm: Motors: Check frame
   class and type`. The copter launchers passed no parameter file, so
   `FRAME_CLASS`/`FRAME_TYPE` were unset. Fix: both copter launchers now load
   `config/vehicles/copter_params.parm` (`FRAME_CLASS 1`, `FRAME_TYPE 1`) with
   `--add-param-file` and `--wipe-eeprom` so frame params apply
   deterministically. After the fix, `copter` armed and reached 10.0 m.
2. **`bridge-plane` produced no observable output** — Python block-buffers
   stdout when piped, so the bridge's connection/status prints never appeared.
   Fix: bridge launchers now run `python3 -u` (unbuffered). After the fix, the
   bridge console showed `Connected to system 1`, `Subscribed to /lidar`, and
   live `AGL` rangefinder readings.

## Bridge And Logger Result

| Command / check | Result | Reason / evidence |
| --- | --- | --- |
| `scripts/ops/launch.sh bridge-plane` | PASS | After the `-u` fix: `Connecting to ArduPilot on port 14550...` -> `Connected to system 1` -> `Subscribed to /lidar via Gazebo Transport`. 46 `AGL` readings; values tracked the plane's climb (1.83 m -> 35.60 m) then "out of range" above 40 m. Confirms end-to-end Gazebo LiDAR -> bridge -> MAVLink -> ArduPilot. `bridge-plane_console.txt`. |
| `scripts/ops/launch.sh logger` | PASS | Run 2026-05-21 against a live `plane` SITL MAVLink source. Logger connected (`Connecting to udp:127.0.0.1:14551...` -> `Connected to 1:0`), captured live telemetry and mode transitions, and wrote a 48 KB flight log to `var/logs/flight_logger/flight_20260521_065708.log` (raw, under `var/`, not promoted). Curated proof: `logger_evidence.txt`; the raw console stays under `var/logs/flight_logger/`. |
| Logger output path configuration | PASS | Logger wrote under `var/logs/flight_logger/` as configured; confirmed by the produced log file. |

## Cleanup Result

Result: PASS. `scripts/ops/launch.sh cleanup` printed `Cleanup complete`. The
post-cleanup `pgrep` scan found no `gz sim`, SITL, MAVProxy, or bridge
processes.

## Runtime Output Location Check

Result: PASS.

- `setup.bash` sets `ARDUPILOT_LOGS` to `var/logs` and caches under `var/cache`.
- SITL launch commands pass `--use-dir=var/runs/sitl/<target>`.
- SITL/MAVProxy launch commands pass `--aircraft=var/logs/mavproxy/<target>`.
- Logger configuration points to `var/logs/flight_logger/`.
- All 20 `.tlog`/`.tlog.raw` files present after the 2026-05-21 correction
  runs are under `var/`.
- Curated decoded summaries were promoted to
  `evidence/curated_logs/phase_2_runtime_2026-05-20/`; raw telemetry was not
  promoted. This bootstrap workspace still has no root Git commit, so these
  summaries are not yet Git-tracked.

## Raw Log Leakage Check

Result: PASS. The scan outside allowed ignored/runtime areas returned no files:

```bash
find . \( -path './.git' -o -path './var' -o -path './.private' \
  -o -path './src/ardupilot' -o -path './src/SITL_Models' \
  -o -path './src/ardupilot_gazebo' -o -path './env' \) -prune \
  -o -type f \( -iname '*.bin' -o -name '*.tlog' -o -name '*.tlog.raw' \) -print
```

## Unresolved Blockers

- `copter-lidar` proved the SITL/Gazebo/MAVLink/bridge handshake but the
  forward LiDAR returned no obstacle hit (the copter flew above the 3 m
  obstacle band). The handshake is proven; an obstacle-detection return is not.
- Non-core launch targets remain not yet tested (`plane-airspeed-lidar`,
  `plane-altitude-wind`, `plane-rebuild`, `plane-staircase`, and the matching
  Gazebo worlds). They are not in the Phase 2 required smoke set.
- Workspace Gazebo plugin build output `build/ardupilot_gazebo` is absent;
  Gazebo loaded through the system plugin path `/usr/local/lib/ardupilot_gazebo`.
- Gazebo/Python import paths emit protobuf duplicate-descriptor warnings on
  stderr; they are noisy but non-fatal (bridge imports verified to succeed).
- Legacy compatibility path `src/SIM_ARD_GAW` remains required by migrated
  scripts.
- `cleanup` still uses broad `pkill -9` patterns that are not scoped to this
  workspace and could affect unrelated or production-reference processes.
  Tracked as a known issue in `.ai/issues/open.md`.
- Production dirty state recorded in Phase 0 remains unresolved.

## Conclusion

Phase 2 status: PASS.

The Phase 2 exit gate requires that required static checks pass and that the
runtime smoke commands prove the expected SITL/Gazebo/bridge behavior directly.
Both conditions are met:

- Static checks, structure validation, launch-target surface comparison, and
  the retired-target check all pass.
- Every required runtime smoke target was run and produced direct evidence:
  `copter`, `copter-lidar`, `plane`, `plane-lidar`, `plane-cte`, the matching
  `gazebo-*` worlds, `bridge-plane`, `bridge-copter`, `logger`, and `cleanup`.
  Each vehicle/Gazebo target proved a SITL/Gazebo/MAVLink handshake;
  `plane-cte`, `plane-lidar`, `copter`, and `copter-lidar` additionally proved
  airborne flight.
- `bridge-plane` proved an end-to-end LiDAR data path with real terrain
  returns (Gazebo -> bridge -> MAVLink -> ArduPilot). `bridge-copter` proved
  the bridge MAVLink path (922 `DISTANCE_SENSOR` messages).
- `logger` connected to a live MAVLink source, captured telemetry, and wrote a
  flight log under `var/logs/flight_logger/`.

The one remaining caveat is that `copter-lidar` did not capture a LiDAR
obstacle return (a flight-path limitation, not a target failure); the runbook
requires the `copter-lidar` handshake, which is proven. Non-core launch targets
remain untested and are tracked in `.ai/issues/open.md`. Vehicle docs reflect
verified-in-`workspace_next` status only for the lanes with dated evidence
here; everything else stays production-reference-only.

The old workspace was not modified. The old workspace is not deprecated yet and
remains the production reference until a future cutover phase supported by
evidence.
