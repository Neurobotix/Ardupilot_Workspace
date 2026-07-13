# GPS Failure Behavior — Feature Bundle

Start here to understand the feature, find any file, or pick up work at any
phase.

Feature slug: `gps_failure_behavior`
Current status: Phase 0 design is locked. Phase 1 no-SITL foundation (Chunks
1-6) is **Accepted** (2026-07-13, final no-SITL review): scaffold, payload
semantics, static mission/parameter-stack integration, synthetic mechanism-gate
evaluation, a fake-testable runtime/MAVLink parameter contract, and
integration-readiness wiring into the shared suite path (a `--preflight`
readiness report). All prior findings are resolved and verified in code (see
`review.md`). Phase 2 live smoke is next and remains unverified: no live
SITL/runtime execution, real parameter readback, live MAVLink connection,
BIN/log mechanism extraction, campaign execution, or scientific evidence claim
exists.

## Read Order for New Work

1. `plan.md` — scope, the four-fault catalog, the two-tier knee, behavior
   vocabulary, feature phases, default stack, injection rule, verdict model.
2. `design_research.md` — source-level derivation of the knee (verbatim EKF3
   `posTestRatio` gate and SIM_GPS fault application), and the excluded-knob
   reasoning.
3. `design_adrs.md` — full draft reasoning behind the five Proposed ADRs.
4. `implementation.md` — code homes, Phase 1 no-SITL module map, and pending live gates.
5. `review.md` — phase acceptance records, repair status, and future smoke ledger.
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

## Code Paths

| Path | Purpose |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/` | Plugin package, built from the `airspeed_failure` template |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/readiness.py` | No-SITL integration-readiness report (Chunk 6) |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | CLI entry point (`--list-cases`, `--dry-run`, `--probe-schema`, `--preflight`) |
| `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py` | Registry key `gps_failure` |
| `tests/unit/test_gps_failure_phase1.py` | No-SITL unit tests |
| `tests/unit/test_gps_mechanism_gate.py` | Synthetic mechanism-gate unit tests |
| `tests/unit/test_gps_failure_mavlink.py` | No-SITL MAVLink/runtime contract tests with fake connections |
| `tests/unit/test_gps_failure_readiness.py` | No-SITL integration-readiness and `--preflight` CLI tests |

## Mission and Config

| Path | Purpose |
| --- | --- |
| `assets/missions/gps_failure_behavior_mission.waypoints` | Long one-way mission (based on the 36 km airspeed mission), seq-4 inject, no reciprocal/RTL |
| `config/vehicles/plane_base.parm` | Base vehicle parameters |
| `config/overlays/plane_gps.parm` | GPS overlay pinning `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`, `FS_EKF_THRESH`, `EK3_GPS_CHECK`, `EK3_SRC*`, calm wind |

## Launch Targets

Dedicated identities `plane-gps` and `gazebo-plane-gps` (added structurally
2026-07-13; not live-smoke verified). `plane-gps` loads `plane_base.parm ->
plane_gps.parm` only (no airspeed overlay, no local override, wipes EEPROM);
`gazebo-plane-gps` reuses the sensor-neutral base `mini_talon_runway.sdf` world.
These replaced the earlier incorrect `plane-cte` / `gazebo-plane-cte` references.
See ADR-0021's 2026-07-13 amendment and `design_adrs.md`.

## Human Docs

| Path | Purpose |
| --- | --- |
| `docs/architecture/gps_failure_lane.md` | Lane description, fault set, behavior vocabulary, the knee, ADR cross-links |
| `docs/operations/gps_failure_runbook.md` | Verified no-SITL CLI commands, planned stack, output paths, live-run gate |

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
