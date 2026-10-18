# GPS-Denied Navigation Implementation

## Mainline State

No GPS-denied implementation is on the current mainline. The tracked inputs
are the INS-only overlay, world, and model listed in `README.md`. No launch
target selects them on this branch.

## Recovered INS-Only Implementation

An uncommitted INS-only implementation was saved as a git stash on 2026-08-03
(base commit `bef0a06`, "Docs: gps failure envelope wiring"). On 2026-10-12 the
stash commit `c873af0` was preserved as the branch `archive/ins-only-stash`.
It is not merged and not reviewed.

It touches 27 tracked files (+2515 / -102 lines):

- `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/`: analyzers,
  case generator, config, control, defaults, environment, manifest, MAVLink,
  monitor, readiness, telemetry, and a new `source_contract.py`.
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py`
- `src/sim_ard_gaw/launch/launch.sh`
- `tests/unit/`: `test_gps_failure_phase1.py`,
  `test_gps_failure_phase2_path.py`, `test_gps_failure_readiness.py`,
  `test_gps_launch_targets.py`
- docs, indexes, and the `gps_failure_behavior` bundle.

The stash's untracked-file parent holds the INS-only assets, overlays, and the
three IMU documents. Those were committed separately in `b097951` and are
already on the mainline.

To inspect the recovered change against its base:

```bash
git diff archive/ins-only-stash^1 archive/ins-only-stash
```

## Shahin-E Model

Stage 1 (2026-10-13) added the model, world, and parameter file; sources and
validation gates are in `shahin_e_model_sources.md`. Stage 1b (2026-10-13)
added the launch targets `plane-shahin-e` (loads `config/vehicles/shahin_e.parm`
only, `--wipe-eeprom`, `-f JSON`, `udp:127.0.0.1:14551`, local override
excluded) and `gazebo-plane-shahin-e` (`assets/worlds/shahin_e_runway.sdf`).
Structural tests: `tests/unit/test_shahin_e_launch_targets.py` and
`tests/unit/test_shahin_e_model_assets.py` (parameter-file line length, flap input, no
rangefinder dependency). Gate 1 (2026-10-13/15): rudder sign flipped, all control surfaces
checked. A SITL rangefinder was tried and dropped (it broke Gazebo lock-step); the backup EKF
source set 3 uses the barometer in SITL instead. Gates 0-4 passed in SITL
2026-10-15/18 (Gate 3: wing a0 0.097; Gate 4 untuned). Missions:
`assets/missions/shahin_e_gate{2_first_flight,3_level_cruise,4_climb_descent}.waypoints`.
Gate 5 not run. Gate run records go to
`var/analysis/shahin_e_model_validation/gate_results.md`.

## Runtime Output

Study runs write under `var/runs/gps_denied_navigation/`.
