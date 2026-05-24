# High-Wind 12/12 Debug History

> Follow-up:
> the later automated matrix mismatch was not caused by the wind command,
> `run_one.py` AUTO control, or Gazebo `/wind_info` clipping. The resolved
> automation root cause is documented in
> [09 Matrix Launcher Environment Root Cause](09_matrix_launcher_environment_root_cause.md).
> In short, matrix launched Gazebo with drift-prone inherited `GZ_SIM_*` paths,
> while the working manual stack used `launch.sh` to construct the correct
> Gazebo plugin/resource environment.

This note documents the manual debugging session for the `x=12, y=12` wind case in the CTE lane.

## Case

The target test case was:

```text
Gazebo wind:
  x = 12 m/s East
  y = 12 m/s North
  z = 0
```

This is not a 12 m/s wind. It is a diagonal wind with magnitude:

```text
sqrt(12^2 + 12^2) = 16.97 m/s
```

The original CTE airspeed overlay had:

```text
AIRSPEED_CRUISE  14
AIRSPEED_MIN     10
AIRSPEED_MAX     22
TRIM_THROTTLE    55   # inherited from plane_base.parm
```

So the test wind was stronger than the aircraft's normal cruise airspeed. On any upwind or partially upwind leg, the aircraft had very little ground-speed margin. This made the case a genuine high-wind stress test, not an ordinary matrix corner.

## Manual Run Commands

The no-script manual stack was:

Terminal 1, SITL/MAVProxy:

```bash
cd /home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts
./launch.sh cleanup
./launch.sh plane-cte
```

Terminal 2, Gazebo:

```bash
cd /home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts
./launch.sh gazebo-plane-cte
```

Terminal 3, inject 12/12 wind:

```bash
gz topic -t "/world/mini_talon_wind_runway/wind/" \
  -m gz.msgs.Wind \
  -p "linear_velocity:{x:12.000,y:12.000,z:0.000}, enable_wind:true"
```

MAVProxy commands:

```text
wp clear
wp load /home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/missions/square_500m_five_laps_loiter5_land.waypoints
wp list
wp set 1
arm throttle force
mode AUTO
```

For live parameter patching without restart, the final critical airspeed watchdog overrides are:

```text
param set ARSPD_OPTIONS 0
param set ARSPD_WIND_GATE 0
param set ARSPD_USE 1
```

Restarting SITL is cleaner because `plane-cte` wipes EEPROM and reloads the param stack from files.

## Initial Failure

The first observed behavior was that the plane got blown far outside the square and AUTO dragged a long diagonal path back toward the mission.

Likely causes in that first run:

- The run was manual and did not use `run_one.py` mission upload/verification.
- `run_one_og.py` does not reset mission state or verify mission identity.
- The wind case was extremely strong relative to the original aircraft speed profile.
- The aircraft could start the square from a bad state and then the wind made recovery very hard.

The immediate manual mitigation was to start from a clean stack and explicitly reset the mission:

```text
wp clear
wp load /home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/missions/square_500m_five_laps_loiter5_land.waypoints
wp set 1
arm throttle force
mode AUTO
```

## First Parameter Change

The first real parameter fix was to make the CTE airspeed overlay faster. This was done in:

```text
src/SIM_ARD_GAW/config/plane_airspeed.parm
```

The old effective profile was too slow:

```text
AIRSPEED_CRUISE  14
AIRSPEED_MIN     10
AIRSPEED_MAX     22
```

The first high-wind profile raised the requested speed and throttle margin:

```text
AIRSPEED_CRUISE  24
AIRSPEED_MIN     14
AIRSPEED_MAX     32
TRIM_THROTTLE    75
TECS_SPDWEIGHT   2.0
TKOFF_ROTATE_SPD 16
TECS_LAND_ARSPD  16
TECS_LAND_THR    65
AHRS_WIND_MAX    35
```

Why this helped:

