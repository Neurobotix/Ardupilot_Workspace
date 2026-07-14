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

- Phase 1 no-SITL foundation accepted 2026-07-13; Phase 2 live smoke is next and
  remains unverified.
- Phase 0 (design lock): accepted 2026-07-06.
- Phase 1 Chunks 1–2 no-SITL foundation: plugin skeleton, deterministic case
  catalog, payload conversion/previews, dry-run CLI, registry entry, and unit
  tests exist.
- Phase 1 Chunk 3 is implemented pending review: the locked five-item,
  approximately 36 km one-way mission, dedicated GPS parameter overlay,
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
  `gazebo-plane-gps` were added (structural only) to replace the earlier
  incorrect use of the CTE/airspeed targets, which loaded the airspeed overlay
  and the local override. See the Launch Identities section below and ADR-0021's
  amendment. No live smoke of these targets has occurred.
- Phase 1 no-SITL foundation is **Accepted** (2026-07-13, final no-SITL review):
  all prior BLOCKER/HIGH/MEDIUM findings are resolved and verified in code, and
  the final review found no new BLOCKER/HIGH/MEDIUM/substantiated-LOW issue. This
  is a no-SITL acceptance of the plugin foundation only. Phase 2 live smoke is
  next and remains unverified: no live run or parameter readback has occurred;
  realized straight-leg duration, BIN/log analysis, and evidence claims remain
  open.
- Pre-smoke Phase 2 implementation code now exists for later authorized live
  smoke: live telemetry/source-contract helpers, explicit connection/launch/
  mission adapters, production mission-adapter installation from the MAVLink
  master, source-contract-gated monitor acceptance, cleanup wait/kill behavior,
  protected smoke-case planning, and decoded-record BIN analysis helpers. This
  is no-SITL implementation only and does not verify the dedicated targets or
  accept Phase 2.
- A 2026-07-13 strict pre-smoke review rejected the first Phase 2 live path. Its
  findings are remediated in the working tree with no-live tests: launch cleanup
  is ordered before Gazebo, cleanup gates terminal success, trigger evidence is
  fresh and one-shot, all scheduled writes gate acceptance, behavior/BIN
  analysis is injection-window scoped, JSON is strict/atomic, and the CLI stops
  on the first non-success. A fresh strict no-live review on 2026-07-14 found no
  remaining BLOCKER or HIGH finding and accepted the exact corrected diff for
  the single nominal live smoke. No live result is claimed by that acceptance.

## The Knee

The central result is the **knee**: the boundary between the EKF fusing a
corrupted GPS fix and rejecting it, measured on two tiers.

- **Mechanism tier (primary):** the position innovation test ratio
  `posTestRatio`. Live, this is derived as
  `EKF_STATUS_REPORT.pos_horiz_variance ** 2`; in BIN decoded `XKF4`, it is
  `(SP / 100.0) ** 2` on the primary core selected by `PI`. The knee is
  `posTestRatio` crossing `1.0` — ArduPilot's own gate
  (`AP_NavEKF3_PosVelFusion.cpp`). Below `1.0` the fix is fused and the belief
  moves toward the drifting fix; at/above `1.0` the fix is rejected only when
  the validated source preconditions hold.
- **Behavior tier:** the believed-vs-truth horizontal position gap, attitude/
  altitude band, and mode/failsafe changes.

Accepted is not captured: an admitted fix can barely move the belief when the
Kalman gain is small; only sustained cumulative drift walks the belief off. The
truth-vs-belief gap is a mandatory logged field — it is the only signal that
reveals a lie the filter itself believes is fine.

## Fault Set

| Fault | Knob(s) | Real-world case |
| --- | --- | --- |
| `slow_drift` | `SIM_GPS1_GLTCH_{X,Y}` growing ramp | GPS spoofing / slow position capture |
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
result of the campaign, not a bar to clear.

## Launch Identities

The lane uses dedicated launch targets `plane-gps` and `gazebo-plane-gps`
(corrected 2026-07-13 from the CTE/airspeed targets, which load a different
parameter stack):

- `plane-gps` loads exactly `config/vehicles/plane_base.parm ->
  config/overlays/plane_gps.parm` — no airspeed overlay and no local plane
  override — wipes EEPROM, and emits `udp:127.0.0.1:14551`.
- `gazebo-plane-gps` reuses the sensor-neutral base runway world
  `assets/worlds/mini_talon_runway.sdf` (GPS/NavSat, calm, no wind publisher, no
  airspeed sensor, no LiDAR bridge) as a dedicated identity, not an alias of
  `gazebo-plane`.

These targets are structurally implemented with no-SITL structural tests only;
they are **not** live-smoke verified. See ADR-0021 (2026-07-13 amendment) and
`docs/operations/gps_failure_runbook.md`.

## Output Paths

- Raw runtime output: `var/runs/gps_failure_behavior_*/` (not in git).
- Curated evidence (Phase 4): `evidence/curated_logs/gps_failure_behavior_<date>/`.

## References

- Feature runbook: `governance/runbooks/features/gps_failure_behavior/`
- Decisions: `governance/decisions/ADR-0017`..`ADR-0021`
- Operations runbook: `docs/operations/gps_failure_runbook.md`
