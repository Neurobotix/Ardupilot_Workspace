# GPS Failure Behavior — Implementation

Status: Phase 1 no-SITL foundation (Chunks 1–6) is **Accepted** (2026-07-13,
final no-SITL review): the lane is wired into the shared suite path with a
no-SITL integration-readiness report, and all prior findings are resolved and
verified in code. Pre-smoke Phase 2 implementation is present for later
authorized live smoke, but Phase 2 live smoke remains unverified (no live
SITL/Gazebo run, real parameter readback, real BIN parse, or evidence claim).

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

## Dedicated Launch Identities (2026-07-13, structural only)

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/launch/launch.sh` | Adds `PLANE_GPS_PARAM_FILE`, `build_plane_gps_param_args()` (base + `plane_gps.parm` only; local override excluded and printed), `launch_plane_gps()` (`--wipe-eeprom`, `var/runs/sitl/plane-gps`, `udp:127.0.0.1:14551`), `launch_gazebo_plane_gps()` (reuses base `mini_talon_runway.sdf` by reference), help entries, quick-start block, and `plane-gps` / `gazebo-plane-gps` dispatch cases. Existing targets and the shared `build_plane_param_args()` are unchanged. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/defaults.py` | `SITL_TARGET="plane-gps"`, `GAZEBO_TARGET="gazebo-plane-gps"`; `parameter_schema()` reports both targets. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/readiness.py` | `--preflight` parameter-stack section reports the dedicated targets and the airspeed-overlay / local-override exclusions. |
| `tests/unit/test_gps_launch_targets.py` | No-SITL structural tests: help discovery, dispatch routing, GPS builder/function body isolation (no airspeed overlay, no local override, wipe-eeprom, single UDP out), base-world Gazebo reuse (no CTE wind path), CTE-lane regression, and plugin/readiness target reporting. |

These identities replace the earlier incorrect `plane-cte` / `gazebo-plane-cte`
references. They are structurally implemented and tested no-SITL only; no live
run, parameter readback, or evidence claim exists. See ADR-0021's 2026-07-13
amendment and `design_adrs.md`.

## Implemented In Pre-Smoke Phase 2 (2026-07-13, no live run)

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/source_contract.py` | Source-backed live/BIN preconditions: `EKF_STATUS_REPORT.pos_horiz_variance ** 2` for live `posTestRatio`, `XKF4.SP/100` squared for BIN, `EK3_GLITCH_RAD > 0`, GPS source readbacks, EKF absolute-position status flags, and explicit "validated proxy" wording for absolute aiding. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/telemetry.py` | Testable telemetry rate requests for `HEARTBEAT`, `MISSION_CURRENT`, `STATUSTEXT`, `GLOBAL_POSITION_INT`, `ATTITUDE`, `SIMSTATE`, `EKF_STATUS_REPORT`, and `GPS_RAW_INT`; each `MAV_CMD_SET_MESSAGE_INTERVAL` request requires a matching accepted `COMMAND_ACK`, and malformed EKF samples normalize to fail-closed records instead of raising. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/bin_analysis.py` | Current-attempt BIN decode/analysis boundary: lazy `pymavlink.DFReader` decode for live use, fake decoder injection for tests, `XKF4` primary-core mechanism extraction (`PI` selects the primary core and must be present on every analyzed row), reset detection from `OFN/OFE`, and `SIM` truth versus `POS` canonical-belief pairing on `TimeUS` with <=0.1 s skew. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/mavlink.py` | Explicit `connect_mavlink()` factory hook (no import-time connection), live contract readback list, and no-SITL tests preserving atomic batch validation. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/environment.py` | Later-live launch plan uses only `plane-gps` / `gazebo-plane-gps`, routes attempt runtime under `var/`, records process/log handles through injectable launchers for no-SITL tests, snapshots pre-launch BIN names, installs a production mission adapter from the live MAVLink master, accepts only one new `.BIN` for attempt analysis, and waits/terminates/kills/clears process handles during cleanup. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/control.py` | Mission control now has a production `MavlinkGpsMissionAdapter` for upload/verify/arm/AUTO, with fake adapter support retained for tests; no live upload was executed during this task. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/monitor.py` | Later-live monitor requests the GPS telemetry set with ACK-gated rate changes, records monotonic arrivals, reads the GPS/EKF source-contract parameters, validates the canonical seq-1->2->3->4 armed/AUTO trigger, executes only authorized injection plans, schedules bounded restores/ramped slow-drift updates, observes at least 90 s post-injection, emits the required observation artifacts plus `source_contract.json`, gates mechanism evidence on the source contract, and overlays the selected current-attempt BIN analysis when exactly one new BIN exists. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Adds `--phase2-smoke-plan` as a plan-only no-live action and a guarded runnable Phase 2 path for the protected smoke slice only: `--live-phase2-smoke --confirm-live-phase2` or `--live-case <protected-case> --confirm-live-phase2`. The full Phase 3 matrix is not enabled through this live CLI. |
| `tests/unit/test_gps_failure_phase2_path.py` | No-SITL/fake coverage for the source contract, source-contract-gated monitor acceptance, telemetry ACK/malformed-sample handling, decoded/current-attempt BIN helpers, launch plan, production mission adapter installation, cleanup wait/kill behavior, monitor scheduling/artifact emission, guarded live CLI parsing, and connection factory. |