- `AIRSPEED_CRUISE` became higher than the 16.97 m/s wind magnitude.
- `AIRSPEED_MAX` gave TECS room to demand more speed.
- `TRIM_THROTTLE` gave automatic throttle a more realistic high-wind cruise baseline.
- `AHRS_WIND_MAX` was raised so the estimator would tolerate larger wind.

Why it still failed:

- The aircraft still crashed or lost control after AUTO/arm in one run.
- Log inspection showed the takeoff itself actually completed, so the main issue was not just launch throttle.
- The aircraft reached early mission waypoints, then lost altitude and control on a hard/upwind segment.
- Airspeed values in the log were collapsing during the stressed segment.

## Second Parameter Change

The next patch hardened the high-wind profile further:

```text
par

AIRSPEED_MIN     18
AIRSPEED_MAX     38
TRIM_THROTTLE    75
TECS_SPDWEIGHT   1.2
TECS_CLMB_MAX    8
TECS_SINK_MAX    3
MIN_GROUNDSPEED  8
ROLL_LIMIT_DEG   30
NAVL1_PERIOD     22
NAVL1_LIM_BANK   25
TECS_PITCH_MIN   -5
TKOFF_THR_MAX    100
TKOFF_ROTATE_SPD 14
TECS_LAND_ARSPD  16
TECS_LAND_THR    65
AHRS_WIND_MAX    35
```

Why this helped:

- `AIRSPEED_CRUISE 28` gave stronger margin over the 16.97 m/s wind.
- `AIRSPEED_MIN 18` kept the controller away from a too-slow operating point.
- `AIRSPEED_MAX 38` allowed higher commanded speed when needed.
- `TECS_CLMB_MAX 8` gave TECS more climb-rate authority.
- `MIN_GROUNDSPEED 8` made ArduPlane bias navigation to maintain ground progress.
- `NAVL1_LIM_BANK 25` reduced aggressive high-bank recovery attempts while slow.
- `TKOFF_THR_MAX 100` made takeoff throttle explicit.
- `TKOFF_ROTATE_SPD 14` avoided waiting too long for rotation in disturbed wind.

This version flew much better. The plane reached many more waypoints, including:

```text
AP: Reached waypoint #14 dist 20m
AP: Mission: 15 WP
```

Why it still failed later:

The later failure was different. The aircraft was working until ArduPilot disabled the airspeed sensor:

```text
AP: Airspeed sensor 1 failure. Disabling
...
AP: Airspeed sensor 1 now OK. Re-enabled
```

After the sensor was disabled, TECS lost the Gazebo JSON airspeed input during an extreme wind case. The aircraft altitude then dropped badly:

```text
height 47
height 36
height 24
height 14
height 5
...
height -8
```

This made the root cause clearer: the flight was no longer failing simply because of insufficient speed. It was failing because ArduPilot's airspeed health logic was disabling the exact sensor needed for high-wind TECS control.

## Airspeed Watchdog Root Cause

ArduPilot's airspeed library has a health check controlled by `ARSPD_OPTIONS`, `ARSPD_WIND_MAX`, and `ARSPD_WIND_GATE`.

Relevant source behavior:

- `ARSPD_OPTIONS` bit 0 allows disabling airspeed use based on airspeed/groundspeed mismatch.
- `ARSPD_OPTIONS` bit 1 allows automatic re-enable after recovery.
- `ARSPD_OPTIONS` bit 3 enables EKF3 consistency checking.
- The default observed value was:

```text
ARSPD_OPTIONS = 11
```

`11` means bits `0 + 1 + 3` were active:

```text
1  = SpeedMismatchDisable
2  = AllowSpeedMismatchRecovery
8  = UseEkf3Consistency
11 = 1 + 2 + 8
```

That behavior is reasonable for a real pitot sensor. It is not appropriate for this deliberate Gazebo high-wind stress test because large airspeed/groundspeed differences are expected.

The latest BIN showed:

```text
ARSPD_OPTIONS   11
ARSPD_WIND_GATE 5
```

Then the flight produced:

