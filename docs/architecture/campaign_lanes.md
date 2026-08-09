# Campaign Lanes

A **campaign lane** is an end-to-end fault investigation: a fault is injected
into a running simulation, cases are swept, behavior is classified into
verdicts, and evidence is produced. Campaign lanes are `test_suite` plugins.

This is the canonical registry for that axis. It does **not** cover simulation
lanes — the aircraft + world + launcher + bridge combinations a campaign lane
runs on. Those live in `docs/architecture/simulation_lanes.md`.

The two axes are different things and the unqualified word "lane" is ambiguous
between them. See `governance/standards/naming.md` for the terminology rule.

The executable source of truth for which campaign lanes exist is
`src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py`. A lane is reachable as
soon as it is registered there. Per-lane defaults are declared in
`src/sim_ard_gaw/campaigns/test_suite/plugins/<lane>/defaults.py`.

## Registry

Three campaign lanes are registered.

| Campaign lane | Runs on (simulation lane) | Aircraft / world | Default mission | Default parameter overlay | CLI entry point |
| --- | --- | --- | --- | --- | --- |
| `wind_matrix` | CTE / airspeed (`plane-cte` + `gazebo-plane-cte`) | Mini Talon / `mini_talon_wind_runway` | `assets/missions/square_500m_five_laps_loiter5_land.waypoints` | `config/vehicles/plane_base.parm` → `config/overlays/plane_airspeed.parm`, plus `.private/config/plane_params.local.parm` when present | `sim-test case`, `sim-test suite`, `sim-test rr` |
| `airspeed_failure` | CTE / airspeed (`plane-cte` + `gazebo-plane-cte`) | Mini Talon / `mini_talon_wind_runway` | `assets/missions/airspeed_failure_behavior_mission.waypoints` | `config/vehicles/plane_base.parm` → `config/overlays/plane_airspeed.parm` | `sim-test airspeed` |
| `gps_failure` | GPS failure behavior (`plane-gps` + `gazebo-plane-gps`) | Mini Talon / `mini_talon_gps_runway` | `assets/missions/gps_failure_behavior_mission.waypoints` | `config/vehicles/plane_base.parm` → `config/overlays/plane_gps.parm` (no airspeed overlay, no local override) | `sim-test gps` |

`sim-test` is the console script declared in `pyproject.toml`, pointing at
`sim_ard_gaw.campaigns.test_suite.cli.run:main`. Running `sim-test` with no
arguments launches the interactive wizard, which dispatches to the same runners
the flag path uses.

### Docs and runbooks

| Campaign lane | Architecture doc | Runbook | Feature runbook bundle |
| --- | --- | --- | --- |
| `wind_matrix` | none; status note is `docs/campaigns/wind_matrix.md` | none under `docs/operations/` | `governance/runbooks/features/test_suite_migration/` |
| `airspeed_failure` | `docs/architecture/airspeed_failure_lane.md` | `docs/operations/airspeed_failure_runbook.md` | `governance/runbooks/features/airspeed_failure_behavior/` |
| `gps_failure` | `docs/architecture/gps_failure_lane.md` | `docs/operations/gps_failure_runbook.md` | `governance/runbooks/features/gps_failure_behavior/` |

## Cells not sourced from code

Every cell above is read from the code except where noted here. These gaps are
finding L-06 — a lane that does not declare something in code forces the reader
to infer it.

- **`wind_matrix` simulation lane and launch targets.** `wind_matrix` declares
  no `SITL_TARGET` / `GAZEBO_TARGET` constants, unlike the other two lanes. Its
  defaults declare only the command strings `CTE_SITL_COMMAND` and
  `CTE_GAZEBO_COMMAND` (`scripts/ops/launch.sh plane-cte` and
  `... gazebo-plane-cte`). The simulation lane in the table is read from those
  strings.
- **Aircraft.** No lane declares its airframe as a constant. "Mini Talon" is
  inferred from the world names (`mini_talon_*`) declared in each lane's
  `defaults.py`, and is consistent with `docs/architecture/simulation_lanes.md`.
- **`wind_matrix` and `airspeed_failure` world files.** Both declare
  `WORLD_NAME = "mini_talon_wind_runway"` but no world-file path constant.
  `gps_failure` does declare `GAZEBO_WORLD_FILE`.
- **CLI entry points.** The `sim-test <subcommand>` strings come from the
  `_SUBCOMMANDS` map in `cli/run.py`, not from any per-lane declaration. The
  lane names in `_registry.py` (`airspeed_failure`, `gps_failure`) do not match
  their subcommands (`airspeed`, `gps`).
- **Docs and runbook paths.** Not declared in code; taken from the filesystem
  and `.ai/index.md`.

## Notes per lane

### `wind_matrix`

The CTE wind campaign. Sweeps Gazebo wind values over a square mission and
scores cross-track error. `WIND_VALUES = (0, 4, 8, 12)` and
`RUNS_PER_COMBO = 5` in `defaults.py`.

This is the only lane the generic runners (`sim-test case` / `suite` / `rr`)
can drive. Those runners take wind-matrix case coordinates (`--x` / `--y`) and
validate the square-wind mission contract, so they reject the other lanes'
missions — see `_WIND_SHAPED_RUNNER_LANES` in `cli/_plugin_select.py`. The
other two lanes have their own entry points.

### `airspeed_failure`

Behavior characterization under a degraded or corrupted airspeed signal.
Injects via `SIM_ARSPD_*` parameters at a `MISSION_CURRENT` seq-4 trigger.
Declares four additional missions beyond the default for ramp, pulse-ladder,
and long-cruise work.

### `gps_failure`

Behavior characterization under degraded or corrupted GPS (drift, glitch,
denial, jamming), centered on the EKF innovation-gate knee. This lane uses
dedicated launch identities rather than the CTE ones: `defaults.py` states that
`plane-cte` loads the airspeed overlay and the local plane override, which
ADR-0021 rejects for GPS.

It is the only lane declaring named **envelopes** — parameter/mission bundles
selected by name, in `ENVELOPE_DEFINITIONS`: `baseline`, `fast_cruise_18mps`,
`ekf_gate300_glitch0`, and `ekf_glitch10`. The `fast_cruise_18mps` envelope
uses the second Gazebo target `gazebo-plane-gps-airspeed` and the
`mini_talon_gps_airspeed_runway` world; the table above lists the `baseline`
envelope, which is the lane default.

## Status

Lane status claims are not repeated here — they date quickly and would drift
from the records that own them. For current status see each lane's
architecture doc and runbook in the table above, the status rows in
`docs/architecture/simulation_lanes.md`, and `.ai/index.md`.
