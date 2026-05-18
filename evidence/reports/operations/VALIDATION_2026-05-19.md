# Workspace Next Validation — 2026-05-19

Status: bootstrapped, not production.

Checks run:

- `source setup.bash`: passed; exported `ARDUPILOT_WORKSPACE`, `ARDUPILOT_LOGS`, and Gazebo resource paths for `workspace_next`.
- `scripts/ops/doctor.sh`: passed.
- `scripts/ops/launch.sh help`: passed.
- `make test-parity`: passed using the production virtualenv fallback at `/home/ahmed/ardupilot_workspace/env/bin/python3`.
- Broken-symlink scan: passed.
- Raw log scan for `.BIN`, `.tlog`, `.tlog.raw` outside ignored runtime output: passed.
- Active `config/` nested `.private` scan: passed.

Intentional current limitations:

- This workspace is not production until the full shadow parity runbook passes.
- `wind-check-altitude` is retired because production referenced a missing validator script.
- `src/SIM_ARD_GAW` remains as a symlink compatibility layer for migrated legacy scripts.
- `src/ardupilot/` and `src/SITL_Models/` are external dependencies and were not copied.
