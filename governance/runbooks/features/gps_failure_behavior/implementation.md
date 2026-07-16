# GPS Failure Behavior — Implementation

Status: Phase 1 no-SITL foundation (Chunks 1–6) is **Accepted** (2026-07-13,
final no-SITL review). On 2026-07-14 the corrected protected nominal path also
completed one governed raw validation through seq 9 and stabilized planned RTL,
with accepted source/BIN/behavior analysis and clean cleanup. That raw run is
not curated Phase-2 evidence, and no fault case has run.
On 2026-07-15, a no-live campaign-readiness update added the protected
round-robin campaign command, workflow-complete counting, and pre-injection
source-contract staging. No new live result is claimed.

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
| `assets/missions/gps_failure_behavior_mission.waypoints` | QGC WPL 110 GPS mission with the airspeed-style lifecycle but GPS-owned calm-lane geometry: seq-4 injection edge, explicit 15 m/s command, 500 m settle, 2000 m Eastbound measurement leg, reciprocal return leg 500 m North, and RTL at seq 9. |
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
| `src/sim_ard_gaw/launch/launch.sh` | Adds `PLANE_GPS_PARAM_FILE`, `build_plane_gps_param_args()` (base + `plane_gps.parm` only; local override excluded and printed), `launch_plane_gps()` (`--wipe-eeprom`, `var/runs/sitl/plane-gps`, `udp:127.0.0.1:14551`), and `launch_gazebo_plane_gps()` using the dedicated east-facing `mini_talon_gps_runway.sdf`. Existing targets and the shared `build_plane_param_args()` are unchanged. |
| `assets/worlds/mini_talon_gps_runway.sdf` | Dedicated calm/NavSat GPS world using the sensor-neutral Mini Talon with the east-facing behavior-mission pose; avoids changing the shared base world. |
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
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/source_contract.py` | Source-backed live/BIN preconditions: `EKF_STATUS_REPORT.pos_horiz_variance ** 2` for live `posTestRatio`, already-scaled decoded `XKF4.SP ** 2` for BIN, `EK3_GLITCH_RAD > 0`, GPS source readbacks, EKF absolute-position status flags, and explicit "validated proxy" wording for absolute aiding. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/telemetry.py` | Uses the GPS-owned `MAV_DATA_STREAM` request helper. It does not require `COMMAND_ACK` for event-driven `STATUSTEXT`; the monitor instead fails closed unless every required periodic message type is actually observed. Malformed EKF samples normalize to fail-closed records instead of raising. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/bin_analysis.py` | Current-attempt BIN decode/analysis boundary: lazy `pymavlink.DFReader` decode after cleanup closes the log, fake decoder injection for tests, `XKF4` primary-core mechanism extraction (`PI` selects the primary core and must be present on every analyzed row), reset detection from `OFN/OFE`, and decoded-degree `SIM` truth versus `POS` canonical-belief pairing on `TimeUS` with <=0.1 s skew. Mission-upload `CMD` rows are never treated as execution anchors; the live seq-4 boot timestamp is primary and an injection-parameter transition is the only decoded-log fallback. The post-cleanup analyzer archives the selected BIN into the attempt directory before decoding it, then records the copied artifact as `raw_log` / `raw_log_path`. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/mavlink.py` | Explicit `connect_mavlink()` factory hook (no import-time connection), live contract readback list, and no-SITL tests preserving atomic batch validation. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/environment.py` | Later-live launch plan uses only `plane-gps` / `gazebo-plane-gps`, routes attempt runtime under `var/`, records a required `run_config.json` with mission/world/parameter/plugin/source-tree provenance, snapshots pre-launch BIN names, installs a production mission adapter from the live MAVLink master, accepts only one new `.BIN` for attempt analysis, and performs direct-handle cleanup followed by GPS-owned workspace-scoped process cleanup, canonical launcher cleanup, and a final survivor scan. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/control.py` | Mission control now has a production `MavlinkGpsMissionAdapter` for upload/verify/arm/AUTO, with fake adapter support retained for tests; no live upload was executed during this task. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/monitor.py` | Later-live monitor requests GPS-owned Plane data streams without an ACK gate, latches a fresh immutable seq-4 boot-time event, tracks `MISSION_ITEM_REACHED`, maximum sequence and AUTO-to-RTL progress, executes only authorized injection plans, schedules bounded restores/ramped slow-drift updates, treats 20 s nominal / 90 s fault as minimum evidence rather than termination, and normally continues through planned RTL plus 10 s stabilization. It emits terminal mission progress with the live artifacts and leaves stable BIN replacement to the post-cleanup analyzer. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Adds `--phase2-smoke-plan` as a plan-only no-live action and a guarded runnable Phase 2 path for the protected smoke slice only: `--live-phase2-smoke --confirm-live-phase2` or `--live-case <protected-case> --confirm-live-phase2`. The full Phase 3 matrix is not enabled through this live CLI. |
| `tests/unit/test_gps_failure_phase2_path.py` | No-SITL/fake coverage for the source contract, source-contract-gated monitor acceptance, GPS-owned stream setup, event-driven `STATUSTEXT` handling, actual-message delivery gating, malformed samples, decoded/current-attempt BIN helpers, attempt-local BIN archival, launch plan, GPS-owned production mission protocol, workspace-scoped/canonical cleanup, Python-named MAVProxy matching, sibling-plugin isolation, monitor scheduling/artifact emission, guarded live CLI parsing, and connection factory. |

No SITL, Gazebo, MAVProxy, real MAVLink connection, mission upload, parameter
write, BIN/tlog generation, live BIN decode, or evidence promotion was performed
for this implementation.

## Campaign-Readiness Update (2026-07-15, no live run)

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Adds `--live-phase2-round-robin-campaign` guarded by both `--confirm-live-phase2` and `--confirm-live-campaign`. The command writes `campaign_contract.json`, runs the protected case set in true round-robin order, defaults to five workflow-complete physical attempts per case, uses zero automatic retries, and stops on workflow/cleanup/raw-log failure. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/manifest.py` | Adds workflow-complete counting separate from strict accepted-observation counting. A workflow-complete attempt can have failed analysis and still remain a preserved physical run; it does not become an accepted scientific observation. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/monitor.py` | Source-contract artifact now validates the pre-injection EKF aiding flags and records post-injection flags separately, so expected post-fault GPS rejection is behavior rather than failed setup. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/analyzers.py` | Final post-cleanup summary marks `workflow_status=complete` only after cleanup is clean and the attempt-local raw BIN exists. The analyzer can still reject behavior without erasing the workflow-complete physical attempt. |
| `tests/unit/test_gps_failure_phase1.py` and `tests/unit/test_gps_failure_phase2_path.py` | No-live regression coverage for workflow-vs-accepted-observation separation, campaign CLI confirmation guards, protected round-robin parsing, and pre-injection source-contract staging. |

