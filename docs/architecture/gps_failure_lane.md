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

## Current Status

- Phase 0 (design lock) accepted 2026-07-06; Phase 1 no-SITL foundation
  accepted 2026-07-13 (final no-SITL review; all prior BLOCKER/HIGH/MEDIUM
  findings resolved and verified in code).
- The corrected protected nominal completed reviewed raw validation on
  2026-07-14 (`var/runs/gps_failure_behavior_20260714T120212630044Z/`), and
  the corrected framework was live-validated on the bounded v4 mission and the
  longer v5 validation slice on 2026-07-16. Earlier 2026-07-14 attempts remain
  rejected historical roots; the fixes they forced (GPS-owned readiness,
  stream, mission-protocol and cleanup helpers, seq-0/seq-2 trigger
  corrections, immutable first-edge BIN anchoring, terminal mission
  acceptance) are all in the current code. The condensed history lives in
  `docs/operations/gps_failure_runbook.md`; full narratives are in
  `.ai/current.md` and the feature runbook.
- The active mission is v6, the shorter final-science candidate authorized
  2026-07-16: 1000 m controlled baseline, seq-4 injection onto a 6000 m
  straight fault-observation leg, 1000 m straight recovery/continuation, 30 s
  terminal loiter, seq-8 terminal gate, seq-9 RTL. The seq-4 trigger,
  front-half seq-1/3 evidence, and planned-RTL terminal contract are
  unchanged. V6 is structurally tested only; it has not been flown, and no
  curated evidence or final science campaign claim exists.
- The next live action is gated: `--preflight` reports the Phase A-G no-live
  gates (vehicle-time scheduling, BIN stimulus fidelity, three-verdict
  manifest semantics, lifecycle-window artifact authority, hard-denial
  transient visibility, source-proof labels, altitude/attitude source
  authority) and `ready_for_live_run` is true only when every gate has
  explicit proof. The protected validation rerun is exactly `nominal`,
  `slow_drift_0p5_mps`, and `hard_denial_15s`, one physical run each, zero
  automatic retries, strict stop-on-failure. It does not authorize the full
  science campaign.

## Evidence Contracts

- **Vehicle-time scheduling:** physical slow-drift strength and bounded
  restore schedules use MAVLink `time_boot_ms` elapsed from the seq-4 trigger;
  wall time is diagnostic only, and missing vehicle time fails physical writes
  closed. Attempt artifacts persist both `wall_elapsed_s` and
  `vehicle_elapsed_s` plus the payload clock source.
- **Stimulus fidelity:** required `stimulus_fidelity.json` +
  `stimulus_fidelity_status` verify the requested dose was physically realized,
  separately from behavior classification; missing or unanchored BIN evidence
  fails closed.
- **Lifecycle windows:** required `gps_lifecycle_windows.json` is the ordered
  evidence authority (pre-trigger baseline, trigger, injection, fault-active,
  EKF response, recovery/continuation, terminal), each window carrying timing,
  source, status, metrics, and evidence references.
- **Hard-denial transient visibility:** a top-level `hard_denial_transient`
  section exposes denial/restore timing, GPS quality before/during/after,
  reset times/offsets, the full post-trigger max truth-vs-belief gap, and the
  active post-reset gap summary. Reset-segmented active samples remain the
  classifier input; the full-window summary is additive.
- **Three-verdict manifest:** `workflow_status`, `stimulus_fidelity_status`,
  and `behavior_status` are separate, with distinct `accepted_observation` and
  `accepted_repetition`. Bad-dose behavior observations never count as
  accepted requested-recipe repetitions.
- **Source proof levels:** `exact_internal_proof` stays false because
  `PV_AidingMode == AID_ABSOLUTE` is not directly logged; EK3 readbacks are
  configuration proof, decoded XKF4/GPS rows are BIN-observable context, and
  the pre-injection live source gate is `validated_proxy_proof`.
- **Altitude/attitude envelope:** `attitude_altitude_envelope.json` labels its
  source authority. Live telemetry is the pre-cleanup runtime guard;
  post-cleanup artifacts prefer BIN-derived `POS.RelHomeAlt` or `CTUN.Alt`
  achieved altitude and `ATT` attitude. `POS.Alt` and `CTUN.DAlt` are not
  accepted; BIN/live disagreement or missing final sources fails closed. The
  envelope can block reviewability but is not the behavior classifier.

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
excluded-knob table in the runbook's `design_research.md`). Jamming cases are
part of the designed v1 catalog but are outside the protected Phase-2 case set
and the non-jamming campaign allowlist.

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
An accepted repetition additionally requires stimulus fidelity to pass.

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

These targets are covered by structural tests and were exercised by the
governed raw validation runs; no curated Phase-2 evidence has been promoted.
See ADR-0021 (2026-07-13 amendment) and
`docs/operations/gps_failure_runbook.md`.

## Output Paths

- Raw runtime output: `var/runs/gps_failure_behavior_*/` (not in git).
- Curated evidence (Phase 4): `evidence/curated_logs/gps_failure_behavior_<date>/`.

## References

- Feature runbook: `governance/runbooks/features/gps_failure_behavior/`
- Decisions: `governance/decisions/ADR-0017`..`ADR-0021`
- Operations runbook: `docs/operations/gps_failure_runbook.md`