```text
Airspeed sensor 1 failure. Disabling
Airspeed sensor 1 now OK. Re-enabled
```

That disable/re-enable cycle caused the late mission failure.

## Final Critical Fix

The CTE airspeed overlay now includes:

```text
ARSPD_OPTIONS    0
ARSPD_WIND_GATE  0
```

Full current high-wind section:

```text
ARSPD_TYPE       100
ARSPD_USE        1
ARSPD_AUTOCAL    0
ARSPD_SKIP_CAL   1
ARSPD_OFFSET     0
ARSPD_OPTIONS    0
ARSPD_WIND_GATE  0

AIRSPEED_CRUISE  28
AIRSPEED_MIN     18
AIRSPEED_MAX     38
TRIM_THROTTLE    75
TECS_SPDWEIGHT   2.0
TECS_CLMB_MAX    8
TECS_SINK_MAX    3
MIN_GROUNDSPEED  8
NAVL1_LIM_BANK   25
TKOFF_THR_MAX    100
TKOFF_ROTATE_SPD 14
TECS_LAND_ARSPD  16
TECS_LAND_THR    65
STALL_PREVENTION 1

SIM_WIND_SPD     0
SIM_WIND_DIR     180
SIM_WIND_TURB    0
AHRS_WIND_MAX    35
```

Why this setup worked better in the first successful run:

1. The aircraft now has an airspeed target that is above the diagonal wind magnitude.
2. TECS has enough allowed speed range and climb authority to recover on upwind legs.
3. Navigation was intended to be less aggressive because bank limiting was added for this stress case.
4. Minimum groundspeed encourages forward progress instead of letting the wind dominate path following.
5. Most importantly, ArduPilot no longer disables the Gazebo JSON airspeed sensor during the very wind mismatch this experiment intentionally creates.

## Latest Failure: Landing Segment

The next run failed again, but it was not the same failure as before.

Log inspected:

```text
src/ardupilot/logs/00000241.BIN
```

The airspeed watchdog fix was active in this run:

```text
ARSPD_OPTIONS    0
ARSPD_WIND_GATE  0
ARSPD_USE        1
```

There were no `Airspeed sensor 1 failure. Disabling` messages in this run. The aircraft completed the square and reached the loiter phase:

```text
10:40:21  Takeoff complete at 98.60m
10:41:16  Reached waypoint #3
...
10:57:35  Reached waypoint #22
10:57:35  Mission: 23 LoitTurns
11:06:58  Loiter orbits complete
11:06:58  Mission: 24 LandStart
11:06:58  Mission: 25 LoitAltitude
```

The crash happened after the objective part of the mission, during the landing staircase:

```text
11:09:18  Loiter to alt complete
11:09:18  Mission: 26 WP
11:09:23  Passed waypoint #26 dist 36m
11:09:23  Mission: 27 WP
11:09:24  EKF3 lane switch 0
11:09:31  Passed waypoint #27 dist 79m
11:09:31  Mission: 28 WP
11:09:34  EKF3 lane switch 1
```

The mission tail is very aggressive for a 16.97 m/s diagonal wind:

```text
WP25 LOITER_TO_ALT 10m
WP26 waypoint       4m
WP27 waypoint       2m
WP28 waypoint       1m
WP29 LAND           0m
```

At the end of the log, the aircraft was effectively on the ground and rolled over while still trying to reach WP28:

```text
relative altitude: about 0.08 m
roll:              about 178.9 deg
target:            WP28, still about 175 m away
cross-track error: about 66 m
throttle:          100 percent
airspeed:          about 16.3 m/s
```

Conclusion:

That run proved the airspeed-watchdog fix was necessary and that the old landing segment was unsafe. It did not prove the square/loiter setup was fully reproducible, because a later run failed before loiter.

For the CTE matrix objective, stop after square plus loiter and do not continue into landing.

Scripted command:

```bash
cd /home/ahmed/ardupilot_workspace
env/bin/python3 src/SIM_ARD_GAW/scripts/run_one.py \
  --x 12 --y 12 --rep 1 \
  --campaign-root src/SIM_ARD_GAW/logs/013_Square_Wind_Matrix_CTE_wind_verified \
  --auto \
  --accept-square-only
```

Manual no-script rule:

```text
When MAVProxy shows "Loiter orbits complete" or "Mission: 24 LandStart",
stop the run. Do not let this mission continue into WP25-WP29 landing.
```

If a full landing is required for a separate experiment, create a high-wind landing mission variant instead of using the current 10m -> 4m -> 2m -> 1m staircase.

## Follow-Up Failure: Lap 5 Altitude Loss

A later run with `--accept-square-only` also failed, but earlier than the landing segment.

Log inspected:

```text
src/ardupilot/logs/00000242.BIN
```

This run reached WP18, then failed while trying to reach WP19:

```text
11:49:30  Reached waypoint #17
11:49:30  Mission: 18 WP
11:49:48  Reached waypoint #18
11:49:48  Mission: 19 WP
11:50:02  AHRS: DCM active
11:50:02  AHRS: EKF3 active
11:50:03  AHRS: DCM active
11:50:03  AHRS: EKF3 active
```

The failure was a real mid-square loss of control. `--accept-square-only` did not help because the aircraft never reached the loiter phase.

Key evidence near the failure:

```text
target altitude:     100 m
relative altitude:   fell to about 0 m, then bounced/rose after upset
target waypoint:     WP19
cross-track error:   about 190 m
commanded bank:      about 43 deg before the upset
airspeed target:     28 m/s
throttle demand:     100 percent
measured airspeed:   later collapsed to about 3-7 m/s during the tumble
```

The bad assumption in the previous tuning was `NAVL1_LIM_BANK`. That parameter only limits loiter bank. It does not limit ordinary square waypoint turns. The real waypoint bank limit remained:

```text
ROLL_LIMIT_DEG 45
```

With large cross-track error in 12/12 wind, L1 still commanded more than 40 degrees of bank. At the same time:

```text
TECS_SPDWEIGHT 2.0
```

made TECS strongly prefer airspeed over altitude. The aircraft was allowed to keep diving while far below the 100m target altitude.

The next high-wind patch changed the overlay to preserve altitude and reduce aggressive square turns:

```text
TECS_SPDWEIGHT  1.2
ROLL_LIMIT_DEG  30
NAVL1_PERIOD    22
TECS_PITCH_MIN  -5
```

Why:

- `ROLL_LIMIT_DEG 30` is the real waypoint turn bank cap.
- `NAVL1_PERIOD 22` makes L1 less aggressive when cross-track error is large.
- `TECS_SPDWEIGHT 1.2` stops TECS from sacrificing nearly all altitude to protect speed.
- `TECS_PITCH_MIN -5` prevents prolonged steep nose-down commands while the aircraft is already below target altitude.

This is expected to increase CTE but should keep the aircraft alive, which is the first requirement for a reproducible matrix run.

## What To Watch In Future Runs

A healthy run should not show:

```text
Airspeed sensor 1 failure. Disabling
```

Watch these during the mission:

```text
watch VFR_HUD.airspeed
watch VFR_HUD.groundspeed
watch GLOBAL_POSITION_INT.relative_alt
```

Expected behavior:

- Airspeed should stay meaningfully above the wind magnitude on stressed legs.
- Groundspeed may become low on upwind legs, but it should not collapse to zero for long.
- Relative altitude should not bleed down through the square.
- The plane may still have large cross-track error in 12/12 wind, but it should keep flying rather than losing TECS control.

## Important Caveat

This setup is tuned for a specific simulation stress case. It is not a general Mini Talon real-world parameter set.

The choice to set:

```text
ARSPD_OPTIONS 0
```

means the autopilot will trust the configured airspeed source more strongly. That is appropriate here because the source is a Gazebo JSON airspeed sensor in a deliberate high-wind simulation. It would be a different safety tradeoff on real hardware.