This update prepares the first protected repeated campaign command. It does not
authorize or claim execution of that campaign.

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
  ordered seq-1→3→4 navigation event, permitting an optional seq-2 DO-command
  report. Untimestamped/stale evidence fails closed, and the
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

## Post-Rejection Smoke Remediation (2026-07-14, no live rerun)

The rejected nominal attempt exposed three runtime gaps. The working tree fixes
them without starting SITL, Gazebo, MAVProxy, or a MAVLink connection:

- `GpsFailureEnvironment.assert_ready()` now uses separate heartbeat and
  vehicle-ready timeouts. After the first heartbeat it applies the existing
  proven Plane readiness gate: AUTO must be available, the mode must no longer
  be `INITIALISING`, GPS and EKF must be ready, and two consecutive ready
  heartbeats must be observed. The mission adapter is installed only after this
  gate passes, so mission upload cannot begin from the first heartbeat alone.
- `GpsFailureEnvironment.cleanup()` still terminates direct process groups and
  closes MAVLink, then invokes the canonical governed
  `scripts/ops/launch.sh cleanup` command for launcher descendants, records its
  exit/stdout/stderr result, and independently scans for survivors. Any command
  failure, timeout, scan failure, survivor, close failure, or artifact failure
  keeps cleanup failed closed.
