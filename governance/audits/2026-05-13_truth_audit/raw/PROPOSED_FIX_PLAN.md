# PROPOSED_FIX_PLAN.md — Grouped by File, Minimal Edits

Each edit shows 2-3 lines of context and the exact replacement. No unrelated rewrites.

---

## `.ai/QUICK_START.md`

### Fix 1: logs/flights/ → correct log path
```
**Around line 119:**
-Logs saved to: `src/SIM_ARD_GAW/logs/flights/`
+Logs saved to: `src/SIM_ARD_GAW/logs/` (in numbered bucket directories, e.g., `002_Plane_Base/`)
```

### Fix 2: Add copter manual launch section
```
**After line 59 (end of Plane manual launch):**
+### Manual Copter Launch
+```bash
+cd ~/ardupilot_workspace/src/ardupilot
+sim_vehicle.py -v ArduCopter -f JSON --console --map
+# In another terminal:
+cd ~/ardupilot_workspace/src/SIM_ARD_GAW/scripts
+./launch.sh gazebo-copter
+```
```

### Fix 3: Remove trailing slash from wind topic
```
**Line 130:**
-gz topic -t "/world/mini_talon_wind_runway/wind/"
+gz topic -t "/world/mini_talon_wind_runway/wind"
```

---

## `.ai/reconciliation/MASTER_STATUS_MATRIX.md`

### Fix 1: Update last_updated date
```
**Line 2:**
-last_updated: 2026-05-11
+last_updated: 2026-05-12
```

### Fix 2: Add Wind Matrix / CTE major track
```
**After line 39 (end of major tracks table), add new row:**
+| Wind Matrix / CTE Validation | `IMPLEMENTED_UNPUBLISHED` | Param contrast campaign (old 009 vs new params). 017 = old-param failure analysis; 018/019 = new-param CTE matrix & report. Primary active campaign per CURRENT.md. |
```

### Fix 3: Resolve DEPRECATED_ARCHIVE vs deferred contradiction
```
**Lines 120-121:**
-Landing gear / rear wheels track → DEPRECATED_ARCHIVE
+Landing gear / rear wheels track → DEFERRED (or DEPRECATED_ARCHIVE after confirming with CURRENT.md)
```

---

## `.ai/architecture/SIMULATION_LANES.md`

### Fix 1: Fix gazebo-plane-wind-sea-level alias
```
**Line 34:**
-| `gazebo-plane-wind-sea-level` | Alias for Airspeed/CTE lane |
+| `gazebo-plane-wind-sea-level` | Separate lane using `mini_talon_wind_runway_sea_level.sdf` |
```

### Fix 2: Remove or fix wind-check-altitude
```
**Line 38:**
-| `wind-check-altitude` | Post-flight scoring |
+| `wind-check-altitude` | ⚠️ LAUNCH TARGET BROKEN — script `wind_altitude_log_check.py` missing |
```

---

## `.ai/architecture/COMMANDS.md`

### Fix 1: Fix wind-check-altitude
```
**Line 52:**
-wind-check-altitude: validates altitude-wind lane from BIN log
+wind-check-altitude: ⚠️ BROKEN — script wind_altitude_log_check.py missing
```

---

## `.ai/issues/RESOLVED.md`

### Fix 1: Update last_updated and updated_by
```
**Lines 4-5:**
-last_updated: 2026-03-10
-updated_by: 2026-03-10_001
+last_updated: 2026-05-11
+updated_by: 2026-05-11_001
```

### Fix 2: Add note about missing session files
```
**After line 132 (FW-002):**
+⚠️ Session file `2026-05-11_001.md` referenced but does not exist in `.ai/sessions/`.
```

### Fix 3: Add note about missing waypoints file
```
**After line 38 (LAND-001 resolution):**
+⚠️ File `config/full_auto_mission_v7.waypoints` is referenced but does not currently exist in the repository.
```

### Fix 4: Stale world name
```
**Line 156:**
-`worlds/plane_lidar_runway.sdf` → `worlds/mini_talon_lidar_runway.sdf`
+`worlds/mini_talon_lidar_runway.sdf`
```

---

## `.ai/issues/README.md`

### Fix 1: Add missing prefixes to table
```
**Lines 31-42 (prefix table), add:**
+| `LAND-` | Landing issues |
+| `GEAR-` | Landing Gear (Archived) |
+| `ARSPD-` | Airspeed sensor issues |
+| `TECH-` | Technical debt |
```

