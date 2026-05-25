# Matrix Launcher Environment Root Cause

This note documents the resolved cause of the 12/12 automated wind mismatch.

It is intentionally not framed as "`launch.sh` works, `run_one.py` works, matrix
does not." That wording is too shallow. The real issue was that the successful
and failing paths built different Gazebo runtime environments, so Gazebo could
publish the requested world wind while the aircraft/plugin/airspeed path was not
equivalent to the known-good manual stack.

## Short Version

The wind command was not the bug.

This command worked in both manual and automated paths:

```bash
gz topic -t "/world/mini_talon_wind_runway/wind/" \
  -m gz.msgs.Wind \
  -p "linear_velocity:{x:12.000,y:12.000,z:0.000}, enable_wind:true"
```

The root cause was the way `run_matrix.py` and
`run_matrix_round_robin.py` launched Gazebo directly with an environment built
by `run_one.runtime_env()`.

`runtime_env()` used `setdefault()` for the Gazebo resource and plugin paths.
That means:

```python
env.setdefault("GZ_SIM_RESOURCE_PATH", ...)
env.setdefault("GZ_SIM_SYSTEM_PLUGIN_PATH", ...)
```

If either variable already existed in the parent shell, the matrix runner did
not prepend the known project paths. It preserved whatever was already there.

The known-good launcher, `launch.sh`, does not do that. It actively prepends
the project paths every time through `configure_gazebo_environment()`.

That difference allowed the matrix runner to start a Gazebo world where:

- `/world/mini_talon_wind_runway/wind_info` correctly reached `x=12, y=12`
- the BIN still logged low EKF wind, around `1-3 m/s`
- `ARSP.Airspeed` tracked `GPS.Spd`, which means ArduPilot did not receive the
  same wind-relative pitot evidence seen in the working manual stack

## Successful Path

The working path has three pieces.

Terminal 1:

```bash
./scripts/launch.sh plane-cte
```

Terminal 2:

```bash
./scripts/launch.sh gazebo-plane-cte
```

Terminal 3, either manual wind + manual mission control, or `run_one.py` auto
control:

```bash
env/bin/python src/SIM_ARD_GAW/scripts/run_one.py \
  --x 12 \
  --y 12 \
  --rep 1 \
  --auto \
  --auto-wind-phase before-arm \
  --accept-square-only \
  --campaign-root src/SIM_ARD_GAW/logs/debug_12_12_manual_launch_auto_control
```

This succeeded. The important result is that `run_one.py` automation was not the
problem when the stack was launched through `launch.sh`.

## Failing Path

The failing path was:

```bash
env/bin/python src/SIM_ARD_GAW/scripts/run_matrix_round_robin.py \
  --focus-combo wind_x_12_y_12 \
  --runs-per-combo 1 \
  --max-passes 1 \
  --accept-square-only \
  --wind-world-mode calm-runtime \
  --auto-wind-phase before-arm \
  --campaign-root src/SIM_ARD_GAW/logs/debug_12_12_before_arm
```

That run did inject wind before arming and did publish to the correct topic.
During the run, live Gazebo state was confirmed externally:

```bash
gz topic -e -t /world/mini_talon_wind_runway/wind_info -n 10 2</dev/null
```

Observed:

```text
linear_velocity {
  x: 11.999999999983933
  y: 11.999999999971841
}
```

So Gazebo world wind was correct.

But the BIN still showed low EKF wind:

```text
XKF2 C=0 all:
  VWN mean=1.83, max=5.85
  VWE mean=1.26, max=3.96

XKF2 C=1 all:
  same values
```

The key clue was not `XKF2` itself. It was the relationship between airspeed and
groundspeed:

```text
square-ish window:
  ARSP.Airspeed mean=11.14, median=7.31
  GPS.Spd       mean=11.34, median=7.54
```

In a real `12 East, 12 North` wind case, airspeed and groundspeed should not
track each other that closely across the square. If ArduPilot sees
`ARSP ~= GPS.Spd`, EKF3 has no strong measurement evidence for a 16.97 m/s wind
vector, so `XKF2.VWN/VWE` remain small.

## Why `/wind_info` Was Not Enough

`/wind_info` answers only this question:

```text
Is Gazebo's live world wind vector correct?
```

It does not answer these separate questions:

```text
Did Gazebo load the same model files?
Did Gazebo load the same plugin binary?
Did the airspeed sensor publish the same pressure semantics?
Did ArduPilotPlugin convert and forward that sensor data the same way?
Did SITL receive a wind-relative airspeed that EKF3 can use?
```

The failed matrix run proved that question 1 was true. It did not prove the
rest of the pipeline was equivalent.

## Exact Launcher Difference

### `launch.sh` path construction

`launch.sh` configures Gazebo like this:

```bash
configure_gazebo_environment() {
    local resource_path="${GZ_SIM_RESOURCE_PATH:-}"
    local plugin_path="${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"

    plugin_path="$(prepend_path_entry "$GAZEBO_PLUGIN_INSTALL_DIR" "$plugin_path")"
    plugin_path="$(prepend_path_entry "$GAZEBO_PLUGIN_BUILD_DIR" "$plugin_path")"

    for resource_dir in "${GAZEBO_RESOURCE_PATHS[@]}"; do
        resource_path="$(prepend_path_entry "$resource_dir" "$resource_path")"
    done

    export GZ_SIM_SYSTEM_PLUGIN_PATH="$plugin_path"
    export GZ_SIM_RESOURCE_PATH="$resource_path"
}
```

