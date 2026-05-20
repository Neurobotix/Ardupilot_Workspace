# COVERAGE.md — Audit Coverage Tracking

Every .ai/**/*.md file listed with line count, audit status, and finding count.
Audited: 2026-05-13

| File | Lines | Status | Findings | Notes |
|------|-------|--------|----------|-------|
| .ai/README.md | 212 | READ_FULL | 7 | Directory tree omissions; all path/status claims verified |
| .ai/QUICK_START.md | 169 | READ_FULL | 5 | logs/flights/ path BUG; no copter manual launch section |
| .ai/architecture/COMMANDS.md | 293 | READ_FULL | 6 | wind-check-altitude missing script; RNGFND port docs |
| .ai/architecture/DATA_FLOW.md | 265 | READ_FULL | 3 | Internal arch descriptions, no FS path errors |
| .ai/architecture/OVERVIEW.md | 183 | READ_FULL | 2 | Key files table verified; bridge script exists |
| .ai/architecture/PATHS.md | 237 | READ_FULL | 4 | Generally accurate; 8 undeclared files on disk not listed |
| .ai/architecture/SIMULATION_LANES.md | 46 | READ_FULL | 13 | gazebo-wind-sea-level mislabeled; wind-check-altitude missing script |
| .ai/reconciliation/MASTER_STATUS_MATRIX.md | 154 | READ_FULL | 11 | Date anomaly; missing archive log; contradiction with CURRENT.md; missing Wind Matrix track |
| .ai/sessions/CURRENT.md | 124 | READ_FULL | 4 | Broken path test_suite; claims consistent with RESULTS.md |
| .ai/sessions/2026-01-19_INIT.md | 112 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-01-19_001.md | 99 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-01-19_002.md | 177 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-01-20_001.md | 128 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-01-21_001.md | 90 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-01-26_001.md | 103 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-01-27_001.md | 315 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-02-07_001.md | 158 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-02-08_001.md | 137 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-02-10_001.md | 264 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-02-15_001.md | 182 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-02-15_002.md | 290 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-02-16_001.md | 128 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-02-18_001.md | 181 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-02-24_001.md | 272 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-05_001.md | 635 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-10_001.md | 299 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-11_001.md | 716 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-15_001.md | 307 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-15_002.md | 132 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-18_001.md | 179 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-24_001.md | 243 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-24_002.md | 476 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-24_003.md | 471 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-26_001.md | 357 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-29_001.md | 220 | READ_FULL | 0 | Historical session, no issues |
| .ai/sessions/2026-03-30_001.md | 377 | READ_FULL | 0 | Historical session, no issues |
| .ai/features/README.md | 93 | READ_FULL | 0 | Structural overview, no direct claims needing verification |
| .ai/features/airspeed/00_SCOPE_AND_STATUS.md | 51 | READ_FULL | 1 | Verified scope claims match actual files |
| .ai/features/airspeed/10_SENSOR_MODEL.md | 77 | READ_FULL | 1 | Noise=0.0 confirmed; sensor model validated |
| .ai/features/airspeed/20_WIND_WORLDS.md | 85 | READ_FULL | 1 | Wind world paths verified; sinusoidal variation zeroed |
| .ai/features/airspeed/30_BENCHES.md | 86 | READ_FULL | 1 | Self-acknowledged bench model discrepancy |
| .ai/features/airspeed/40_PLUGIN_TRANSPORT.md | 67 | READ_FULL | 0 | Internal arch description, no FS errors |
| .ai/features/airspeed/50_ARDUPILOT_CALIBRATION.md | 95 | READ_FULL | 1 | ARSPD_TYPE context ambiguous |
| .ai/features/airspeed/60_LAUNCH_AND_PARAMS.md | 93 | READ_FULL | 1 | Incomplete param stack (missing local override) |
| .ai/features/airspeed/70_FLIGHT_VALIDATION.md | 81 | READ_FULL | 0 | Mission files verified |
| .ai/features/airspeed/80_OPEN_ISSUES.md | 54 | READ_FULL | 1 | Doc outdated claim verified as accurate |
| .ai/features/airspeed/90_CHANGELOG.md | 44 | READ_FULL | 0 | Clean changelog |
| .ai/features/airspeed/CHANGELOG.md | 11 | READ_FULL | 0 | Symlink/short changelog |
| .ai/features/airspeed/IMPLEMENTATION.md | 12 | READ_FULL | 0 | Placeholder stub |
| .ai/features/airspeed/IMPLEMENTATION.md.old | 617 | READ_FULL | 0 | ARCHIVAL_OK — proper banner, no cross-links |
| .ai/features/airspeed/README.md | 70 | READ_FULL | 1 | Missing T07 evidence from index |
| .ai/features/airspeed/STATUS.md | 13 | READ_FULL | 0 | Accurate summary |
| .ai/features/airspeed/TEST_MATRIX.md | 458 | READ_FULL | 3 | Broken T03 evidence path; model/world paths verified |
| .ai/features/airspeed_lidar_integrated/STATUS.md | 11 | READ_FULL | 0 | Accurate |
| .ai/features/airspeed_lidar_integrated/IMPLEMENTATION.md | 13 | READ_FULL | 1 | Missing AIRSPEED_CRUISE and AHRS_WIND_MAX values |
| .ai/features/airspeed_lidar_integrated/CHANGELOG.md | 6 | READ_FULL | 0 | Clean |
| .ai/features/altitude_wind/STATUS.md | 17 | READ_FULL | 1 | wind-check-altitude references missing script |
| .ai/features/altitude_wind/IMPLEMENTATION.md | 16 | READ_FULL | 0 | Accurate |
| .ai/features/altitude_wind/CHANGELOG.md | 7 | READ_FULL | 0 | Clean |
| .ai/features/lidar/STATUS.md | 136 | READ_FULL | 3 | Contradiction with quadcopter STATUS on verification date; missing 00000110.BIN path |
| .ai/features/lidar/IMPLEMENTATION.md | 258 | READ_FULL | 0 | Gazebo sensor range 0.3-40m confirmed |
| .ai/features/lidar/CHANGELOG.md | 96 | READ_FULL | 2 | Stale world name; contradictory fixed-wing status |
| .ai/features/wind_matrix/00_SCOPE_AND_STATUS.md | 19 | READ_FULL | 0 | Accurate 017/018 designation |
| .ai/features/wind_matrix/10_CAMPAIGN_DESIGN.md | 13 | READ_FULL | 0 | Mission file verified |
| .ai/features/wind_matrix/20_RUNNERS.md | 10 | READ_FULL | 0 | Structural |
| .ai/features/wind_matrix/30_DATA_PRODUCTS.md | 7 | READ_FULL | 0 | Structural |
| .ai/features/wind_matrix/40_ANALYSIS_PIPELINE.md | 7 | READ_FULL | 0 | Structural |
| .ai/features/wind_matrix/50_ENVIRONMENT_ROOT_CAUSE.md | 8 | READ_FULL | 0 | Accurate |
| .ai/features/wind_matrix/55_DATASET_QUALITY_AND_PARAM_FAILURE.md | 35 | READ_FULL | 2 | BIN count ambiguity (63 vs 106); param contrast accurate |
| .ai/features/wind_matrix/60_TEST_SUITE_INTEGRATION.md | 7 | READ_FULL | 0 | Structural |
| .ai/features/wind_matrix/80_OPEN_ISSUES.md | 53 | READ_FULL | 0 | All WM issues match source findings |
| .ai/features/wind_matrix/90_CHANGELOG.md | 6 | READ_FULL | 0 | Clean |
| .ai/features/wind_matrix/evidence/README.md | 11 | READ_FULL | 1 | 019 is report-only, not raw data |
| .ai/features/wind_matrix/README.md | 22 | READ_FULL | 0 | Accurate |
| .ai/features/_TEMPLATE/STATUS.md | 40 | READ_PARTIAL | 0 | TEMPLATE_EXAMPLE_OK |
| .ai/features/_TEMPLATE/IMPLEMENTATION.md | 54 | READ_PARTIAL | 0 | TEMPLATE_EXAMPLE_OK |
| .ai/features/_TEMPLATE/CHANGELOG.md | 44 | READ_PARTIAL | 0 | TEMPLATE_EXAMPLE_OK |
| .ai/issues/DISCOVERED.md | 63 | READ_FULL | 1 | SYS-001 status "Suspected" consistent |
| .ai/issues/GEAR-001.md | 315 | READ_FULL | 0 | ARCHIVAL_OK — proper status |
| .ai/issues/GEAR-002.md | 261 | READ_FULL | 0 | ARCHIVAL_OK |
| .ai/issues/GEAR-003.md | 299 | READ_FULL | 0 | ARCHIVAL_OK — RESOLVED |
| .ai/issues/OPEN.md | 62 | READ_FULL | 1 | GEAR-003 (RESOLVED) in deprecated archive table — acceptable per README |
| .ai/issues/README.md | 82 | READ_FULL | 1 | 4 issue prefixes missing from table |
| .ai/issues/RESOLVED.md | 187 | READ_FULL | 6 | Date anomaly; missing session files; missing waypoints file; stale world name |
| .ai/templates/EXTERNAL_MOD.md | 124 | READ_PARTIAL | 0 | TEMPLATE_EXAMPLE_OK |
| .ai/templates/ISSUE_REPORT.md | 69 | READ_PARTIAL | 0 | TEMPLATE_EXAMPLE_OK — stale world name in example |
| .ai/templates/SESSION_ENTRY.md | 96 | READ_PARTIAL | 0 | TEMPLATE_EXAMPLE_OK |
| .ai/templates/TEST_RESULT.md | 122 | READ_PARTIAL | 0 | TEMPLATE_EXAMPLE_OK |
| .ai/tests/README.md | 98 | READ_FULL | 0 | All paths verified |
| .ai/tests/RESULTS.md | 171 | READ_FULL | 1 | Missing log file path for TEST-002 |
| .ai/tests/airspeed_claim_test_matrix.md | 122 | READ_FULL | 3 | diff_pressure sign contradiction; ARSPD_RATIO unanchored |
| .ai/vehicles/README.md | 86 | READ_FULL | 0 | Structural overview |
| .ai/vehicles/fixed_wing/STATUS.md | 138 | READ_FULL | 3 | Stale world name; missing flight log dir; model verification dates verified |
| .ai/vehicles/fixed_wing/ISSUES.md | 79 | READ_FULL | 1 | Stale world name |
| .ai/vehicles/fixed_wing/MODELS.md | 138 | READ_FULL | 2 | Wrong model/world association; missing world from table |
| .ai/vehicles/fixed_wing/PARAMETERS.md | 138 | READ_FULL | 0 | LAND_FLARE_ALT 1 confirmed |
| .ai/vehicles/quadcopter/STATUS.md | 106 | READ_FULL | 2 | Contradictory exclusivity claim; date discrepancy with LiDAR feature |
| .ai/vehicles/quadcopter/ISSUES.md | 56 | READ_FULL | 0 | Clean |
| .ai/vehicles/quadcopter/MODELS.md | 89 | READ_FULL | 0 | All paths verified |
| .ai/vehicles/quadcopter/PARAMETERS.md | 103 | READ_FULL | 0 | Accurate |
| .ai/external_mods/README.md | 146 | READ_FULL | 1 | ARSPD_TYPE mismatch |
| .ai/external_mods/SUMMARY.md | 65 | READ_FULL | 1 | ARSPD_TYPE mismatch |
| .ai/external_mods/ardupilot_gazebo/README.md | 50 | READ_FULL | 2 | ARSPD_TYPE mismatch; missing .hh file |
| .ai/external_mods/ardupilot_gazebo/ArduPilotPlugin/airspeed_json.md | 301 | READ_FULL | 6 | 4 ARSPD_TYPE=100 in plane_base.parm claims; missing session file; wrong section header |
| .ai/external_mods/ardupilot/README.md | 50 | READ_PARTIAL | 0 | Structural |
| .ai/external_mods/gazebo/README.md | 50 | READ_PARTIAL | 0 | Structural |
