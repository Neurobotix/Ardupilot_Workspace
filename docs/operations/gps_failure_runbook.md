# GPS Failure Runbook

Status: Phase 1 no-SITL foundation is **Accepted** (2026-07-13, final no-SITL
review). The GPS failure lane has the no-SITL plugin foundation, locked static
mission and GPS parameter overlay, structural tests, a synthetic no-SITL
mechanism gate, a fake-testable runtime/MAVLink parameter contract, and
integration-readiness wiring into the shared suite path. A pre-smoke Phase 2
implementation path now exists for an authorized live smoke, including
explicit telemetry/source-contract helpers, production mission-adapter wiring,
cleanup hardening, and decoded-record BIN analysis helpers. On 2026-07-14 one
corrected protected nominal completed reviewed raw validation, including a full
mission terminal state and accepted parameter/behavior analysis. No curated
evidence or fault-case result exists, so Phase 2 remains open. A strict
pre-smoke review rejected the initial live path; its fixes were
implemented and no-live tested, then a fresh strict no-live review on 2026-07-14
found no remaining BLOCKER or HIGH finding and accepted the exact corrected
diff for the single nominal live smoke. Two nominal attempts on 2026-07-14 are
both rejected. Attempt 1 failed before arming because readiness was too weak.
Attempt 2 proved the readiness and mission paths through arming and AUTO, but
the monitor incorrectly required an accepted telemetry-rate ACK for
event-driven `STATUSTEXT`; cleanup also missed the real `mavproxy.py` process
name. No trigger, 90 s observation, accepted result, or faulted case occurred.
An additional unaccepted diagnostic later emitted `MISSION_CURRENT` as
`0 -> 1 -> 3 -> 4`, proving seq 2 (`DO_CHANGE_SPEED`) is not a reliable current
event. The trigger now requires fresh armed/AUTO navigation seqs 1 and 3,
permits optional seq 2, and still latches only the first seq-4 edge.
The working tree now uses GPS-owned data-stream, readiness, mission-protocol,
and owned-process cleanup helpers, gates telemetry on messages actually
observed, and explicitly matches `mavproxy.py` in canonical cleanup. GPS has no
runtime import from a sibling plugin; a structural test enforces that boundary.
Those corrections subsequently passed strict no-live review and were exercised
by corrected governed nominal runs. Live cases remain explicit operator actions;
the run command still requires its confirmation guard.

A later nominal run at
`var/runs/gps_failure_behavior_live_nominal_codex_20260714T095246Z/` reached a
terminal row that declared success, but strict review rejects that declaration.
Analysis ran before cleanup closed the BIN, used a mission-upload CMD row as the
window anchor, double-scaled decoded XKF4 and SIM/POS fields, advertised the
wrong nominal duration, omitted terminal injection/provenance contracts, and
left stale plan-only stimulus state. The 2026-07-14 no-live remediation moves
staged analysis after cleanup, uses a live boot-time anchor, fixes decoded
units, locks per-case duration metadata, synchronizes artifacts, and records
shared campaign provenance. That root remained rejected; the later corrected
protected nominal is the current raw validation result.

A governed nominal attempt at
`var/runs/gps_failure_behavior_phase2_nominal_20260714T083812969855707Z/`
proved the GPS-owned readiness, verified mission, arming/AUTO, telemetry, and
cleanup paths, but is **not accepted**. Leading home-row seq 0 poisoned the
trigger trace before valid `1 -> 3 -> 4` progress. The attempt was interrupted
instead of waiting for the then-current 900 s timeout; its terminal row is `interrupted` and
cleanup is fully clean. The no-live correction ignores seq 0 only before
trigger evidence starts and retains any later seq-0 regression as invalid.

