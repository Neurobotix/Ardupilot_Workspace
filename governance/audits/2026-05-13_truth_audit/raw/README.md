# Audit README

## Scope

Documentation correctness audit of `.ai/` knowledge base against real project state in `src/SIM_ARD_GAW/` and `.private/`.

**Audit date**: 2026-05-13  
**Auditor**: opencode automated audit  
**Output directory**: `/home/ahmed/ardupilot_workspace/.tmp_ai_truth_audit/`

## Command Inventory

All verification commands used in this audit:
- `find` — file discovery across config/, models/, worlds/, missions/, logs/
- `grep -rn` — content search (rg unavailable)
- `ls -la` — directory listing
- `sed -n` — reading specific line ranges
- `nl -ba` — line-numbered file reading (via Read tool)
- `wc -l` — line counts

## Pass/Fail Summary

| Check | Result |
|-------|--------|
| Forbidden dataset references (009/010) in .ai/ | ✅ PASS (0 hits) |
| Nonexistent log bucket refs (012-016) | ✅ PASS (0 hits) |
| Compound param path refs | ✅ PASS (0 hits outside .old) |
| AI pipeline artifacts | ✅ PASS (0 hits) |
| .private refs all resolve | ✅ PASS (10 refs, all valid) |
| Path references (overall) | ⚠️ FAIL (~85% accurate, see PATH_AUDIT.csv) |
| Param value claims | ❌ FAIL (6 critical ARSPD_TYPE=100 in wrong file) |
| Issue tracking consistency | ❌ FAIL (stale dates, missing session files) |
| Evidence file paths | ⚠️ FAIL (broken logs/flights/ path, broken T03 path) |
| Command validity | ❌ FAIL (wind-check-altitude BROKEN_TARGET) |
| Contradiction consistency | ❌ FAIL (14 contradictions found) |

## Output Files

| File | Description |
|------|-------------|
| `AUDIT_LOG.md` | Append-only audit trail |
| `COVERAGE.md` | Every .ai file with coverage status |
| `FINDINGS.md` | All findings ordered by severity (42 total) |
| `PROPOSED_FIX_PLAN.md` | Grouped by file, exact edits with context |
| `CLAIMS_MATRIX.csv` | All claims with CSV-escaped values |
| `PATH_AUDIT.csv` | Every path-like reference classified |
| `COMMAND_AUDIT.md` | Every command classified |
| `ISSUE_AUDIT.md` | Issue tracking consistency |
| `PARAMETER_TRUTH.md` | Parameter truth table |
| `EVIDENCE_MAP.md` | Evidence-to-artifact mapping |
| `DEAD_LINKS_AND_MISSING_TARGETS.md` | Missing links and files |
| `CONTRADICTIONS.md` | Internal and external contradictions |
| `FINAL_VERIFICATION.md` | Final verification and verdict |
