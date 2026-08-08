# GPS Failure Behavior — Review

Status: Phase 1 no-SITL foundation is **Accepted** (2026-07-13, final no-SITL
review). A corrected protected nominal completed reviewed raw validation on
2026-07-14; Phase 2 remains open because no curated evidence was promoted and
no fault case has run.

## Phase Acceptance Ledger

| Phase | Status | Date | Notes |
| --- | --- | --- | --- |
| Phase 0 — design lock | Accepted | 2026-07-06 | Full brainstorm; four faults, two-tier knee, seven bands, characterize-not-gate; five Proposed ADRs (0017–0021). |
| Phase 1 — no-SITL plugin foundation | Accepted | 2026-07-13 | Chunks 1–6: scaffold, payload semantics, static mission/parameter-stack integration, synthetic mechanism-gate evaluation, runtime/MAVLink contract helpers, and integration-readiness wiring. All prior BLOCKER/HIGH/MEDIUM findings resolved and verified in code; a final no-SITL review (2026-07-13) found no new BLOCKER/HIGH/MEDIUM/substantiated-LOW issue. No-SITL acceptance of the plugin foundation only — no live result. Live connection, mission execution, and BIN/log extraction remain Phase 2. |
| Phase 2 — live smoke | Open (protected nominal raw validation passed) | 2026-07-14 | Root `var/runs/gps_failure_behavior_20260714T120212630044Z/` completed seq 9, planned RTL stabilization, accepted source/BIN/behavior analysis, and clean cleanup. Raw output only: no evidence promotion, fault smoke, or Phase-2 acceptance. |
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

## Phase 1 Chunk 4 Review Note

Phase 1 Chunk 4 is implemented pending review. It adds the synthetic no-SITL
mechanism-gate evaluator for EKF-like records, with the ADR-0018 knee locked at
`posTestRatio >= 1.0`, reset evidence preserved as a distinct mechanism state,
and fail-closed handling for empty, missing, malformed, non-finite, or
out-of-order mechanism data. It does not parse BIN logs, start SITL/Gazebo, use
live MAVLink, or establish an evidence claim.

## Phase 1 Chunk 5 Review Note

Phase 1 Chunk 5 is implemented pending review. It adds no-SITL-testable
runtime/MAVLink contract helpers: deterministic parameter set/read/readback
comparison with fake connections, trigger-metadata-based GPS injection plans,
GLTCH degree payload resolution from trigger-time latitude, bounded restore
plans for denial/jamming, readback rules for every injected parameter, and
fail-closed plan/execution results when metadata or a connection is missing. It
does not start SITL/Gazebo, open a live MAVLink connection, execute a mission,
capture telemetry, parse BIN/logs, or establish an evidence claim.

## Phase 1 Chunk 6 Review Note

Phase 1 Chunk 6 is implemented pending review. It adds `readiness.py` and a
`--preflight` CLI action that produce a deterministic no-SITL integration-
readiness report: the plugin builds through the shared registry factory, the
full 23-case catalog is scheduled, and the SuiteRunner seams (attempt runner,
attempt-dir factory, case generator, manifest) are all present. The report
surfaces the manifest and artifact contracts and the effective two-file
parameter stack, and it reports `ready_for_live_run=false` alongside the three
live-adapter blockers (environment/control/monitor) plus the MAVLink and
BIN/log blockers. It starts no SITL/Gazebo, opens no MAVLink connection, writes
no manifest, parses no BIN/logs, and makes no evidence claim.

## Phase 1 Strict-Review Blocker Resolution (2026-07-13)

A strict Phase 1 review of Chunks 4–6 raised six confirmed BLOCKERs. All six are
now resolved in the working tree with regression tests. No live SITL/Gazebo run,
real MAVLink connection, live parameter readback, BIN/log parsing, or evidence
claim was performed for this work; every fix is no-SITL.

- **B1 — Chunks 4–6 uncommitted.** The GPS Phase 1 working-tree scope (plugin
  modules, CLI, tests, docs, `.ai/index.md`) is being committed in one scoped
  local commit after the fixes below and all required checks passed.
- **B2 — runtime plans bypassed ADR-0020 trigger validation.**
  `runtime.py` now separates preview-only payload resolution
  (`build_live_injection_plan`, never execution-authorized) from
  execution authorization. `build_authorized_injection_plan` requires a
  structured monitor trace validated through the canonical
  `monitor.first_seq4_edge_after_armed_auto_front_half` helper (no second
  trigger definition), producing deterministic, JSON-safe `TriggerEvidence`.
  `execute_injection_plan` refuses any non-nominal, parameter-writing plan that
  lacks validated trigger authorization *before* any connection call; nominal
  no-write plans remain non-mutating without a trigger.
- **B3 — analyzer accepted marker booleans as evidence.** `analyzers.py` now
  classifies from substantive, finite behavior-tier metrics (truth-vs-belief
  gap, gap growth, attitude band, mechanism state), not a caller-supplied
  `behavior_evidence=True` marker. Nominal requires explicit nominal evidence;
  each non-nominal class requires its own evidence; missing, contradictory,
  malformed, non-finite, or unsupported behavior evidence returns
  `analysis_incomplete` / `accepted_observation=false` with a specific reason.
- **B4 — manifest accepted contradictory verdict/analysis.**
  `manifest.accepted_observation_from_attempt` now requires all
  acceptance-bearing signals to agree: valid terminal success, a success verdict
  with explicit `accepted_observation=true` metadata, non-empty analysis results
  each ok+accepted, a single authoritative analysis behavior class, and
  agreement between the verdict behavior and that class. `verdict.reason =
  loss_of_control` with `analysis behavior = detected_rejected` is now rejected.
  Adverse-but-valid behaviors still count as accepted.
- **B5 — `gps_injection.json` missing from the artifact schema.**
  `analyzers.artifact_schema()` now includes `gps_injection.json` with required
  fields matching `stimulus.build_injection_artifact()`
  (`case_id`, `fault_type`, `requested_payload`, `injection_schedule`,
  `fault_recipe`, `payload_resolution`, `reset_payload`, `trigger`,
  `readback_rules`, `readback_status_shape`, `live_plan_contract`). Readiness
  reports schema coverage of the full required-artifact set; output stays strict
  JSON. Phase 1 preview fields remain honest (no live-readback claim).
- **B6 — MAVLink batch mutated before full validation.** `mavlink.py` adds an
  atomic `preflight_batch` stage that validates payload type, parameter names,
  values, readback-rule structure, expected values, tolerances, and
  payload/rule key correspondence before the first write. `SIM_GPS1_JAM=inf`
  sorted after a valid `SIM_GPS1_ENABLE=0` now performs zero writes/reads.
  Sorted deterministic write order and post-validation transport fail-closed
  behavior are preserved.

Checks actually run for this work (all exit 0):