The later nominal root
`var/runs/gps_failure_behavior_20260714T113259746238Z/` is rejected even though
its generated summary says `valid_nominal`. It spawned north against an
eastbound mission, stopped at seq 4 plus the 20 s minimum window, selected the
last repeated seq-4 message instead of the immutable injection edge for BIN
analysis, and had no mission-completion acceptance gate. The current no-live
fix uses `mini_talon_gps_runway.sdf`, treats 20/90 s only as minimum evidence,
continues until RTL stabilizes for 10 s (or a real terminal fault occurs),
records `MISSION_ITEM_REACHED` and RTL progress, and requires terminal mission
evidence for nominal acceptance.

The corrected governed nominal root
`var/runs/gps_failure_behavior_20260714T120212630044Z/` then passed raw
validation: first seq-4 trigger at boot 56.487 s, max seq 9, reached rows 2–8,
AUTO-to-RTL at seq 8, 10 s RTL stabilization, accepted source/BIN/behavior
analysis, an approximately 89.27-degree initial yaw, and clean cleanup. The
preceding readiness-only failure also caused the gate to add five-second stream
request refresh and detailed timeout state. This validates the protected
nominal implementation path only; no fault case or curated Phase-2 evidence is
claimed.

Post-run BIN review found that the v2 calm-lane takeoff reached 98.22 m AGL
around 323 m East, placing the copied 300 m seq-3 waypoint behind the aircraft
and causing the visible turnback loop before injection. Mission v3 moves seq
3/7 to 500 m East and seq 4/5/6 to 1300 m East while preserving both 800 m
measurement legs and every sequence/trigger/RTL contract. The corrected asset
was raw-validated at
`var/runs/gps_failure_behavior_20260714T122459635208Z/`: it carried the v3 hash,
completed through seq 9 and planned RTL, and flew monotonically East from
takeoff completion to seq 3 with only 2.1 degrees maximum absolute roll. The
loop is fixed. Fault cases and curated Phase-2 evidence remain open.

Mission v4 kept the validated 500 m settle while extending both measurement
legs to 2000 m and widening their separation to 500 m. It preserved seq-4
injection and seq-9 RTL, but had no live result before it was superseded.
Mission v6 is now the active shorter final-science candidate: 1000 m controlled
baseline, 6000 m straight fault-observation leg after the seq-4 trigger,
1000 m straight recovery/continuation, 30 s terminal loiter, seq-8 terminal
gate, and seq-9 RTL. The active hash is
`ba22c669c895f694e8556e0e9573e9f9dd278d159086e46706eb30a3714d7261`.
V6 has no-live structural coverage and is now the active mission for the next
live science campaign. The corrected framework was live-validated on the
bounded v4 mission and the longer v5 validation slice on 2026-07-16; no v6 live
campaign evidence exists yet.

On 2026-07-15, the working tree added a guarded protected round-robin live
campaign entry point and no-live tests for the workflow/analysis separation:
campaign counting now uses workflow-complete physical attempts, while behavior
acceptance remains a separate post-cleanup analysis result. The source contract
also now validates pre-injection EKF/GPS aiding flags and records post-fault
flags as behavior context. This is no-live implementation evidence only; no
new live campaign result is claimed.

On 2026-07-16, the working tree tightened GPS terminal manifest semantics into
a three-verdict model: `workflow_status`, `stimulus_fidelity_status`, and
`behavior_status` are separate fields, and `accepted_observation` is distinct
from `accepted_repetition`. A stimulus-failed attempt can be a behavior
observation only when workflow and behavior evidence are complete, but it does
not count as a valid requested-recipe repetition. This is a no-live contract
change and does not claim a new live result.

Also on 2026-07-16, `source_contract.json` was reframed around explicit proof
levels: `exact_internal_proof`, `bin_observable_proof`, and
`validated_proxy_proof`. Exact internal proof remains false unless a directly
logged EKF internal source signal is added in the future. EK3 readbacks are
configuration proof, decoded XKF4/GPS fields are BIN-observable mechanism
context, and the live pre-injection source gate is a validated proxy for the
internal `PV_AidingMode == AID_ABSOLUTE` condition.

