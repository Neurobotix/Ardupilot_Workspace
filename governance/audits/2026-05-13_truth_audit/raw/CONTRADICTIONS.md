# CONTRADICTIONS.md — Contradictions Inside .ai and Between .ai and src/SIM_ARD_GAW

## Internal .ai Contradictions

### C-001: MASTER_STATUS_MATRIX vs CURRENT.md — Landing Gear status
- **A**: `.ai/reconciliation/MASTER_STATUS_MATRIX.md:42,120-121` — "DEPRECATED_ARCHIVE — abandoned"
- **B**: `.ai/sessions/CURRENT.md:36-37,57` — "GEAR-001/002: Deferred"
- **Type**: Status contradiction (permanently abandoned vs backlogged)
- **Severity**: High

### C-002: Quadcopter exclusivity claim vs Fixed-wing WORKING
- **A**: `.ai/vehicles/quadcopter/STATUS.md:12` — "the only verified working configuration"
- **B**: `.ai/vehicles/README.md:16,29` — Fixed-wing marked "WORKING"
- **Type**: Exclusivity contradiction
- **Severity**: High

### C-003: LiDAR feature STATUS date vs Quadcopter STATUS date
- **A**: `.ai/features/lidar/STATUS.md:13` — "Last verified 2026-05-11"
- **B**: `.ai/vehicles/quadcopter/STATUS.md:71` — Last verification "2026-01-15"
- **Type**: Date inconsistency
- **Severity**: Medium

### C-004: LiDAR CHANGELOG vs LiDAR STATUS — Fixed-wing status
- **A**: `.ai/features/lidar/CHANGELOG.md:55-56` — INIT entry says "Fixed-Wing: NOT WORKING"
- **B**: `.ai/features/lidar/STATUS.md:14` — Fixed-wing "WORKING"
- **Type**: Status contradiction within same feature
- **Severity**: Medium

### C-005: RESOLVED.md last_updated vs actual content dates
- **A**: `.ai/issues/RESOLVED.md:4` — `last_updated: 2026-03-10`
- **B**: `.ai/issues/RESOLVED.md:131-173` — Contains entries from 2026-05-11
- **Type**: Metadata contradiction
- **Severity**: High

### C-006: MASTER_STATUS_MATRIX date anomaly
- **A**: `.ai/reconciliation/MASTER_STATUS_MATRIX.md:2` — `last_updated: 2026-05-11`
- **B**: `.ai/reconciliation/MASTER_STATUS_MATRIX.md:42` — "user decision on 2026-05-12"
- **Type**: Date contradiction (decision postdates doc update)
- **Severity**: High

### C-007: test matrix vs SDF — diff_pressure sign
- **A**: `.ai/tests/airspeed_claim_test_matrix.md:20,70,116` — "diff_pressure ≈ +15.31 Pa"
- **B**: `src/SIM_ARD_GAW/worlds/bench_s1_airspeed.sdf:13` — "≈ -15.3 Pa"
- **Type**: Sign contradiction between doc and source SDF
- **Severity**: Critical

### C-008: External mods claim ARSPD_TYPE=100 is in plane_base.parm vs actual value
- **A**: `.ai/external_mods/SUMMARY.md:36`, `airspeed_json.md:192-197,236-238,272` — Claims ARSPD_TYPE=100 is in plane_base.parm
- **B**: `src/SIM_ARD_GAW/config/plane_base.parm:46` — ARSPD_TYPE=0
- **Type**: File attribution contradiction
- **Severity**: Critical

### C-009: MODELS.md world association vs SDF content
- **A**: `.ai/vehicles/fixed_wing/MODELS.md:15` — `mini_talon_with_airspeed` uses `bench_s1_airspeed.sdf`
- **B**: `src/SIM_ARD_GAW/worlds/bench_s1_airspeed.sdf` — Includes `wind_sitl_probe`, not the full aircraft
- **Type**: Model-world association contradiction
- **Severity**: High

## .ai vs src/SIM_ARD_GAW Contradictions

### C-010: logs/flights/ path doesn't exist
- **A**: `.ai/QUICK_START.md:119`, `.ai/architecture/COMMANDS.md:272`, `.ai/vehicles/fixed_wing/STATUS.md:66` — Claim logs go to `logs/flights/`
- **B**: Actual filesystem — `logs/` exists but `logs/flights/` does not. Real dirs: `001_Quad_LiDAR/`, `002_Plane_Base/`, etc.
- **Severity**: High

### C-011: Stale world name plane_lidar_runway.sdf
- **A**: `.ai/vehicles/fixed_wing/STATUS.md:83`, `ISSUES.md:63`, `RESOLVED.md:156` — References `plane_lidar_runway.sdf`
- **B**: Actual world file named `mini_talon_lidar_runway.sdf`
- **Severity**: High

### C-012: Sinusoidal wind variation claim vs actual SDF
- **A**: `src/SIM_ARD_GAW/logs/003_Plane_Airspeed/TEST_RESULT_2026-02-04.md:58-62` — Claims sinusoidal wind magnitude variation (period 60s, amplitude 5%) and direction variation (period 20s, amplitude 5°)
- **B**: `src/SIM_ARD_GAW/worlds/mini_talon_wind_runway.sdf:56,61` — `<amplitude_percent>0</amplitude_percent>`, `<amplitude>0</amplitude>` — all zeroed
- **Severity**: Critical

### C-013: wind-check-altitude target documented but script missing
- **A**: `.ai/architecture/COMMANDS.md:52`, `SIMULATION_LANES.md:38`, `features/altitude_wind/STATUS.md:15` — wind-check-altitude is a valid post-flight scoring target
- **B**: `launch.sh:935-938` calls `wind_altitude_log_check.py` which does NOT exist
- **Severity**: Critical

### C-014: Full_auto_mission_v7.waypoints referenced but missing
- **A**: `.ai/issues/RESOLVED.md:38,50,64` — Claims `config/full_auto_mission_v7.waypoints` was created
- **B**: File does NOT exist anywhere in repository
- **Severity**: High
