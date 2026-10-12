# GPS-Denied Navigation Implementation

## Current State

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

## Runtime Output

Study runs write under `var/runs/gps_denied_navigation/`.
