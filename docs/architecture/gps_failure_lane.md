# GPS Failure Lane

The GPS failure lane deliberately degrades or corrupts the simulated GPS signal
on a Mini Talon ArduPlane SITL + Gazebo stack, then records what the aircraft —
and the EKF underneath it — does. The goal is **behavior characterization** —
not safety certification and not recovery-controller design.

This is the third `test_suite` plugin family, after the CTE wind-matrix lane
(Lane 1) and the airspeed failure lane (Lane 2). The airspeed plugin is the
structural template for this lane.

GPS is the maximally different sensor at the fusion level: airspeed corrupts a
control *input*, while GPS corrupts the vehicle's *belief about where it is*,
which the EKF actively accepts or rejects through its own innovation gate. That
gate makes GPS the sharpest available "knee" experiment.

Current status:

- The corrected protected nominal root
  `var/runs/gps_failure_behavior_20260714T120212630044Z/` completed reviewed raw
  validation on 2026-07-14: east-facing launch, immutable first seq-4 anchor,
  continued flight through seq 9, planned RTL stabilization, accepted
  source/BIN/behavior analysis, and clean cleanup. It is not curated evidence;
  Phase 2 and every fault case remain open.
- Review of that nominal's pre-trigger path found the calm-lane aircraft
  completed its 100 m climb around 323 m East, beyond the copied 300 m settle
  waypoint. Mission v3 therefore uses a 500 m settle and shifts the paired far
  endpoints to 1300 m, preserving both 800 m legs and the seq-4 trigger. This
  geometry was raw-validated at
  `var/runs/gps_failure_behavior_20260714T122459635208Z/`: the aircraft flew
  monotonically East from takeoff completion to seq 3 with maximum absolute
  roll of 2.1 degrees, then completed through seq 9 and planned RTL. Fault cases
  and curated evidence remain open.
- The active v6 geometry is the shorter final-science candidate authorized on
  2026-07-16: a one-way 100 m AGL mission with a 1000 m controlled baseline,
  seq-4 injection onto a 6000 m straight fault-observation leg, 1000 m
  straight recovery/continuation, a 30 s terminal loiter, a seq-8 terminal gate,
  and seq-9 RTL. The seq-4 trigger, front-half seq-1/3 evidence, and planned RTL
  terminal contract are unchanged. V6 is structurally tested only; no live
  validation, curated evidence, or final science campaign claim exists yet.
- A 2026-07-16 Phase H no-live readiness update gates the next live validation
  rerun behind explicit Phase A-G proof: vehicle-time scheduling, BIN stimulus
  fidelity, three-verdict manifest semantics, lifecycle-window artifact
  authority, hard-denial transient visibility, source-proof labels, and
  altitude/attitude source authority. The protected validation rerun is exactly
  `nominal`, `slow_drift_0p5_mps`, and `hard_denial_15s`, one physical run each,
  zero automatic retries, and strict stop-on-failure. It does not authorize the
  full science campaign.
- A 2026-07-16 no-live scheduling correction makes physical GPS slow-drift
  strength vehicle-time based. Live GLTCH ramp updates use MAVLink
  `time_boot_ms` elapsed from the seq-4 trigger; monitor wall time remains only
  for deadlines, progress logs, and diagnostics. Attempt artifacts persist both
  `wall_elapsed_s` and `vehicle_elapsed_s` plus the payload clock source, and
  missing vehicle time fails closed for physical writes.
- A 2026-07-16 no-live stimulus-fidelity contract adds
  `stimulus_fidelity.json` and `stimulus_fidelity_status`. The post-cleanup BIN
  pass now checks nominal no-fault preservation, slow-drift realized GLTCH
  slope, and hard-denial disable/degrade/restore/recover timing separately from
  behavior classification. Missing or unanchored BIN evidence fails closed. No
  live result or historical campaign final-science claim is made by this
  implementation.
- A 2026-07-16 no-live lifecycle-window contract adds required
  `gps_lifecycle_windows.json` for live/post-cleanup analyzed attempts. It is
  the evidence authority for the ordered sequence: pre-trigger baseline,
  trigger, injection, fault-active, EKF response, recovery/continuation, and
  terminal state. Each window carries timing, source, status, metrics, and
  evidence references; missing anchors, baseline proof, BIN fault evidence, EKF
  response, cleanup, raw-BIN archival, or required artifacts fail closed.
