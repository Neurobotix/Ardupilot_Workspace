## mini_talon_airspeed_lidar world lane

This directory owns the integrated validation world for the first clean Mini Talon sensor stack.

Implemented file:
- `wind_staircase.sdf`

Included systems:
- `gz::sim::systems::AirSpeed`
- `gz::sim::systems::Sensors`
- `gz::sim::systems::WindEffects`
- staircase terrain with five stepped platforms

Reference frame:
- inherits the takeoff frame from `worlds/mini_talon_wind_runway.sdf`
- runway at the origin, runway yaw `90`, aircraft yaw `0`
- 5 m/s headwind for eastbound departure
- staircase platforms laid out along +X so the world and mission share the same frame

The world is dedicated to the `mini_talon_airspeed_lidar` aircraft and is meant to exercise both sensors together.
