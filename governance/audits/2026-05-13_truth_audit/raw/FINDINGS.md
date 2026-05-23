# FINDINGS.md — All Audit Findings

Ordered by severity (Critical → High → Medium → Low), then by file path.

---

## CRITICAL Findings (reader following doc would corrupt source, destroy data, or cite nonexistent evidence)

### C-001: airspeed_bridge.py missing but referenced as created
- **File**: `.ai/features/airspeed/80_OPEN_ISSUES.md:13` (via ref to `logs/003_Plane_Airspeed/TEST_RESULT_2026-02-04.md:75-77`)
- **Claim**: `airspeed_bridge.py` "✅ Created" at `src/SIM_ARD_GAW/scripts/airspeed_bridge.py`
- **Reality**: File does not exist anywhere under `scripts/`. Architecture was superseded when ArduPilotPlugin native JSON transport replaced the Python bridge.
- **Severity**: Critical
- **Confidence**: High
- **Fix**: Remove the "✅ Created" claim or add a note that this was superseded by native JSON transport.

### C-002: wind_altitude_log_check.py missing but referenced as valid launch target
- **File**: `.ai/architecture/COMMANDS.md:52`, `.ai/architecture/SIMULATION_LANES.md:38,44`, `.ai/features/altitude_wind/STATUS.md:15`
- **Claim**: `wind-check-altitude` is a valid launch target that calls `wind_altitude_log_check.py`
- **Reality**: Script `wind_altitude_log_check.py` does NOT exist at `src/SIM_ARD_GAW/scripts/wind_altitude_log_check.py`. The launch target in `launch.sh:935-938` calls a nonexistent script.
- **Severity**: Critical
- **Confidence**: High
- **Fix**: Either create the script or remove the launch target from launch.sh and all docs.

### C-003: ARSPD_TYPE=100 claimed in plane_base.parm (6 occurrences)
- **File(s)**: 
  - `.ai/external_mods/SUMMARY.md:36` — "✅ ARSPD_TYPE=100 in plane_base.parm"
  - `.ai/external_mods/ardupilot_gazebo/ArduPilotPlugin/airspeed_json.md:192-197` — Section "ArduPilot Parameters (plane_base.parm)" showing ARSPD_TYPE 100
  - `.ai/external_mods/ardupilot_gazebo/ArduPilotPlugin/airspeed_json.md:236-238` — Grep command expects ARSPD_TYPE 100 in plane_base.parm
  - `.ai/external_mods/ardupilot_gazebo/ArduPilotPlugin/airspeed_json.md:272` — plane_base.parm labeled (ARSPD_TYPE=100)
  - `.ai/external_mods/ardupilot_gazebo/README.md:41` — ARSPD_TYPE=100 confirmed active (ambiguous)
- **Reality**: `plane_base.parm:46` has `ARSPD_TYPE 0`. The correct file is `plane_airspeed.parm:8` which has `ARSPD_TYPE 100`.
- **Severity**: Critical
- **Confidence**: High
- **Fix**: Change all references from `plane_base.parm` to `plane_airspeed.parm`.

### C-004: Missing session files referenced by issues
- **File(s)**: `.ai/issues/RESOLVED.md:132,143,153,164`, `.ai/issues/OPEN.md:5`
- **Claim**: References sessions `2026-05-11_001`, `2026-05-11_002`, `2026-05-12_001`
- **Reality**: These session files do NOT exist in `.ai/sessions/`. The most recent session file is `2026-03-30_001.md`.
- **Severity**: Critical
- **Confidence**: High
- **Fix**: Create the missing session files or update references to existing sessions.

### C-005: diff_pressure sign contradiction in airspeed test matrix
- **File**: `.ai/tests/airspeed_claim_test_matrix.md:20,70,116`
- **Claim**: `diff_pressure ≈ +15.31 Pa`
- **Reality**: Actual SDF (`bench_s1_airspeed.sdf:13`) says `≈ -15.3 Pa`. Sensor pose is 0° (model.sdf:39); with wind in +X, diff_pressure should be positive.
- **Severity**: Critical
- **Confidence**: High
- **Fix**: Reconcile sign convention. If sensor is oriented correctly, update SDF from `-15.3` to `+15.3` or vice versa.