No SITL, Gazebo, MAVProxy, real MAVLink connection, mission upload, parameter
write, BIN/tlog generation, live BIN decode, or evidence promotion was performed
for this implementation.

## Pre-Smoke Strict-Review Remediation (2026-07-13, no live run)

The first strict review of the Phase 2 path rejected live-smoke authorization.
The implementation was then hardened without starting SITL, Gazebo, or MAVLink:

- `environment.py` starts `plane-gps` first and waits for its governed
  `Cleanup complete` barrier before starting `gazebo-plane-gps`, so the Plane
  target cannot kill its own Gazebo process. Cleanup verifies process exit after
  terminate/kill, closes the MAVLink master and log handles, records a cleanup
  result in `gps_cleanup.json` and the terminal manifest, and raises on any
  surviving process or close failure.
- `AttemptRunner` performs cleanup before persisting terminal success. The GPS
  runner prewrites `running`, so a cleanup exception produces a terminal error
  row rather than leaving success or no manifest record.
- Trigger authorization requires bounded heartbeat and SIMSTATE ages on every
  ordered seq-1→2→3→4 event. Untimestamped/stale evidence fails closed, and the
  monitor latches the first injection attempt whether it succeeds or fails.
- Initial injection, every slow-drift update, and every restore readback are
  acceptance-gating. Any failed operation stops monitoring; expected update and
  restore counts must be complete before observation acceptance.
- Live behavior artifacts use only post-trigger samples. They calculate real
  mode/failsafe/disarm changes, roll/pitch crossings, ordered altitude
  drawdown, reset events, and substantive truth-vs-belief coverage. Missing
  behavior samples fail closed instead of becoming nominal.
- BIN analysis requires a seq-4 or matching parameter-transition injection
  anchor, discards pre-trigger rows, and segments truth-vs-belief samples at
  `XKF4.OFN/OFE` reset events so gap growth never spans a reset.
- The live CLI inspects the returned terminal record, exits nonzero on anything
  other than an explicitly accepted success, and stops the protected sequence
  immediately.
- GPS JSON writes use `allow_nan=False`, fsync, and atomic replace; telemetry
  normalizes non-finite fields to `None`. The source contract checks all five
  pinned source enums and the exact checked-in knee values. A real connection
  factory must receive a heartbeat; an explicit heartbeat timeout is fatal.

This is implementation remediation only; it does not accept Phase 2. A fresh
strict no-live review on 2026-07-14 found no remaining BLOCKER or HIGH finding
and accepted the exact corrected diff for the single nominal live smoke. That
review acceptance is not a live result or a full-campaign authorization.

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

The following remain open until an explicitly authorized live smoke:

- Real execution of the launch, mission upload/control, monitor loop, parameter
  writes/readbacks, restore timing, and BIN decoding against a live run.
- Live verification of `plane-gps` / `gazebo-plane-gps` and the realized
  `plane_base.parm -> plane_gps.parm` stack.
- Any empirical-knee, behavior, parity, or Phase 2 acceptance claim.

## Live Gates (Future Phase 2)

- Read back every injected `SIM_GPS1_*` param.
- Read live `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`, `FS_EKF_THRESH`,
  `EK3_GPS_CHECK`, and `EK3_SRC1_*`; require `EK3_GLITCH_RAD > 0`, integer GPS
  source enums, and EKF absolute-position status flags as the validated
  GPS-aiding proxy.
- Confirm the realized straight-leg duration and bracket the empirical knee.
