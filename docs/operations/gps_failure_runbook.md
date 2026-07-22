# GPS Failure Runbook

Status: Phase 0 (design lock) accepted 2026-07-06. Phase 1 no-SITL foundation
accepted 2026-07-13 (final no-SITL review). The corrected protected nominal
completed reviewed raw validation on 2026-07-14, and the corrected framework
was live-validated on the bounded v4 mission and the longer v5 validation
slice on 2026-07-16. Mission v6 is the active shorter final-science candidate;
it has no-live structural coverage only and has not been flown. No curated
Phase-2 evidence or fault-case result has been promoted, so Phase 2 remains
open. Live cases remain explicit operator actions behind confirmation guards.

## Current Contracts

- **Trigger (ADR-0020):** inject on the first `MISSION_CURRENT` `seq == 4`
  edge after fresh armed/AUTO navigation progress through seqs 1 and 3
  (seq 2 is `DO_CHANGE_SPEED` and is optional), first-edge latched, never
  re-fired. Leading home-row seq 0 is ignored only before evidence starts; a
  later regression to a lower seq invalidates the trace. A missed/late trigger
  is `pre_injection_failure`.
- **Physical scheduling:** live slow-drift GLTCH strength and bounded restore
  schedules are driven by MAVLink `time_boot_ms` vehicle elapsed time from the
  seq-4 trigger; monitor wall time is for deadlines/diagnostics only.
  `gps_injection.json` records `wall_elapsed_s`, `vehicle_elapsed_s`,
  `clock_ratio`, and the payload clock source. Missing or stale vehicle time
  fails physical scheduling closed.
- **Stimulus fidelity:** required `stimulus_fidelity.json` plus terminal
  `stimulus_fidelity_status`. Post-cleanup BIN analysis separately verifies the
  requested stimulus was physically realized (nominal no-fault preservation,
  slow-drift realized GLTCH slope, hard-denial disable/degrade/restore/recover
  timing). Missing, malformed, non-finite, or unanchored BIN evidence fails
  closed.
- **Lifecycle windows:** required `gps_lifecycle_windows.json` is the ordered
  evidence authority for `pre_trigger_baseline`, `trigger`, `injection`,
  `fault_active`, `ekf_response`, `recovery_or_continuation`, and `terminal`,
  each with timing, source, status, metrics, and evidence references. Missing
  anchors or evidence fail the artifact closed.
- **Hard-denial transient visibility:** lifecycle and final behavior-summary
  artifacts carry `hard_denial_transient` (denial/restore timing, GPS quality
  before/during/after, reset times/offsets, full post-trigger max
  truth-vs-belief gap, active post-reset gap summary). Reviewers should
  inspect both `full_window_gap_summary` and `active_segment_gap_summary`;
  missing reset details fail the section closed. Non-hard-denial cases report
  `not_applicable`.
- **Three-verdict manifest:** terminal rows persist `workflow_status`,
  `stimulus_fidelity_status`, and `behavior_status`, with distinct
  `accepted_observation` and `accepted_repetition`. A stimulus-failed attempt
  can remain a behavior observation when workflow and behavior evidence are
  complete, but it never counts as a requested-recipe repetition. Scheduler
  `accepted_count` counts accepted repetitions; the protected campaign path
  counts workflow-complete physical attempts.
- **Source proof levels:** `source_contract.json` labels
  `exact_internal_proof` (always false — `PV_AidingMode` is not directly
  logged), `bin_observable_proof` (decoded XKF4/GPS context), and
  `validated_proxy_proof` (the live pre-injection source gate). EK3 readbacks
  are configuration proof, not internal runtime proof.
- **Altitude/attitude envelope:** `attitude_altitude_envelope.json` declares
  `source`, `altitude_source`, `attitude_source`, sampling limits, and
  evidence quality. The live monitor writes a `runtime_guard` artifact before
  cleanup; the post-cleanup analyzer rewrites it from the attempt-local BIN
  (`POS.RelHomeAlt` or `CTUN.Alt` achieved altitude plus `ATT` attitude,
  `final_evidence_quality=true`). `POS.Alt` and `CTUN.DAlt` are not accepted
  envelope sources; BIN/live disagreement beyond tolerance fails the envelope.
  It can block reviewability but is not the behavior classifier.
- **Raw BIN archival:** live attempts archive the selected post-cleanup
  DataFlash BIN into the attempt directory as
  `<case>__rep_NN__attempt_NNN.BIN`, analyze that copy, and expose it as
  `raw_log` / `raw_log_path` in the terminal row. Campaign runs keep
  ArduPilot/MAVProxy byproducts in a campaign-local per-attempt working tree
  under `<campaign_root>/_sitl_state/<case_id>/attempt_NNN/`.
