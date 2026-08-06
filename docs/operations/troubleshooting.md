# Troubleshooting

Common issues running ArduPilot SITL with Gazebo Sim in
`ardupilot_workspace_next`. This is the canonical troubleshooting reference.
Entries below marked "verified" were observed and resolved during 2026-05-20
runtime validation
(`evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`).

## `make doctor` reports missing references (verified)

If `make doctor` fails with many `ref missing:` lines, `ripgrep` is not
installed. The structure validator uses `rg`. Install it:
`sudo apt install ripgrep`.

## Vehicle target produces no heartbeat

A SITL vehicle launched with `-f JSON` waits for Gazebo. Running a vehicle
target alone (e.g. under a timeout) will never get a heartbeat. Always run the
Gazebo world target in a second terminal. Order: start Gazebo first, then the
vehicle.

## Copter will not arm: "Check frame class and type" (verified)

ArduCopter refuses to arm when `FRAME_CLASS`/`FRAME_TYPE` are unset. The
`copter` and `copter-lidar` launchers load `config/vehicles/copter_params.parm`
(`FRAME_CLASS 1`, `FRAME_TYPE 1`) with `--wipe-eeprom` so the frame applies
deterministically. If you see this error, confirm the launcher printed
`Applying copter params:` and that `config/vehicles/copter_params.parm` exists.

## Arming fails: "Need Position Estimate" (verified)

The EKF needs a few seconds after `EKF3 ... origin set` before it has a usable
position estimate. Wait for `EKF3 IMU0 is using GPS` and `AHRS: EKF3 active`
before arming. If it still fails immediately after `using GPS`, wait another
5-10 s and retry.

## LiDAR bridge shows no output (verified)

Python block-buffers stdout when piped, hiding the bridge's status. The bridge
launchers run `python3 -u` (unbuffered) so connection and `AGL` readings are
visible. A working bridge prints `Connected to system 1` and
`Subscribed to /lidar via Gazebo Transport`. Protobuf
`File already exists in database` lines on stderr are noisy but non-fatal.

## Gazebo: stale processes after a run

If Gazebo or SITL processes linger after a run, run
`scripts/ops/launch.sh cleanup` and confirm with
`pgrep -af 'gz sim|arduplane|arducopter|mavproxy'`. Cleanup uses broad
simulator process patterns by policy so the next governed run starts from a
clean stack. Do not use it while a simulator session you need to preserve is
running.

## Gazebo: model or world not found

Worlds resolve through `assets/worlds/`. Confirm `source setup.bash` ran so
`GZ_SIM_RESOURCE_PATH` is set. Missing upstream models usually mean
`src/SITL_Models/` is not provisioned.

## Runtime output location

All runtime output belongs under `var/` (ignored, disposable): SITL state in
`var/runs/sitl/<target>/`, MAVProxy telemetry in `var/logs/mavproxy/<target>/`,
logger output in `var/logs/flight_logger/`. Curated proof is promoted to
`evidence/`; raw `.tlog`/`.BIN` files are never committed.