---

## `.ai/issues/OPEN.md`

### Fix 1: Clarify GEAR archival status
```
**After line 34 (end of deprecated archive table):**
+> Note: GEAR issues are deprecated archival — the prefix is not an active issue category.
```

---

## `.ai/external_mods/SUMMARY.md`

### Fix 1: Fix ARSPD_TYPE file reference
```
**Line 36:**
-✅ ARSPD_TYPE=100 in plane_base.parm
+✅ ARSPD_TYPE=100 in plane_airspeed.parm
```

---

## `.ai/external_mods/ardupilot_gazebo/README.md`

### Fix 1: Clarify ARSPD_TYPE=100 file
```
**Line 41:**
-ARSPD_TYPE=100 confirmed active
+ARSPD_TYPE=100 confirmed active in plane_airspeed.parm
```

### Fix 2: Remove ArduPilotPlugin.hh
```
**Line 69:**
-src/ArduPilotPlugin.hh    | Plugin header (unmodified)
+[Remove line — file does not exist]
```

---

## `.ai/external_mods/ardupilot_gazebo/ArduPilotPlugin/airspeed_json.md`

### Fix 1: Fix section header and ARSPD_TYPE references
```
**Lines 192-197:**
-### ArduPilot Parameters (`plane_base.parm`)
+### ArduPilot Parameters (`plane_airspeed.parm`)
```

```
**Lines 236-238:**
-grep "ARSPD_TYPE" ~/ardupilot_workspace/src/SIM_ARD_GAW/config/plane_base.parm
-Should show `ARSPD_TYPE 100`
+grep "ARSPD_TYPE" ~/ardupilot_workspace/src/SIM_ARD_GAW/config/plane_airspeed.parm
+Should show `ARSPD_TYPE 100`
```

```
**Line 272:**
-`src/SIM_ARD_GAW/config/plane_base.parm` | ArduPilot params (ARSPD_TYPE=100)
+`src/SIM_ARD_GAW/config/plane_airspeed.parm` | ArduPilot params (ARSPD_TYPE=100)
```

---

## `.ai/vehicles/fixed_wing/STATUS.md`

### Fix 1: Stale world name
```
**Line 83:**
-`plane_lidar_runway.sdf`
+`mini_talon_lidar_runway.sdf`
```

---

## `.ai/vehicles/fixed_wing/ISSUES.md`

### Fix 1: Stale world name
```
**Line 63:**
-worlds/plane_lidar_runway.sdf
+worlds/mini_talon_lidar_runway.sdf
```

---

## `.ai/vehicles/fixed_wing/MODELS.md`

### Fix 1: Fix world association for mini_talon_with_airspeed
```
**Line 15:**
-`mini_talon_with_airspeed` | WORKING | ... | `bench_s1_airspeed.sdf`...
+`mini_talon_with_airspeed` | WORKING | ... | `mini_talon_wind_bench.sdf` (bench uses `wind_sitl_probe`, not the full model)...
```

---

## `.ai/vehicles/quadcopter/STATUS.md`

### Fix 1: Remove contradictory exclusivity claim
```
**Line 12:**
-"the only verified working configuration" (or similar exclusivity language)
+"The first verified working configuration (2026-01-15)"
```

---

## `.ai/features/airspeed/60_LAUNCH_AND_PARAMS.md`

### Fix 1: Add local override to param stack
```
**Line 32:**
-plane_base.parm + plane_airspeed.parm
+plane_base.parm + plane_airspeed.parm → .private/config/plane_params.local.parm (optional override)
```

---

## `.ai/features/airspeed/README.md`

### Fix 1: Add T07 evidence to index
```
**After line 36, add:**
+| T07 | Reciprocal Validation | `evidence/raw/T07_after_2026-04-01.csv` | `evidence/T07_RESULTS_2026-04-01.md` | `evidence/figures/T07_first_100s_diagnostics_2026-04-01.png` |
```

---

## `.ai/features/airspeed/TEST_MATRIX.md`

### Fix 1: Fix T03 evidence path
```
**Line 194:**
-evidence/T03_RESULTS_2026-04-01.md
+evidence/raw/T03_RESULTS_2026-04-01.md
```

---

## `.ai/features/airspeed/50_ARDUPILOT_CALIBRATION.md`

