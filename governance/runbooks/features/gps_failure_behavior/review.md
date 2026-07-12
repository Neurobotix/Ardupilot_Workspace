# GPS Failure Behavior — Review

Status: Phase 1 Chunk 3 is **implemented pending review**. Full Phase 1 remains
open.

## Phase Acceptance Ledger

| Phase | Status | Date | Notes |
| --- | --- | --- | --- |
| Phase 0 — design lock | Accepted | 2026-07-06 | Full brainstorm; four faults, two-tier knee, seven bands, characterize-not-gate; five Proposed ADRs (0017–0021). |
| Phase 1 — no-SITL plugin foundation | Open | — | Chunks 1–3 exist: scaffold, payload semantics, and static mission/parameter-stack integration. Chunk 3 is implemented pending review; runtime and mechanism-gate work remain open. |
| Phase 2 — live smoke | Open | — | — |
| Phase 3 — full v1 campaign | Open | — | — |
| Phase 4 — evidence curation | Open | — | — |

## Phase 1 Chunk 1 Review Note

Phase 1 Chunk 1 is a scaffold, not full Phase 1 acceptance. It includes the
no-SITL plugin skeleton, deterministic case catalog, dry-run CLI, registry
construction, and unit tests. At the Chunk 1 boundary it did not include the
GPS mission, `plane_gps.parm`, runtime/MAVLink, live monitoring, BIN
mechanism-gate extraction, or any evidence claim.

## Phase 1 Chunk 2 Review Note

Phase 1 Chunk 2 is implemented pending review. It adds pure GLTCH
metre-to-degree conversion helpers, resolved `slow_drift`/`step_glitch` preview
payloads from a reference latitude, and the locked continuous slow-drift
accumulation metadata case. At the Chunk 2 boundary, live trigger-time payload
resolution, mission assets, `plane_gps.parm`, runtime MAVLink injection, and
the mechanism gate were still open.

## Phase 1 Chunk 3 Review Note

Phase 1 Chunk 3 is implemented pending review. It adds the locked GPS mission,
dedicated `plane_gps.parm`, base-then-overlay default-stack integration, and
static/no-SITL structural tests. No live SITL/Gazebo run or parameter readback
has occurred, and the realized straight-leg duration remains a Phase-2
validation item. Full Phase 1 remains open; this chunk is not accepted and does
not establish scientific validity.

## Phase 0 Baseline

No accepted GPS-failure behavior evidence existed before this lane. The design
is grounded in source (`design_research.md`); no live SITL run was performed for
Phase 0.

## Residual Risks / Open Items (carried to Phase 1–2)

- The knee bracket (`0.2–8.0 m/s`) is a design guess; the empirical knee is a
  Phase-2 result. Extend the rate list if it lands outside the bracket.
- The four pinned EKF params are fixed in the checked-in overlay and must still
  be read back live.
- The GPS mission's realized straight-leg duration must be confirmed sufficient
  for the slowest drift rate.

## Smoke Ledger (Phase 2)

Empty until Phase 2. Will record raw run roots, artifact checklists, and the gate
decision before Phase 3.

## Rollback Rule

Phase 0 is docs-only (runbook + ADRs + human docs + index entries); rollback is
deleting the `gps_failure_behavior` bundle, the five ADRs, and reverting the
index edits. No code or runtime state is touched in Phase 0.
