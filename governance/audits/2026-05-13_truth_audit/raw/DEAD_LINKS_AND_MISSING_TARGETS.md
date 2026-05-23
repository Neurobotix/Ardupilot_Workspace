# DEAD_LINKS_AND_MISSING_TARGETS.md

## Missing Markdown Links (internal)

| Source File:Line | Target | Status |
|-----------------|--------|--------|
| various | `2026-05-11_001.md` session link | 🔴 MISSING — most recent session is 2026-03-30_001.md |
| various | `2026-05-11_002.md` session link | 🔴 MISSING |
| various | `2026-05-12_001.md` session link | 🔴 MISSING |

## Broken Relative Paths

| Source File:Line | Broken Path | Correct Path |
|-----------------|------------|-------------|
| QUICK_START.md:119 | `logs/flights/` | `logs/002_Plane_Base/` etc. |
| COMMANDS.md:272 | `logs/flights/` | `logs/` |
| PATHS.md:101 | `logs/flights/` | `logs/` |
| STATUS.md:66 | `logs/flights/flight_20260121_150436.log` | `logs/002_Plane_Base/flight_20260121_150436.log` |
| RESULTS.md:100 | `logs/flights/flight_20260121_150436.log` | `logs/002_Plane_Base/flight_20260121_150436.log` |
| TEST_MATRIX.md:194 | `evidence/T03_RESULTS_2026-04-01.md` | `evidence/raw/T03_RESULTS_2026-04-01.md` |
| STATUS.md:83 | `plane_lidar_runway.sdf` | `mini_talon_lidar_runway.sdf` |
| ISSUES.md:63 | `plane_lidar_runway.sdf` | `mini_talon_lidar_runway.sdf` |
| RESOLVED.md:156 | `plane_lidar_runway.sdf` | `mini_talon_lidar_runway.sdf` |
| external_mods/airspeed_json.md:236 | `plane_base.parm` (expecting ARSPD_TYPE 100) | `plane_airspeed.parm` |

## Missing Log/Report Paths

| Source File:Line | Missing Path | Notes |
|-----------------|-------------|-------|
| launch.sh:935-938 | `scripts/wind_altitude_log_check.py` | Script never existed |
| TEST_RESULT_2026-02-04.md:75-77 | `scripts/airspeed_bridge.py` | Architecture migrated away |
| RESOLVED.md:38,50,64 | `config/full_auto_mission_v7.waypoints` | Never committed or deleted |

## Nonexistent Session IDs

| Session ID | Referenced In | Notes |
|-----------|--------------|-------|
| 2026-05-11_001 | RESOLVED.md:132,143,153; external_mods/airspeed_json.md:7,299 | Would be needed for FW-002, FW-004, FW-001 resolutions |
| 2026-05-11_002 | RESOLVED.md:164 | Would be needed for TECH-001 |
| 2026-05-12_001 | OPEN.md:5 | Would be needed for OPEN.md update |

## Nonexistent File References

| File | Referenced In | Status |
|------|--------------|--------|
| `arpupilot_gazebo/src/ArduPilotPlugin.hh` | external_mods/ardupilot_gazebo/README.md:69 | 🔴 File does not exist (only .cc) |
| `src/ardupilot/logs/00000075_analysis.txt` | sessions/2026-02-07_001.md:78 | Not verified (in ardupilot repo, not SIM_ARD_GAW) |
