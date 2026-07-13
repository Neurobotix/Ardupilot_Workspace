# Parameter And Config Index

Last updated: 2026-07-13

Scope: Phase 4 classification of shared runtime parameter files, archives,
local-only overlays, and recovered historical parameter evidence.

## Ownership Rules

- Shared canonical config belongs under `config/`.
- `config/vehicles/` owns vehicle bases and standalone lane stacks.
- `config/overlays/` owns files layered after a base vehicle config.
- `config/campaigns/` owns shared campaign or integrated-lane config.
- `config/archive/` is retained comparison material, not current launcher input.
- `.private/config/*.local.parm` is optional local overlay space only.
- `evidence/curated_logs/recovered_param_stacks/` stores recovered historical
  stacks for provenance and comparison, not runtime defaults.

Phase 8 retired the old root compatibility symlink bridge from active runtime
path resolution. Launch and campaign callers now resolve shared files directly
through the canonical `config/` owners named below, while retained
compatibility runners and wrappers still govern some command surfaces.

## Indexed Files

| Path | Role | Category | Shared canonical config | SHA-256 | Known runtime stack membership |
| --- | --- | --- | --- | --- | --- |
| `config/vehicles/plane_base.parm` | Sensor-neutral Mini Talon base with generic `AIRSPEED_*` defaults. | vehicle base | yes | `410226094248709c7660ee51517b07a9077314d1d15a774b8453794c343c09c4` | First file for `plane`, `plane-cte` / `plane-airspeed`, `plane-gps`, `plane-lidar`, `plane-staircase`, `plane-airspeed-lidar`, `plane-altitude-wind`, the `gps_failure` lane, and current CTE campaign callers. |
| `config/vehicles/copter_params.parm` | Iris frame and Copter SITL defaults. | vehicle base | yes | `fd12b0f6398de5438a1b0d3f2638c5f1b9e682bb672a03ea81fc4d005fe38579` | `copter` and `copter-lidar`; launcher loads with `--wipe-eeprom`. |
| `config/vehicles/plane_params_rebuild.parm` | Standalone rebuild stack. | vehicle base | yes | `c5d38923b87daed0cb495d85c72ce8023721e089313ed5d44f1ad7375b2ece3e` | `plane-rebuild` only; do not stack with `plane_base.parm` or local plane override. |
| `config/overlays/plane_airspeed.parm` | Default Gazebo airspeed overlay; production-like conservative 14/10/22 envelope. | overlay | yes | `154bf537b26c6018e55a8a0e8c0c0d2ca2103e7d91931c923db478f0622c6159` | After `plane_base.parm` for `plane-cte` / `plane-airspeed` and current CTE/wind-matrix campaign callers. |
| `config/overlays/plane_gps.parm` | GPS failure overlay pinning four EKF knee inputs, the complete primary EKF source set, and calm SITL wind; contains no airspeed tuning. | overlay | yes | `f8e4303e1a3e2f9a0b0f013300a4e0cd7334576a407ce0cdb6f1e1826545c70c` | Follows `plane_base.parm` for the `plane-gps` launch target and the `gps_failure` lane; the launcher excludes the local override. Static/no-SITL integration exists; no live readback has occurred. |
| `config/overlays/plane_airspeed_cte_high_wind_aggressive.parm` | Deliberately named aggressive high-wind CTE stress overlay (28/18/38). NOT the default airspeed overlay. | overlay | yes | `5fd76251d9d0a4738fec6b57365357200f030604588c1602d22bae0e750c8f95` | None by default; not wired into any launch target or campaign default. Stress experiments only, named explicitly. |
| `config/overlays/plane_lidar.parm` | MAVLink bridge-backed downward rangefinder overlay. | overlay | yes | `5837ebe4c1e7e23ee7d0343de2318a2044f924ea4f8d5f22d05b01582f77210b` | After `plane_base.parm` for `plane-lidar`; also before staircase nav overlay for `plane-staircase`. |
| `config/overlays/staircase_plane_params.parm` | Tight nav overlay for staircase LiDAR mission. | overlay | yes | `1b045dde27f2fae2dffbeeedaa695e2b8246a0b11a3397ffe7b6ef0f8acd24a1` | Final shared overlay for `plane-staircase` before any optional local plane override. |
| `config/campaigns/mini_talon_airspeed_lidar/plane_full.parm` | Shared integrated airspeed + LiDAR lane parameters. | campaign | yes | `32f38f58cd90dc8bd5522612a92eec747a90326108fa2d9ddc05635dca9a8b33` | After `plane_base.parm` for `plane-airspeed-lidar`. |
| `config/campaigns/mini_talon_altitude_wind/plane_full.parm` | Shared altitude-wind lane overlay. | campaign | yes | `0ff9bc7610a9beb9d29bc2256abd79a8e34c2c6a09554558a37d9a1d6681fe87` | After `plane_base.parm` for `plane-altitude-wind`. |
| `config/campaigns/airspeed_failure_tailwind_counterparts.json` | No-SITL recipe for the operator-approved 17 deduplicated tailwind counterpart attempts and historical-root provenance. | campaign recipe | yes | `93010d6803525d7d31e9dabd07a218b82259b8396199657626486ee81535a9ef` | Planning/configuration input only; does not launch a campaign. |
| `config/archive/plane_all_in_one_legacy.parm` | Superseded mixed plane snapshot. | archive | no | n/a | None; comparison only. |
| `config/archive/plane_benchmark_dualwind_legacy.parm` | Superseded benchmark snapshot with dual-wind behavior. | archive | no | n/a | None; comparison only. |
| `.private/config/plane_params.local.parm` | Local plane final overlay observed on this machine. | local-only override | no | n/a | Appended by most compatibility plane lanes and current CTE campaign callers when present; skipped by `plane-rebuild`. |
| `evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/src/SIM_ARD_GAW/config/plane_base.parm` | Recovered production-era base evidence. | historical evidence | no | `bbeab1e85c43c10065c01cf47144d8c436df9f70494ad1d10376f07c948c5038` | Historical comparison stack only. |
| `evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/src/SIM_ARD_GAW/config/plane_airspeed.parm` | Recovered production-era airspeed evidence. | historical evidence | no | `fdb665e2f19bc0025bea7c97c97509aa958d8a384164806775174dee7bb667d4` | Historical comparison stack only. |
| `evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/private_overlay/config/plane_params.local.parm` | Recovered production-era local override evidence. | historical evidence | no | `22cca998572217d9fc44fdc62132c842af4ed6b19fd4277804becc3a77715c4d` | Historical comparison stack only; preserved outside `.private/`. |