Also on 2026-07-16, `attitude_altitude_envelope.json` gained explicit source
authority fields. The live monitor writes a `source=live_telemetry` artifact
with `evidence_quality=runtime_guard` before cleanup so low-altitude,
unexpected-disarm, and attitude-threshold safety guards remain visible during
the attempt. The post-cleanup analyzer rewrites the artifact from the selected
attempt-local BIN when decoded `POS.RelHomeAlt` or `CTUN.Alt` achieved altitude
and `ATT` attitude rows are available, marking it `source=BIN` and
`final_evidence_quality=true`. `POS.Alt` absolute altitude and `CTUN.DAlt`
desired altitude are not accepted as achieved/relative envelope sources. If one
axis is missing, the artifact is labeled `hybrid` or incomplete; if BIN and live
values differ beyond the recorded tolerances, the envelope status is `fail`.
This artifact can block reviewability, but it is not the GPS mechanism or
truth-vs-belief behavior classifier.

Also on 2026-07-16, post-cleanup GPS BIN analysis gained required
`gps_lifecycle_windows.json`. Reviewers should use this artifact as the
authoritative lifecycle sequence for baseline, trigger, injection,
fault-active, EKF response, recovery/continuation, and terminal state. Behavior
summaries may quote the outcome, but they do not replace the window evidence.
For `hard_denial` attempts, the lifecycle artifact and final
`gps_behavior_summary.json` also carry `hard_denial_transient`: denial timing,
restore timing, GPS quality before/during/after, reset times/offsets, full
post-trigger max truth-vs-belief gap, and active post-reset gap summary. The
classifier still consumes reset-segmented active samples; the full-window
summary is present so the denial/reset snap remains visible at top level.

## Current State

- Phase 0 (design lock) accepted 2026-07-06.
- Phase 1 Chunks 1–2 provide plugin construction, case listing, payload
  conversion/previews, schema probing, dry-run JSON, and unit tests.
- Phase 1 Chunk 3 adds the locked mission, GPS overlay, default-stack
  integration, and static/no-SITL contract tests.
- Phase 1 Chunk 4 adds `mechanism_gate.py`, a synthetic-record evaluator for
  the ADR-0018 `posTestRatio >= 1.0` mechanism boundary.
- Phase 1 Chunk 5 adds `mavlink.py` and `runtime.py` for deterministic
  parameter write/readback contracts and trigger-metadata-based injection plans.
  Unit tests use fakes only; no live MAVLink connection is opened.
- Phase 1 Chunk 6 adds `readiness.py` and the `--preflight` CLI action, wiring
  the lane into the shared suite path and emitting a no-SITL readiness report
  (`ready_for_live_run=false` with explicit live blockers).
- A 2026-07-13 strict-review pass resolved six confirmed Phase-1 BLOCKERs
  (no-SITL, with regression tests): ADR-0020 trigger-gated executable injection
  plans with preview strictly non-executable, substantive behavior evidence in
  the analyzer, contradiction-safe manifest acceptance, `gps_injection.json` in
  the artifact schema, and atomic MAVLink batch prevalidation. Pre-smoke Phase 2
  remains unaccepted until authorized live smoke supplies dated evidence.
- One reviewed raw nominal run has complete-mission and accepted BIN/log
  analysis. It remains raw runtime output; curated evidence and fault-case
  validation are still open.
- Future live attempts archive the selected post-cleanup DataFlash BIN into the
  attempt directory as `<case>__rep_NN__attempt_NNN.BIN`, analyze that copied
  artifact, and expose it as `raw_log` / `raw_log_path` in the terminal
  manifest row. Campaign runs also use an airspeed-style per-attempt SITL
  working tree under
  `<campaign_root>/_sitl_state/<case_id>/attempt_NNN/`, so future GPS runs keep
  ArduPilot/MAVProxy byproducts next to the campaign.
- The guarded live path now constructs mission control from the live MAVLink
  master and gates mechanism acceptance on the EKF/GPS source contract, but
  those paths remain no-SITL/fake tested only until authorized smoke.
