# Simulation Lanes

The project runs several Mini Talon (and Iris) simulation lanes. They serve
different purposes and are not interchangeable. This is the canonical lane
reference and replaces the archived
`docs/archive/src_docs/SIMULATION_LANES.md`.

The executable source of truth for target names is `scripts/ops/launch.sh help`.
Per-target runtime status is in `docs/operations/launch_targets.md`.

## Rules

- `base` is sensor-neutral: no airspeed dependency, no LiDAR dependency.
- `airspeed` / `cte` uses Gazebo wind as the only wind source.
- `lidar` uses the MAVLink bridge path for rangefinder data.
- `bench` worlds are isolation harnesses, not flight-ready operating worlds.
- `rebuild` is a separate investigation lane with its own params and worlds.
- Legacy all-in-one plane parameter snapshots live under `config/archive/`.

## Lane map

| Lane | Purpose | Launcher | Bridge | Phase 2 status |
| --- | --- | --- | --- | --- |
| Base plane | Clean fixed-wing baseline | `plane` + `gazebo-plane` | No | Verified |
| CTE / airspeed | Wind and pitot validation | `plane-cte` + `gazebo-plane-cte` | No | Verified |
| LiDAR | Terrain / rangefinder work | `plane-lidar` + `gazebo-plane-lidar` + `bridge-plane` | Yes | Verified |
| Copter base | Iris baseline | `copter` + `gazebo-copter` | No | Verified |
| Copter LiDAR | Iris obstacle work | `copter-lidar` + `gazebo-copter-lidar` + `bridge-copter` | Yes | Verified handshake and flight; obstacle return not captured |
| Airspeed failure behavior | Behavior characterization under degraded/corrupted airspeed signal; `test_suite` plugin lane | `plane-cte` + `gazebo-plane-cte` (plugin-owned launch) | No | Phase 2 measurement smoke accepted 2026-06-06; Phase 4A ratio/ramp/pulse characterization accepted 2026-06-14; fixed-case Phase 4B remains open. See `docs/architecture/airspeed_failure_lane.md` |
| Staircase | Tight LiDAR overpass mission | `plane-staircase` + `gazebo-plane-staircase` + `bridge-plane` | Yes | Not yet tested |
| Integrated airspeed+LiDAR | First clean integrated stack | `plane-airspeed-lidar` + `gazebo-plane-airspeed-lidar` + `bridge-plane` | Yes | Not yet tested |
| Altitude-wind | Runtime wind-function proof lane | `plane-altitude-wind` + `gazebo-plane-altitude-wind` + `wind-publisher-altitude` | No | Not yet tested |
| Rebuild | Incremental wind/airspeed investigation | `plane-rebuild` + `gazebo-plane-rebuild` | No | Not yet tested |
| Bench | Isolated sensor experiments | `gazebo-plane-bench` and related | Manual | Not a flight lane |

"Verified" statuses are backed by
`evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`.

## Errata vs the archived lane doc

- The archived doc said the altitude-wind lane is scored post-flight with
  `./launch.sh wind-check-altitude`. That target is **retired** in
  `workspace_next` — it exits with a retired-target error because the
  production validator `wind_altitude_log_check.py` did not exist. Do not rely
  on it for scoring.

## Flight modes (quick reference)

Common modes used in these lanes. For the full ArduPilot mode list, see the
ArduPilot documentation.

| Vehicle | Mode | Use in these lanes |
| --- | --- | --- |
| Plane | `FBWA` | Stabilized manual-throttle flying / quick checks |
| Plane | `TAKEOFF` | Reliable auto-takeoff (recommended over manual rotation) |
| Plane | `AUTO` | Waypoint missions (staircase, integrated lanes) |
| Plane | `RTL` / `AUTOLAND` | Return / land |
| Copter | `GUIDED` | Programmatic control; required for `takeoff` |
| Copter | `LOITER` / `RTL` | Hold / return |

Phase 2 takeaway: for planes, `mode TAKEOFF` then `arm throttle` is the
reliable airborne path; for copters, `mode GUIDED` then `arm throttle force`
then `takeoff <alt>` after `EKF3 ... is using GPS`.
