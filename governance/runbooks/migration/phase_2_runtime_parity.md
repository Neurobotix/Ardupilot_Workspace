# Phase 2: Runtime Parity

Purpose: prove that `workspace_next` can reproduce the production runtime
surface before it is trusted.

Phase 2 is a proof phase only. It does not cut over production, deprecate the
old workspace, retire compatibility paths beyond already-documented target
retirements, or perform major refactors.

## Status Semantics

- `PASS`: the exact command was run in `workspace_next` and produced direct
  evidence for the claimed behavior.
- `FAIL`: the command was executable but exited unsuccessfully or produced a
  runtime error that must be fixed before the target can be trusted.
- `BLOCKED`: the command could not prove the behavior because a dependency,
  environment service, display, simulator component, or prerequisite runtime
  was missing. A blocked command is not a pass.
- `PARTIAL`: a target started far enough to prove a narrow prerequisite, but no
  SITL/Gazebo/MAVLink handshake or equivalent runtime proof was captured.

If only static checks pass while SITL/Gazebo smoke is blocked, Phase 2 is not
fully passed.

## Required Setup

Run all commands from `/home/ahmed/ardupilot_workspace_next`.

`make doctor` requires `ripgrep` (`rg`): the structure validator
`scripts/maintenance/validate_structure.sh` uses it for `.private` policy and
migration-plan-link checks. Without `rg` the validator reports spurious missing
references and `make doctor` fails. Install it with `sudo apt install ripgrep`.

Runtime smoke targets must be run in concurrent terminals (SITL in one
terminal, Gazebo in another, the LiDAR bridge in a third). A SITL vehicle
launched with `-f JSON` waits for Gazebo; running a vehicle target alone under
a timeout will never produce a heartbeat and is not a valid test.
`scripts/ops/capture_round.sh <target>` decodes the newest tlog for a target
into working review output under `var/`. Use
`scripts/ops/capture_round.sh --promote-reviewed --evidence-id <new-id>
<target>` only after review into a new versioned curated artifact under
`evidence/`; do not replace an already-cataloged Phase 2 summary.

The old workspace may be read for comparison only:

```bash
/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help
```

Do not edit `/home/ahmed/ardupilot_workspace`.

Before claiming runtime parity, confirm the local runtime dependency surface is
self-contained enough to execute the smoke commands:

- `src/ardupilot/` may be provisioned as an ignored local dependency checkout,
  but it is not a canonical documentation or evidence home.
- `src/SITL_Models/` may be provisioned as ignored local runtime dependency
  state when Gazebo worlds require it.
- `env/` may be used as an ignored local Python environment. Required runtime
  packages must be listed in root `requirements.txt`.
- Runtime state, telemetry, and caches must remain under `var/runs/`,
  `var/logs/`, and `var/cache/`.
- Upstream fixture, firmware, bootloader, or sample log files inside ignored
  external dependency trees do not satisfy runtime evidence. Workspace-generated
  raw runtime output must stay under `var/`.
- Bounded Gazebo smoke checks must leave no stale Gazebo GUI/server child
  processes after timeout, interrupt, or cleanup.

## Tasks

- Run `source setup.bash`.
- Compare launch target help output:
  - production:
    `/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help`
  - new: `scripts/ops/launch.sh help`
- Record production targets, new workspace targets, and differences.
- Verify `wind-check-altitude` is intentionally retired and returns a
  non-success retired-target result in `workspace_next`.
- Run static imports for migrated scripts and `test_suite`.
- Run `make doctor`.
- Run `make test-parity`.
- Run `scripts/maintenance/validate_structure.sh`.
- Smoke-test core launch targets:
  - `copter`
  - `copter-lidar`
  - `plane`
  - `plane-lidar`
  - `plane-cte`
  - `gazebo-plane`
  - `gazebo-plane-cte`
  - `cleanup`
- Smoke-test `bridge-plane` without claiming full flight readiness unless a
  MAVLink/Gazebo connection is directly proven.
- Verify the logger is configured to write under
  `var/logs/flight_logger/`. If no MAVLink source is available, record logger
  execution as `BLOCKED`, not passed.
- Run process checks before and after cleanup.
- Run a raw-log scan for `.BIN`, `.bin`, `.tlog`, and `.tlog.raw` outside
  allowed ignored/runtime areas.

## Minimum Validation Commands

```bash
source setup.bash
make doctor
make test-parity
scripts/maintenance/validate_structure.sh
scripts/ops/launch.sh help
scripts/ops/launch.sh wind-check-altitude
scripts/ops/launch.sh cleanup
scripts/ops/launch.sh copter
scripts/ops/launch.sh copter-lidar
scripts/ops/launch.sh plane
scripts/ops/launch.sh plane-lidar
scripts/ops/launch.sh plane-cte
scripts/ops/launch.sh gazebo-plane
scripts/ops/launch.sh gazebo-plane-cte
scripts/ops/launch.sh bridge-plane
```

Runtime smoke commands may use a bounded timeout for evidence capture. Timeout
without a proven handshake is `BLOCKED` or `PARTIAL`, not `PASS`.

## Runtime Output Policy

- Runtime output belongs under `var/`.
- Logger output belongs under `var/logs/flight_logger/`.
- Raw `.BIN`, `.bin`, `.tlog`, and `.tlog.raw` files must not be committed or
  promoted into tracked evidence. Promote only curated reports, manifests,
  summaries, and indexes.

## Required Updates

- `docs/operations/launch_targets.md`: keep target behavior current.
- `docs/vehicles/status.md`: distinguish production reference, verified in
  `workspace_next`, blocked, and not-yet-tested status. Promote statuses only
  when dated evidence exists.
- `.ai/current.md`: update active parity state.
- `.ai/issues/open.md`: record failed targets.
- Relevant governance docs if Phase 2 rules change.
- `evidence/reports/`: store dated conclusions.
- `evidence/curated_logs/`: store reviewed selected summaries or bounded
  runtime artifacts that support those conclusions.

## Exit Gate

Create `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_<date>.md` with pass/fail rows
for every target. Vehicle docs must still say "production reference only" for
anything not reverified in `workspace_next`.

The evidence report must include:

- date/time and timezone,
- scope,
- files changed,
- commands run,
- production launch target list summary,
- new workspace launch target list summary,
- launch target differences,
- static checks result,
- `make doctor` result,
- `make test-parity` result,
- structure validation result,
- each runtime smoke command result: `PASS`, `FAIL`, `PARTIAL`, or `BLOCKED`,
- bridge/logger result,
- cleanup result,
- runtime output location check,
- raw log leakage check,
- unresolved blockers,
- pass/fail conclusion,
- explicit statement that the old workspace was not modified,
- explicit statement that the old workspace is not deprecated yet.

Phase 2 passes only when required static checks pass and runtime smoke commands
prove the expected SITL/Gazebo/bridge behavior directly. Missing external
dependencies, missing `src/ardupilot`, missing Gazebo, or unproven handshakes
make the phase `BLOCKED`.