- Pre-smoke hardening now waits for the Plane target's cleanup barrier before
  starting Gazebo, requires fresh heartbeat/SIMSTATE trigger evidence, latches
  one injection attempt, gates on every write/restore and verified cleanup,
  scopes behavior/BIN analysis to the injection window, and makes the CLI stop
  on the first non-accepted repetition. These are no-live implementation
  facts, not smoke evidence.
- Post-rejection remediation on 2026-07-14 adds a 120 s vehicle-readiness gate
  (AUTO available, no `INITIALISING`, GPS ready, EKF active, two consecutive
  ready heartbeats) before the mission adapter is installed. Per-attempt cleanup
  now calls `scripts/ops/launch.sh cleanup`, records its structured result, then
  scans independently for surviving simulator processes. `AttemptRunner` runs
  cleanup before persisting a terminal error and preserves the original failure
  if cleanup also fails. GPS terminal rows now persist the framework `status`
  and monitor result. These are no-live code/test facts only.
- Second rejected-smoke remediation adds GPS-owned `MAV_DATA_STREAM`, vehicle
  readiness, mission-protocol, and workspace-owned cleanup helpers instead of
  importing another feature plugin. It does not require per-message
  `COMMAND_ACK`, records actual required-message delivery in
  `mode_timeline.json`, and adds an explicit canonical `[m]avproxy.py` matcher.
  A structural test rejects sibling-plugin imports. These are no-live code/test
  facts only.
- The 2026-07-15 campaign-readiness update adds
  `--live-phase2-round-robin-campaign` for the protected Phase-2 case set. It
  writes `campaign_contract.json`, runs true round robin, uses zero automatic
  retries, stops on workflow/cleanup/raw-log failure, and does not let analysis
  rejection erase or consume the workflow attempt. Phase H supersedes this as
  the next live step: the default protected validation rerun is one run per
  protected case, not a five-run campaign.
- The 2026-07-16 vehicle-time scheduling update makes live slow-drift GLTCH
  strength use MAVLink `time_boot_ms` vehicle elapsed time, not monitor wall
  elapsed time. The monitor still uses wall time for deadlines and operator
  progress messages. `gps_injection.json` now records `wall_elapsed_s`,
  `vehicle_elapsed_s`, `clock_ratio`, and the physical payload clock source so
  reviewers can verify which clock drove each scheduled write. Missing or stale
  vehicle time fails closed for physical GPS scheduling instead of falling back
  to wall time.
- The 2026-07-16 no-live stimulus-fidelity update adds required
  `stimulus_fidelity.json` and terminal `stimulus_fidelity_status` fields.
  Post-cleanup BIN analysis now separately evaluates whether nominal,
  `slow_drift_0p5_mps`, and `hard_denial_15s` physically realized the requested
  stimulus. Missing, malformed, non-finite, unanchored, or absent BIN evidence
  fails stimulus fidelity closed. This is separate from behavior classification
  and does not claim a new live result.
- The 2026-07-16 no-live lifecycle-window update adds required
  `gps_lifecycle_windows.json`. The post-cleanup artifact must contain the
  ordered windows `pre_trigger_baseline`, `trigger`, `injection`,
  `fault_active`, `ekf_response`, `recovery_or_continuation`, and `terminal`,
  each with timing, source, status, metrics, and evidence references. Missing
  baseline, injection anchor, case-specific BIN stimulus, reset/snap or drift
  growth evidence, cleanup, raw-BIN archival, or required artifacts fails the
  lifecycle artifact closed.
- The 2026-07-16 no-live hard-denial transient update adds
  `hard_denial_transient` to lifecycle and final behavior-summary artifacts.
  Hard-denial review should inspect both `full_window_gap_summary` and
  `active_segment_gap_summary`; missing reset event times or offsets fail the
  transient section closed. Non-hard-denial cases report this section as
  `not_applicable`.
