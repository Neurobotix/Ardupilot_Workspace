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
instead of waiting for the 900 s timeout; its terminal row is `interrupted` and
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

Mission v4 keeps the validated 500 m settle while extending both measurement
legs to 2000 m and widening their separation to 500 m. It preserves seq-4
injection and seq-9 RTL. The active hash is
`8d1c8de43c6e496946b1f6bdf3d88f4aa14cd3ba7abe84067cb6a4edd27d7f35`;
v4 has no-live geometry coverage but no live result yet.

On 2026-07-15, the working tree added a guarded protected round-robin live
campaign entry point and no-live tests for the workflow/analysis separation:
campaign counting now uses workflow-complete physical attempts, while behavior
acceptance remains a separate post-cleanup analysis result. The source contract
also now validates pre-injection EKF/GPS aiding flags and records post-fault
flags as behavior context. This is no-live implementation evidence only; no
new live campaign result is claimed.

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
  manifest row. Older raw roots may still reference the shared
  `var/runs/sitl/plane-gps/logs/` source path.
- The guarded live path now constructs mission control from the live MAVLink
  master and gates mechanism acceptance on the EKF/GPS source contract, but
  those paths remain no-SITL/fake tested only until authorized smoke.
- Pre-smoke hardening now waits for the Plane target's cleanup barrier before
  starting Gazebo, requires fresh heartbeat/SIMSTATE trigger evidence, latches
  one injection attempt, gates on every write/restore and verified cleanup,
  scopes behavior/BIN analysis to the injection window, and makes the CLI stop
  on the first non-accepted terminal record. These are no-live implementation
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
  writes `campaign_contract.json`, runs true round robin, defaults to five
  workflow-complete physical attempts per case, uses zero automatic retries,
  stops on workflow/cleanup/raw-log failure, and does not let analysis rejection
  erase or consume the workflow attempt.

## Static Default Stack

- SITL target: `plane-gps` (dedicated GPS failure identity)
- Gazebo target: `gazebo-plane-gps` (dedicated GPS failure identity)
- Mission: `assets/missions/gps_failure_behavior_mission.waypoints`
- Params: `config/vehicles/plane_base.parm` + `config/overlays/plane_gps.parm`
  in that order, with no airspeed overlay and no local plane override.

Mission v4 uses a 500 m calm-lane settle and 500→2500 m outbound measurement
leg, avoiding the v2 takeoff turnback while providing 2000 m outbound and
reciprocal legs separated by 500 m.

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
  unconditionally and the launcher prints that exclusion). It wipes EEPROM, uses
  `var/runs/sitl/plane-gps` and a `plane-gps` MAVProxy identity, and emits
  `udp:127.0.0.1:14551`.
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
- A guarded protected round-robin campaign runner exists for the same protected
  case set only: `--live-phase2-round-robin-campaign --confirm-live-phase2
  --confirm-live-campaign`. It is the operator path for five workflow-complete
  physical runs per protected case.
- `--phase2-smoke-plan` is plan-only and does not start SITL/Gazebo or open
  MAVLink.

Example no-SITL and guard checks (the `--live-case nominal` command without
confirmation must fail before launch):

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --list-cases
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --probe-schema
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --preflight
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --phase2-smoke-plan
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
absolute-position status flags as the validated GPS-aiding proxy, and confirm
the exact checked-in source set (`3/3/1/3/1`) and knee values plus the
straight-leg duration. Trigger authorization additionally requires fresh,
co-temporal heartbeat and SIMSTATE evidence; cleanup, all scheduled operations,
and a workflow-complete terminal record must succeed. Behavior acceptance is
recorded separately by post-cleanup analysis and does not make a dirty workflow
valid. See
`governance/runbooks/features/gps_failure_behavior/plan.md`.

Before another nominal smoke, review both post-rejection remediation diffs and
its focused Pyright/unit results. A previous live confirmation does not carry
forward: a new live attempt still requires explicit operator authorization.

Protected Phase 2 smoke implementation slice:

- `nominal`
- `slow_drift_0p5_mps`
- `hard_denial_15s`

Run only the protected 15-second hard-denial case from the workspace root:

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --live-case hard_denial_15s --confirm-live-phase2 --mission-timeout 900 --campaign-root "$(pwd)/var/runs/gps_failure_behavior_hard_denial_15s_$(date -u +%Y%m%dT%H%M%SZ)"
```

Run the first protected five-run round-robin campaign from the workspace root
only after explicit live campaign authorization:

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --live-phase2-round-robin-campaign --confirm-live-phase2 --confirm-live-campaign --campaign-cases nominal,slow_drift_0p5_mps,hard_denial_15s --runs-per-case 5 --mission-timeout 900 --campaign-root "$(pwd)/var/runs/gps_failure_behavior_phase2_protected_rr_$(date -u +%Y%m%dT%H%M%SZ)"
```

The full Phase 3 matrix remains gated; do not infer that `--phase2-smoke-plan`
or the protected Phase 2 live/campaign flags authorize the full v1 GPS catalog.

## References

- Lane description: `docs/architecture/gps_failure_lane.md`
- Feature runbook: `governance/runbooks/features/gps_failure_behavior/`
