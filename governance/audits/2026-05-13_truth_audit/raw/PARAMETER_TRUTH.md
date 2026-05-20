# PARAMETER_TRUTH.md — Actual Parameter Inventory vs .ai Claims

## Actual Key Values Across All .parm Files

| Param | plane_base.parm | plane_airspeed.parm | plane_lidar.parm | plane_full.parm (airspeed_lidar) | plane_full.parm (altitude_wind) | plane_params_rebuild.parm | .private/local.parm |
|-------|-----------------|--------------------|-----------------|----------------------------------|--------------------------------|--------------------------|--------------------|
| ARSPD_TYPE | 0 | **100** | — | **100** | **100** | **100** | — |
| ARSPD_USE | 0 | **1** | — | **1** | **1** | **1** | — |
| ARSPD_AUTOCAL | 0 | 0 | — | 0 | 0 | 0 | — |
| ARSPD_SKIP_CAL | — | 1 | — | 1 | 1 | 1 | 1 |
| ARSPD_OFFSET | — | 0 | — | 0 | 0 | 0 | 0 |
| ARSPD_RATIO | — | — | — | — | — | — | — |
| SIM_WIND_SPD | 0 | 0 | — | 0 | 0 | 0 | — |
| SIM_WIND_DIR | 180 | 180 | — | 180 | 180 | 180 | — |
| SIM_WIND_TURB | 0 | 0 | — | 0 | 0 | 0 | — |
| SERVO1_FUNCTION | 4 | — | — | 4 | — | 4 | — |
| SERVO2_FUNCTION | 79 | — | — | 79 | — | 79 | — |
| SERVO3_FUNCTION | 70 | — | — | 70 | — | 70 | — |
| SERVO4_FUNCTION | 80 | — | — | 80 | — | 80 | — |
| LAND_FLARE_ALT | 1 | — | — | 1 | — | 1 | — |
| LAND_FLARE_SEC | 0.5 | — | — | 0.5 | — | 0.5 | — |
| LAND_FLARE_AIM | 20 | — | — | 20 | — | 20 | — |
| RNGFND1_TYPE | 0 | — | 10 | 10 | — | 0 | — |
| RNGFND1_ORIENT | — | — | 25 | 25 | — | — | — |
| RNGFND1_MIN_CM | — | — | 50 | 30 | — | — | — |
| RNGFND1_MAX_CM | — | — | 5000 | 4000 | — | — | — |
| RNGFND1_GNDCLEAR | — | — | 10 | 10 | — | — | — |
| AHRS_WIND_MAX | **25** | **35** | — | **15** | **20** | **15** | — |
| AHRS_EKF_TYPE | 3 | — | — | 3 | — | 3 | — |
| AIRSPEED_CRUISE | 14 | **28** | — | 14 | 14 | 14 | — |
| AIRSPEED_MIN | 10 | **18** | — | 10 | 10 | 10 | — |
| AIRSPEED_MAX | 22 | **38** | — | 22 | 22 | 22 | — |
| TRIM_THROTTLE | 55 | **75** | — | 55 | — | 55 | — |
| MIN_GROUNDSPEED | — | 8 | — | — | — | — | — |

Note: `—` means parameter is NOT present in that file (inherits from earlier file in stack or uses ArduPilot default).

## .ai Claims That Disagree

| Param | .ai Claim | .ai File:Line | Actual Value | Agrees? | Severity |
|-------|-----------|---------------|-------------|---------|----------|
| ARSPD_TYPE=100 in plane_base.parm | "in plane_base.parm" | external_mods/SUMMARY.md:36 | plane_base.parm has ARSPD_TYPE=0 | ❌ | Critical |
| ARSPD_TYPE=100 in plane_base.parm | Section header "ArduPilot Parameters (plane_base.parm)" | external_mods/ardupilot_gazebo/airspeed_json.md:192-197 | Wrong file | ❌ | Critical |
| ARSPD_TYPE=100 in plane_base.parm | Grep command expects 100 in plane_base.parm | external_mods/ardupilot_gazebo/airspeed_json.md:236-238 | Wrong file | ❌ | Critical |
| AHRS_WIND_MAX | 25 (implied as universal) | Various docs | Varies by lane (15-35) | ⚠️ | Medium |
| AIRSPEED_CRUISE | 14 (implied as universal) | Various docs | Varies by lane (14 or 28) | ⚠️ | Medium |

## Stale / Nonexistent Param File Claims

| Claim | File | Reality |
|-------|------|---------|
| `plane_params.parm` (as a single file) | Multiple .ai docs | Does not exist — params are split into base + overlays |
| `plane_base.parm + plane_airspeed.parm` (compound literal path) | IMPLEMENTATION.md.old:367 | ARCHIVAL_OK — old style |
| `recovered_009_param_stack_7439211` | Not referenced in .ai/ at all | Exists at config/archive/recovered_009_param_stack_7439211/ |

## Param Overlay Order (Verified via launch.sh)

Per `launch.sh:82-83` comment block:
1. plane_base.parm (always first)
2. Lane-specific param file (e.g., plane_airspeed.parm)
3. .private/config/plane_params.local.parm (optional, last wins)

**.ai doc claim**: Most docs omit step 3 (local override). Fix needed.
