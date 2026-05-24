# Simulation Lanes

> **ARCHIVED — superseded.** Canonical lane reference for `workspace_next` is
> `docs/architecture/simulation_lanes.md`. The altitude-wind row below cites
> `./launch.sh wind-check-altitude`, which is **retired** in `workspace_next`.
> Errata: `governance/audits/2026-05-20_phase3_docs_errata.md`.

This project currently has multiple Mini Talon simulation lanes. They serve
different purposes and should not be treated as one interchangeable stack.

## Authoritative Rule Set

- `base` is sensor-neutral. No airspeed dependency. No LiDAR dependency.
- `airspeed` uses Gazebo wind as the only wind source.
- `lidar` uses the MAVLink bridge path for rangefinder data.
- `mini_talon_airspeed_lidar` is the first clean integrated fixed-wing lane.
- `altitude-wind` is an experiment lane where runtime wind is published as a function.
- `bench` worlds are isolation harnesses, not flight-ready operating worlds.
- `rebuild` is a separate investigation lane with its own params and worlds.
- legacy all-in-one plane parameter snapshots live in `config/archive/`.

## Lane Map

| Lane | Purpose | Gazebo World | Param Stack | Launcher | Notes |
|------|---------|--------------|-------------|----------|-------|
| Base | Clean fixed-wing baseline | `mini_talon_runway.sdf` | `plane_base.parm` | `plane` + `gazebo-plane` | No bridge required |
| Airspeed | Wind and pitot validation | `mini_talon_wind_runway.sdf` or `mini_talon_wind_runway_sea_level.sdf` | `plane_base.parm` + `plane_airspeed.parm` | `plane-airspeed` + `gazebo-plane-wind` | Gazebo is the only wind source |
| LiDAR | Terrain / rangefinder work | `mini_talon_lidar_runway.sdf` | `plane_base.parm` + `plane_lidar.parm` | `plane-lidar` + `gazebo-plane-lidar` + `bridge-plane` | Bridge required |
| Staircase | Tight LiDAR overpass mission | `mini_talon_lidar_staircase.sdf` | `plane_base.parm` + `plane_lidar.parm` + `staircase_plane_params.parm` | `plane-staircase` + `gazebo-plane-staircase` + `bridge-plane` | Navigation overlay only |
| Integrated | First clean airspeed + LiDAR stack | `worlds/mini_talon_airspeed_lidar/wind_staircase.sdf` | `config/mini_talon_airspeed_lidar/plane_full.parm` | `plane-airspeed-lidar` + `gazebo-plane-airspeed-lidar` + `bridge-plane` | Dedicated lane subtree |
| Altitude-Wind | Runtime wind function proof lane | `worlds/mini_talon_altitude_wind/runway.sdf` | `config/mini_talon_altitude_wind/plane_full.parm` | `plane-altitude-wind` + `gazebo-plane-altitude-wind` + `wind-publisher-altitude` | Default function: wind speed from altitude; post-flight score with `./launch.sh wind-check-altitude` |
| Bench | Isolated sensor experiments | `mini_talon_lidar_bench.sdf`, `bench_s1_airspeed.sdf`, `mini_talon_wind_bench.sdf` | Scenario-specific | Manual / targeted use | Not the default ops lane |
| Rebuild | Incremental wind / airspeed investigation | `mini_talon_rebuild_still_air.sdf`, `mini_talon_rebuild_wind.sdf` | `plane_params_rebuild.parm` | `plane-rebuild` + `gazebo-plane-rebuild` | Standalone lane |

## Why This Split Exists

- The Mini Talon model variants are currently copy-based.
- The world files enable different Gazebo systems depending on the scenario.
- The previous single all-in-one param file caused ambiguity between base,
  airspeed, and LiDAR workflows.

Until the aircraft composition work lands, the safest workflow is to keep these
lanes explicit and only combine the pieces that are known to belong together.
