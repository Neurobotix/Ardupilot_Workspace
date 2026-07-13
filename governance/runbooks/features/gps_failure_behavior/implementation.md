# GPS Failure Behavior — Implementation

Status: Phase 1 Chunk 6 is implemented pending review; it wires the lane into the
shared suite path and adds a no-SITL integration-readiness report. Full Phase 1
remains open (no live SITL/Gazebo run or evidence claim).

## Implemented In Phase 1 Chunk 1

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/` | No-SITL plugin skeleton: defaults, config, deterministic case generator, stimulus metadata, manifest, analyzer schema/classifier, environment/control/monitor stubs, and plugin assembly. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | No-SITL CLI entry point for `--list-cases`, `--dry-run --case <case_id>`, and `--probe-schema`. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py` | Registry key `gps_failure`. |
| `tests/unit/test_gps_failure_phase1.py` | No-SITL unit tests for case catalog, schema, trigger metadata/helpers, dry-run JSON, registry construction, manifest counting, classifier states, and legacy-runner exclusion. |

## Implemented In Phase 1 Chunk 2

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/glitch.py` | Pure metre-to-degree conversion helpers for `SIM_GPS1_GLTCH_X/Y`, plus deterministic `step_glitch_payload` and `slow_drift_payload` builders. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/case_generator.py` | GLTCH cases now carry explicit frame/sign/conversion recipes, example reference-latitude payloads, and the ADR-0019 continuous slow-drift accumulation metadata case. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Dry-run accepts `--reference-latitude-deg` and `--preview-elapsed-s` to emit preview-only resolved payloads without launching SITL. |
| `tests/unit/test_gps_failure_phase1.py` | No-SITL tests cover GLTCH unit/frame/sign behavior, dry-run preview behavior, accumulation metadata, and denial/jamming payload regressions. |

## Implemented In Phase 1 Chunk 3

| Path | Responsibility |
| --- | --- |
| `assets/missions/gps_failure_behavior_mission.waypoints` | Locked QGC WPL 110 five-item GPS mission: seq-4 injection edge, explicit 15 m/s command, approximately 36 km one-way Eastbound leg, and no reciprocal/RTL/landing items. |
| `config/overlays/plane_gps.parm` | Dedicated overlay applied after `plane_base.parm`; pins the four EKF knee inputs, complete primary EKF source set, and calm SITL wind without airspeed tuning. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/defaults.py` | Two-file Phase-1 default parameter stack and current overlay schema status. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Dry-run output exposes the effective two-file parameter stack. |
| `tests/unit/test_gps_failure_phase1.py` | Deterministic no-SITL parsers and structural tests for mission geometry, parsed parameter values/uniqueness, stack order/override, generated case mission paths, and CLI schema output. |

## Implemented In Phase 1 Chunk 4

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/mechanism_gate.py` | Synthetic no-SITL EKF mechanism-gate evaluator for decoded records; validates time and `posTestRatio`, computes gate/reset/rejection metrics, and fails closed for missing, malformed, non-finite, or out-of-order data. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/analyzers.py` | Backward-compatible classifier hook that can consume a mechanism-gate result shape while preserving the existing `mechanism_evidence=True` path. |
| `tests/unit/test_gps_mechanism_gate.py` | Unit tests for below-gate fusion, exact/above-gate rejection, reset evidence, malformed data, metrics, out-of-order timestamps, JSON-safe serialization, analyzer consumption, and no runtime command invocation. |

## Implemented In Phase 1 Chunk 5

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/mavlink.py` | Fake-testable parameter adapter and helpers for deterministic set/read, batch writes, injected-parameter readback, tolerance comparison, missing/non-finite rejection, and structured write/readback results. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/runtime.py` | Plan-only runtime bridge from `TestCase` plus trigger metadata to resolved GPS injection payloads, readback rules, restore plans, and explicit fail-closed execution results when no connection is supplied. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/stimulus.py` | Stimulus artifact now records the plan-only live contract and exposes a `build_live_plan_preview()` helper without executing MAVLink writes. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Dry-run JSON explicitly reports `launch_performed=false` and `live_readback_performed=false`. |
| `tests/unit/test_gps_failure_mavlink.py` | Focused no-SITL tests for fake-connection parameter I/O, readback failures, runtime plan resolution, restore plans, fail-closed missing metadata, and no dependency on real MAVLink/SITL. |

