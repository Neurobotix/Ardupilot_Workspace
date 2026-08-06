# Installation

Setup for ArduPilot SITL with Gazebo Sim in `ardupilot_workspace_next`.

This guide is the canonical install reference for the active workspace.

## Evidence boundary

The current launch surface has dated runtime evidence in
`evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`. The curated
runtime captures identify ArduPilot SITL at commit `f198baa9`
(ArduPlane/ArduCopter `V4.7.0-dev`). Current governed runs follow
`governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md` and
must use the workspace-built Gazebo plugin described below.

Record host kernel, Python, and Gazebo package versions in dated evidence before
calling them parity-verified.

## Prerequisites

System build tooling: `git`, `cmake`, `build-essential`, Python 3 development
packages, and `ripgrep` (`rg`). `ripgrep` is required by `make doctor` — the
structure validator uses it for `.private` policy and workspace-status-link
checks. Install it with `sudo apt install ripgrep`.

## Step 1: Gazebo Sim

Install a Gazebo Sim version compatible with the local ArduPilot Gazebo plugin.
Confirm it with `gz sim --version` and record the version when producing runtime
evidence.

## Step 2: Local runtime dependencies

The workspace expects these as ignored local checkouts (see
`src/external/DEPENDENCIES.md`):

- `src/ardupilot/` — ArduPilot source, built for SITL with `waf`
  (`./waf configure --board sitl && ./waf plane copter`).
- `src/SITL_Models/` — upstream Gazebo models, when a world needs them.
- `src/ardupilot_gazebo/` — the Gazebo plugin source used to build the required
  workspace plugin binary.
- `env/` — a local Python virtualenv. Required packages are listed in the
  root `requirements.txt` (`pymavlink`, `MAVProxy`, etc.).

These trees are gitignored. They are runtime dependencies, not canonical
workspace evidence.

## Step 3: Build The Workspace Gazebo Plugin

Governed runtime entrypoints use only:

```text
build/ardupilot_gazebo/libArduPilotPlugin.so
```

An installed plugin under `/usr/local/lib/ardupilot_gazebo` is not a fallback
path for this workspace. Build the workspace binary from the local source:

```bash
cd /home/ahmed/ardupilot_workspace_next
cmake -S src/ardupilot_gazebo -B build/ardupilot_gazebo -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build/ardupilot_gazebo -j2
test -f build/ardupilot_gazebo/libArduPilotPlugin.so
```

`src/external/DEPENDENCIES.md` records the observed local system packages for
that build. Launch and wind-matrix entrypoints fail closed when the workspace
plugin binary is missing.

## Step 4: Environment

`source setup.bash` from the workspace root. It exports `ARDUPILOT_WORKSPACE`,
`GZ_SIM_RESOURCE_PATH`, `GZ_SIM_SYSTEM_PLUGIN_PATH`, routes logs/caches under
`var/`, and activates `env/` if present. `GZ_SIM_SYSTEM_PLUGIN_PATH` must point
at `build/ardupilot_gazebo`. Do not hand-edit `GZ_SIM_*` — `setup.bash` and
`launch.sh` own them.

## Step 5: Verify

```bash
cd /home/ahmed/ardupilot_workspace_next
source setup.bash
test "$GZ_SIM_SYSTEM_PLUGIN_PATH" = "$PWD/build/ardupilot_gazebo"
make doctor
python -m pytest tests/unit -q
python -m pytest tests/integration -q
scripts/ops/launch.sh help
```

All four should pass. For a runtime check, follow
`docs/operations/launch_targets.md` and run a vehicle target with its Gazebo
world in a second terminal (a SITL vehicle launched with `-f JSON` waits for
Gazebo — never run a vehicle target alone).

## Troubleshooting

See `docs/operations/troubleshooting.md`.
