# Vehicle Status

This page lists current vehicle and lane evidence. Do not promote a narrower
vehicle or lane claim beyond the evidence listed here without a dated report
under `evidence/reports/`.

Latest workspace-next runtime evidence:
`evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`,
`evidence/reports/migration/PHASE_7_REPROOF_2026-05-24.md`, and
`evidence/reports/migration/CUTOVER_2026-05-24.md`.

## Config Ownership

- Mini Talon base config is `config/vehicles/plane_base.parm`. It is
  sensor-neutral for enablement: the base keeps generic `AIRSPEED_*` defaults
  while airspeed sensor enablement, lane-specific/high-wind airspeed overrides,
  and LiDAR behavior are layered from `config/overlays/` or campaign-specific
  files.
- Copter frame defaults are `config/vehicles/copter_params.parm`.
- Rebuild uses standalone `config/vehicles/plane_params_rebuild.parm`.
- Integrated or altitude-wind lane files under `config/campaigns/` are shared
  campaign config, but current docs do not promote those non-core launch lanes
  beyond the evidence listed below.
- Local files under `.private/config/` may be appended by plane launchers, but
  they are not shared vehicle status or canonical config.

| Vehicle / lane | Current evidence | Blocked | Not yet tested |
| --- | --- | --- | --- |
| `iris` copter base | `copter` + `gazebo-copter` proved SITL/Gazebo/MAVLink handshake; armed and reached 10.0 m (2026-05-20). | No | No |
| `iris_with_lidar` | `copter-lidar` + `gazebo-copter-lidar` + `bridge-copter` proved SITL/Gazebo/MAVLink handshake; armed, flew to 4.04 m, bridge streamed 922 DISTANCE_SENSOR messages (2026-05-21). LiDAR obstacle return not captured. | No | No |
| `mini_talon` plane base | `plane` + `gazebo-plane` proved SITL/Gazebo/MAVLink handshake; armed, 17.3 m/s (2026-05-20). | No | No |
| `mini_talon_with_lidar` | `plane-lidar` + `gazebo-plane-lidar` + `bridge-plane` proved end-to-end LiDAR; flew to 52.5 m (2026-05-20). | No | No |
| `mini_talon` CTE lane | `plane-cte` + `gazebo-plane-cte` proved SITL/Gazebo/MAVLink handshake; flew to 46.9 m (2026-05-20). | No | No |
| Airspeed/LiDAR integrated lane | No runtime evidence promoted. | No | Yes |
| Altitude-driven wind lane | No runtime evidence promoted. | No | Yes |
| Rebuild lane | No runtime evidence promoted. | No | Yes |

Verified statuses above are backed by
`evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`, the per-target
curated captures in `evidence/curated_logs/phase_2_runtime_2026-05-20/`, and
the representative Phase 7 proof accepted in
`evidence/reports/migration/CUTOVER_2026-05-24.md`.
