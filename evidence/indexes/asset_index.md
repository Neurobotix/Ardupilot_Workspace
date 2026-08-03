# Asset Index

Date: 2026-05-21

Scope: canonical Phase 4 inventory of workspace-owned Gazebo models, Gazebo
worlds, and waypoint missions under `assets/`.

Verification labels stay evidence-aware:

- `verified in workspace_next` means a dated report names the current lane or
  world that exercised the asset. Current proof is Phase 2 runtime evidence.
- `not yet verified` means a current launch lane or asset family exists but the
  current evidence does not prove that asset in `workspace_next`.
- `unknown` means no current evidence or concrete current runtime reference was
  found in this Phase 4 pass.

Verification of a world-backed lane does not prove every sibling probe,
alternate world, mission, or mesh variant in the same directory.

## Models

| Path | Asset type | Role / purpose | Status | Known references | Verification |
| --- | --- | --- | --- | --- | --- |
| `assets/models/mini_talon/` | Gazebo model | Base Mini Talon V-tail model (IMU + NavSat/GPS, JSON ArduPilotPlugin; no airspeed/LiDAR). | active | `assets/worlds/mini_talon_runway.sdf`; `assets/worlds/mini_talon_gps_runway.sdf`; `gazebo-plane`; `gazebo-plane-gps`. | verified in `workspace_next` for `gazebo-plane`; dedicated GPS-world pose is no-live structurally tested only |
| `assets/models/mini_talon_with_airspeed/` | Gazebo model | Mini Talon with Gazebo airspeed path for CTE/wind worlds and the GPS fast-cruise envelope world. | active | `mini_talon_wind_runway.sdf`; `mini_talon_wind_runway_sea_level.sdf`; `mini_talon_gps_airspeed_runway.sdf`; `gazebo-plane-cte`; `gazebo-plane-gps-airspeed`. | verified in `workspace_next` for the CTE wind-runway lane; GPS fast-cruise use is no-live structurally tested only |
| `assets/models/mini_talon_with_lidar/` | Gazebo model | Mini Talon with downward LiDAR for bridge-backed terrain readings. | active | `mini_talon_lidar_runway.sdf`; LiDAR bench/staircase worlds; `gazebo-plane-lidar`. | verified in `workspace_next` for the LiDAR runway lane |
| `assets/models/iris_with_lidar/` | Gazebo model | Iris with LiDAR and obstacle-world bridge path. | active | `assets/worlds/iris_lidar_obstacles.sdf`; `gazebo-copter-lidar`. | verified in `workspace_next` for handshake/bridge evidence; obstacle return remains unproven |
| `assets/models/mini_talon_airspeed_lidar/` | Gazebo model | Integrated airspeed + LiDAR lane model. | campaign-specific | Integrated lane README, world, mission, and `gazebo-plane-airspeed-lidar`. | not yet verified |
| `assets/models/mini_talon_altitude_wind/` | Gazebo model | Wrapper for the altitude-driven wind lane. | campaign-specific | `assets/worlds/mini_talon_altitude_wind/runway.sdf`; `gazebo-plane-altitude-wind`. | not yet verified |
| `assets/models/mini_talon_rebuild/` | Gazebo model | Standalone rebuild model used by rebuild worlds. | probe | `mini_talon_rebuild_still_air.sdf`; `mini_talon_rebuild_wind.sdf`; `gazebo-plane-rebuild*`. | not yet verified |
| `assets/models/mini_talon_landing_gear/` | Gazebo model | Landing-gear Mini Talon variant retained in assets. | unknown | No current launch-lane reference found in this pass. | unknown |
| `assets/models/wind_sensor_probe/` | Gazebo model | Sensor-only wind bench probe. | probe | `assets/worlds/mini_talon_wind_bench.sdf`. | not yet verified |
| `assets/models/wind_sitl_probe/` | Gazebo model | Wind bench probe with ArduPilot-plugin path. | probe | `assets/worlds/bench_s1_airspeed.sdf`. | not yet verified |

## Worlds

