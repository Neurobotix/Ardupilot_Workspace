# ADR-0018: GPS Failure Two-Tier Knee And Behavior Classification

Status: Proposed

Date: 2026-07-06

The GPS failure lane defines its central result — the knee between the EKF
fusing a corrupted fix and rejecting it — on a measured signal, classifies
observed behavior into named bands, and characterizes rather than gates.

Decision:

- Two tiers.
  - Mechanism tier (primary knee signal): the position innovation test ratio
    `posTestRatio`. Live telemetry derives it as
    `EKF_STATUS_REPORT.pos_horiz_variance ** 2`; decoded BIN analysis derives it
    from the selected primary core's already-scaled `XKF4.SP` as `SP ** 2`, with
    `XKF4.PI` required to identify that primary core. The knee is
    `posTestRatio` crossing `1.0`, which is ArduPilot's own gate
    (`AP_NavEKF3_PosVelFusion.cpp:824`). Below `1.0` the fix is fused and the
    belief moves toward the drifting fix; at/above `1.0` the fix is rejected
    (not fused), and the belief only moves later via `ResetPosition` when
    variance exceeds `EK3_GLITCH_RAD²` or on `posTimeout`.
  - Behavior tier: the believed-vs-truth horizontal position gap, attitude/
    altitude band, and mode/failsafe changes.
- Accepted is not captured: an admitted fix (`posTestRatio < 1`) can barely move
  the belief when the Kalman gain is small; only sustained cumulative drift walks
  the belief off. The mechanism tier defines the knee; the behavior tier proves
  it matters. The truth-vs-belief gap is a mandatory logged field because it is
  the only signal that reveals a lie the filter believes is fine.
- Seven behavior bands, ordered by reaction (not danger): `nominal`,
  `silent_drift`, `detected_rejected`, `reset_captured`, `autopilot_contained`,
  `loss_of_control`, `pre_injection_failure` (discard). Detection and danger are
  separate axes; `silent_drift` is behaviorally mild but the worst outcome. No
  single field names `silent_drift` — it is the conjunction fused AND
  gap-growing AND no-failsafe.
- Verdict model: characterize, not gate. A run is never PASS/FAIL. Accepted =
  measurement validity only (fault injected + read back, enough post-injection
  flight, required fields present, valid terminal evidence; nominal additionally
  requires planned mission completion); Behavior class = which band it landed in. The
  `silent_drift` vs `detected_rejected` boundary (the knee) is the result of the
  campaign, not a bar to clear.

Full derivation (verbatim EKF source), per-band raw signals, and alternatives:
`governance/runbooks/features/gps_failure_behavior/design_adrs.md`
("ADR (Proposed): Two-Tier Knee And Behavior Classification") and
`design_research.md`.

Open validation (Phase 2 smoke): live `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`,
`FS_EKF_THRESH`, `EK3_GPS_CHECK`, and `EK3_SRC1_*`; require
the exact checked-in knee values and complete source contract
(`POSXY=3`, `VELXY=3`, `POSZ=1`, `VELZ=3`, `YAW=1`), with every source enum
integral, plus EKF absolute-position status flags as the validated GPS-aiding
proxy; baseline `posTestRatio` and gap ranges from the `nominal` control.