Important details:

- it sources the workspace setup first
- it checks that Gazebo plugin variables exist
- it prepends known paths instead of leaving inherited values alone
- it prints the final plugin/resource paths before launching Gazebo

That means every manual `gazebo-plane-cte` launch rebuilds a known project
environment.

### Matrix path construction

`run_matrix.py` launched Gazebo directly:

```python
cmd = ["gz", "sim", "-v4", "-r", str(world)]
return launch_process(cmd, run_one.WORKSPACE_ROOT, log_path)
```

`launch_process()` used:

```python
env=run_one.runtime_env()
```

`runtime_env()` built paths with:

```python
env.setdefault("GZ_SIM_RESOURCE_PATH",
               ":".join(str(p) for p in resource_paths if p.exists()))
env.setdefault("GZ_SIM_SYSTEM_PLUGIN_PATH",
               ":".join(str(p) for p in plugin_paths if p.exists()))
```

That is the bug. If a parent terminal already had either variable set, matrix
did not repair the path order. It could inherit stale, incomplete, or differently
ordered Gazebo paths.

## Why This Can Produce The Observed Symptom

There are multiple ArduPilot Gazebo plugin binaries on this machine:

```text
build/ardupilot_gazebo/libArduPilotPlugin.so
/usr/local/lib/ardupilot_gazebo/libArduPilotPlugin.so
```

There are also multiple Gazebo model/resource roots:

```text
src/SIM_ARD_GAW/models
src/SITL_Models/Gazebo/models
src/ardupilot_gazebo/models
/usr/local/share/ardupilot_gazebo/models
```

The manual launcher controls the order. The matrix runner could preserve a
different inherited order.

A wrong or stale path order does not have to break the world entirely. Gazebo can
still load:

- the world
- the `WindEffects` system
- the `/world/.../wind` command topic
- the `/world/.../wind_info` live wind topic

At the same time, the aircraft-side path can differ:

- model resolution can select a different resource copy
- plugin resolution can select a different `ArduPilotPlugin`
- the `/airspeed` bridge behavior can differ
- ArduPilot can receive airspeed close to groundspeed instead of wind-relative
  pitot speed

That is exactly what the failing BIN showed.

## What Was Ruled Out

The A/B tests ruled out these suspected causes:

- `gz topic` payload formatting
- trailing slash on `/world/mini_talon_wind_runway/wind/`
- injecting before arm versus after takeoff
- `run_one.py` MAVLink mission upload and AUTO control
- wrong EKF core (`XKF2 C=0` and `C=1` both showed the same low wind in the
  failing matrix run)
- Gazebo world wind being clipped to zero

The decisive split was:

```text
launch.sh stack + run_one.py auto control = works
run_matrix_round_robin stack + same run_one auto logic = fails
```

Therefore the remaining difference is the stack launch environment.

## Correct Fix

There are two acceptable fixes.

### Preferred fix: make Python environment construction match `launch.sh`

Replace `setdefault()` behavior with deterministic prepend behavior:

- always include project model/world paths
- always include both plugin directories in the intended order
- do not let inherited `GZ_SIM_RESOURCE_PATH` or `GZ_SIM_SYSTEM_PLUGIN_PATH`
  hide required entries
- log the final paths into each attempt directory

The Python behavior should match `launch.sh`'s `prepend_path_entry()` semantics.

### Conservative fix: have matrix launch through `launch.sh`

Instead of direct:

```python
["gz", "sim", "-v4", "-r", world]
```

matrix can use a launcher wrapper that first runs the same environment setup
logic as `launch.sh`.

This is less modular, but it reduces drift because there is one operational
source of truth.

## Regression Test To Keep

Keep this A/B test as the permanent regression:

1. Start the stack manually:

   ```bash
   ./scripts/launch.sh plane-cte
   ./scripts/launch.sh gazebo-plane-cte
   ```

2. Run:

   ```bash
   env/bin/python src/SIM_ARD_GAW/scripts/run_one.py \
     --x 12 --y 12 --rep 1 \
     --auto \
     --auto-wind-phase before-arm \
     --accept-square-only \
     --campaign-root src/SIM_ARD_GAW/logs/debug_12_12_manual_launch_auto_control
   ```

3. Compare against matrix after the environment fix:

   ```bash
   env/bin/python src/SIM_ARD_GAW/scripts/run_matrix_round_robin.py \
     --focus-combo wind_x_12_y_12 \
     --runs-per-combo 1 \
     --max-passes 1 \
     --accept-square-only \
     --wind-world-mode calm-runtime \
     --auto-wind-phase before-arm \
     --campaign-root src/SIM_ARD_GAW/logs/debug_12_12_matrix_env_fixed
   ```

Expected:

- `/wind_info` reaches `x ~= 12, y ~= 12`
- `ARSP.Airspeed` no longer simply tracks `GPS.Spd`
- BIN `XKF2[0].VWN/VWE` or MAVExplorer `XKF2[0].VMN/VME` reflects the intended
  wind similarly to the manual stack

## Bottom Line

The automation bug was environmental, not aerodynamic.

The matrix runner launched Gazebo outside the known-good `launch.sh` environment
and preserved inherited Gazebo path variables. That allowed a run where the
global wind topic was correct but the aircraft/plugin/airspeed pipeline was not
equivalent to the manual stack. The solution is to make matrix Gazebo launches
use the same deterministic Gazebo plugin/resource path construction as
`launch.sh`.