- The 2026-07-16 no-live three-verdict update persists
  `workflow_status`, `stimulus_fidelity_status`, `behavior_status`,
  `accepted_observation`, and `accepted_repetition` in terminal rows. Generic
  manifest views preserve these fields. GPS scheduler `accepted_count` counts
  accepted repetitions, while the protected campaign path explicitly counts
  workflow-complete physical attempts.
- The 2026-07-16 no-live envelope-authority update requires
  `attitude_altitude_envelope.json` to declare `source`, `altitude_source`,
  `attitude_source`, sampling limits, and evidence quality. Final post-cleanup
  evidence prefers BIN-derived altitude/attitude values; live telemetry remains
  a runtime guard and fallback context only when labeled.

## Static Default Stack

- SITL target: `plane-gps` (dedicated GPS failure identity)
- Gazebo target: `gazebo-plane-gps` (dedicated GPS failure identity)
- Mission: `assets/missions/gps_failure_behavior_mission.waypoints`
- Params: `config/vehicles/plane_base.parm` + `config/overlays/plane_gps.parm`
  in that order, with no airspeed overlay and no local plane override.

Mission v6 uses a one-way shorter final-science candidate geometry: 1000 m
controlled baseline to seq 3, injection on the first seq-4 edge, a 6000 m
straight fault-observation leg to seq 4, a 1000 m straight recovery/continuation segment
to seq 5, a 30 s terminal loiter at seq 6, terminal gates at seq 7/8, and RTL at
seq 9. This keeps ambiguous return-home turns out of the main observation
window and gives the lowest locked slow-drift rate (`0.2 m/s`) roughly 400 s of
straight-line exposure at the commanded 15 m/s speed.

The overlay pins the four EKF knee parameters, complete primary EKF source set,
and calm SITL wind. These checked-in values provide reproducible static inputs;
they do not prove the empirical knee. Live readback and realized straight-leg
duration remain Phase-2 requirements.

### Dedicated launch identities (corrected 2026-07-13; nominal live-validated 2026-07-14)

`plane-gps` and `gazebo-plane-gps` exist structurally in the governed launcher
and are **not** the CTE/airspeed targets:

- `plane-gps` loads exactly `plane_base.parm -> plane_gps.parm`. It does not
  load `plane_airspeed.parm` and does not append
  `.private/config/plane_params.local.parm` (the local override is excluded
  unconditionally and the launcher prints that exclusion). It wipes EEPROM and
  emits `udp:127.0.0.1:14551`. Manual launches default to
  `var/runs/sitl/plane-gps`; GPS campaign launches override that with
  `<campaign_root>/_sitl_state/<case_id>/attempt_NNN/`.
- `gazebo-plane-gps` uses `assets/worlds/mini_talon_gps_runway.sdf`: the same
  sensor-neutral Mini Talon capabilities, but an east-facing pose aligned to
  the behavior mission. The shared `mini_talon_runway.sdf` is unchanged.
- Using the earlier `plane-cte` / `gazebo-plane-cte` for GPS was unsafe: those
  load the airspeed overlay and the local override, a different stack than this
  contract. See ADR-0021 (2026-07-13 amendment).

These targets are covered by structural tests and completed the protected
nominal raw validation above. No curated evidence or fault-case validation has
been promoted; Phase 2 remains pending.

## No-SITL CLI

- `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` exists for
  no-SITL `--list-cases`, `--dry-run --case <case_id>`, `--probe-schema`, and
  `--preflight` (integration-readiness report).
- A guarded Phase 2 smoke runner exists for the protected smoke slice only:
  `--live-phase2-smoke --confirm-live-phase2`, or
  `--live-case <case> --confirm-live-phase2` for one of the protected cases
  below. Do not run it without explicit live-smoke authorization.
- A guarded Phase H validation rerun runner exists for the same protected case
  set only: `--live-phase2-validation-rerun --confirm-live-phase2
  --confirm-validation-rerun`. It remains a one-run protected sanity path.
- The protected round-robin campaign flag requires `--confirm-live-campaign`
  and is the intended v6 live science campaign path after the corrected
  framework has passed validation: five workflow-complete physical runs each
  for `nominal`, `slow_drift_0p5_mps`, and `hard_denial_15s`, with zero
  automatic retries.
