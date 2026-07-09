# GPS Failure Behavior — Feature Bundle

Start here to understand the feature, find any file, or pick up work at any
phase.

Feature slug: `gps_failure_behavior`
Current status: Phase 0 (design lock) accepted 2026-07-06. No plugin, no live
run, no evidence yet. Phases 1–4 are open.

## Read Order for New Work

1. `plan.md` — scope, the four-fault catalog, the two-tier knee, behavior
   vocabulary, feature phases, default stack, injection rule, verdict model.
2. `design_research.md` — source-level derivation of the knee (verbatim EKF3
   `posTestRatio` gate and SIM_GPS fault application), and the excluded-knob
   reasoning.
3. `design_adrs.md` — full draft reasoning behind the five Proposed ADRs.
4. `implementation.md` — code homes and Phase 1 build plan (stub until Phase 1).
5. `review.md` — phase acceptance records and smoke ledger (stub until Phase 2).
6. `evidence.md` — evidence pointers (stub until Phase 4).

## This Bundle

| File | Phase | Purpose |
| --- | --- | --- |
| `plan.md` | Phase 0 | Scope, fault catalog, knee, behavior vocabulary, phases, default stack, injection rule, verdict model, required outputs |
| `design_research.md` | Phase 0 | Verbatim EKF3/SIM_GPS source analysis, the knee mechanism, accepted-is-not-captured, excluded-knob table |
| `design_adrs.md` | Phase 0 | Full ADR draft reasoning for the five Proposed decisions |
| `implementation.md` | Phase 1–2 | Code routing, module map, CLI/registry, artifacts, live gates (stub) |
| `review.md` | Phase 0–3 | Acceptance records, smoke ledger, residual risks, rollback rule (stub) |
| `evidence.md` | Phase 2–4 | Raw and curated evidence pointers, closure requirements (stub) |

## Proposed ADRs

All five design decisions were locked 2026-07-06 and promoted to numbered
records in `governance/decisions/`. They are `Status: Proposed` until validated
through live Phase-2 measurement.

| ADR | Subject |
| --- | --- |
| [ADR-0017](../../../decisions/ADR-0017-gps-failure-fault-catalog.md) | Fault catalog and `SIM_GPS1_*` knob mapping (four headline faults) |
| [ADR-0018](../../../decisions/ADR-0018-gps-failure-knee-and-classification.md) | Two-tier knee (`posTestRatio` = 1.0), behavior bands, characterize-not-gate |
| [ADR-0019](../../../decisions/ADR-0019-gps-failure-sweep-design.md) | Severity-sweep design (one variable per fault; drift-has-memory) |
| [ADR-0020](../../../decisions/ADR-0020-gps-failure-mission-and-trigger.md) | Long one-way mission and seq-4 injection trigger |
| [ADR-0021](../../../decisions/ADR-0021-gps-failure-parameter-overlay.md) | `plane_gps.parm` overlay pinning the four knee params |

## Code Paths (planned; created in Phase 1)

| Path | Purpose |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/` | Plugin package, built from the `airspeed_failure` template |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | CLI entry point |
| `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py` | Registry key `gps_failure` |
| `tests/unit/test_gps_failure_phase1.py` | No-SITL unit tests |

## Mission and Config (planned; created in Phase 1)

| Path | Purpose |
| --- | --- |
| `assets/missions/gps_failure_behavior_mission.waypoints` | Long one-way mission (based on the 36 km airspeed mission), seq-4 inject, no reciprocal/RTL |
| `config/vehicles/plane_base.parm` | Base vehicle parameters |
| `config/overlays/plane_gps.parm` | GPS overlay pinning `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`, `FS_EKF_THRESH`, `EK3_GPS_CHECK`, `EK3_SRC*`, calm wind |

## Human Docs

| Path | Purpose |
| --- | --- |
| `docs/architecture/gps_failure_lane.md` | Lane description, fault set, behavior vocabulary, the knee, ADR cross-links |
| `docs/operations/gps_failure_runbook.md` | Verified CLI commands, stack, output paths, live-run gate (stub until Phase 1) |

## Evidence Paths (future)

| Path | Phase | Status |
| --- | --- | --- |
| `var/runs/gps_failure_behavior_*/` | 2–3 | Raw runtime output; not in git |
| `evidence/curated_logs/gps_failure_behavior_<date>/` | 4 | Future curated package |
| `evidence/reports/features/<date>_gps_failure_behavior.md` | 4 | Future evidence report |

## Relationship To Other Lanes

Lane 1 is CTE / wind-matrix (`docs/campaigns/wind_matrix.md`). Lane 2 is
airspeed failure (`governance/runbooks/features/airspeed_failure_behavior/`),
whose plugin is the structural template for this lane. GPS is the maximally
different sensor at the fusion level: airspeed corrupts a control input, GPS
corrupts the vehicle's belief about where it is, which the EKF actively accepts
or rejects — making GPS the sharpest available "knee" experiment.