- `AttemptRunner` now performs cleanup inside the exception path before
  constructing and appending the terminal error row. Cleanup artifacts and the
  structured cleanup result are refreshed into that row; if cleanup also
  raises, the cleanup exception is recorded while the original stage exception
  remains the exception re-raised and the primary verdict metadata. Successful
  attempts retain cleanup-before-success persistence.
- `GpsFailureManifest` explicitly persists framework terminal `status`; the
  generic terminal payload also carries the structured monitor result. This is
  additive for GPS and does not overwrite the wind-matrix legacy status
  vocabulary.

Fake/injected unit boundaries cover readiness success and failure, exact
governed-cleanup invocation, cleanup ordering and fail-closed behavior,
cleanup-proof persistence on stage failure, primary-error preservation on a
secondary cleanup failure, and explicit GPS terminal status. The focused
GPS/core/adjacent-airspeed set passed 324 tests (258 subtests), and focused
Pyright reported zero errors/warnings. This is no-live implementation proof
only. It does not rehabilitate the rejected attempt or authorize a new live
attempt.

## Second Rejected-Smoke Remediation (2026-07-14, no live rerun)

The second nominal attempt proved the first remediation's readiness, mission,
and terminal-record paths, then exposed two independent regressions introduced
by the GPS live adapter:

- The GPS monitor had replaced airspeed's proven `MAV_DATA_STREAM` setup with
  per-message `MAV_CMD_SET_MESSAGE_INTERVAL` commands and mandatory ACKs. The
  vehicle denied the `STATUSTEXT` interval command; `STATUSTEXT` is event-driven,
  so that denial incorrectly aborted the monitor before source readback,
  trigger, or observation. GPS now owns the data-stream request path. Setup is
  best-effort, and monitor acceptance fails closed on actual receipt of every
  required periodic message type. `STATUSTEXT` remains observed when emitted
  but is not a required periodic-delivery signal.
- Canonical cleanup used `pkill -x mavproxy`, while the real process name was
  `mavproxy.py`. GPS governed cleanup now first runs its own workspace-scoped
  process cleanup, then canonical cleanup and the independent survivor scan as
  before. Canonical `launch.sh cleanup` also matches `[m]avproxy.py` explicitly.
- GPS owns its stream, readiness, mission-protocol, and cleanup helpers. It has
  no dependency on `airspeed_failure` or another sibling plugin; a structural
  test enforces this boundary.

Focused fake tests reproduce both failure shapes and verify fail-closed actual
telemetry delivery. The GPS/core/adjacent-airspeed regression set passed 334
tests (262 subtests); focused Pyright reported zero errors/warnings; no-live CLI
guards/planning, shell syntax, `git diff --check`, and `make doctor` passed. No
SITL, Gazebo, mission, MAVLink, parameter write, or live retry was started by
this remediation. The second attempt remains rejected and Phase 2 remains open.

## Full-Flight Lifecycle Remediation And Raw Validation (2026-07-14)

The rejected nominal root
`var/runs/gps_failure_behavior_20260714T113259746238Z/` exposed four additional
GPS-only regressions relative to the proven airspeed behavior lifecycle:

- `gazebo-plane-gps` reused a base world that realized an approximately north
  heading while the copied mission begins east. The target now owns
  `mini_talon_gps_runway.sdf`, retaining the sensor-neutral model while applying
  the proven east-facing pose. `run_config.json` hashes the world.
- The monitor stopped at the minimum post-injection duration. That duration is
  now only an acceptance threshold; the monitor tracks reached waypoints and
  AUTO-to-RTL progress and waits for planned RTL plus 10 s stabilization.
- The analyzer searched repeated seq-4 telemetry backwards and selected the
  last report. It now consumes the immutable first validated trigger event from
  the authorized injection plan, with first-trace fallback only.