## Runtime Stack Summary

| Lane | Canonical shared stack | Local policy |
| --- | --- | --- |
| `plane` | `plane_base.parm` | Optional local plane override when present. |
| `plane-cte` / `plane-airspeed` | `plane_base.parm` -> `plane_airspeed.parm` | Optional local plane override when present. |
| `plane-gps` | `plane_base.parm` -> `plane_gps.parm` | Local override **excluded unconditionally** by the dedicated `build_plane_gps_param_args`; no airspeed overlay. Structural only, not yet live-smoke verified. |
| `gps_failure` | `plane_base.parm` -> `plane_gps.parm` | Plugin default stack (targets `plane-gps` / `gazebo-plane-gps`); caller-supplied stacks override it. Static/no-SITL only; no live run or readback yet. |
| `plane-lidar` | `plane_base.parm` -> `plane_lidar.parm` | Optional local plane override when present. |
| `plane-staircase` | `plane_base.parm` -> `plane_lidar.parm` -> `staircase_plane_params.parm` | Optional local plane override when present. |
| `plane-airspeed-lidar` | `plane_base.parm` -> campaign `mini_talon_airspeed_lidar/plane_full.parm` | Optional local plane override when present. |
| `plane-altitude-wind` | `plane_base.parm` -> campaign `mini_talon_altitude_wind/plane_full.parm` | Optional local plane override when present. |
| `plane-rebuild` | `plane_params_rebuild.parm` | No local plane override. |
| `copter` / `copter-lidar` | `copter_params.parm` | No local config append in the launcher. |
| Current CTE `run_one.py` / `run_matrix.py` | `plane_base.parm` -> `plane_airspeed.parm` | Local plane override is appended when present unless the caller disables or replaces it. |
| Legacy CTE `run_one_og.py` | `plane_base.parm` -> `plane_airspeed.parm` | Retained legacy compatibility caller appends the local plane override when invoked. |

## Notes

- `plane_base.parm` explicitly leaves `ARSPD_TYPE` disabled while keeping
  generic `AIRSPEED_*` defaults. Gazebo airspeed sensor enablement and
  lane-specific airspeed overrides live in the airspeed overlay or campaign
  lane files.
- 2026-06-03 airspeed-overlay boundary fix: `config/overlays/plane_airspeed.parm`
  was restored to the production-like conservative Mini Talon envelope
  (`AIRSPEED_CRUISE 14`, `AIRSPEED_MIN 10`, `AIRSPEED_MAX 22`,
  `AHRS_WIND_MAX 15`) so the default Gazebo airspeed overlay matches the
  recovered production-era overlay and the accepted CTE wind-envelope evidence
  (`evidence/reports/features/2026-06-02_cte_wind_envelope_result.md`, cruise
  = 14 m/s). The aggressive high-wind CTE tuning that had leaked into that file
  (`AIRSPEED_CRUISE 28`, `AIRSPEED_MIN 18`, `AIRSPEED_MAX 38`,
  `TRIM_THROTTLE 75`, `AHRS_WIND_MAX 35`, etc.) was moved verbatim into the new
  separately named `config/overlays/plane_airspeed_cte_high_wind_aggressive.parm`.
  That aggressive overlay is a stress profile only and is not the default; it is
  not wired into any launch target or CTE/wind-matrix default param stack.
  `plane-cte`, `plane-airspeed`, and the wind-matrix/CTE callers
  (`run_one.py`, `run_one_og.py`, `run_matrix.py`, and the `wind_matrix`
  test-suite plugin defaults) reference `plane_airspeed.parm` by path and so now
  load the conservative 14 m/s envelope, preserving the existing
  cruise-airspeed-limited CTE evidence story.
- Hashes above are for shared active and campaign files in the Phase 4 runtime
  stack audit. Historical comparison-input hashes are also recorded above and
  in the recovered-stack `SHA256SUMS` evidence manifest; archive and local-only
  files are not shared canonical config.
- Historical recovered files were found under evidence; active `config/`
  contains no nested `.private` home in this pass.
