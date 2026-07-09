# GPS Failure Behavior — Evidence

Status: **stub.** No evidence exists yet. Phase 0 is design-only; the first raw
runtime output appears in Phase 2, and the first curated package in Phase 4.

## Current Evidence

None. Phase 0 produced design records only:

- `governance/runbooks/features/gps_failure_behavior/` (this bundle)
- `governance/decisions/ADR-0017..0021`

## Future Evidence Paths

| Path | Phase | Status |
| --- | --- | --- |
| `var/runs/gps_failure_behavior_*/` | 2–3 | Raw runtime output; not in git |
| `evidence/curated_logs/gps_failure_behavior_<date>/` | 4 | Future curated package |
| `evidence/reports/features/<date>_gps_failure_behavior.md` | 4 | Future evidence report |

## Closure Requirements (Phase 4)

- Curate a dated package under `evidence/curated_logs/`.
- Add a dated report under `evidence/reports/features/`.
- Update `evidence/indexes/evidence_catalog.md`.
- Report the knee (the drift rate where the mechanism tier flips from
  `silent_drift` to `detected_rejected`) with the pinned gate values.