---

## HIGH Findings (reader would make wrong technical decision or run broken command)

### H-001: MASTER_STATUS_MATRIX date anomaly — decision postdates last_updated
- **File**: `.ai/reconciliation/MASTER_STATUS_MATRIX.md:2` (frontmatter) vs `:42`
- **Claim**: `last_updated: 2026-05-11`
- **Reality**: Line 42 says "user decision on 2026-05-12 abandoned all gear." Decision date (May 12) is one day AFTER last_updated date.
- **Severity**: High
- **Confidence**: High
- **Fix**: Update `last_updated` to `2026-05-12` or later.

### H-002: Missing archive log 00000110.BIN
- **File**: `.ai/reconciliation/MASTER_STATUS_MATRIX.md:107`
- **Claim**: `archive/ardupilot_logs_20260506/00000110.BIN` is primary LiDAR evidence
- **Reality**: File does NOT exist at that path. File actually exists at workspace root `/home/ahmed/ardupilot_workspace/archive/ardupilot_logs_20260506/00000110.BIN` — the path in the doc is relative but ambiguous; also referenced from multiple other files with no workspace-root prefix.
- **Severity**: High
- **Confidence**: High
- **Fix**: Document explicit absolute path or clarify workspace-relative prefix.

### H-003: MASTER_STATUS_MATRIX DEPRECATED_ARCHIVE vs CURRENT.md "deferred"
- **File(s)**: `.ai/reconciliation/MASTER_STATUS_MATRIX.md:42,113-121` vs `.ai/sessions/CURRENT.md:36-37,57`
- **Claim**: Matrix says Landing Gear "DEPRECATED_ARCHIVE — abandoned"; CURRENT.md says "GEAR-001/002: Deferred"
- **Reality**: Contradictory statuses. One says permanently abandoned, other says backlogged.
- **Severity**: High
- **Confidence**: High
- **Fix**: Resolve contradiction — update one to match the other.

### H-004: logs/flights/ path does not exist (multiple docs)
- **File(s)**: `.ai/QUICK_START.md:119`, `.ai/architecture/COMMANDS.md:272`, `.ai/architecture/PATHS.md:101`, `.ai/vehicles/fixed_wing/STATUS.md:66`, `.ai/tests/RESULTS.md:100`
- **Claim**: Logs saved to `src/SIM_ARD_GAW/logs/flights/`
- **Reality**: Directory `logs/flights/` does NOT exist. Real log storage is `logs/001_Quad_LiDAR/`, `logs/002_Plane_Base/`, etc. Also hardcoded in `launch.sh:689,699`.
- **Severity**: High
- **Confidence**: High
- **Fix**: Update all docs and launch.sh to point to actual log directory structure.

### H-005: Stale world name plane_lidar_runway.sdf (renamed)
- **File(s)**: `.ai/vehicles/fixed_wing/STATUS.md:83`, `.ai/vehicles/fixed_wing/ISSUES.md:63`, `.ai/issues/RESOLVED.md:156`
- **Claim**: References `worlds/plane_lidar_runway.sdf`
- **Reality**: File was renamed to `worlds/mini_talon_lidar_runway.sdf`. Old name does not exist.
- **Severity**: High
- **Confidence**: High
- **Fix**: Update all references to use the current filename.

### H-006: Quadcopter STATUS claims exclusivity contradicted by Fixed-wing WORKING status
- **File**: `.ai/vehicles/quadcopter/STATUS.md:12`
- **Claim**: "the only verified working configuration"
- **Reality**: `.ai/vehicles/README.md:16,29` marks Fixed-Wing as "WORKING" since 2026-05-13. Direct contradiction.
- **Severity**: High
- **Confidence**: High
- **Fix**: Remove "only" from quadcopter STATUS or clarify it means historically first.