| Path | Asset type | Role / purpose | Status | Known references | Verification |
| --- | --- | --- | --- | --- | --- |
| `assets/worlds/mini_talon_runway.sdf` | Gazebo world | Base Mini Talon runway (sensor-neutral: NavSat/GPS + IMU, JSON FDM; no wind publisher, no airspeed sensor, no LiDAR). | active | `gazebo-plane`; Phase 2 `plane` lane. | verified in `workspace_next` for `gazebo-plane` |
| `assets/worlds/mini_talon_gps_runway.sdf` | Gazebo world | Dedicated calm GPS-failure runway using the sensor-neutral Mini Talon with an east-facing spawn aligned to the behavior mission. | active candidate | `gazebo-plane-gps`; GPS failure lane. | no-live structure/launcher tests only; source hash `69d1a7f18348...`; live heading verification pending |
| `assets/worlds/mini_talon_gps_airspeed_runway.sdf` | Gazebo world | Dedicated calm GPS-failure fast-cruise envelope world using the east-facing GPS mission pose and Mini Talon JSON airspeed model. | active candidate | `gazebo-plane-gps-airspeed`; GPS failure `fast_cruise_18mps` envelope. | no-live structure/launcher tests only; source hash `94fb25e1d81261450edb21212298ac293485bbdfd43ab74ebea01152741a4039`; live achieved-speed verification pending |
| `assets/worlds/mini_talon_lidar_runway.sdf` | Gazebo world | LiDAR runway/terrain world. | active | `gazebo-plane-lidar`; `plane-lidar`; `bridge-plane`. | verified in `workspace_next` |
| `assets/worlds/mini_talon_wind_runway.sdf` | Gazebo world | Calm-by-default CTE wind world mutated/injected by campaign tools. | active | `gazebo-plane-cte`; `run_one.py`; `run_matrix.py`. | verified in `workspace_next` for Phase 2 CTE lane |
| `assets/worlds/iris_runway.sdf` | Gazebo world | Base Iris runway world using external Iris model. | active | `gazebo-copter`; Phase 2 `copter` lane. | verified in `workspace_next` |
| `assets/worlds/iris_lidar_obstacles.sdf` | Gazebo world | Iris LiDAR obstacle world. | active | `gazebo-copter-lidar`; `copter-lidar`; `bridge-copter`. | verified in `workspace_next` for handshake/bridge evidence |
| `assets/worlds/mini_talon_wind_runway_sea_level.sdf` | Gazebo world | Sea-level density comparison wind world. | probe | `gazebo-plane-wind-sea-level`. | not yet verified |
| `assets/worlds/mini_talon_lidar_bench.sdf` | Gazebo world | Static LiDAR bench. | probe | `gazebo-plane-bench`. | not yet verified |
| `assets/worlds/mini_talon_lidar_staircase.sdf` | Gazebo world | LiDAR staircase mission world. | active | `gazebo-plane-staircase`; `plane-staircase`. | not yet verified |
| `assets/worlds/mini_talon_airspeed_lidar/wind_staircase.sdf` | Gazebo world | Integrated wind + airspeed + LiDAR staircase world. | campaign-specific | `gazebo-plane-airspeed-lidar`; integrated lane README. | not yet verified |
| `assets/worlds/mini_talon_altitude_wind/runway.sdf` | Gazebo world | Altitude-driven wind publisher world. | campaign-specific | `gazebo-plane-altitude-wind`; `wind-publisher-altitude`. | not yet verified |
| `assets/worlds/mini_talon_rebuild_still_air.sdf` | Gazebo world | Rebuild still-air baseline. | probe | `gazebo-plane-rebuild`; `plane-rebuild`. | not yet verified |
| `assets/worlds/mini_talon_rebuild_wind.sdf` | Gazebo world | Rebuild wind placeholder world. | probe | `gazebo-plane-rebuild-wind`. | not yet verified |
| `assets/worlds/mini_talon_wind_bench.sdf` | Gazebo world | Sensor-only wind bench. | probe | `wind_sensor_probe` world include. | not yet verified |
| `assets/worlds/bench_s1_airspeed.sdf` | Gazebo world | ArduPilot-connected airspeed bench. | probe | `wind_sitl_probe` world include. | not yet verified |

## Missions