- A 2026-07-16 no-live hard-denial transient visibility update adds a top-level
  `hard_denial_transient` section to the lifecycle artifact and final behavior
  summary. Reviewers can see denial start/end, restore, GPS quality
  before/during/after, reset times/offsets, the full post-trigger max
  truth-vs-belief gap, and the active post-reset gap summary without drilling
  into nested decoded records. Reset-segmented active samples remain the
  classifier input; the full-window summary is additive.
- A 2026-07-16 no-live three-verdict contract separates
  `workflow_status`, `stimulus_fidelity_status`, and `behavior_status`, with
  distinct `accepted_observation` and `accepted_repetition` fields. GPS generic
  manifest views preserve the distinction: bad-dose behavior observations do
  not count as accepted requested-recipe repetitions.
- A 2026-07-16 no-live source-contract reframing makes proof levels explicit in
  `source_contract.json` and BIN mechanism output. `exact_internal_proof`
  remains false because `PV_AidingMode == AID_ABSOLUTE` is not directly logged;
  EK3 source/knee readbacks are configuration proof, XKF4/GPS decoded rows are
  BIN-observable context, and the pre-injection live source gate is labeled as
  `validated_proxy_proof`.
- A 2026-07-16 no-live altitude/attitude envelope authority update makes
  `attitude_altitude_envelope.json` label its `source`, `altitude_source`,
  `attitude_source`, sampling limits, and evidence quality. Live telemetry is
  retained as a pre-cleanup runtime guard; post-cleanup artifacts prefer
  BIN-derived `POS.RelHomeAlt` or `CTUN.Alt` achieved altitude and `ATT`
  attitude for final evidence. `POS.Alt` absolute altitude and `CTUN.DAlt`
  desired altitude are not accepted as achieved/relative envelope sources. If
  BIN and live guard values disagree beyond tolerance, or if final envelope
  sources are missing, behavior review fails closed instead of silently choosing
  either source.

- Phase 1 no-SITL foundation accepted 2026-07-13. Two nominal smoke attempts on
  2026-07-14 are rejected. Attempt 1 exposed weak readiness and incomplete
  cleanup/terminal proof. Attempt 2 reached verified mission upload, arming, and
  AUTO, then stopped before the trigger because GPS incorrectly ACK-gated an
  event-driven `STATUSTEXT` interval request; cleanup matched `mavproxy` but not
  the real `mavproxy.py` name. GPS now owns its stream, readiness,
  mission-protocol, and process-cleanup implementations, gates on telemetry
  actually observed, and adds the canonical `.py` matcher. A structural test
  forbids imports from sibling plugins. A later unaccepted diagnostic showed
  real `MISSION_CURRENT` progress `0 -> 1 -> 3 -> 4`; seq 2 is the verified
  `DO_CHANGE_SPEED` mission item and is not necessarily emitted. The amended
  trigger therefore requires navigation seqs 1 and 3 and permits optional seq
  2 before the first seq-4 edge. These earlier fixes were later exercised by
  the corrected protected nominal, while Phase 2 remains open.
- A governed nominal attempt on 2026-07-14 subsequently proved the GPS-owned
  readiness, mission, telemetry, and cleanup paths, but was interrupted and is
  not accepted. It exposed one more trigger issue: leading home-row seq 0 was
  stored as evidence and poisoned the later valid `1 -> 3 -> 4` progression.
  The monitor now ignores seq 0 only before evidence starts and rejects any
  later regression to 0. Phase 2 remains open.
- Phase 0 (design lock): accepted 2026-07-06.
- Phase 1 Chunks 1–2 no-SITL foundation: plugin skeleton, deterministic case
  catalog, payload conversion/previews, dry-run CLI, registry entry, and unit
  tests exist.
- Phase 1 Chunk 3 is implemented pending review: the locked airspeed-style
  smoke mission geometry, dedicated GPS parameter overlay,
  default-stack integration, and static/no-SITL contract tests exist.
- Phase 1 Chunk 4 is implemented pending review: a synthetic no-SITL mechanism
  gate evaluates decoded EKF-like records at the locked `posTestRatio >= 1.0`
  boundary, with reset evidence distinct from simple rejection.
- Phase 1 Chunk 5 is implemented pending review: a no-SITL runtime/MAVLink
  contract layer builds live injection plans from trigger metadata and verifies
  parameter write/readback behavior with fake connections.