### H-007: RESOLVED.md last_updated metadata stale
- **File**: `.ai/issues/RESOLVED.md:4-5`
- **Claim**: `last_updated: 2026-03-10`, `updated_by: 2026-03-10_001`
- **Reality**: Contains entries dated `2026-05-11` (FW-002, FW-004, FW-001, TECH-001 at lines 131-173).
- **Severity**: High
- **Confidence**: High
- **Fix**: Update `last_updated` to `2026-05-11` and `updated_by` to most recent session.

### H-008: ArduPilotPlugin.hh referenced but does not exist
- **File**: `.ai/external_mods/ardupilot_gazebo/README.md:69`
- **Claim**: `src/ArduPilotPlugin.hh` listed as unmodified plugin header
- **Reality**: File does NOT exist. Only `ArduPilotPlugin.cc` exists in that directory.
- **Severity**: High
- **Confidence**: High
- **Fix**: Remove the entry or correct the file extension.

### H-009: Missing waypoints file config/full_auto_mission_v7.waypoints
- **File**: `.ai/issues/RESOLVED.md:38,50,64` (LAND-001/002/003 resolution claims)
- **Claim**: `config/full_auto_mission_v7.waypoints` was created with corrected staircase
- **Reality**: File does NOT exist anywhere in the repository.
- **Severity**: High
- **Confidence**: High
- **Fix**: Either create the file or update RESOLVED.md to note it was deleted/lost.

### H-010: Missing T07 evidence from airspeed README index
- **File**: `.ai/features/airspeed/README.md:21-36`
- **Claim**: Evidence file index lists T03, T04, T05 but omits T07
- **Reality**: T07 evidence files exist on disk (T07_RESULTS_2026-04-01.md, T07_summary_2026-04-01.md, etc.) but are NOT listed in index.
- **Severity**: High
- **Confidence**: High
- **Fix**: Add T07 entries to evidence file listing.

### H-011: Incomplete param stack in airspeed launch docs
- **File**: `.ai/features/airspeed/60_LAUNCH_AND_PARAMS.md:32`
- **Claim**: Canonical stack is `plane_base.parm` + `plane_airspeed.parm`
- **Reality**: Actual launch.sh also applies local override `.private/config/plane_params.local.parm` which provides essential ARSPD_SKIP_CAL=1 and ARSPD_OFFSET=0.
- **Severity**: High
- **Confidence**: High
- **Fix**: Add "→ local override" to the canonical param stack description.

---

## MEDIUM Findings

### M-001: MASTER_STATUS_MATRIX missing Wind Matrix / CTE campaign track
- **File**: `.ai/reconciliation/MASTER_STATUS_MATRIX.md:33-43`
- **Claim**: 8 major tracks cover all significant work
- **Reality**: Log directories 017, 018, 019 (the primary active campaign per CURRENT.md) have no matrix track.
- **Fix**: Add "Wind Matrix / CTE Validation" major track.

### M-002: gazebo-plane-wind-sea-level mislabeled as alias
- **File**: `.ai/architecture/SIMULATION_LANES.md:34`
- **Claim**: `gazebo-plane-wind-sea-level` is an alias for Airspeed/CTE lane
- **Reality**: It is a separate launch case calling a dedicated function with a distinct world file.
- **Fix**: Remove from alias list or add as separate lane entry.

### M-003: RESOLVED.md last_updated not matching content
- **File**: `.ai/issues/RESOLVED.md:4-5`
- **Claim**: `last_updated: 2026-03-10`
- **Reality**: Contains entries from 2026-05-11
- **Fix**: Update metadata to reflect true last update.

### M-004: 4 issue prefixes missing from README.md table
- **File**: `.ai/issues/README.md:31-42`
- **Claim**: Prefix table lists all documented issue prefixes
- **Reality**: LAND-, GEAR-, ARSPD-, TECH- prefixes are missing from the table.
- **Fix**: Add all 4 missing prefixes with descriptions.

### M-005: OPEN.md references GEAR-003 (RESOLVED) in deprecated archive
- **File**: `.ai/issues/OPEN.md:29-34`
- **Claim**: GEAR-003 listed in deprecated archive section
- **Reality**: GEAR-003 status is RESOLVED. Appearing in OPEN.md is technically inconsistent but acceptable per README.md:24 stating GEAR files are archival.
- **Fix**: Add explicit note that GEAR entries are archival-only context, not active issues.