| Path | Asset type | Role / purpose | Status | Known references | Verification |
| --- | --- | --- | --- | --- | --- |
| `assets/missions/square_500m_five_laps_loiter5_land.waypoints` | waypoint mission | Wind-matrix square, loiter, land mission. | campaign-specific | `run_one.py`; `run_matrix.py`; `docs/campaigns/wind_matrix.md`. | not yet verified |
| `assets/missions/lidar_staircase_mission.waypoints` | waypoint mission | Staircase LiDAR overpass mission. | active | `plane-staircase` launch guidance. | not yet verified |
| `assets/missions/mini_talon_airspeed_lidar/staircase_sensor_validation.waypoints` | waypoint mission | Integrated airspeed + LiDAR staircase mission. | campaign-specific | `plane-airspeed-lidar`; integrated lane README. | not yet verified |
| `assets/missions/airspeed_validation_mission.waypoints` | waypoint mission | Reciprocal-leg airspeed INTEGRATION validation mission (legacy; not the fault lane). | active | `assets/missions/README.md`. | unknown |
| `assets/missions/airspeed_failure_behavior_mission.waypoints` | waypoint mission | Airspeed fault-injection behavior lane mission: 100 m cruise, 800 m reciprocal legs, inject on entering seq 4, ends in RTL (no landing). | active (Phase 2 measurement smoke run 2026-06-06) | `assets/missions/README.md`; `governance/runbooks/features/airspeed_failure_behavior/`; raw root `var/runs/airspeed_failure_behavior_20260606T164050810132Z/`. | not yet verified (Phase 2 is raw-only smoke; no dated evidence report under `evidence/reports/` yet) |
| `assets/missions/airspeed_failure_headwind_ramp_mission.waypoints` | waypoint mission | Historical 23 km Eastbound stepped-ramp mission with DO15. | active historical control | Airspeed-failure lane docs and headwind runs. | source hash `6b24eb505109...`; historical live artifacts exist |
| `assets/missions/airspeed_failure_headwind_ramp_mission_cruisefollow.waypoints` | waypoint mission | Historical 23 km Eastbound cruise-follow ramp mission without DO15. | active historical control | Tier-1 and Tier-2 headwind roots. | source hash `79986b39b023...`; historical live artifacts exist |
| `assets/missions/airspeed_failure_headwind_pulse_ladder_mission.waypoints` | waypoint mission | Historical 23 km Eastbound pulse-ladder mission with DO15. | active historical control | Airspeed-failure pulse root. | source hash `552c4fa683a3...`; historical live artifact exists |
| `assets/missions/airspeed_failure_eastbound_long_speed_15_mission.waypoints` | waypoint mission | Direction-neutral 36 km Eastbound line with DO15 for tailwind counterparts. | Phase 2 no-SITL; live-unverified | Tailwind counterpart recipe and airspeed-failure runbook. | source hash `8c842dd4ffb2...`; live validation pending |
| `assets/missions/airspeed_failure_eastbound_long_cruise_follow_mission.waypoints` | waypoint mission | Direction-neutral 36 km Eastbound line following AIRSPEED_CRUISE. | Phase 2 no-SITL; live-unverified | Tailwind counterpart recipe and airspeed-failure runbook. | source hash `bea0bf2ea4a5...`; live validation pending |
| `assets/missions/gps_failure_behavior_mission.waypoints` | waypoint mission | GPS failure behavior mission v6 shorter final-science candidate: 100 m cruise, 1000 m controlled baseline, seq-4 injection, 6000 m straight fault-observation leg, 1000 m recovery/continuation, 30 s terminal loiter, seq-8 terminal gate, seq-9 RTL. | active candidate | GPS failure docs/runbooks and `GpsFailureConfig`. | v6 no-live structural geometry test passed in `tests/unit/test_gps_failure_phase1.py`; source hash `ba22c669c895...`; v5 hash `27336ee6b21c...` was live-validated as a protected three-case slice on 2026-07-16 but superseded for runtime length; v4 hash `8d1c8de43c6e...` was structurally tested only; v3 hash `3d111b32351a...` was raw-nominal validated 2026-07-14 at `var/runs/gps_failure_behavior_20260714T122459635208Z/`; v2 hash `c372bf6253c9...` is historical and exposed the pre-injection turnback |
| `assets/missions/gps_failure_behavior_mission_fast_cruise_18mps.waypoints` | waypoint mission | GPS failure behavior v6 envelope variant: unchanged geometry, seq-4 trigger, terminal loiter, seq-8 terminal gate, and seq-9 RTL, with explicit `DO_CHANGE_SPEED=18` instead of 15. | envelope candidate | GPS failure named envelope `fast_cruise_18mps`. | no-live structural comparison test only; source hash `bb21ad98439a...`; live validation pending |
| `assets/missions/quad_star_showcase_mission.waypoints` | waypoint mission | Iris quadcopter showcase mission that traces a five-point star and returns to launch. | active | `assets/missions/README.md`. | not yet verified |
| `assets/missions/runway_autoland_gentle_approach_v8.waypoints` | waypoint mission | Retained runway autoland tuning mission. | active | `assets/missions/README.md`. | unknown |
| `assets/missions/archive/runway_autoland_short_final_v7.waypoints` | waypoint mission | Historical runway autoland variant. | archive | `assets/missions/archive/README.md`. | unknown |

## Inventory Counts

Count basis for this pass:

- models: 10 first-level model directories under `assets/models/`;
- worlds: 14 `.sdf` files under `assets/worlds/`;
- missions: 13 non-archive `.waypoints` files under `assets/missions`, plus
  1 archived historical variant.
