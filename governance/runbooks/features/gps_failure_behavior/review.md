# GPS Failure Behavior — Review

Status: Phase 1 Chunk 6 (integration readiness) is **implemented pending
review**. Full Phase 1 remains open until the checklist below is signed off.

## Phase Acceptance Ledger

| Phase | Status | Date | Notes |
| --- | --- | --- | --- |
| Phase 0 — design lock | Accepted | 2026-07-06 | Full brainstorm; four faults, two-tier knee, seven bands, characterize-not-gate; five Proposed ADRs (0017–0021). |
| Phase 1 — no-SITL plugin foundation | Open | — | Chunks 1–6 exist: scaffold, payload semantics, static mission/parameter-stack integration, synthetic mechanism-gate evaluation, runtime/MAVLink contract helpers, and integration-readiness wiring. Chunk 6 is implemented pending review; the Phase 1 acceptance checklist below is not yet signed off. Live connection, mission execution, and BIN/log extraction remain open. |
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
- [~] Code review of Chunks 4–6 recorded and findings resolved. The six
  confirmed BLOCKERs are resolved (see "Phase 1 Strict-Review Blocker Resolution
  (2026-07-13)" above); any remaining HIGH/MEDIUM/LOW review findings still gate
  acceptance and are not yet cleared.
- [x] Docs/index status lines reconciled to the implemented no-SITL behavior
  (trigger-gated executable plans, substantive behavior evidence,
  contradiction-safe manifest, complete artifact schema, atomic MAVLink batch);
  live runs remain deferred.
- [x] Working tree committed on `feature/gps-failure-behavior` (the scoped
  blocker-fix commit).

Phase 1 is not marked Accepted by this work: the strict-review blockers are
resolved, but acceptance remains pending the remaining review findings. No live
SITL/Gazebo run, real parameter readback, or evidence claim is part of Phase 1
acceptance; those are Phase 2.

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