### M-006: airspeed docs ARSPD_TYPE context ambiguous
- **File**: `.ai/features/airspeed/50_ARDUPILOT_CALIBRATION.md:38`
- **Claim**: ARSPD_TYPE target value is 100
- **Reality**: This is only true when the airspeed overlay is loaded; plane_base.parm has ARSPD_TYPE 0.
- **Fix**: Add qualifying context about base vs overlay.

### M-007: 018 BIN count ambiguity (63 vs 106)
- **File**: `.ai/features/wind_matrix/55_DATASET_QUALITY_AND_PARAM_FAILURE.md:7-10`
- **Claim**: 63 named BINs audited for 018
- **Reality**: 018 has 106 BIN files; the 63 count may be a filtered subset.
- **Fix**: Clarify whether 63 is pre- or post-audit count.

### M-008: Integrated lane missing param documentation
- **File**: `.ai/features/airspeed_lidar_integrated/IMPLEMENTATION.md:9-12`
- **Claim**: No mention of AIRSPEED_CRUISE or AHRS_WIND_MAX values
- **Reality**: `plane_full.parm` has AIRSPEED_CRUISE=14, AHRS_WIND_MAX=15 (old conservative params)
- **Fix**: Add these values explicitly to IMPLEMENTATION.md.

### M-009: TEST_MATRIX.md broken T03 evidence path
- **File**: `.ai/features/airspeed/TEST_MATRIX.md:194`
- **Claim**: References `evidence/T03_RESULTS_2026-04-01.md`
- **Reality**: File exists at `evidence/raw/T03_RESULTS_2026-04-01.md` instead.
- **Fix**: Change path to `evidence/raw/T03_RESULTS_2026-04-01.md`.

### M-010: CURRENT.md path under-documented
- **File**: `.ai/sessions/CURRENT.md:24`
- **Claim**: `Test_suite framework (scripts/test_suite/) Phase 1 landed`
- **Reality**: Actual path is `src/SIM_ARD_GAW/scripts/test_suite/`
- **Fix**: Make path explicit.

### M-011: LiDAR STATUS date discrepancy with quadcopter
- **File**: `.ai/features/lidar/STATUS.md:13` vs `.ai/vehicles/quadcopter/STATUS.md:71`
- **Claim**: LiDAR says quadcopter last verified 2026-05-11; quadcopter says 2026-01-15
- **Fix**: Sync verification dates or add 2026-05-11 re-verification note.

### M-012: LiDAR CHANGELOG contradictory fixed-wing status
- **File**: `.ai/features/lidar/CHANGELOG.md:55-56` vs `.ai/features/lidar/STATUS.md:14`
- **Claim**: CHANGELOG says "Fixed-Wing: NOT WORKING (blocked)"; STATUS says Fixed-Wing "WORKING"
- **Fix**: Add note that CHANGELOG INIT entry is historical baseline, not current status.

### M-013: TEST_RESULT.md template example uses stale world name
- **File**: `.ai/templates/ISSUE_REPORT.md:63`, `.ai/templates/TEST_RESULT.md:88`
- **Claim**: Example references `plane_lidar_runway.sdf`
- **Reality**: File is `mini_talon_lidar_runway.sdf`. Template example is acceptable but could cause confusion.
- **Classification**: TEMPLATE_EXAMPLE_OK
- **Fix**: Update to current filename for clarity.

### M-014: MODELS.md wrong world association
- **File**: `.ai/vehicles/fixed_wing/MODELS.md:15`
- **Claim**: `mini_talon_with_airspeed` uses `bench_s1_airspeed.sdf` world
- **Reality**: `bench_s1_airspeed.sdf` includes `wind_sitl_probe`, not the full aircraft. The bench uses the probe model.
- **Fix**: Correct the world association for `mini_talon_with_airspeed`.

---

## LOW Findings

### L-001: README.md directory tree omits reconciliation/ directory
- **File**: `.ai/README.md:62-105`
- **Claim**: Directory tree
- **Reality**: Omits `reconciliation/` directory which contains MASTER_STATUS_MATRIX.md
- **Fix**: Add to directory tree.