- `pytest tests/unit/test_gps_failure_phase1.py tests/unit/test_gps_mechanism_gate.py
  tests/unit/test_gps_failure_mavlink.py tests/unit/test_gps_failure_readiness.py`
  → 123 passed.
- Airspeed regression `pytest tests/unit/test_airspeed_failure_phase1.py
  tests/unit/test_airspeed_mechanism_gate.py` → passed (164 total with the GPS
  suite).
- `pyright` over the GPS plugin, CLI, and four test files → 0 errors, 0 warnings.
- `run_gps_failure --list-cases | --probe-schema | --preflight |
  --dry-run --case nominal` → all exit 0.
- `git diff --check` and `make doctor` → pass.

Acceptance state: **the six strict-review blockers are resolved; Phase 1
acceptance is still pending the remaining review findings** (the Chunks 4–6
review's HIGH/MEDIUM/LOW items and the code-review sign-off item below). This
note does not itself close Phase 1.

## Phase 1 Strict-Review Second Pass (2026-07-13)

A second adversarial review pass found four more BLOCKERs and one HIGH left open
by the first pass. All are now resolved no-SITL with regression tests; probes
that previously executed a write or forged acceptance now fail closed.

- **Trigger evidence accepted duplicate/regressive mission-current traces.**
  `monitor.first_seq4_edge_after_armed_auto_front_half` now requires a clean,
  ordered seq 1->2->3->4 progression: it rejects any regression to a lower seq
  and any skipped front-half seq, while still allowing benign repeated
  `MISSION_CURRENT` events for the current seq. `1,2,3,2,4` and skip traces now
  fail closed.
- **Public plan construction could forge authorization.** Execution no longer
  trusts a plain `TriggerEvidence.validated` flag. `validate_trigger_trace` mints
  an internal authorization token (not exported) and stores the source trace;
  `TriggerEvidence.is_authorized()` re-checks the token by identity *and* replays
  the stored trace through the canonical validator, so a directly-constructed
  plan with `validated=True` cannot authorize a write.
- **Analyzer accepted forged mechanism markers and raised on malformed input.**
  Mechanism-accepted markers must now be a strict boolean `True` (the string
  `"true"` or `1` no longer become accepted), and the observation-window/metric
  coercion fails closed with a deterministic reason instead of raising on
  non-numeric input (`post_injection_s="bad"` -> `analysis_incomplete`).
- **Manifest accepted malformed top-level acceptance and unknown quality.** A
  top-level `accepted_observation`, when present, must be a strict boolean `True`
  (`"true"`/`1` fail closed), and an observation-quality class, when present,
  must be one of the known-good accepted classes (an `unknown_quality` fails
  closed) rather than merely not a known-bad string.
- **MAVLink rule validation leaked `KeyError`/`TypeError` (HIGH).**
  `normalize_readback_rules` now raises `ValueError` for a rule missing
  `expected`/`tolerance` or for a non-mapping rule object, keeping the public
  fail-closed batch contract consistent; atomicity (zero writes on failure) is
  preserved.

Checks re-run for this pass (all exit 0): GPS unit suite (130 passed), airspeed
regression (41 passed), `pyright` 0 errors over the GPS plugin/CLI/four test
files, `run_gps_failure` all four no-SITL actions, `git diff --check`, and
`make doctor`. No live SITL/Gazebo run, real MAVLink connection, live readback,
BIN/log parsing, or evidence claim was performed. Phase 1 acceptance remains
pending any further review findings.

## Phase 1 Strict-Review Third Pass (2026-07-13)

A third review pass found one more BLOCKER left open by the earlier passes; it is
now resolved no-SITL with regression tests.

- **A failed mechanism result could be overridden by a stale
  `mechanism_evidence=True` marker.** `analyzers._with_mechanism_result` used
  `setdefault`, so when a caller supplied both `mechanism_evidence=True` and a
  failed/unverified `mechanism_result`, the failed result did not override the
  stale marker and the observation could classify as accepted `nominal`. A
  supplied mechanism result is now authoritative: it *overwrites*
  `mechanism_evidence` (a failed result forces `mechanism_evidence=False` →
  `missing_mechanism_fields`), and the derived mechanism-tier flags
  (`reset_event`, `pos_test_ratio_rejected`, `fused`) are cleared and re-set only
  from the accepted result, so a caller cannot pre-seed them to mask a rejection.

Checks re-run (all exit 0): GPS unit suite 132 passed, airspeed regression 41
passed, `pyright` 0 errors, `run_gps_failure` all four no-SITL actions,
`git diff --check`, and `make doctor`. No live SITL/Gazebo run, real MAVLink
connection, live readback, BIN/log parsing, or evidence claim was performed.
Phase 1 acceptance remains pending any further review findings.

## Phase 1 Strict-Review HIGH-Finding Resolution (2026-07-13)

The three original HIGH findings from the strict Chunks 4–6 review are now
closed. Two were verified already-resolved on the current branch (no code change
manufactured); one required a code fix with regression tests. All work is
no-SITL: no live SITL/Gazebo run, real MAVLink connection, live parameter
readback, BIN/log parsing, or evidence claim was performed.

- **H1 — malformed runtime recipes could escape as uncaught exceptions
  (fixed).** `runtime._resolve_step_glitch_payload` indexed
  `recipe["offset_magnitude_m"]` directly, so a `step_glitch` recipe missing that
  field raised `KeyError`; `_build_plan` caught only `ValueError`, so the
  exception escaped instead of returning a structured not-ready plan. Added
  `_required_recipe_float` (the recipe equivalent of `_required_event_float`,
  raising `ValueError` on a missing or non-finite field) and used it for
  `offset_magnitude_m`. The `trigger_event` normalization also moved
  into the fail-closed path via `_as_event_mapping`, which raises `ValueError`
  for a non-mapping trigger_event instead of crashing on a bare `dict()`
  `TypeError`. The case `trigger` *metadata* is validated more strictly by
  `_resolve_case_trigger`: every generated fault case carries the populated
  ADR-0020 trigger, so a missing / `None` / empty / non-mapping trigger on any
  parameter-writing (non-nominal) case is malformed public input and fails closed
  with `missing required trigger metadata for fault case` (or
  `trigger must be a mapping`); a nominal no-write case does not require a
  trigger. A malformed public `TestCase`/recipe/trigger now returns
  `ready_to_inject=False` with an empty payload, empty readback rules, no restore
  steps, and deterministic `plan_resolution_failed` detail (no raw `KeyError`
  text); executing such a plan — even with a genuinely valid monitor trace —
  makes zero connection calls. Intentional
  semantics are preserved: slow-drift keeps its documented event-based rate
  fallback, and a missing optional restore duration still means no restore step.
  The whole planner is *not* wrapped in `except Exception`; only expected
  malformed-input errors are converted, so internal programming errors stay
  visible. Regression tests added to `tests/unit/test_gps_failure_mavlink.py`
  (`GpsFailureMalformedRecipeFailClosedTests`): missing `offset_magnitude_m`,
  `None`, non-numeric string, `NaN`/±inf; `fault_recipe` as list/string/number;
  malformed `trigger`/`trigger_event` (including the authorized-builder
  not-validated branch with a malformed `trigger` and an invalid trace);
  missing / `None` / empty trigger metadata on each fault case failing closed for
  both preview and authorized (valid-trace) builders while nominal stays ready;
  preview
  and authorized builders both returning structured failures; failed-plan
  execution making zero connection calls; unchanged valid
  step-glitch/slow-drift/denial/jamming output; unchanged optional-duration
  behavior; and unsupported fault type failing closed.
- **H2 — focused Pyright previously failed in the MAVLink adapter (verified
  resolved).** The exact focused Pyright command was run before any edit and
  reported **0 errors, 0 warnings, 0 informations**. No production type edit,
  `type: ignore`, or configuration change was manufactured. Pyright was rerun
  after the H1 changes and still reports 0 errors, 0 warnings. The dynamically
  discovered fake convenience methods and the protocol-based MAVLink transport
  path retain their runtime behavior; invalid connection values still fail closed
  through `finite_float`.
- **H3 — committed `.ai` and governance status previously lagged the
  implementation (verified and reconciled).** Committed `.ai/current.md`,
  `.ai/index.md`, the feature runbook, `docs/architecture/gps_failure_lane.md`,
  and `docs/operations/gps_failure_runbook.md` were audited against the
  required-truth contract: Chunks 1–6 implemented, six blockers resolved no-SITL,
  no live run / real readback / BIN-log / empirical-knee claim, Phase 2 deferred,
  active GPS work routed to this feature runbook, and no claim that Chunks 4–6 or
  live adapters are present. They already satisfied that contract; the only
  reconciliation needed was recording this HIGH-finding resolution (this note and
  the checklist line below).

Checks actually run for this HIGH-finding work (all exit 0):

- `pytest tests/unit/test_gps_failure_phase1.py tests/unit/test_gps_mechanism_gate.py
  tests/unit/test_gps_failure_mavlink.py tests/unit/test_gps_failure_readiness.py`
  → **150 passed, 178 subtests passed** (132 → 150 with the new H1
  regression tests, including the trigger-metadata follow-up below).
- Airspeed regression `pytest tests/unit/test_airspeed_failure_phase1.py
  tests/unit/test_airspeed_mechanism_gate.py` → **41 passed**.
- Focused `pyright` over the GPS plugin, CLI, and four test files →
  **0 errors, 0 warnings, 0 informations** (a new-pyright-version notice is not a
  code failure).
- `run_gps_failure --list-cases | --probe-schema | --preflight |
  --dry-run --case nominal` → all exit 0.
- `git diff --check` and `make doctor` → pass.

Previously resolved blocker contracts were re-checked and did not regress:
trigger authorization, preview isolation, substantive analyzer evidence,
contradiction-safe manifest accounting, the `gps_injection.json` artifact schema,
and atomic MAVLink batch prevalidation all retain their tests and pass.

### H1 follow-up: missing trigger metadata (found in HIGH-finding re-review)

A re-review of the first H1 commit found the fail-closed contract still open for
one input class: a fault-writing `TestCase` with `parameters["trigger"] = None`
(or missing/empty) was accepted as ready and, with a valid monitor trace,
executed parameter writes (`SIM_GPS1_GLTCH_X/Y/Z`). The first fix normalized the
`trigger` through `_as_event_mapping`, which maps `None -> {}`; that is correct
for a `trigger_event` preview but wrong for the required trigger *metadata* of a
fault case. Fix: `_resolve_case_trigger` now treats a missing / `None` / empty /
non-mapping trigger on any non-nominal case as malformed public input and fails
closed (`missing required trigger metadata for fault case`), while nominal
no-write cases still need no trigger. Verified on the current branch: `trigger`
`None`/missing/empty on `step_glitch`/`slow_drift`/`hard_denial`/`jamming` now
return `ready_to_inject=False`, empty payload/rules, no restore, and zero
connection calls even with a valid trace; no generated case is affected (every
fault case carries the populated ADR-0020 trigger). Regression coverage added to
`GpsFailureMalformedRecipeFailClosedTests`.

Acceptance state: the three original HIGH findings are now closed. Phase 1
acceptance still remains pending the remaining MEDIUM/LOW review findings and the
code-review sign-off item below; this note does not itself close Phase 1.

## Phase 1 Strict-Review MEDIUM-Finding Resolution (2026-07-13)

- **MEDIUM — duplicate failure reporting in the MAVLink batch result
  (fixed).** In `mavlink.read_back_injected_parameters` and
  `mavlink.set_and_read_back_parameters`, a parameter whose read/write errored
  was reported twice in `missing_parameters`: once from the transport
  read/write-failure list and once from `compare_readbacks`, because a failed
  transport leaves the value out of the observed set so the comparison also
  flags it missing. Both paths returned
  `missing_parameters=['SIM_GPS1_JAM', 'SIM_GPS1_JAM']`. Fix: a shared
  `_merge_missing` helper deduplicates the comparison-missing names with the
  transport-error param names into a single deterministic sorted list, so each
  failed parameter appears exactly once in `missing_parameters` while its error
  reason still appears once in `tolerance_failures`. `success` semantics and the
  reported error detail are unchanged; genuinely-missing (non-error) parameters
  are still reported. Regression tests added to
  `GpsFailureBatchPreflightTests` in `tests/unit/test_gps_failure_mavlink.py`
  (failed write reported once; failed read reported once; mixed
  failed/successful parameters deduped and sorted).

Checks re-run for this MEDIUM fix (all exit 0): GPS unit suite 153 passed,
airspeed regression 41 passed, focused `pyright` 0 errors/0 warnings,
`run_gps_failure` all four no-SITL actions, `git diff --check`, and `make
doctor`. No live SITL/Gazebo run, real MAVLink connection, live readback,
BIN/log parsing, or evidence claim was performed.

## Dedicated Launch-Path Correction (2026-07-13, pre-Phase-2)

The GPS design and `defaults.py` previously named `plane-cte` /
`gazebo-plane-cte`. That was a contract mismatch: `plane-cte` is the CTE/airspeed
lane and loads `plane_base.parm -> plane_airspeed.parm ->
.private/config/plane_params.local.parm` — the airspeed overlay ADR-0021 rejects
plus an uncontrolled local override. Corrected before Phase 2 by adding dedicated
identities:

- `plane-gps`: `build_plane_gps_param_args()` loads `plane_base.parm ->
  plane_gps.parm` only, excludes the local override unconditionally (printed),
  wipes EEPROM, uses `var/runs/sitl/plane-gps` and a `plane-gps` MAVProxy
  identity, emits `udp:127.0.0.1:14551`, prints its effective stack, and points
  the operator at `gazebo-plane-gps`.
- `gazebo-plane-gps`: reuses the sensor-neutral base `mini_talon_runway.sdf`
  world by reference (GPS/NavSat, calm, no wind publisher, no airspeed sensor, no
  LiDAR bridge); a dedicated identity, not an alias of `gazebo-plane`. No world
  was duplicated — the base world already satisfies the JSON/GPS contract, so
  duplicating an SDF only to produce a GPS filename was unnecessary.
- Shared `build_plane_param_args()` and all existing targets are unchanged;
  `plane-cte` remains the airspeed/CTE lane.
- Coverage: `tests/unit/test_gps_launch_targets.py` (10 no-SITL structural
  tests). Governance: ADR-0021 2026-07-13 amendment and `design_adrs.md`.

This is structural only. `plane-gps` / `gazebo-plane-gps` have not been
live-smoke verified; the Phase-2 smoke ledger below still gates any live claim,
and Phase-2 must read back the realized stack live.

## Phase 2 Pre-Smoke Rejection And Remediation (2026-07-13)

A fresh strict no-live review rejected the initial pre-smoke Phase 2 path. No
live process was started. The rejection identified launch self-termination,
post-success cleanup, stale trigger evidence/retry, non-substantive behavior
artifacts, non-gating scheduled operations, ignored CLI terminal status,
non-strict JSON, incomplete source-enum validation, and unanchored/reset-spanning
BIN analysis.

The working tree now contains no-live fixes and adversarial regressions for each
finding:

- Plane cleanup completes before Gazebo starts; process/MAVLink cleanup is
  verified, recorded in `gps_cleanup.json` and the terminal manifest, and
  terminal success is persisted only afterward.
- GPS attempts prewrite `running`; cleanup failure cannot leave success and is
  persisted as terminal error.
- Trigger traces require fresh heartbeat and SIMSTATE ages; a failed injection
  is latched and never retried.
- Injection, drift updates, and restore readbacks all gate acceptance and stop
  on first failure.
- Mode, failsafe, disarm, attitude, altitude drawdown, reset, and
  truth-vs-belief metrics are computed from post-trigger samples only; missing
  substantive samples fail closed.
- BIN analysis requires an injection-window anchor and segments position-gap
  samples across EKF resets.
- The protected live CLI requires an accepted success record and stops the
  sequence on the first other terminal outcome.
- Artifact writes are strict finite atomic JSON; live heartbeat timeout is
  fatal; every pinned knee/source readback is checked against the exact overlay
  contract.

Checks run after remediation:

- GPS no-live suite (`phase1`, mechanism gate, MAVLink, readiness, launch
  targets, Phase 2 path): **216 passed, 197 subtests passed**.
- GPS plus shared staged-attempt lifecycle regression: **265 passed,
  205 subtests passed** (the three warnings are two protobuf deprecations and
  pytest's existing `TestCase` collection warning).
- Airspeed adjacent regression: **41 passed, 53 subtests passed** (two protobuf
  deprecation warnings).
- Focused Pyright over every changed Python module/test: **0 errors, 0 warnings**.
- Launcher syntax/help, preflight, plan-only CLI, no-confirm live guard,
  `git diff --check`, and `make doctor`: passed; the live guard exited 2 before
  launch as required.
- Repository-wide Pyright remains a pre-existing repository blocker:
  **7336 errors, 519 warnings**, including ignored/runtime analysis under
  `var/reports/`; no Pyright configuration or unrelated source was changed to
  hide that baseline.

Remediation status: **implemented and no-live tested.** The exact corrected diff
received fresh strict no-live acceptance on 2026-07-14 as recorded below. This
is not Phase 2 acceptance and is not a live result. The smoke ledger remains
empty.

## Phase 2 Corrected-Diff Strict Review Acceptance (2026-07-14)

The exact corrected pre-smoke diff was reviewed end to end across the guarded
CLI, shared attempt lifecycle, dedicated launch environment, mission adapter,
MAVLink/source contract, trigger and scheduled operations, telemetry artifacts,
BIN-window analysis, verdict/manifest agreement, and verified cleanup. The
review found no unresolved BLOCKER or HIGH finding.

Checks run against the reviewed diff before acceptance:

- GPS Phase 1/2, MAVLink, readiness, mechanism, and launch-target suite:
  **216 passed, 197 subtests passed**.
- Shared staged-attempt lifecycle regression: **49 passed, 8 subtests passed**
  (three existing warnings).
- Adjacent airspeed Phase 1 regression: **28 passed, 53 subtests passed** (two
  existing protobuf warnings).
- Focused Pyright over the changed GPS plugin, CLI, shared attempt runner, and
  relevant tests: **0 errors, 0 warnings**. The operator explicitly authorized
  focused GPS Pyright for this smoke; the unrelated repository-wide baseline is
  not this gate.

This acceptance authorizes exactly one protected `nominal` live smoke after the
reviewed diff is frozen in a scoped commit and all remaining no-live/runtime
prerequisites pass. It does not authorize `--live-phase2-smoke`, a retry, any
faulted case, the Phase 3 matrix, or evidence promotion.

ACCEPTED FOR NOMINAL LIVE SMOKE

## Phase 1 Acceptance Checklist (final gate for closing Phase 1)

Phase 1 closes to Accepted only when every item below is checked. This is a
no-SITL acceptance: it gates the plugin foundation, not any live result.

- [x] Plugin package built from the airspeed template; registry key
  `gps_failure` resolves (Chunk 1).
- [x] Deterministic case catalog: nominal + four fault sweeps + accumulation
  instrument, one variable per fault (Chunks 1–2, ADR-0017/0019).
- [x] GLTCH metre→degree payload contract with previews (Chunk 2).
- [x] Locked mission + `plane_gps.parm` overlay + base-then-overlay default
  stack, statically validated (Chunk 3, ADR-0020/0021).
- [x] Synthetic mechanism gate at `posTestRatio >= 1.0`, reset distinct from
  rejection, fail-closed on bad data (Chunk 4, ADR-0018).
- [x] Fake-testable runtime/MAVLink parameter contract; no real transport at
  import (Chunk 5).
- [x] Lane wired into the shared suite path; `--preflight` readiness report with
  explicit live blockers and `ready_for_live_run=false` (Chunk 6).
- [x] No-SITL unit suite green (`test_gps_failure_phase1`,
  `test_gps_mechanism_gate`, `test_gps_failure_mavlink`,
  `test_gps_failure_readiness`).
- [x] Code review of Chunks 4–6 recorded and findings resolved. The six
  confirmed BLOCKERs are resolved (see "Phase 1 Strict-Review Blocker Resolution
  (2026-07-13)" above), the three HIGH findings are now closed (see "Phase 1
  Strict-Review HIGH-Finding Resolution (2026-07-13)" above), and the MEDIUM
  duplicate-failure-reporting finding is fixed (see "Phase 1 Strict-Review
  MEDIUM-Finding Resolution (2026-07-13)" above). The final no-SITL review
  (2026-07-13, "Phase 1 Final No-SITL Review Acceptance" below) re-verified every
  prior finding in code and found no new BLOCKER/HIGH/MEDIUM/substantiated-LOW
  issue, closing the formal review sign-off.
- [x] Docs/index status lines reconciled to the implemented no-SITL behavior
  (trigger-gated executable plans, substantive behavior evidence,
  contradiction-safe manifest, complete artifact schema, atomic MAVLink batch);
  live runs remain deferred.
- [x] Working tree committed on `feature/gps-failure-behavior` (the scoped
  blocker-fix commit).

Phase 1 is Accepted as a no-SITL foundation by the 2026-07-13 final review
(below). No live SITL/Gazebo run, real parameter readback, or evidence claim is
part of Phase 1 acceptance; those are Phase 2 and remain unverified.

## Phase 1 Final No-SITL Review Acceptance (2026-07-13)

An independent final no-SITL review re-verified the whole Phase 1 foundation and
**accepts it**. This is a no-SITL acceptance of the plugin foundation only; it
makes no live claim.

Every previously reported finding was re-verified as resolved in the current
committed code (not merely claimed in prose):

- Former BLOCKERs: runtime injection requires a validated seq 1→3→4 navigation
  trigger (with an optional seq-2 DO-command report)
  trace before any write (`runtime.py`, `monitor.py`); preview plans are never
  execution-authorized; the analyzer requires substantive finite behavior-tier
  evidence, not a marker boolean (`analyzers.py`); missing/contradictory evidence
  cannot become nominal/accepted; the manifest fails closed on contradictory
  classifications (`manifest.py`); `gps_injection.json` is in the artifact schema
  and reported by readiness; MAVLink batch writes are atomically prevalidated
  with zero writes on any invalid entry (`mavlink.preflight_batch`); Chunks 4–6
  are committed and the worktree is clean.
- Former HIGH: malformed recipes return structured failures instead of a leaked
  `KeyError`/`TypeError` (`runtime._required_recipe_float`, `_as_event_mapping`,
  `_resolve_case_trigger`; `mavlink.normalize_readback_rules` raises `ValueError`);
  focused Pyright passes (0 errors); `.ai` and governance status match the
  committed code.
- Former MEDIUM: failed reads/writes do not duplicate parameters in
  `missing_parameters` (`mavlink._merge_missing`); failure reporting stays
  deterministic and preserves the error detail once in `tolerance_failures`.

Dedicated launch paths verified structurally: `plane-gps` builds
`plane_base.parm -> plane_gps.parm` only via `build_plane_gps_param_args()`
(no airspeed overlay, local override excluded unconditionally and printed, wipes
EEPROM, dedicated `var/runs/sitl/plane-gps` identity, `udp:127.0.0.1:14551`);
`gazebo-plane-gps` reuses the sensor-neutral base `mini_talon_runway.sdf`
(`$PLANE_WORLD`) by reference with no CTE/wind world path and a dedicated
identity. The plugin `defaults.py`, docs, and readiness all use the dedicated
GPS targets; GPS docs do not route live work through `plane-cte`; airspeed and
wind-matrix paths still use `plane-cte`; no document claims the GPS targets were
live-tested.

Checks actually run for this review (all exit 0):

- `bash -n src/sim_ard_gaw/launch/launch.sh`, `bash -n scripts/ops/launch.sh`,
  `scripts/ops/launch.sh help` — no launch target invoked.
- `pytest test_gps_failure_phase1 test_gps_mechanism_gate test_gps_failure_mavlink
  test_gps_failure_readiness` → **153 passed, 178 subtests**; plus discovered
  `test_gps_launch_targets` → **10 passed** (163 GPS tests total).
- Airspeed regression `pytest test_airspeed_failure_phase1
  test_airspeed_mechanism_gate` → **41 passed**.
- Focused `pyright` over the GPS plugin, CLI, and four test files →
  **0 errors, 0 warnings, 0 informations**.
- `run_gps_failure --list-cases | --probe-schema | --preflight |
  --dry-run --case nominal` → all exit 0; `--preflight` reports
  `ready_for_live_run=false`.
- `git diff --check` and `make doctor` → pass; worktree clean.

No SITL, Gazebo, or MAVLink activity occurred; no mission was executed. Phase 2
live smoke is next and remains unverified: no live SITL/Gazebo GPS smoke, real
parameter readback, real mission timing, BIN extraction, empirical-knee result,
or scientific-evidence claim exists. `ready_for_live_run=false` remains correct
because the live adapters are not implemented yet.

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
- The dedicated `plane-gps` / `gazebo-plane-gps` targets are structural only;
  Phase-2 smoke must confirm the realized parameter stack (base + `plane_gps.parm`
  with no local override) and Gazebo GPS/NavSat availability live.

## Smoke Ledger (Phase 2)

### 2026-07-14 — protected nominal attempt 1

- Time: start `2026-07-14T07:40:06Z` / `2026-07-14T10:40:06+03:00 EEST`;
  terminal record `2026-07-14T07:40:20Z`.
- Reviewed live-run HEAD:
  `f21395c75a53cf9832c5fbac67360c02ba97b394` (`Fixed: harden gps nominal
  live smoke path`).
- Exact command:

  ```bash
  PYTHONPATH=src ./env/bin/python3 -m \
    sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure \
    --live-case nominal \
    --confirm-live-phase2 \
    --campaign-root /home/ahmed/ardupilot_workspace_next/var/runs/gps_failure_behavior_phase2_nominal_20260714T073957200424999Z
  ```

- Raw root:
  `var/runs/gps_failure_behavior_phase2_nominal_20260714T073957200424999Z/`.
  Attempt directory: `nominal/runs/attempt_001/`. Command exit status: **1**.
- Launch identity: `plane-gps` and `gazebo-plane-gps` both started. The Plane
  log records exactly `plane_base.parm -> plane_gps.parm`, explicitly excludes
  `.private/config/plane_params.local.parm`, and contains no airspeed overlay.
  Gazebo reported the governed workspace-only plugin search path
  `/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo`; the loaded
  plugin emitted `ArduPilotPlugin` runtime messages. Pre-run plugin SHA-256:
  `1d4089bb6306ecc602e484e9b4e3e77dfb7ecf6649a4292ba872f6d420415fc0`.
- Mission/trigger/observation: upload of the five-item mission failed with
  `MISSION_ACK type=4`, decoded as `MAV_MISSION_NO_SPACE`. The Plane console was
  still in `INITIALISING`. Mission verification, arming, AUTO, seq-1->2->3->4,
  the trigger, realized straight-leg duration, and the required 90 s
  observation did not occur.
- Nominal fault contract: `gps_injection.json` records `fault_type=nominal`, an
  empty requested payload and empty schedule. Failure occurred before monitor
  execution; `live_execution` is absent and no `SIM_GPS1_*` fault write was
  attempted.
- Live parameter/source contract: not reached. No live knee/source readbacks,
  estimator flags, or live `posTestRatio` samples exist.
- Artifact checklist: `manifest.json`, `gps_injection.json`,
  `gps_cleanup.json`, `plane_gps.log`, and `gazebo_plane_gps.log` exist and the
  JSON files parse as strict finite JSON. Required behavior artifacts
  `gps_behavior_summary.json`, `ekf_innovation_metrics.json`,
  `truth_vs_belief.json`, `mode_timeline.json`,
  `attitude_altitude_envelope.json`, and `source_contract.json` are absent
  because control failed before the monitor. Manifest SHA-256:
  `6f90b7c564774808b6e1aadfa0b59656205b68fa12ad1a396fc910a9315bde7a`;
  injection SHA-256:
  `4a248638589bb216f5fbfeff73fec8cff3656bf923a6f499c740f96c846ad476`;
  cleanup SHA-256:
  `ca8aa07e75a08d5d731d942d7cda5d25d02e41615542702f0581c423d7ec0657`.
- BIN/log analysis: no current-attempt DataFlash BIN was produced, so no XKF4,
  SIM, or POS analysis and no BIN hash exist. MAVProxy created a zero-byte
  `var/logs/mavproxy/plane-gps/logs/2026-07-14/flight1/flight.tlog`; it is raw
  runtime state, not evidence.
- Behavior class: **not classifiable / analysis incomplete**. The terminal
  manifest verdict is `failed_retryable` / `error` with the mission-upload
  exception; no analyzer ran and no accepted observation exists.
- Cleanup: attempt-owned termination closed its direct handles and MAVLink but
  `gps_cleanup.json` is `ok=false` because three MAVProxy child processes
  remained. The governed `scripts/ops/launch.sh cleanup` was then run once;
  afterward the simulator-process scan was clean and port 14551 was free.
- Blockers exposed by the attempt: the GPS environment waits only for the first
  heartbeat and did not establish initialized/GPS/EKF vehicle readiness before
  mission upload; attempt cleanup did not own/terminate every MAVProxy child;
  the terminal error row was persisted before failed cleanup and therefore did
  not include the cleanup artifact/result. These require no-live remediation
  and a fresh strict review before any new live authorization.
- Gate decision: **NOMINAL_SMOKE_REJECTED**. No retry, slow drift, hard denial,
  jamming, step glitch, combined smoke, matrix, evidence promotion, commit, or
  push followed this attempt.

### 2026-07-14 — post-rejection remediation state (no live rerun)

- The historical rejected attempt and its hashes above are unchanged.
- Readiness remediation is implemented: mission control is unavailable until
  the existing Plane gate confirms AUTO availability, a non-`INITIALISING`
  mode, GPS readiness, EKF readiness, and two consecutive ready heartbeats.
- Cleanup remediation is implemented: direct handle termination and MAVLink
  close are followed by canonical `scripts/ops/launch.sh cleanup`, structured
  command-result capture, and an independent final survivor scan. Any failure
  remains terminal.
- Terminal-record remediation is implemented: on a stage exception,
  `AttemptRunner` cleans up before appending the error row, refreshes cleanup
  artifacts/results into that row, records a secondary cleanup exception if
  present, and re-raises the original failure. GPS rows explicitly persist
  framework `status` and the generic monitor result.
- All remediation paths are fake/injection tested; no SITL, Gazebo, MAVProxy,
  MAVLink, mission upload, parameter readback/write, BIN decode, live retry, or
  evidence promotion occurred.
- Checks run after the remediation: the focused GPS/core/adjacent-airspeed
  regression set passed (**324 tests, 258 subtests**); focused Pyright over the
  GPS plugin/CLI, changed core files, and affected tests reported **0 errors, 0
  warnings**; no-live `--preflight` and `--phase2-smoke-plan` passed; the live
  CLI without confirmation remained denied; `make doctor` and
  `git diff --check` passed.
- Gate decision remains **NOMINAL_SMOKE_REJECTED / PHASE_2_OPEN**. The next
  permitted action is a fresh strict no-live review. A second nominal live
  attempt requires separate operator authorization after that review.

### 2026-07-14 — protected nominal attempt 2

- Time: start `2026-07-14T08:01:23Z` / `2026-07-14T11:01:23+03:00 EEST`;
  terminal record `2026-07-14T08:02:12Z`. Reviewed live-run HEAD remained
  `f21395c75a53cf9832c5fbac67360c02ba97b394`.
- Exact command:

  ```bash
  PYTHONPATH=src ./env/bin/python3 -m \
    sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure \
    --live-case nominal \
    --confirm-live-phase2 \
    --campaign-root /home/ahmed/ardupilot_workspace_next/var/runs/gps_failure_behavior_phase2_nominal_20260714T080120722888267Z
  ```

- Raw root:
  `var/runs/gps_failure_behavior_phase2_nominal_20260714T080120722888267Z/`.
  Attempt directory: `nominal/runs/attempt_001/`. Command exit status: **1**.
- Progress proved: the remediated gate reported AUTO availability, a
  non-`INITIALISING` vehicle, GPS readiness, EKF readiness, and two ready
  heartbeats. The five-item mission uploaded and verified, the vehicle armed,
  and AUTO was entered. This validates those paths only; it is not an accepted
  smoke.
- Monitor failure: `mode_timeline.json` records
  `telemetry_rate_request_failed`, an empty trigger trace, and no mode samples.
  Read-only extraction from the raw tlog found four command-511 ACKs in request
  order: accepted, accepted, denied, accepted. The then-current code's third
  request was `STATUSTEXT`, an event-driven message. Requiring its interval ACK
  incorrectly stopped the monitor before live source-contract readback,
  seq-1->2->3->4 trigger, nominal no-write execution, or the 90 s observation.
- Behavior/artifacts: `gps_behavior_summary.json` is
  `pre_injection_failure` / `accepted_observation=false`. The behavior files
  exist but contain no accepted live observation; `source_contract.json` lacks
  the required live readbacks. The current-attempt BIN and tlog are retained
  only as raw diagnostics. BIN SHA-256:
  `0c471d27db854a4ebcd5a134180536fbdce680e7290700b764772c8506df64ec`;
  tlog SHA-256:
  `c9a9d4ea3ad59ae04595312bb4e21f7e8a2783787906732aee44a5d81fb850c1`.
- Cleanup: the canonical command returned 1 and the final scan reported one
  live MAVProxy plus two children/zombies. The command used exact-name
  `mavproxy`, while the real executable name was `mavproxy.py`. The proven
  airspeed workspace-owned cleanup was then used manually to remove the
  attempt's remnants; the dated final simulator-process scan was clean.
- Terminal-record remediation proved effective: the final row is `status=error`
  / `failed_retryable`, contains the structured monitor result, and contains
  `gps_cleanup.json` plus the cleanup errors. Manifest SHA-256:
  `87d6f335ea989b76db2ae2e9b70ffd5759b04fd98eb2316c1072d0d1ded72e1a`;
  injection SHA-256:
  `4a248638589bb216f5fbfeff73fec8cff3656bf923a6f499c740f96c846ad476`;
  cleanup SHA-256:
  `91b81a0826eca7f2efb4cd5092cb98b0475a594db9de2ce2fab734b27683642a`.
- Gate decision: **NOMINAL_SMOKE_REJECTED / PHASE_2_OPEN**. No faulted case,
  matrix run, evidence promotion, commit, or push followed.

### 2026-07-14 — attempt-2 remediation state (no live rerun)

- GPS telemetry setup now uses its own `request_live_streams` helper. It makes
  no per-message ACK a prerequisite;
  the monitor records and fails closed on actual required periodic-message
  delivery. `STATUSTEXT` remains optional/event-driven.
- GPS governed cleanup now runs its own workspace-scoped process cleanup before
  canonical cleanup and the independent survivor scan. Canonical
  `launch.sh cleanup` additionally matches `[m]avproxy.py`.
- GPS owns its stream, readiness, mission-protocol, and cleanup helpers. A
  structural test fails on any GPS import from a sibling plugin.
- Focused tests reproduce the denied/missing ACK condition without aborting,
  verify all four proven stream requests, require actual telemetry delivery,
  verify cleanup-helper reuse, and assert the canonical Python-name matcher.
  The GPS/core/adjacent-airspeed regression set passed **334 tests, 262
  subtests**; focused Pyright reported **0 errors, 0 warnings**; no-live
  `--preflight`, `--phase2-smoke-plan`, and the unconfirmed-live denial passed;
  both launcher syntax checks, `git diff --check`, and `make doctor` passed.
- Gate decision remains **NOMINAL_SMOKE_REJECTED / PHASE_2_OPEN**. A third
  nominal attempt requires fresh strict no-live review and separate operator
  authorization.

### 2026-07-14 — unaccepted diagnostic attempt 3

- An operator-started nominal diagnostic used raw root
  `var/tmp/gps_failure_behavior_phase2_nominal_20260714T081602434288891Z/`.
  It was not an accepted or promoted smoke result; the attempt root was not
  retained at final review.
- The telemetry ACK failure did not recur. Read-only inspection of raw flight-3
  telemetry showed the required message streams arriving, AUTO armed flight,
  and `MISSION_CURRENT` progress `0 -> 1 -> 3 -> 4`. Seq 2 was absent because
  it is the verified `DO_CHANGE_SPEED` command, not a navigation item whose
  current report ArduPlane guarantees. Tlog SHA-256:
  `3b77a45c0fceba45db03cd686560bb7446a4f9f179127924f406a2c6383ae35c`.
- The then-running monitor still required seq 2, so it could not authorize the
  seq-4 trigger. The process ended without an accepted terminal result and left
  three orphaned MAVProxy processes. The new GPS-owned workspace cleanup
  removed those exact remnants; the final simulator-process scan was empty.
- ADR-0020 is amended to require fresh, monotonic, armed/AUTO navigation seqs 1
  and 3, permit an optional seq-2 DO-command report, and retain first-edge seq-4
  latching. Fake tests cover both emitted forms (`1 -> 2 -> 3 -> 4` and
  `1 -> 3 -> 4`) plus regressions and missing required navigation progress.
- Gate decision: **UNACCEPTED_DIAGNOSTIC / PHASE_2_OPEN**. No new live attempt
  is authorized by this diagnostic or remediation.

### 2026-07-14 — governed nominal attempt 4

- Raw root:
  `var/runs/gps_failure_behavior_phase2_nominal_20260714T083812969855707Z/`.
  Start `2026-07-14T08:38:22Z`; terminal `2026-07-14T08:46:54Z`.
- GPS-owned readiness passed, all five mission items uploaded and verified, the
  vehicle armed and entered AUTO, and the GPS-owned telemetry stream setup
  delivered real mission progress `0 -> 1 -> 3 -> 4`. The earlier readiness,
  ACK-gate, and sibling-plugin defects did not recur.
- The attempt did not trigger. Leading home-row seq 0 had entered
  `trigger_trace`; the validator correctly rejects out-of-contract evidence,
  but the monitor should not have treated pre-navigation home-row reports as
  evidence at all. Once present, seq 0 made later `1 -> 3 -> 4` permanently
  invalid. The attempt was interrupted rather than waiting for the 900 s
  timeout.
- Terminal status is `interrupted` / `failed_retryable`; no behavior artifacts
  or accepted observation exist. Cleanup is `ok=true`: GPS-owned cleanup and
  canonical cleanup succeeded, MAVLink closed, and the final process scan is
  empty. Manifest SHA-256:
  `e80ae97acee34622835471e888b828656ddae8c5d20880c4ee08919b206e4e3a`;
  cleanup SHA-256:
  `2bc8bff61234a0c4143cbb7b32202e956d07263ff6e9763a0cd52e6b5d687036`;
  raw tlog SHA-256:
  `664c9c500e278da1215a79d6ace88c972755e3fadcc42b84774c4a3440311a61`;
  current-attempt BIN (`00000003.BIN`) SHA-256:
  `8693b69750a13e4b5f7cda2cb92cd9fb0a9f4c607e8ebd158aae248025033ca5`.
- No-live remediation now ignores seq 0 only while `trigger_trace` is empty.
  After seq 1, seq 0 is retained and rejected as a regression. Tests cover both
  cases.
- Gate decision: **NOMINAL_SMOKE_REJECTED / PHASE_2_OPEN**. No automatic retry
  or faulted case ran.

### 2026-07-14 — nominal run declared success but rejected on strict review

- Raw root:
  `var/runs/gps_failure_behavior_live_nominal_codex_20260714T095246Z/`.
  The terminal row says `success` / `valid_nominal`; that declaration is not
  accepted as Phase-2 evidence.
- Review found the BIN was decoded while it was still growing, before cleanup
  closed the logger. The decoded window was also anchored to the mission-upload
  `CMD CNum=4` row rather than live seq-4 execution.
- Pymavlink had already scaled decoded `XKF4.SP` and decoded `SIM/POS Lat/Lng`
  into engineering units. Applying another `/100` and `/1e7` suppressed the
  innovation ratio and truth-vs-belief distance.
- The nominal case advertised a 90 s acceptance window while the monitor used
  20 s. `gps_injection.json` existed but was omitted from the terminal artifact
  map, the terminal stimulus retained stale plan-only fields, and no required
  run configuration/source-tree/input provenance was captured.
- No-live remediation moves staged analysis/verdict after framework cleanup,
  records a fresh live seq-4 boot-time anchor, rejects CMD upload rows as an
  anchor, fixes decoded units, makes case metadata the duration source of
  truth, synchronizes the injection artifact/stimulus, and adds shared
  campaign-level provenance used independently by GPS and airspeed. GPS still
  has no sibling-plugin import.
- Gate decision: **DECLARED_RESULT_REJECTED / PHASE_2_OPEN**. A new live run is
  required; the raw root is retained only as diagnostic output.

### 2026-07-14 — full-flight lifecycle comparison and no-live correction

- Raw root:
  `var/runs/gps_failure_behavior_20260714T113259746238Z/`.
- The run is rejected despite `gps_behavior_summary.json` declaring
  `valid_nominal`. It observed only mission-current seqs 1, 3 and 4 and stopped
  with `post_injection_observation_complete` after the 20 s minimum window;
  seqs 5–9 and planned RTL were never observed.
- The GPS base world realized an approximately 359-degree initial heading while
  the copied behavior mission begins east. Historical airspeed comparison
  realized approximately 89 degrees and completed seq 9 / stabilized RTL.
- The authorized first trigger event was at boot time 83.186 s. The analyzer's
  reverse trace search selected a repeated seq-4 message near 102.686 s,
  leaving only five persisted BIN mechanism/truth samples. Read-only analysis
  from the correct first edge produced hundreds of paired samples; the BIN was
  usable but the stored analysis window was not.
- No-live correction: dedicated east-facing `mini_talon_gps_runway.sdf`;
  `MISSION_ITEM_REACHED`, max-seq and AUTO-to-RTL tracking; 20/90 s as minimum
  evidence only; planned RTL plus 10 s stabilization; immutable first-edge BIN
  anchor; and terminal/mission-completion gates in classifier, summary and
  manifest acceptance. The shared base world and airspeed plugin are unchanged.
- Gate decision: **DECLARED_RESULT_REJECTED / NO-LIVE_FIX_TESTED /
  PHASE_2_OPEN**. No fault case is authorized by this record; a fresh governed
  nominal run must verify the realized heading and full mission terminal path.

### 2026-07-14 — corrected protected nominal raw validation

- Exact command:

  ```bash
  env/bin/python -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure \
    --live-case nominal --confirm-live-phase2
  ```

- Raw root:
  `var/runs/gps_failure_behavior_20260714T120212630044Z/`; attempt directory
  `nominal/runs/attempt_001/`; command exit status **0**.
- A preceding post-fix attempt at
  `var/runs/gps_failure_behavior_20260714T115636180733Z/` timed out at the
  readiness gate before flight. The timeout exposed insufficient diagnostics,
  not a missing world signal: a read-only probe observed GPS fix type 6 with 10
  satellites and EKF flags 831. The readiness loop now refreshes idempotent
  stream requests every five seconds and includes all observed gate state in a
  timeout. The fresh run then passed readiness normally.
- Flight lifecycle: immutable trigger seq 4 at boot `56.487 s`; monitor duration
  `208.43 s`; max mission seq 9; distinct reached rows 2–8; AUTO-to-RTL at seq
  8; stop reason `planned_rtl_stabilized`; terminal and mission-complete flags
  both true. Initial BIN ATT yaw was approximately `89.27 deg` east.
- Analysis: `gps_behavior_summary.json` is `valid_nominal`,
  `accepted_observation=true`; the live source contract is `ok=true`; BIN
  `window_start_time_us=56487000` matches the stored first-edge trigger and
  contains 4,038 truth/belief pairs plus 4,039 mechanism samples.
- Provenance: world SHA-256
  `69d1a7f18348f0cef21507c93226bc6e982f4c103b31c5ef7dafc7c357b6fa26`;
  mission SHA-256
  `c372bf6253c986acd7ecb48f1292f6bc5bc9861161d1b869503514ca71362c2e`.
- Cleanup: `gps_cleanup.json` is `ok=true`; canonical cleanup exited 0 and the
  final simulator-process scan was empty.
- Gate decision: **PROTECTED_NOMINAL_RAW_VALIDATION_PASSED / PHASE_2_OPEN**.
  The run is not promoted curated evidence, does not establish an empirical
  knee, and does not authorize or claim any fault-case result.

### 2026-07-14 — post-nominal takeoff-loop correction

- Read-only BIN review tied the visible pre-injection loop to mission geometry:
  takeoff completed at `98.22 m` AGL around `323 m` East, after which the copied
  seq-3 waypoint at `300 m` was behind the aircraft and outside the configured
  20 m waypoint radius. Target bearing reversed to approximately `-92.8 deg`
  and commanded roll reached about 40–45 degrees until seq 3 was passed.
- Mission v3 moves seq 3/7 to 500 m East and seq 4/5/6 to 1300 m East. It keeps
  both 800 m analysis legs, seq numbering, 100 m altitude, first seq-4 trigger,
  reciprocal path, and planned RTL unchanged.
- Active mission SHA-256 is
  `3d111b32351a527500eafa43e4ad67d74b71ffc09555bd878e570cbed5f671bd`.
  The raw nominal above remains bound to its recorded v2 hash
  `c372bf6253c986acd7ecb48f1292f6bc5bc9861161d1b869503514ca71362c2e`.
- Fresh governed nominal:
  `var/runs/gps_failure_behavior_20260714T122459635208Z/`.
- The run recorded the active v3 hash, reached seq 9, observed reached rows
  2–8, transitioned to planned RTL at seq 8, stopped after RTL stabilization,
  and emitted `accepted_observation=true` with clean cleanup.
- From takeoff completion to seq 3, East displacement was monotonic, waypoint
  distance fell from about 180 m to less than 1 m, north span was 3.7 m, target
  bearing remained eastward, and maximum absolute roll was 2.1 degrees.
- Gate decision: **V3_GEOMETRY_RAW_VALIDATED / FAULT_CASES_STILL_OPEN**. The
  pre-injection loop is fixed. This does not promote curated evidence or accept
  Phase 2.

### 2026-07-14 — v4 longer/wider fault geometry

- Mission v4 retains the raw-validated 500 m settle and all trigger/terminal
  sequence contracts.
- Seq 4/5/6 move to 2500 m East; seq 5–8 move to 500 m North. The outbound and
  reciprocal measurement legs are 2000 m and their lane spacing is 500 m.
- Active SHA-256:
  `8d1c8de43c6e496946b1f6bdf3d88f4aa14cd3ba7abe84067cb6a4edd27d7f35`.
- Targeted mission geometry and `hard_denial_15s` dry-run checks pass. V4 has
  not yet been flown; the v3 nominal remains the latest raw live validation.

## Rollback Rule

Phase 0 is docs-only (runbook + ADRs + human docs + index entries); rollback is
deleting the `gps_failure_behavior` bundle, the five ADRs, and reverting the
index edits. No code or runtime state is touched in Phase 0.