### Fix 1: Add context to ARSPD_TYPE
```
**Line 38 (or nearby):**
-ARSPD_TYPE target value is 100
+ARSPD_TYPE target value is 100 (in plane_airspeed.parm; plane_base.parm keeps ARSPD_TYPE 0)
```

---

## `.ai/features/airspeed_lidar_integrated/IMPLEMENTATION.md`

### Fix 1: Add param values
```
**After line 12, add:**
+Key parameters: AIRSPEED_CRUISE=14, AIRSPEED_MIN=10, AIRSPEED_MAX=22, AHRS_WIND_MAX=15 (conservative old-param profile).
```

---

## `.ai/features/lidar/CHANGELOG.md`

### Fix 1: Add note that INIT entry is historical
```
**After line 56:**
+> Note: The "NOT WORKING" status above is a historical baseline entry, not the current state. Current STATUS shows Fixed-Wing LiDAR as WORKING.
```

---

## `.ai/features/lidar/STATUS.md`

### Fix 1: Clarify verification date
```
**Line 13:**
-Last verified 2026-05-11 (add context)
+Last verified 2026-05-11 (re-verification); original flight evidence 2026-01-15 (quadcopter), 2026-03-08 (fixed-wing).
```

---

## `.ai/features/wind_matrix/55_DATASET_QUALITY_AND_PARAM_FAILURE.md`

### Fix 1: Clarify BIN count
```
**Lines 7-10:**
-63 named BINs audited
+63 named BINs audited (filtered from 106 total BIN files in 018; excludes eeprom.bin and state files)
```

---

## `.ai/features/wind_matrix/evidence/README.md`

### Fix 1: Document 019 is report-only
```
**Line 10:**
-Cross-link to 019
+019 contains only post-processed summary/report artifacts. Raw BIN data is in 018.
```

---

## `.ai/README.md`

### Fix 1: Fix directory tree omissions (lines 62-105)
```
Add: reconciliation/ under .ai/ root
Add: airspeed/, airspeed_lidar_integrated/, altitude_wind/, wind_matrix/ under features/
Add: SIMULATION_LANES.md under architecture/
Add: GEAR-001.md, GEAR-002.md, GEAR-003.md under issues/ (with archival note)
Add: EXTERNAL_MOD.md under templates/
Add: airspeed_claim_test_matrix.md under tests/
```

---

## `.ai/sessions/CURRENT.md`

### Fix 1: Fix test_suite path
```
**Line 24:**
-Test_suite framework (scripts/test_suite/)
+Test_suite framework (src/SIM_ARD_GAW/scripts/test_suite/)
```

---

## `src/SIM_ARD_GAW/scripts/launch.sh`

### Fix 1: Fix logs/flights/ path (lines 689, 699)
```
-LOG_DIR="$SIM_ARD_GAW_DIR/logs/flights"
+LOG_DIR="$SIM_ARD_GAW_DIR/logs/$(date +%Y%m%d_%H%M%S)_flight"
(or document the convention properly)
```

### Fix 2: Fix or remove wind-check-altitude target
```
**Lines 935-938:**
-    wind-check-altitude)
-        ...
-        python3 "$SIM_ARD_GAW_DIR/scripts/wind_altitude_log_check.py"
-Either create the script or remove the case entirely.
```

---

## `.ai/templates/ISSUE_REPORT.md` & `.ai/templates/TEST_RESULT.md`

### Fix (nice-to-have): Update stale world name in examples
```
-plane_lidar_runway.sdf → mini_talon_lidar_runway.sdf
```

---

## `.ai/tests/RESULTS.md`

### Fix 1: Fix TEST-002 log path
```
**Line 100:**
-src/SIM_ARD_GAW/logs/flights/flight_20260121_150436.log
+src/SIM_ARD_GAW/logs/002_Plane_Base/flight_20260121_150436.log
```

---

## `.ai/tests/airspeed_claim_test_matrix.md`

### Fix 1: Reconcile diff_pressure sign
```
**Lines 20, 70, 116:**
-diff_pressure ≈ +15.31 Pa
+diff_pressure ≈ ±15.31 Pa (sign convention depends on sensor orientation; SDF shows −15.3 Pa)
```

---

## `.ai/vehicles/fixed_wing/STATUS.md`

### Fix 2: Fix flight log path
```
**Line 66:**
-logs/flights/flight_20260121_150436.log
+logs/002_Plane_Base/flight_20260121_150436.log
```
