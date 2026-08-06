# SITL And Gazebo Runtime Notes

This page holds shared operational facts for ArduPilot SITL and Gazebo in
`workspace_next`. `.private/notes/` must not be used as the source of truth for
these details.

## Canonical Environment

Source `setup.bash` from the workspace root before launching tools:

```bash
cd /home/ahmed/ardupilot_workspace_next
source setup.bash
```

`setup.bash` exports the Gazebo resource and plugin paths. Governed runs use
the workspace plugin build only:

```bash
GZ_SIM_SYSTEM_PLUGIN_PATH=/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo
```

Resource paths still include tracked workspace assets and local dependency
trees needed by the selected world. `setup.bash` and `launch.sh` own the
Gazebo environment so old shell-profile plugin paths cannot reintroduce an
installed plugin.

## Wind Evidence Plugin Boundary

Wind-matrix evidence must record the workspace `libArduPilotPlugin.so`
selected by Gazebo:

```text
build/ardupilot_gazebo/libArduPilotPlugin.so
```

If that file is absent, launch and wind-matrix entrypoints fail
closed. The first Phase 5 `4,4` comparison remediation showed why: an installed
plugin fallback let Gazebo wind topic echo verification pass while the
ArduPilot-side estimated wind stayed low. The corrected recheck loaded the
workspace build and restored the known-good wind behavior.

Build or rebuild the plugin before runtime evidence:

```bash
cmake -S src/ardupilot_gazebo -B build/ardupilot_gazebo -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build/ardupilot_gazebo -j2
test -f build/ardupilot_gazebo/libArduPilotPlugin.so
```

Use the detailed incident record when auditing this failure class:

`governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`

## JSON Backend

The Gazebo JSON backend must be enabled for shared simulation lanes. The
canonical place for that value is tracked parameter config:

- `config/vehicles/copter_params.parm`: `SIM_JSON_MASTER 1`
- `config/vehicles/plane_base.parm`: `SIM_JSON_MASTER 1`
- `config/campaigns/*/plane_full.parm`: lane-specific full stacks also set it

If a manual SITL session was started without loading one of these files, set it
in MAVProxy before relying on Gazebo sensor data:

```bash
param set SIM_JSON_MASTER 1
```

## Parameter Truth

Shared tuned parameters live in tracked config files:

- Copter frame and navigation defaults: `config/vehicles/copter_params.parm`
- Mini Talon base airframe defaults: `config/vehicles/plane_base.parm`
- Default Gazebo airspeed overlay (conservative 14/10/22):
  `config/overlays/plane_airspeed.parm`
- Aggressive high-wind CTE stress overlay (28/18/38; non-default, name
  explicitly): `config/overlays/plane_airspeed_cte_high_wind_aggressive.parm`
- LiDAR overlay: `config/overlays/plane_lidar.parm`
- Campaign full stacks: `config/campaigns/*/plane_full.parm`

Local-only overrides may be placed in `.private/config/*.local.parm`, but a
private override must not be required for shared operation. If an override
becomes required, promote it into `config/` and update evidence.

## Mini Talon AUTO Procedure

For manual Mini Talon AUTO validation, start in FBWA long enough to establish
stable airspeed, then switch to AUTO:

```bash
mode FBWA
arm throttle force
rc 3 1700
# Fly for at least 30 seconds.
mode AUTO
```

Historical waypoint-following issues were tied to missing or unsuitable airspeed
and navigation tuning, overly large loiter radius for the small airframe, and
waypoints placed too close together. The current tracked Mini Talon configs use
`AIRSPEED_CRUISE`, `AIRSPEED_MIN`, `AIRSPEED_MAX`, `NAVL1_PERIOD`,
`NAVL1_DAMPING`, `WP_RADIUS`, and `WP_LOITER_RAD` in tracked files instead of
private notes.

## World Files

Prefer workspace worlds under `assets/worlds/` and plugin source worlds under
`src/ardupilot_gazebo/worlds/`. Do not make undocumented system-wide edits under
`/usr/local/share/ardupilot_gazebo`.

If a fallback installed Iris runway world references `iris_with_gimbal` where an
ArduPilot-controlled Iris is required, treat the installed world as suspect and
use a tracked workspace world instead. If the installed world must be repaired,
record the exact file diff and promote the fix to the relevant source asset.

## Process Shutdown

The launcher performs broad pre-run cleanup before governed simulation runs.
That is intentional clean-run policy: the workspace owns the active simulator
stack for the run so stale Gazebo, SITL, MAVProxy, bridge, or logger processes
cannot contaminate the result. Do not start a governed run beside another
simulator session you need to keep alive.

For manual cleanup outside the launcher, stop processes in this order:

1. Gazebo processes: `gz`, `gz sim`, `gz-sim-*`, the `ruby .../gz sim`
   wrapper, `gzserver`, `gzclient`
2. Vehicle binaries: `arduplane`, `arducopter`
3. MAVProxy
4. `sim_vehicle.py`

## Installation

Fresh-machine setup belongs in `docs/onboarding/installation.md`. Keep this page
for runtime facts after the workspace and its local dependencies are present.

## Known Benign Message

Gazebo or protobuf startup may print a `File already exists in database`
message. Treat it as benign only when the relevant Gazebo/SITL process continues
running and the expected topics or JSON sensor data are present.

## Local Shell Cleanup

If old hard-coded Gazebo paths were added to a user shell profile, remove them
from the local profile and use `setup.bash` instead:

```bash
sed -i '/GZ_SIM_SYSTEM_PLUGIN_PATH/d' ~/.bashrc
sed -i '/GZ_SIM_RESOURCE_PATH/d' ~/.bashrc
```