- Nominal classification and manifest counting now require a valid terminal
  state and planned mission completion. Terminal fields are persisted in the
  summary and manifest; an incomplete nominal cannot declare success.

GPS telemetry now decodes ArduPlane mode 11 as `RTL` and includes
`MISSION_ITEM_REACHED` / `NAV_CONTROLLER_OUTPUT`. No GPS module imports the
airspeed plugin. Focused tests cover the dedicated world, minimum-window
non-termination, RTL stabilization, unique reached waypoints, immutable trigger
anchoring, and fail-closed nominal/manifest behavior.

The first post-fix launch timed out at readiness before flight. A read-only
MAVLink probe then confirmed the dedicated world supplied a healthy GPS fix and
complete EKF flags. Readiness now reissues idempotent Plane stream requests
every five seconds during wiped-EEPROM initialization and reports the observed
mode, GPS fix/satellite state, EKF flags, ready-heartbeat count, and per-message
counts on timeout.

The fresh governed nominal root
`var/runs/gps_failure_behavior_20260714T120212630044Z/` then completed with a
terminal success row and `accepted_observation=true`. It latched the first seq-4
edge at boot time `56.487 s`, continued for `208.43 s` of monitoring, reached
mission seq 9, observed distinct reached rows 2–8, transitioned AUTO-to-RTL at
seq 8, and stopped only after the 10 s RTL stabilization window. The initial
BIN attitude yaw was approximately `89.27 deg`; BIN analysis used
`window_start_time_us=56487000`, matching the immutable trigger, and produced
4,038 truth/belief pairs. World and mission hashes match the indexed assets;
cleanup was clean. This is reviewed raw validation only: no evidence promotion,
fault case, empirical-knee result, Phase-2 acceptance, commit, or push followed.

Post-run path review found the v2 takeoff completed around 323 m East, beyond
the copied 300 m settle waypoint, and caused the aircraft to turn back before
seq 4. Mission v3 moves the paired settle endpoints to 500 m and the far
endpoints to 1300 m, preserving both 800 m measurement legs, all sequence
numbers, and the trigger contract. Structural tests now require a 450–550 m
home-to-settle distance and both 750–850 m measurement legs. This asset change
was then validated by the fresh governed nominal root
`var/runs/gps_failure_behavior_20260714T122459635208Z/`, which records the v3
hash, completes through seq 9 and planned RTL, and removes the loop. Between
takeoff completion and seq 3, East displacement is monotonic, waypoint distance
falls from about 180 m to less than 1 m, north span is 3.7 m, and maximum
absolute roll is 2.1 degrees. The earlier raw nominal remains tied to v2.

Mission v4 subsequently enlarges the fault-test envelope while preserving the
validated settle and lifecycle contracts: seq 4/5/6 are 2500 m East, seq 5–8
are 500 m North, and both measurement legs are 2000 m. Structural tests check
the 500 m settle, 2000 m legs, and 500 m lane spacing. Active mission SHA-256 is
`8d1c8de43c6e496946b1f6bdf3d88f4aa14cd3ba7abe84067cb6a4edd27d7f35`.
No v4 live result is claimed.

## Current No-SITL Semantics

- Case generation covers `nominal`, the ADR-0019 drift-rate ladder, the
  continuous slow-drift accumulation instrument, step-glitch magnitude ladder,
  denial-duration ladder, and five jamming repeat cases.
- The trigger helpers model amended ADR-0020 at schema level: navigation seqs 1
  and 3 must be observed before the first seq 4; seq 2 is optional because it
  is a DO command. The monitor ignores leading home-row seq 0 before evidence
  begins but retains a later seq-0 regression. The structured helper additionally requires
  those front-half events and the seq-4 event to be armed and in `AUTO`.
- The generated acceptance requirements use a 20 s minimum for nominal and a
  90 s minimum for fault cases. Neither minimum terminates the flight.
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
  `monitor.first_seq4_edge_after_armed_auto_front_half` helper (required
  seq 1→3→4, optional seq 2,
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