- Phase 1 Chunk 6 is implemented pending review: the lane is wired into the
  shared suite path, with a `--preflight` integration-readiness report that
  reports the SuiteRunner seams, manifest/artifact contract, parameter stack,
  and explicit live blockers (`ready_for_live_run=false`).
- A 2026-07-13 strict-review pass resolved six confirmed Phase-1 BLOCKERs
  (no-SITL): trigger-gated executable injection plans (preview stays
  non-executable), substantive behavior evidence in the classifier,
  contradiction-safe manifest acceptance, the complete artifact schema including
  `gps_injection.json`, and atomic MAVLink batch prevalidation. See the feature
  runbook's `review.md`.
- Also on 2026-07-13, dedicated launch identities `plane-gps` /
  `gazebo-plane-gps` were added to replace the earlier
  incorrect use of the CTE/airspeed targets, which loaded the airspeed overlay
  and the local override. See the Launch Identities section below and ADR-0021's
  amendment. Their corrected world/stack path later completed the protected
  nominal raw validation recorded above.
- Phase 1 no-SITL foundation is **Accepted** (2026-07-13, final no-SITL review):
  all prior BLOCKER/HIGH/MEDIUM findings are resolved and verified in code, and
  the final review found no new BLOCKER/HIGH/MEDIUM/substantiated-LOW issue. This
  is a no-SITL acceptance of the plugin foundation only. The later protected
  nominal raw validation is separate and has not been promoted as curated
  Phase-2 evidence.
- Phase 2 implementation code includes live telemetry/source-contract helpers,
  explicit connection/launch/
  mission adapters, production mission-adapter installation from the MAVLink
  master, source-contract-gated monitor acceptance, cleanup wait/kill behavior,
  protected smoke-case planning, protected round-robin campaign automation,
  decoded-record BIN analysis helpers, and a required lifecycle-window artifact
  that makes the ordered evidence sequence authoritative. Hard-denial lifecycle
  artifacts also expose full-window transient/reset visibility separately from
  active post-reset classification samples. The source contract now validates
  pre-injection EKF/GPS aiding flags as validated proxy proof and records
  post-fault flags as behavior context; it does not claim exact internal EKF
  aiding proof. The corrected nominal exercised the live path before this
  campaign command existed; fault cases and Phase-2 acceptance remain open.
  `attitude_altitude_envelope.json` is an envelope guard artifact, not the main
  GPS behavior classifier: BIN-derived values are final evidence when complete,
  live telemetry is runtime guard/fallback context, and mismatches or missing
  sources block reviewability.
- A 2026-07-13 strict pre-smoke review rejected the first Phase 2 live path. Its
  findings are remediated in the working tree with no-live tests: launch cleanup
  is ordered before Gazebo, cleanup gates terminal success, trigger evidence is
  fresh and one-shot, all scheduled writes gate acceptance, behavior/BIN
  analysis is injection-window scoped, JSON is strict/atomic, and the CLI stops
  on the first non-success. A fresh strict no-live review on 2026-07-14 found no
  remaining BLOCKER or HIGH finding and accepted the exact corrected diff for
  the single nominal live smoke. No live result is claimed by that acceptance.
- The later raw nominal root
  `var/runs/gps_failure_behavior_live_nominal_codex_20260714T095246Z/`
  declared success, but strict review rejected the declaration: analysis ran
  before cleanup closed the BIN, the window used a mission-upload CMD row,
  decoded engineering units were scaled twice, and provenance/artifact
  contracts were incomplete. That rejected root remains historical; its
  correction was exercised by the later protected nominal.
- The next nominal root
  `var/runs/gps_failure_behavior_20260714T113259746238Z/` is also rejected.
  It exposed GPS-only lifecycle regressions: the base world spawned the aircraft
  north while the copied mission begins east; the monitor treated the 20 s
  minimum evidence window as the end of the experiment; repeated seq-4
  telemetry replaced the true first-edge BIN anchor; and acceptance did not
  require a terminal mission state. The working tree now uses a dedicated
  east-facing calm GPS world, continues through RTL plus 10 s stabilization,
  records reached-waypoint/RTL progress, anchors analysis to the immutable
  first trigger event, and rejects incomplete nominal attempts. These fixes are
  no-live tested and then exercised successfully by the corrected protected
  nominal above; the rejected run itself is not rehabilitated.

## The Knee

The central result is the **knee**: the boundary between the EKF fusing a
corrupted GPS fix and rejecting it, measured on two tiers.