## Implemented In Phase 1 Chunk 6

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/readiness.py` | No-SITL integration-readiness report: builds the plugin (optionally via the shared registry), iterates the full case catalog, and reports the SuiteRunner seams, manifest/artifact contract, effective parameter stack, trigger, and the explicit live blockers with `ready_for_live_run=false`. Opens no connection and writes no manifest. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Adds the `--preflight` action emitting the readiness report as deterministic JSON. |
| `tests/unit/test_gps_failure_readiness.py` | No-SITL tests for the readiness report (suite seams, case counts, manifest/artifact contract, param stack, live blockers, registry consistency, narrowed-config counts, JSON safety) and the `--preflight` CLI (valid JSON, mutual exclusion). |

Chunk 6 is integration-readiness only. It proves the lane is wired into the
shared suite path far enough to run and reports its own Phase-1 no-SITL posture;
it starts no stack, opens no MAVLink connection, parses no BIN/log, and makes no
evidence claim.

## Current No-SITL Semantics

- Case generation covers `nominal`, the ADR-0019 drift-rate ladder, the
  continuous slow-drift accumulation instrument, step-glitch magnitude ladder,
  denial-duration ladder, and five jamming repeat cases.
- The trigger helpers model ADR-0020 at schema level: seq 1, 2, and 3 must be
  observed before the first seq 4; the structured helper additionally requires
  those front-half events and the seq-4 event to be armed and in `AUTO`.
- The generated acceptance requirements use the locked GPS post-injection
  observation window of at least 90 s.
- `slow_drift` and `step_glitch` recipes use the explicit contract from
  `glitch.py`: north metres convert to `SIM_GPS1_GLTCH_X` latitude degrees,
  east metres convert to `SIM_GPS1_GLTCH_Y` longitude degrees using
  `111_320 * cos(latitude_deg)`, and `SIM_GPS1_GLTCH_Z` stays a reset/default
  guard rather than a v1 fault axis.
- Dry-run without a reference latitude emits recipe metadata only. Dry-run with
  `--reference-latitude-deg` emits `resolved_payload_preview`, clearly marked as
  not the live payload.
- `slow_drift_accumulation_ramp` is a no-SITL metadata case for ADR-0019's
  continuous ramp: fresh flight, no in-flight reset, accumulation/endurance
  measurement, not independent knee points.
- The classifier keeps the seven locked behavior bands intact and uses
  `analysis_incomplete` as an analysis/quality state for short windows, missing
  artifacts, or missing mechanism/behavior fields.
- Required no-SITL artifact schema names are the locked JSON names:
  `gps_injection.json`, `gps_behavior_summary.json`,
  `ekf_innovation_metrics.json`, `truth_vs_belief.json`, `mode_timeline.json`,
  and `attitude_altitude_envelope.json`.
- The static default parameter stack is
  `config/vehicles/plane_base.parm` followed by
  `config/overlays/plane_gps.parm`; an explicit caller stack still overrides
  that default.
- The checked-in mission and overlay have static/no-SITL contract coverage.
  No live mission timing or parameter readback is implied.
- The no-SITL mechanism gate accepts synthetic EKF-like records only. It treats
  `posTestRatio >= 1.0` as the locked gate crossing, reports reset evidence as
  distinct from simple rejection, and marks missing/malformed/non-finite or
  out-of-order mechanism data as `mechanism_unverified`.
- The runtime contract separates preview from execution authorization.
  `build_live_injection_plan` resolves a preview payload (for inspection/dry-run)
  but is never execution-authorized. `build_authorized_injection_plan` requires a
  structured monitor trace validated through the canonical
  `monitor.first_seq4_edge_after_armed_auto_front_half` helper (seq 1→2→3→4,
  armed, AUTO), producing deterministic JSON-safe `TriggerEvidence`. Only a
  nominal no-write plan or a plan carrying validated trigger evidence is
  executable; `execute_injection_plan` refuses any unauthorized
  parameter-writing plan before any connection call.
  `slow_drift`/`step_glitch` resolve `SIM_GPS1_GLTCH_*` degree payloads from the
  seq-4 trigger latitude/elapsed time; `hard_denial`/`jamming` include bounded
  restore plans. Every injected or restore parameter has a readback rule.
- The MAVLink contract is an adapter around a supplied connection or fake. It
  does not import or create a real MAVLink transport at module import time. Batch
  writes go through an atomic `preflight_batch` stage that validates the payload
  type, parameter names, values, readback-rule structure, expected values,
  tolerances, and payload/rule key correspondence before the first write, so any
  invalid entry (including one that sorts after a valid entry) performs zero
  writes and zero reads. Sorted deterministic write order is preserved after
  validation succeeds.
- The analyzer classifies from substantive, finite behavior-tier metrics
  (truth-vs-belief gap, gap growth, attitude band, mechanism state), not a bare
  `behavior_evidence=True` marker. Nominal requires explicit nominal evidence;
  each non-nominal band requires its own evidence; missing, contradictory,
  malformed, non-finite, or unsupported behavior evidence yields
  `analysis_incomplete` / `accepted_observation=false` with a specific reason.
- The manifest acceptance rule requires every acceptance-bearing signal to agree
  (terminal success, success verdict with explicit accepted metadata, non-empty
  analysis results each ok+accepted, a single authoritative analysis behavior
  class, and verdict/analysis behavior agreement). Adverse-but-valid behaviors
  still count as accepted; contradictions fail closed.
- The artifact schema includes `gps_injection.json` with required fields
  matching the produced injection artifact; the required-artifact set and its
  schema are reported together by `--preflight`. All output is strict JSON.
- The readiness report (`--preflight`) is a deterministic no-SITL snapshot of
  what a suite run would schedule. It reuses a caller-supplied plugin (including
  the shared registry factory) or builds a default one, and it reports
  `ready_for_live_run=false` plus the three live-adapter blockers so
  "readiness" never reads as "ready to fly".

## Still Open

The following are deliberately not implemented in Phase 1 no-SITL chunks:

- Actual live MAVLink connection creation, real parameter write/readback against
  SITL, live SITL/Gazebo launch, mission upload/control, and live monitor
  behavior.
- Runtime scheduling of multi-event payload updates after trigger. Chunk 5
  builds the individual plan/restore contracts only.
- EKF mechanism-gate extraction from BIN/log data; Chunk 4 covers only synthetic no-SITL records.
- Full Phase 1 acceptance and any Phase 2/3/4 evidence claim.

## Live Gates (Future Phase 2)

- Read back every injected `SIM_GPS1_*` param.
- Read live `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`, `FS_EKF_THRESH`, `EK3_GPS_CHECK`.
- Confirm the realized straight-leg duration and bracket the empirical knee.
