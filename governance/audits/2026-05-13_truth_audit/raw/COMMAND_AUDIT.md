# COMMAND_AUDIT.md — Every Fenced Shell Block and Inline Command

Classification key: OK | BROKEN_PATH | BROKEN_TARGET | STALE_FLAG | NOT_RUN_STRUCTURALLY_VALIDATED | DANGEROUS | UNVERIFIABLE

Note: Per Hard Rule 12, `launch.sh`, `sim_vehicle.py`, `arducopter`, `arduplane`, `gz sim`, `gazebo`, `ros2`, `ign`, `run_matrix.py`, `run_one.py`, `run_matrix_round_robin.py`, `cleanup.sh`, `pkill`, `kill`, `rm -rf`, `git reset --hard`, `git push`, `git clean` are marked NOT_RUN_STRUCTURALLY_VALIDATED.

## From `.ai/QUICK_START.md`

| Line | Command | Classification | Notes |
|------|---------|---------------|-------|
| 15 | `source ~/ardupilot_workspace/setup.bash` | OK | setup.bash exists |
| 35 | `cd ~/ardupilot_workspace/src/SIM_ARD_GAW/scripts` | OK | Dir exists |
| 38 | `./launch.sh plane` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 39 | `./launch.sh gazebo-plane` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 42 | `./launch.sh copter` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 43 | `./launch.sh gazebo-copter` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 51 | `cd ~/ardupilot_workspace/src/ardupilot` | OK | Dir exists |
| 52 | `sim_vehicle.py -v ArduPlane -f JSON --console --map` | NOT_RUN_STRUCTURALLY_VALIDATED | |
| 97 | `./launch.sh plane-lidar` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 98 | `./launch.sh gazebo-plane-lidar` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 99 | `./launch.sh bridge-plane` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 100 | `./launch.sh copter-lidar` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 101 | `./launch.sh gazebo-copter-lidar` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 102 | `./launch.sh bridge-copter` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 113 | `./launch.sh logger` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 114 | `./launch.sh logger-csv` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 115-117 | `./launch.sh gazebo-plane` etc (as pair) | NOT_RUN_STRUCTURALLY_VALIDATED | |
| 130 | `gz topic -t "/world/mini_talon_wind_runway/wind/"` | NOT_RUN_STRUCTURALLY_VALIDATED | Trailing slash non-standard |
| 158 | `./launch.sh cleanup` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target (DANGEROUS — kills processes) |
| 160 | `killall gz arducopter arduplane mavproxy.py` | DANGEROUS | Destructive; duplicates cleanup target |

## From `.ai/architecture/COMMANDS.md`

| Line | Command | Classification | Notes |
|------|---------|---------------|-------|
| 27 | `./launch.sh plane` | NOT_RUN_STRUCTURALLY_VALIDATED | |
| 28 | `./launch.sh gazebo-plane` | NOT_RUN_STRUCTURALLY_VALIDATED | |
| 31 | `./launch.sh plane-airspeed` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target (alias for plane-cte) |
| 32 | `./launch.sh gazebo-plane-wind` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target (alias for gazebo-plane-cte) |
| 36 | `./launch.sh plane-airspeed` | NOT_RUN_STRUCTURALLY_VALIDATED | |
| 42 | `./launch.sh gazebo-plane-cte` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 46 | `./launch.sh plane-rebuild` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 47 | `./launch.sh gazebo-plane-rebuild` | NOT_RUN_STRUCTURALLY_VALIDATED | Valid target |
| 52 | `./launch.sh wind-check-altitude` | **BROKEN_TARGET** | Script wind_altitude_log_check.py MISSING |
| 185 | `param show RNGFND1_TYPE` | OK | MAVProxy command |
| 188 | `param set RNGFND1_TYPE 10` | UNVERIFIABLE | Requires running SITL |
| 201-210 | `param set RNGFND1_TYPE 10` etc | UNVERIFIABLE | Requires running SITL; values match plane_lidar.parm |

## From `.ai/external_mods/ardupilot_gazebo/ArduPilotPlugin/airspeed_json.md`

| Line | Command | Classification | Notes |
|------|---------|---------------|-------|
| 236 | `grep "ARSPD_TYPE" ~/ardupilot_workspace/src/SIM_ARD_GAW/config/plane_base.parm` | **BROKEN_PATH** | plane_base.parm has ARSPD_TYPE=0, not 100. Should grep plane_airspeed.parm |
| 238 | "Should show ARSPD_TYPE 100" | **STALE_CLAIM** | Would show ARSPD_TYPE 0 |

## Self-Check: Cleanup/Dangerous Commands in .ai

| File:Line | Command | Classification |
|-----------|---------|---------------|
| QUICK_START.md:160 | `killall gz arducopter arduplane mavproxy.py` | DANGEROUS |
| launch.sh (in docs) | `pkill -9 gz`, `pkill -9 ruby`, etc. | NOT_RUN_STRUCTURALLY_VALIDATED (DANGEROUS if run) |
| Various sessions | `param set SIM_WIND_SPD 5.0`, etc. | UNVERIFIABLE (requires running SITL) |