- `--phase2-smoke-plan` is plan-only and does not start SITL/Gazebo or open
  MAVLink.
- Dry-run `--preview-elapsed-s` remains a plan-only preview input. During live
  execution, slow-drift payloads and bounded restore schedules are driven by
  vehicle `time_boot_ms`; wall elapsed is diagnostic only.

Example no-SITL and guard checks (the `--live-case nominal` command without
confirmation must fail before launch):

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --list-cases
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --probe-schema
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --preflight
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --phase2-smoke-plan
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --phase2-validation-rerun-plan
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --live-case nominal
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --live-phase2-round-robin-campaign --confirm-live-phase2
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --dry-run --case slow_drift_0p5_mps --reference-latitude-deg -35.363262 --preview-elapsed-s 90
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_mavlink.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_phase2_path.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_phase1.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_mechanism_gate.py
PYTHONPATH=src ./env/bin/python3 -m pytest tests/unit/test_gps_failure_readiness.py
```

## Live-Run Gate (Phase 2)

Before any live matrix: read back every injected `SIM_GPS1_*` param, read live
`EK3_POS_I_GATE` / `EK3_GLITCH_RAD` / `FS_EKF_THRESH` / `EK3_GPS_CHECK` plus
`EK3_SRC1_POSXY` / `EK3_SRC1_VELXY` / `EK3_SRC1_POSZ` / `EK3_SRC1_VELZ` /
`EK3_SRC1_YAW`, require `EK3_GLITCH_RAD > 0`, integral source enums, and EKF
absolute-position status flags as the validated GPS-aiding proxy. Confirm the
checked-in configuration source set (`3/3/1/3/1`) and knee values plus the
straight-leg duration, but do not treat those readbacks as exact internal EKF
runtime proof. Trigger authorization additionally requires fresh,
co-temporal heartbeat and SIMSTATE evidence; cleanup, all scheduled operations,
and a workflow-complete terminal record must succeed. Behavior acceptance is
recorded separately by post-cleanup analysis and does not make a dirty workflow
valid. A bad stimulus dose can remain a useful behavior observation only when
behavior evidence is complete, but it is not an accepted repetition. See
`governance/runbooks/features/gps_failure_behavior/plan.md`.

Before the v6 live science campaign, `--preflight` must report all Phase A-G
no-live gates satisfied: vehicle-time scheduling, BIN stimulus fidelity,
three-verdict manifest semantics, lifecycle-window artifact authority,
hard-denial transient visibility, source-proof labels, and altitude/attitude
source authority. Missing gates are blockers, not warnings. A previous live
confirmation does not carry forward: the v6 campaign still requires explicit
operator authorization.

Protected v6 science campaign slice:

- `nominal`
- `slow_drift_0p5_mps`
- `hard_denial_15s`

Stop the v6 campaign immediately on any workflow failure, stimulus
fidelity failure, lifecycle-window failure, raw-log archival failure, or cleanup
failure. Failed attempts are preserved; there are zero automatic retries unless
the operator separately requests a follow-up.

Run the protected v6 science round-robin from the workspace root only after
`--preflight` shows the gates satisfied and the operator explicitly authorizes
the live campaign:

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --live-phase2-round-robin-campaign --confirm-live-phase2 --confirm-live-campaign --campaign-cases nominal,slow_drift_0p5_mps,hard_denial_15s --runs-per-case 5 --mission-timeout 1800 --campaign-root "$(pwd)/var/runs/gps_failure_behavior_v6_science_rr_$(date -u +%Y%m%dT%H%M%SZ)"
```

The full Phase 3 matrix remains gated; this v6 campaign authorizes only the
protected three-case set above, not the full v1 GPS catalog.

## References

- Lane description: `docs/architecture/gps_failure_lane.md`
- Feature runbook: `governance/runbooks/features/gps_failure_behavior/`
