## mini_talon_airspeed_lidar model lane

This directory now contains the active integrated Mini Talon aircraft for the first clean fixed-wing lane.

Implemented files:
- `model.config`
- `model.sdf`
- `meshes/`

Included systems:
- downward `gpu_lidar` on `/lidar`
- pitot-style `air_speed` sensor on `/airspeed`
- `ArduPilotPlugin` airspeed wiring

Explicit non-goals:
- rear-wheel rebuild work
- rebuild-only geometry
- additional legacy forks
