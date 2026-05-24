## mini_talon_airspeed_lidar lane

This lane is the first clean integrated fixed-wing stack in the project.

Implemented stack:
- Aircraft: Mini Talon with airspeed and downward LiDAR
- World: wind plus staircase terrain
- Params: one full parameter set for the integrated stack
- Missions: repeatable validation flights for this stack

Owned paths:
- `models/mini_talon_airspeed_lidar/`
- `worlds/mini_talon_airspeed_lidar/`
- `config/mini_talon_airspeed_lidar/`
- `missions/mini_talon_airspeed_lidar/`

Implemented files:
- `models/mini_talon_airspeed_lidar/model.config`
- `models/mini_talon_airspeed_lidar/model.sdf`
- `models/mini_talon_airspeed_lidar/meshes/`
- `worlds/mini_talon_airspeed_lidar/wind_staircase.sdf`
- `config/mini_talon_airspeed_lidar/plane_full.parm`
- `missions/mini_talon_airspeed_lidar/staircase_sensor_validation.waypoints`

World frame note:
- the integrated world now inherits the runway, wind, and spawn frame from `mini_talon_wind_runway`
- the staircase and mission are rotated to the same eastbound centerline

Runtime note:
- wind comes from Gazebo only
- LiDAR enters ArduPilot through the existing `bridge-plane` path

Explicit non-goals for this lane:
- Rear-wheel rebuild work
- Global retirement of legacy assets
- Immediate restructuring of every other plane/world path
