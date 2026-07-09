# ADR-0021: GPS Failure Parameter Overlay

Status: Proposed

Date: 2026-07-06

The GPS failure lane uses a new dedicated parameter overlay that pins the EKF
parameters governing the knee, rather than reusing the airspeed overlay.

Decision:

- Default param stack is `config/vehicles/plane_base.parm` (unchanged) plus a new
  `config/overlays/plane_gps.parm`. The airspeed overlay is not reused: verified
  against source, `plane_airspeed.parm` sets zero GPS/EKF params (it is entirely
  `ARSPD_*`/`AIRSPEED_*`/wind), and `plane_base.parm` sets none of the four knee
  params and no `EK3_SRC*`.
- The overlay is a first-class part of the experiment, not boilerplate:
  - Pin the four knee params (`EK3_POS_I_GATE`, `EK3_GLITCH_RAD`,
    `FS_EKF_THRESH`, `EK3_GPS_CHECK`) to explicit, documented values. This makes
    the knee reproducible and enables the secondary "loosen/tighten the gate,
    watch the knee move" axis. `EK3_POS_I_GATE` is in centi-sigma
    (`AP_NavEKF3_PosVelFusion.cpp:820`, the `0.01 *` multiplier), so it directly
    sets where `posTestRatio = 1.0` lands in metres of innovation, and therefore
    where the knee lands in m/s of drift.
  - Set `EK3_SRC*` so GPS is the EKF position source (base sets `AHRS_EKF_TYPE 3`
    / `EK3_ENABLE 1` but no `EK3_SRC*`), so the faults actually bite.
  - Calm wind (GPS does not use wind as a variable).
  - No `ARSPD_*`/`AIRSPEED_*` block — the airspeed sensor is not the subject.

Full reasoning and alternatives:
`governance/runbooks/features/gps_failure_behavior/design_adrs.md`
("ADR (Proposed): GPS Parameter Overlay").

Open validation (Phase 1/2): chosen pinned values for the four params; live
readback of all four in Phase 2 smoke.