### L-002: README.md directory tree omits feature directories
- **File**: `.ai/README.md:62-105`
- **Claim**: Only shows `lidar/` and `_TEMPLATE/` under features/
- **Reality**: Also has `airspeed/`, `airspeed_lidar_integrated/`, `altitude_wind/`, `wind_matrix/`
- **Fix**: Add all feature directories.

### L-003: README.md directory tree omits architecture files
- **File**: `.ai/README.md:90-94`
- **Claim**: Only 4 architecture files listed
- **Reality**: Also has `SIMULATION_LANES.md`
- **Fix**: Add SIMULATION_LANES.md.

### L-004: README.md directory tree omits GEAR issue files
- **File**: `.ai/README.md:96-99`
- **Claim**: Only 3 issues files listed
- **Reality**: Also has GEAR-001.md, GEAR-002.md, GEAR-003.md
- **Fix**: Add GEAR files or note they are deprecated.

### L-005: README.md directory tree omits EXTERNAL_MOD.md
- **File**: `.ai/README.md:101-104`
- **Claim**: Only 3 templates listed
- **Reality**: Also has EXTERNAL_MOD.md
- **Fix**: Add to template list.

### L-006: README.md directory tree omits airspeed_claim_test_matrix.md
- **File**: `.ai/README.md:86-88`
- **Claim**: Only README.md and RESULTS.md in tests/
- **Reality**: Also has airspeed_claim_test_matrix.md
- **Fix**: Add to test file listing.

### L-007: ARCHIVAL-OK — IMPLEMENTATION.md.old cross-links
- **File**: `.ai/features/airspeed/IMPLEMENTATION.md.old:367`
- **Classification**: ARCHIVAL_OK
- **Note**: References "config/plane_base.parm + plane_airspeed.parm" concatenation — historical, not live.

### L-008: No copter manual launch in QUICK_START
- **File**: `.ai/QUICK_START.md:48-59`
- **Claim**: Only shows Plane manual launch
- **Reality**: No copter manual launch section documented
- **Fix**: Add copter manual launch: `cd ardupilot && sim_vehicle.py -v ArduCopter -f JSON --console --map` + `gz sim -v4 -r worlds/iris_runway.sdf`.

### L-009: Gazebo wind topic trailing slash
- **File**: `.ai/QUICK_START.md:130-135`
- **Claim**: World topic `/world/mini_talon_wind_runway/wind/`
- **Reality**: Trailing slash is non-standard; may work but inconsistent with conventions.
- **Fix**: Remove trailing slash: `/world/mini_talon_wind_runway/wind`.

### L-010: ARSPD_RATIO=1.99 not anchored in any config file
- **File**: `.ai/tests/airspeed_claim_test_matrix.md:71,114`
- **Claim**: ARSPD_RATIO=1.99
- **Reality**: Value is ArduPilot's default for SITL JSON, not set in any config/.parm file in this project.
- **Fix**: Add comment linking to ArduPilot default source or set explicitly.

### L-011: 019 evidence is report-only, no raw data
- **File**: `.ai/features/wind_matrix/evidence/README.md:10`
- **Claim**: Cross-link to `019_New_Param_Full_CTE_Report/`
- **Reality**: 019 contains only summary/report artifacts, no raw BIN data. 018 is the raw-data source.
- **Fix**: Document that 019 is a post-processing analytical report over 018 data.

### L-012: Undeclared files not listed in PATHS.md
- **File**: `.ai/architecture/PATHS.md`
- **Reality**: 8 items exist on disk but not in PATHS.md: `models/wind_sensor_probe/`, `models/wind_sitl_probe/`, `config/archive/`, `config/recovered_009_param_stack_7439211/`, `scripts/airspeed_claim_probe.py`, `scripts/run_one_og.py`, `scripts/cleanup.sh`, `scripts/test_suite/core/`, `scripts/test_suite/plugins/`
- **Fix**: Per PATHS.md policy, report in DISCOVERED.md and optionally add to PATHS.md.
