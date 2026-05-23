# ISSUE_AUDIT.md — Issue Tracking Consistency

## Issue Prefixes vs README.md Table

| Prefix | Used In | Documented in README.md:31-42? |
|--------|---------|-------------------------------|
| `LAND-` | RESOLVED.md:9,28,42,56 | **MISSING** |
| `GEAR-` | GEAR-*.md, OPEN.md:32, RESOLVED.md:69 | **MISSING** |
| `ARSPD-` | RESOLVED.md:82 | **MISSING** |
| `TECH-` | RESOLVED.md:163 | **MISSING** |
| `FW-` | RESOLVED.md:99,113,130,141,151 | ✅ Documented |
| `WM-` | features/wind_matrix/80_OPEN_ISSUES.md | ✅ Documented |
| `SYS-` | DISCOVERED.md:24 | ✅ Documented |

## Cross-Reference: OPEN.md ↔ RESOLVED.md ↔ DISCOVERED.md

- ✅ No resolved issue remains in OPEN.md (GEAR-003 in deprecated archive table is acceptable per README.md:24)
- ✅ All OPEN.md resolved entries correspond to RESOLVED.md entries
- 🔴 RESOLVED.md `last_updated: 2026-03-10` contradicts entries dated 2026-05-11
- ✅ DISCOVERED.md SYS-001 (status "Suspected") consistent — not promoted to OPEN.md or RESOLVED.md yet
- 🔴 RESOLVED.md references `2026-05-11_001`, `2026-05-11_002` sessions — both MISSING
- 🔴 OPEN.md references `2026-05-12_001` session — MISSING

## WM Issues vs Source Findings

| WM Issue | 03_findings.md Match | Resolution Status |
|----------|---------------------|-------------------|
| WM-001 | ✅ PATH environment fix — `_prepend_path_entry` present in `run_one.py:194` | ✅ RESOLVED |
| WM-003 | ✅ "run_matrix.py does not use isolated SITL log directories" | Open |
| WM-006 | ✅ "no manifest lock" | Open |
| WM-007 | ✅ "failed_analysis not first-class terminal status" | Open |
| WM-008 | ✅ "mission layout hardcoded" | Open |
| WM-009 | ✅ "regex SDF mutation" | Open |
| WM-010 | ✅ "wind topic injection verification trusts successful publisher return" | Open |
| WM-011 | ✅ "param file content/hash pinning" | Open (not in 03_findings.md but not contradicted) |

## Feature-Level Issue Lists

- ✅ `features/wind_matrix/80_OPEN_ISSUES.md` lists WM-003,006,007,008,009,010,011 — consistent with canonical
- ✅ `features/airspeed/80_OPEN_ISSUES.md` lists 5 unnumbered issues — no overlap with canonical lists

## GEAR Issues Cross-Reference

- GEAR-001.md: DEPRECATED_ARCHIVE (line 7)
- GEAR-002.md: DEPRECATED_ARCHIVE (line 7)
- GEAR-003.md: RESOLVED (line 7) — appears in RESOLVED.md:69
- All reference session `2026-02-15_002` ✅ (exists)
- GEAR-003 references session `2026-02-16_001` ✅ (exists)

## Missing Path References in Issues

| Path | Reference | Status |
|------|-----------|--------|
| `config/full_auto_mission_v7.waypoints` | RESOLVED.md LAND-001:38 | 🔴 MISSING |
| `archive/ardupilot_logs_20260506/00000110.BIN` | RESOLVED.md FW-003:105, FW-005:121 | ✅ EXISTS at workspace root (path ambiguous) |