- **Cleanup:** per-attempt cleanup calls `scripts/ops/launch.sh cleanup`,
  records its structured result, then scans independently for surviving
  simulator processes (including the canonical `[m]avproxy.py` matcher). GPS
  owns its data-stream, readiness, mission-protocol, and cleanup helpers; a
  structural test forbids imports from sibling plugins.

## Validation History (condensed)

Full narratives: `.ai/current.md` and
`governance/runbooks/features/gps_failure_behavior/review.md`.

- 2026-07-14: two early nominal attempts rejected (weak readiness; wrongly
  ACK-gated `STATUSTEXT` stream request and `mavproxy.py` cleanup miss). A
  diagnostic proved `MISSION_CURRENT` progress `0 -> 1 -> 3 -> 4`, fixing the
  seq-2 trigger assumption. An interrupted governed attempt exposed the
  leading-seq-0 trigger poisoning, also fixed.
- 2026-07-14: `var/runs/gps_failure_behavior_live_nominal_codex_20260714T095246Z/`
  and `var/runs/gps_failure_behavior_20260714T113259746238Z/` declared success
  but were rejected by strict review (pre-cleanup BIN decode, CMD-row anchor,
  double-scaled decoded units; north spawn, minimum-window stop, repeated
  seq-4 anchor, no terminal acceptance). Both remain historical.
- 2026-07-14: the corrected protected nominal
  `var/runs/gps_failure_behavior_20260714T120212630044Z/` passed reviewed raw
  validation (first seq-4 boot anchor, full mission through seq 9, planned RTL
  + 10 s stabilization, accepted source/BIN/behavior analysis, clean cleanup).
  Mission v3 then removed the pre-injection turnback loop, raw-validated at
  `var/runs/gps_failure_behavior_20260714T122459635208Z/`.
- 2026-07-16: the corrected framework was live-validated on the bounded v4
  mission and the longer v5 validation slice. Mission v6 (1000 m baseline,
  seq-4 injection onto a 6000 m fault-observation leg, 1000 m recovery,
  30 s terminal loiter, seq-8 terminal gate, seq-9 RTL; active hash
  `ba22c669c895f694e8556e0e9573e9f9dd278d159086e46706eb30a3714d7261`) became
  the active shorter final-science candidate. V6 has not been flown.

## Static Default Stack

- SITL target: `plane-gps` (dedicated GPS failure identity)
- Gazebo target: `gazebo-plane-gps` (dedicated GPS failure identity)
- Mission: `assets/missions/gps_failure_behavior_mission.waypoints` (v6)
- Params: `config/vehicles/plane_base.parm` + `config/overlays/plane_gps.parm`
  in that order, with no airspeed overlay and no local plane override.

Mission v6 keeps ambiguous return-home turns out of the main observation
window and gives the lowest locked slow-drift rate (`0.2 m/s`) roughly 400 s
of straight-line exposure at the commanded 15 m/s speed.

The overlay pins the four EKF knee parameters, the complete primary EKF source
set, and calm SITL wind. These checked-in values provide reproducible static
inputs; they do not prove the empirical knee. Live readback is re-verified on
every live attempt.

### Dedicated launch identities

`plane-gps` and `gazebo-plane-gps` are **not** the CTE/airspeed targets:

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
  load the airspeed overlay and the local override. See ADR-0021 (2026-07-13
  amendment).

These targets are covered by structural tests and were exercised by the
governed raw validation runs above. No curated evidence has been promoted.

## CLI

- `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` provides the
  no-SITL actions `--list-cases`, `--dry-run --case <case_id>`,
  `--probe-schema`, `--preflight` (readiness report with the Phase A-G gates),
  and `--phase2-validation-rerun-plan` (plan-only). None of them start
  SITL/Gazebo or open MAVLink.
- Guarded live actions (never run without explicit operator authorization):
  - `--live-case <case> --confirm-live-phase2` runs one protected case.
  - `--live-phase2-validation-rerun --confirm-live-phase2
    --confirm-validation-rerun` runs the one-run-per-case protected
    validation rerun.
  - `--live-phase2-round-robin-campaign --confirm-live-phase2
    --confirm-live-campaign` runs the protected round-robin campaign.
- Dry-run `--preview-elapsed-s` remains a plan-only preview input. During live
  execution, slow-drift payloads and bounded restore schedules are driven by
  vehicle `time_boot_ms`; wall elapsed is diagnostic only.

Example no-SITL and guard checks (the `--live-case nominal` command without
confirmation must fail before launch):

```bash
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --list-cases
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --probe-schema
PYTHONPATH=src ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure --preflight
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
