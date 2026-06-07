# Airspeed Failure Behavior — Feature Bundle

Start here to understand the feature, find any file, or pick up work at any
phase.

Feature slug: `airspeed_failure_behavior`
Current status: Phase 2 live measurement smoke accepted 2026-06-06. Phase 3
full v1 matrix unlocked; not yet run.

## Read Order for New Work

1. `plan.md` — scope, motivation, case design, phase definitions, and success
   criteria.
2. `implementation.md` — code homes, module responsibilities, injection rule,
   artifact requirements, and live gates.
3. `review.md` — phase acceptance records, smoke ledger, residual risks, and
   rollback rule.
4. `design_research.md` — deep SIM_ARSPD_* signal-chain analysis, parameter
   semantics, and mission geometry reasoning.
5. `design_adrs.md` — full draft reasoning behind the six accepted ADRs.
6. `evidence.md` — pointer file for future curated evidence; no accepted
   behavior evidence exists yet.

## This Bundle

| File | Phase | Purpose |
| --- | --- | --- |
| `plan.md` | Phase 0 | Scope, motivation, case design lock, feature phases, default stack, injection rule, required analysis outputs |
| `implementation.md` | Phase 1–2 | Code routing, module map, CLI/registry, artifact requirements, behavior classification, live gates |
| `review.md` | Phase 0–2 | Acceptance records, smoke ledger (Phase 2 raw run root), residual risks, rollback rule |
| `design_research.md` | Phase 0 | Source-level SIM_ARSPD_* analysis, signal-chain derivation, mission geometry, must-measure items |
| `design_adrs.md` | Phase 0 | Full ADR draft reasoning for the six promoted decisions |
| `evidence.md` | Phase 4 | Pointer to future curated logs and evidence reports; no accepted evidence yet |

## Accepted ADRs

All six design decisions were locked 2026-06-03 and promoted to numbered
records in `governance/decisions/`.

| ADR | Subject |
| --- | --- |
| [ADR-0006](../../../decisions/ADR-0006-airspeed-failure-mission-design.md) | Mission design (100 m cruise, 800 m legs, RTL end, inject entering seq 4) |
| [ADR-0007](../../../decisions/ADR-0007-airspeed-failure-case-payloads-and-ratio-sweep.md) | Case payloads and ratio-sweep recipe |
| [ADR-0008](../../../decisions/ADR-0008-airspeed-failure-reset-protocol.md) | Reset to source defaults, not zeros; boot-baseline capture |
| [ADR-0009](../../../decisions/ADR-0009-airspeed-failure-injection-trigger.md) | Injection trigger on entering seq 4 |
| [ADR-0010](../../../decisions/ADR-0010-airspeed-failure-reference-wind.md) | Fixed reference wind x=−5, y=0, z=0 ENU |
| [ADR-0011](../../../decisions/ADR-0011-airspeed-failure-behavior-classification.md) | Behavior-class vocabulary and observation-quality gating |

## Code Paths

| Path | Purpose |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/` | Plugin package (config, defaults, case_generator, environment, stimulus, control, monitor, analyzers, manifest, plugin, mavlink, runtime) |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py` | CLI entry point (`--list-cases`, `--dry-run`, `--probe-schema`, `--live-smoke`, `--live-measurement-probes`, `--live-case`) |
| `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py` | Registry key `airspeed_failure` |
| `tests/unit/test_airspeed_failure_phase1.py` | No-SITL unit tests (19 tests; Phase 2 follow-up review pass) |

## Mission and Config

| Path | Purpose |
| --- | --- |
| `assets/missions/airspeed_failure_behavior_mission.waypoints` | Purpose-built fault-injection mission (100 m cruise, 800 m legs, seq 4 inject, RTL end) |
| `config/vehicles/plane_base.parm` | Base vehicle parameters |
| `config/overlays/plane_airspeed.parm` | Conservative airspeed overlay (14/10/22); default stack |

## Human Docs

| Path | Purpose |
| --- | --- |
| `docs/architecture/airspeed_failure_lane.md` | Lane description, case set, behavior vocabulary, output paths, ADR cross-links |
| `docs/operations/airspeed_failure_runbook.md` | Verified CLI commands, stack, output paths, live-run gate |

## Evidence Paths (future)

| Path | Phase | Status |
| --- | --- | --- |
| `var/runs/airspeed_failure_behavior_*/` | 2–3 | Raw runtime output; not in git |
| `evidence/curated_logs/airspeed_failure_behavior_<date>/` | 4 | Curated package; not yet created |
| `evidence/reports/features/<date>_airspeed_failure_behavior.md` | 4 | Dated evidence report; not yet created |

The Phase 2 measurement-smoke raw root (not curated evidence):
`var/runs/airspeed_failure_behavior_20260606T164050810132Z/`
