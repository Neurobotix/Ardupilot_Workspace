# External Dependencies

Production source workspace: `/home/ahmed/ardupilot_workspace`

Pinned observations at migration time:

- Production root workspace commit: `a483a534fac1755ea9ba9a007f062981913366d6`
- `workspace_next` root commit: `UNKNOWN`
  - Command: `git rev-parse HEAD`
  - Reason: repository has no `HEAD` commit yet.
- Production `src/ardupilot` commit: `f198baa9c5609a292e6576bce832e66b30cfe0c0`
- `workspace_next` `src/ardupilot` commit:
  `f198baa9c5609a292e6576bce832e66b30cfe0c0`
  - Command: `git -C src/ardupilot rev-parse HEAD`
  - Source: cloned from the production reference with `--no-hardlinks` during
    Phase 2 dependency unblock.
  - Note: this checkout is ignored local runtime dependency state, not a
    canonical evidence home.
- Production `src/SIM_ARD_GAW` commit: `fac4746653fb50d088a5c9209c80d0e5fda6b958`
- `workspace_next` `src/SIM_ARD_GAW` commit: `UNKNOWN`
  - Command: `git -C src/SIM_ARD_GAW rev-parse HEAD`
  - Reason: compatibility path is symlink-only and root-tracked in
    `workspace_next`, not a nested git checkout.
- `ardupilot_gazebo` source commit: `UNKNOWN`
  - Command: `git -C src/ardupilot_gazebo rev-parse --show-toplevel`
  - Reason: both production and `workspace_next` resolve this path to their
    root workspaces; no nested plugin git metadata is present.
- `SITL_Models` source commit: `UNKNOWN`
  - Command: `git -C src/SITL_Models rev-parse --show-toplevel`
  - Reason: production resolves this path to the root workspace. Phase 2 copied
    the directory into `workspace_next` as ignored local runtime dependency
    state, but no nested source commit metadata exists.

Expected local dependency paths:

- `src/ardupilot/`: present in production and provisioned locally in
  `workspace_next`; ignored by git.
- `src/SITL_Models/`: present in production and provisioned locally in
  `workspace_next`; ignored by git.
- `src/ardupilot_gazebo/`: present in both workspaces as root-tracked source.
- `env/`: local ignored Python environment used for Phase 2 runtime checks.
  It includes the runtime Python packages listed in root `requirements.txt`.
  System site packages are enabled locally so MAVProxy map support can import
  the system wx bindings.

Phase 2 dependency-unblock notes:

- `src/ardupilot/modules/` was populated from the production reference so SITL
  waf configure/build could execute in `workspace_next`.
- SITL run state is routed under `var/runs/sitl/<target>/`.
- MAVProxy telemetry logs are routed under `var/logs/mavproxy/<target>/`.
- Python/runtime caches are routed under `var/cache/`.
- External dependency trees may contain upstream fixture, firmware, bootloader,
  or test-log files. Workspace-generated runtime output must still go under
  `var/`.

System packages observed as required for local `ardupilot_gazebo` builds:

- `libgz-sim8-dev`
- `rapidjson-dev`

The workspace Gazebo plugin binary is a required local build for governed
runtime and wind-matrix runs:

```bash
cmake -S src/ardupilot_gazebo -B build/ardupilot_gazebo -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build/ardupilot_gazebo -j2
test -f build/ardupilot_gazebo/libArduPilotPlugin.so
```

`setup.bash`, launch entrypoints, and wind-matrix runtime use that build output
only. `/usr/local/lib/ardupilot_gazebo` is retained as host context when
auditing older evidence, not as a runtime fallback.

Runtime environment is initialized through root `setup.bash`. Do not rely on
private shell notes for canonical Gazebo path setup.

Baseline evidence:

- `evidence/reports/migration/PHASE_0_BASELINE_2026-05-20.md`
