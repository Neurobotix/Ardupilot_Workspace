# EVIDENCE_MAP.md — Evidence Claim Verification

Maps every concrete claim that cites evidence to the actual artifact.

## TEST_RESULT Files

| Evidence Claim | .ai File:Line | Actual File | Exists? | Status |
|---------------|---------------|-------------|---------|--------|
| `logs/001_Quad_LiDAR/TEST_RESULT_2026-01-15.md` | MASTER_STATUS_MATRIX.md:49 | `src/SIM_ARD_GAW/logs/001_Quad_LiDAR/TEST_RESULT_2026-01-15.md` | ✅ | OK |
| `logs/002_Plane_Base/TEST_RESULT_2026-01-21.md` | MASTER_STATUS_MATRIX.md:54 | `src/SIM_ARD_GAW/logs/002_Plane_Base/TEST_RESULT_2026-01-21.md` | ✅ | OK |
| `logs/003_Plane_Airspeed/TEST_RESULT_2026-02-04.md` | MASTER_STATUS_MATRIX.md:60 | `src/SIM_ARD_GAW/logs/003_Plane_Airspeed/TEST_RESULT_2026-02-04.md` | ✅ | Has stale content |
| `logs/004_Plane_AutoMission/TEST_RESULT_2026-02-10.md` | MASTER_STATUS_MATRIX.md:82 | `src/SIM_ARD_GAW/logs/004_Plane_AutoMission/TEST_RESULT_2026-02-10.md` | ✅ | OK |
| `logs/005_Plane_Landing/TEST_RESULT_2026-02-16.md` | MASTER_STATUS_MATRIX.md:88 | `src/SIM_ARD_GAW/logs/005_Plane_Landing/TEST_RESULT_2026-02-16.md` | ✅ | OK |
| `logs/006_Plane_FlightLogger/TEST_RESULT_2026-02-18.md` | MASTER_STATUS_MATRIX.md:94 | `src/SIM_ARD_GAW/logs/006_Plane_FlightLogger/TEST_RESULT_2026-02-18.md` | ✅ | OK |
| `logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md` | MASTER_STATUS_MATRIX.md:37 | `src/SIM_ARD_GAW/logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md` | ✅ | PASS_WITH_ISSUES |

## BIN Logs / Binary Evidence

| Evidence Claim | .ai File:Line | Actual File | Exists? | Status |
|---------------|---------------|-------------|---------|--------|
| `archive/ardupilot_logs_20260506/00000110.BIN` | MASTER_STATUS_MATRIX.md:107, RESOLVED.md:105,121 | `/home/ahmed/ardupilot_workspace/archive/ardupilot_logs_20260506/00000110.BIN` | ✅ | Path is workspace-root-relative, not SIM_ARD_GAW-relative |
| `logs/002_Plane_Base/flight_20260121_150436.log` | STATUS.md:66, RESULTS.md:100 | `src/SIM_ARD_GAW/logs/002_Plane_Base/flight_20260121_150436.log` | ✅ | OK |
| `logs/flights/flight_20260121_150436.log` | STATUS.md:66 (old path) | `logs/flights/` dir doesn't exist | ❌ | Stale path |

## Session Files

| Session | Referenced In | Actual File | Exists? |
|---------|--------------|-------------|---------|
| 2026-01-21_001 | MASTER_STATUS_MATRIX.md:55 | `.ai/sessions/2026-01-21_001.md` | ✅ |
| 2026-05-11_001 | RESOLVED.md:132,143,153 | `.ai/sessions/2026-05-11_001.md` | ❌ |
| 2026-05-11_002 | RESOLVED.md:164 | `.ai/sessions/2026-05-11_002.md` | ❌ |
| 2026-05-12_001 | OPEN.md:5 | `.ai/sessions/2026-05-12_001.md` | ❌ |

## Airspeed Evidence Files (in .ai/features/airspeed/evidence/)

| Evidence | Exists? | Note |
|----------|---------|------|
| `evidence/raw/T03_RESULTS_2026-04-01.md` | ✅ | Referenced correctly as `evidence/raw/...` in README |
| `evidence/T03_RESULTS_2026-04-01.md` | ❌ | **Broken path** in TEST_MATRIX.md:194 — should be `evidence/raw/` |
| `evidence/T04_RESULTS_2026-04-01.md` | ✅ | OK path |
| `evidence/T05_RESULTS_2026-04-01.md` | ✅ | OK path |
| `evidence/T07_RESULTS_2026-04-01.md` | ✅ | Exists but NOT listed in README index |

## Evidence Files NOT Cited in .ai

These evidence artifacts exist but have no .ai doc citation:
- `007_Plane_Airspeed_FollowUp/CODE_SNIPPETS.md`
- `007_Plane_Airspeed_FollowUp/FIGURES.md`
- `007_Plane_Airspeed_FollowUp/ISSUES_ENCOUNTERED.md`
- `008_True_Path_Deviation/` (all analysis files)
- `017_params_old_009_matrix_r3_plugin_fixed/HIGH_WIND_OLD_PARAM_FAILURE_ANALYSIS.md`
- `017_params_old_009_matrix_r3_plugin_fixed/internal_wind_audit/*`
- `017_params_old_009_matrix_r3_plugin_fixed/summary/*`
- `019_New_Param_Full_CTE_Report/summary/*`