- **Mechanism tier (primary):** the position innovation test ratio
  `posTestRatio`. Live, this is derived as validated proxy context from
  `EKF_STATUS_REPORT.pos_horiz_variance ** 2`; in BIN decoded `XKF4`, it is
  `SP ** 2` on the primary core selected by `PI` because pymavlink's DFReader
  has already applied the XKF4 format multiplier. The knee is
  `posTestRatio` crossing `1.0` — ArduPilot's own gate
  (`AP_NavEKF3_PosVelFusion.cpp`). Below `1.0` the fix is fused and the belief
  moves toward the drifting fix; at/above `1.0` the fix is rejected only when
  the validated source preconditions hold. BIN mechanism output labels
  `XKF4.PI`, `XKF4.SP`, `XKF4.GPS`, `XKF4.TS`, `XKF4.OFN/OFE`, and decoded
  `GPS.Status`/`GPS.NSats` as BIN-observable proof, not exact internal
  `PV_AidingMode` proof.
- **Behavior tier:** the believed-vs-truth horizontal position gap, attitude/
  altitude band, and mode/failsafe changes.

Accepted is not captured: an admitted fix can barely move the belief when the
Kalman gain is small; only sustained cumulative drift walks the belief off. The
truth-vs-belief gap is a mandatory logged field — it is the only signal that
reveals a lie the filter itself believes is fine.

## Fault Set

| Fault | Knob(s) | Real-world case |
| --- | --- | --- |
| `slow_drift` | `SIM_GPS1_GLTCH_{X,Y}` growing ramp; live strength uses vehicle `time_boot_ms` elapsed | GPS spoofing / slow position capture |
| `step_glitch` | `SIM_GPS1_GLTCH_{X,Y}` fixed offset | multipath jump / sudden position pop |
| `hard_denial` | `SIM_GPS1_ENABLE=0` | antenna/receiver loss, total denial |
| `jamming` | `SIM_GPS1_JAM=1` | RF jamming (blackout + chaotic garbage) |

`slow_drift` and `step_glitch` share the `GLTCH` knob; the only difference is
onset rate, which isolates onset rate as the single independent variable in the
knee experiment. Other `SIM_GPS1_*` knobs are documented-only (see the
excluded-knob table in the runbook's `design_research.md`).

## Behavior Vocabulary

Seven bands, ordered by how much the system reacts, **not by danger**:
`nominal`, `silent_drift`, `detected_rejected`, `reset_captured`,
`autopilot_contained`, `loss_of_control`, `pre_injection_failure` (discard).

Detection and danger are separate axes. `silent_drift` is behaviorally mild but
strategically the worst outcome: the autopilot flies the aircraft off course
while reporting healthy.

## Verdict Model

Characterize, not gate. A run is never PASS/FAIL. **Accepted** = measurement
validity only; **behavior class** = which band it landed in. The knee is the
result of the campaign, not a bar to clear. Measurement validity includes a
recorded terminal state; nominal additionally requires planned RTL completion.

## Launch Identities

The lane uses dedicated launch targets `plane-gps` and `gazebo-plane-gps`
(corrected 2026-07-13 from the CTE/airspeed targets, which load a different
parameter stack):

- `plane-gps` loads exactly `config/vehicles/plane_base.parm ->
  config/overlays/plane_gps.parm` — no airspeed overlay and no local plane
  override — wipes EEPROM, and emits `udp:127.0.0.1:14551`.
- `gazebo-plane-gps` uses the dedicated sensor-neutral world
  `assets/worlds/mini_talon_gps_runway.sdf` (GPS/NavSat, calm, no wind
  publisher, no airspeed sensor, no LiDAR bridge). Its east-facing pose matches
  the mission's first leg without changing the shared `gazebo-plane` world.

These targets are structurally implemented and have launched in rejected
diagnostic attempts; they are **not** live-smoke verified. See ADR-0021
(2026-07-13 amendment) and
`docs/operations/gps_failure_runbook.md`.

## Output Paths

- Raw runtime output: `var/runs/gps_failure_behavior_*/` (not in git).
- Curated evidence (Phase 4): `evidence/curated_logs/gps_failure_behavior_<date>/`.

## References

- Feature runbook: `governance/runbooks/features/gps_failure_behavior/`
- Decisions: `governance/decisions/ADR-0017`..`ADR-0021`
- Operations runbook: `docs/operations/gps_failure_runbook.md`
