# Quick Start

```bash
cd /home/ahmed/ardupilot_workspace_next
source setup.bash
make doctor
scripts/ops/launch.sh help
```

## Running the test suite

The unified `sim-test` entry point covers all plugins and run modes:

```bash
# Interactive wizard (no arguments)
sim-test

# Direct flag-based invocation (same surface as the individual CLI modules)
sim-test case   --x 0 --y 4 --rep 1 ...
sim-test suite  --x-values 0,4,8,12 ...
sim-test rr     --x-values 0,4,8,12 ...
```

If `sim-test` is not on your PATH, activate the entry point:

```bash
env/bin/pip install -e .
```

The wizard asks: sensor family -> run mode -> case parameters -> "customise
advanced parameters?" (timeouts, MAVLink address, campaign root). All defaults
match the plugin's production values so pressing Enter through the advanced
block is safe for a standard run.

Core runtime dependencies expected inside this workspace as ignored local
runtime state:

- `src/ardupilot/`
- `src/SITL_Models/`
- `env/`
- `src/ardupilot_gazebo/`
- `build/ardupilot_gazebo/libArduPilotPlugin.so`

The Gazebo plugin is workspace-built only. Follow
`docs/onboarding/installation.md` when the build output is missing; governed
entrypoints do not fall back to an installed plugin.

For focused unit and integration checks, use the local environment when
present:

```bash
python -m pytest tests/unit -q
python -m pytest tests/integration -q
```

`make doctor` runs `scripts/ops/doctor.sh`, which delegates to
`scripts/maintenance/validate_structure.sh` for structure checks.
Run the maintenance script directly when investigating a structure failure.

This workspace is production for the governed ArduPilot + Gazebo
fault-injection workflows accepted in
`governance/decisions/ADR-0005-workspace-next-cutover.md`. Launch and campaign
entrypoints perform broad pre-run cleanup by policy so a governed simulation
run starts from a clean simulator stack.

For current status, use `docs/operations/workspace_status.md`. For changes,
follow the change-control rules in `governance/standards/change_control.md`.
