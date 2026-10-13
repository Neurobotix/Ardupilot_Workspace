# GPS Failure Behavior — Evidence

Status: **stub for promoted evidence.** Raw runtime output exists, but no
curated GPS evidence package or feature report exists as of 2026-08-17. Raw
root `var/runs/gps_failure_behavior/` records v6-geometry non-jamming
fault-case runs from 2026-07-20 with one accepted repetition per case; under
`governance/standards/evidence.md`, that `var/` root is not promoted evidence.

## Current Evidence

None promoted. Phase 0 produced design records, and Phase 2 produced raw
runtime output only:

- `governance/runbooks/features/gps_failure_behavior/` (this bundle)
- `governance/decisions/ADR-0017..0021`
- `var/runs/gps_failure_behavior/` (2026-07-20 raw v6-geometry non-jamming
  root, one accepted repetition per case; not curated evidence)

## Future Evidence Paths

| Path | Phase | Status |
| --- | --- | --- |
| `var/runs/gps_failure_behavior/` | 2–3 | Raw v6-geometry non-jamming root from 2026-07-20; one accepted repetition per case; not promoted evidence |
| `var/runs/gps_failure_behavior_*/` | 2–3 | Raw runtime output; not in git |
| `evidence/curated_logs/gps_failure_behavior_<date>/` | 4 | Future curated package |
| `evidence/reports/features/<date>_gps_failure_behavior.md` | 4 | Future evidence report |

## Closure Requirements (Phase 4)

- Curate a dated package under `evidence/curated_logs/`.
- Add a dated report under `evidence/reports/features/`.
- Update `evidence/indexes/evidence_catalog.md`.
- Report the knee (the drift rate where the mechanism tier flips from
  `silent_drift` to `detected_rejected`) with the pinned gate values.
