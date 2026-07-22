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

## Amendment 2026-07-13: Dedicated GPS launch identities

Status: Proposed (extends the original 2026-07-06 decision; not a live claim)

The original decision rejected the airspeed overlay for GPS but did not name a
launch target. Before this amendment the GPS design pointed operators and the
plugin defaults at `plane-cte` / `gazebo-plane-cte`. That is unsafe: the shell
target `plane-cte` is the CTE/airspeed lane and loads a different parameter
stack than this overlay contract:

```text
plane-cte:  plane_base.parm -> plane_airspeed.parm -> .private/config/plane_params.local.parm (when present)
```

So an operator running the documented target would silently launch the airspeed
overlay (rejected above) plus an uncontrolled local override, not the governed
GPS stack.

Decision (execution-path correction):

- Add dedicated launch identities `plane-gps` and `gazebo-plane-gps`; the GPS
  design, plugin defaults, docs, and future plugin-owned launcher use these and
  never `plane-cte`.
- `plane-gps` loads exactly this stack, in order, and nothing else:

  ```text
  plane-gps:  config/vehicles/plane_base.parm -> config/overlays/plane_gps.parm
  ```

  No airspeed overlay. No LiDAR overlay. No campaign airspeed files. The local
  plane override `.private/config/plane_params.local.parm` is excluded
  unconditionally (it is never appended), because it could silently perturb the
  four governed knee params. The launcher prints the effective stack and prints
  that the local override was intentionally excluded. The lane wipes EEPROM for
  clean per-attempt state and emits the governed local output
  `udp:127.0.0.1:14551`; GPS campaign runs place SITL/MAVProxy state under the
  campaign root at `<campaign_root>/_sitl_state/<case_id>/attempt_NNN/`.
- The launcher uses a dedicated `build_plane_gps_param_args()` helper rather
  than the shared `build_plane_param_args()` (which always appends the local
  override), so no existing target's historical override behavior changes.
- `gazebo-plane-gps` uses the dedicated
  `assets/worlds/mini_talon_gps_runway.sdf`. It retains the sensor-neutral base
  Mini Talon, JSON FDM, NavSat/GPS, and calm/no-wind/no-airspeed/no-LiDAR
  contract while owning the spawn orientation required by the GPS mission.
  The shared `gazebo-plane` world remains unchanged.

This execution-path decision is not itself a live claim. Rejected diagnostics
later exercised the targets and parameter readback, but no accepted complete
nominal result or evidence claim exists. Phase 2 smoke must accept the realized
stack and full terminal path before any live GPS matrix.

Amendment (2026-07-14, spawn-frame correction): the rejected nominal root
`var/runs/gps_failure_behavior_20260714T113259746238Z/` showed that reusing
`mini_talon_runway.sdf` violated the mission-frame contract: the aircraft began
approximately north while the copied behavior mission begins east. The GPS
target therefore owns `mini_talon_gps_runway.sdf`, whose model pose matches the
proven east-facing behavior-mission frame. The attempt provenance hashes this
world. This is a no-live structural correction; a fresh run must verify the
realized heading.
