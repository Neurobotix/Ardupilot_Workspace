# Flight Logs & Test Results

## Test Directories

| ID | Date | Test | Status |
|----|------|------|--------|
| 001_Quad_LiDAR | 2026-01-15 | Iris LiDAR integration | **PASS** |
| 002_Plane_Base | 2026-01-21 | Mini Talon base flight | **PASS** |
| 003_Plane_Airspeed | 2026-02-04 | Airspeed sensor integration | **IMPLEMENTATION_COMPLETE** |
| 004_Plane_AutoMission | 2026-02-10 | Full autonomous mission | **PASS_WITH_ISSUES** |
| 005_Plane_Landing | 2026-02-16 | Landing system verified (v1.0.0) | **PASS** |
| 006_Plane_FlightLogger | 2026-02-18 | Flight logger phase detection | **PASS** |
| 007_Plane_Airspeed_FollowUp | 2026-04-02 | Airspeed validation follow-up | **PASS_WITH_ISSUES** |

Notes:
- `003_Plane_Airspeed` is the implementation snapshot.
- `007_Plane_Airspeed_FollowUp` is the authoritative end-to-end validation package for the current airspeed story.

## Flight Logs

This index lists imported historical curated test summaries. New runtime flight
logs in `workspace_next` belong under `var/`, including logger output under
`var/logs/flight_logger/`; raw logs are not promoted here blindly. Use
`docs/operations/evidence_workflow.md` and
`evidence/indexes/evidence_catalog.md` for new reviewed proof.

## Analysis Tools

### Online
Upload .BIN files to https://plot.ardupilot.org

### Command Line
```bash
# View rangefinder data
mavlogdump.py ./XXXXXXXX.BIN --types RFND

# Export to CSV
mavlogdump.py ./XXXXXXXX.BIN --format csv > flight_data.csv
```

### MAVExplorer
```bash
MAVExplorer.py ./XXXXXXXX.BIN
```

## Note
.BIN files are gitignored (can be 100+ MB)
