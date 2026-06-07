# Airspeed Failure Behavior — Operations Runbook

How to work with the `airspeed_failure` plugin from the command line.

Current status: Phase 1 (no-SITL) and Phase 2 (live smoke) accepted. Phase 3
(full v1 matrix) is unlocked but not yet run. **Live SITL runs are gated by
ADR-0004 and require explicit operator authorization** — see the live-run
section below.

Architecture doc:
[docs/architecture/airspeed_failure_lane.md](../architecture/airspeed_failure_lane.md)

Feature runbook:
[governance/runbooks/features/airspeed_failure_behavior/](../../governance/runbooks/features/airspeed_failure_behavior/)

## Prerequisites

Source the workspace before every session:

```bash
source setup.bash
```

This exports `src/` on `PYTHONPATH` so the module CLI is reachable. All
commands below assume the workspace root as the working directory and a sourced
shell.

## No-SITL Commands (verified)

These commands were verified on 2026-06-05 (Phase 1 review) and re-verified on
2026-06-06 (Phase 2 implementation review). They do not start SITL or Gazebo.

### List all cases

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --list-cases
```

Expected output — one case ID per line:

```text
healthy_reference
ofs_noop_probe
noise_5
noise_10
pitot_500pa
fail_primary
sign_reversed
ratio_bias_p10
ratio_bias_p30
ratio_bias_p50
ratio_bias_m10
ratio_bias_m30
ratio_bias_m50
```

### Dry-run a specific case

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --dry-run --case <case_id>
```

Example:

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --dry-run --case fail_primary
```

Prints a JSON object with the case definition, injection payload
(`SIM_ARSPD_FAIL=1.0` for `fail_primary`), reset payload (source defaults),
reference wind artifact schema, and parameter schema. The plugin constructs
fully without starting a launch.

Example for the healthy reference:

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --dry-run --case healthy_reference
```

### Probe the parameter schema

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --probe-schema
```

Prints the required `SIM_ARSPD_*` parameter names, source defaults, and
per-parameter semantic notes. Useful for verifying parameter names against a
SITL build before a live matrix. In Phase 1 this is name-existence validation
only; live SITL probing is Phase 2.

## Stack

The commands above use these defaults (resolvable without a running sim):

| Item | Path |
| --- | --- |
| Mission | `assets/missions/airspeed_failure_behavior_mission.waypoints` |
| SITL target | `plane-cte` |
| Gazebo target | `gazebo-plane-cte` |
| Base params | `config/vehicles/plane_base.parm` |
| Airspeed overlay | `config/overlays/plane_airspeed.parm` |

The airspeed overlay is the conservative production-like default
(`AIRSPEED_CRUISE 14`, `AIRSPEED_MIN 10`, `AIRSPEED_MAX 22`). The mission's
`DO_CHANGE_SPEED 15` command sits inside the `14/22` envelope. The aggressive
stress overlay lives separately in
`config/overlays/plane_airspeed_cte_high_wind_aggressive.parm` and is not wired
into this stack.

## Output Paths

Raw runtime output goes under:

```text
var/runs/airspeed_failure_behavior_<timestamp>/
```

Each case gets a subdirectory:

```text
var/runs/airspeed_failure_behavior_<timestamp>/<case_id>/runs/attempt_001/
```

Required artifacts per attempt: `run_config.json`, `reference_wind.json`,
`airspeed_injection.json`, `airspeed_behavior_summary.json`,
`airspeed_signal_metrics.json`, `mission_progress.json`, `mode_timeline.json`,
`altitude_speed_envelope.json`. `tecs_response.json` is written when MAVLink
fields are available.

The Phase 2 measurement smoke accepted raw root is:
`var/runs/airspeed_failure_behavior_20260606T164050810132Z/`

**Nothing is promoted to `evidence/` automatically.** Promotion to
`evidence/curated_logs/airspeed_failure_behavior_<date>/` and an evidence report
under `evidence/reports/features/` happen only in Phase 4, after explicit
operator acceptance.

## Live SITL Runs — Gated, Not Yet Authorized for Phase 3

Live runs require the workspace-built Gazebo plugin (`build/ardupilot_gazebo/
libArduPilotPlugin.so`), a clean SITL build, and explicit operator
authorization per ADR-0004.

The Phase 2 measurement-smoke entry point (informational — Phase 2 is already
accepted) runs `healthy_reference`, `ofs_noop_probe`, `pitot_500pa`, and
`fail_primary`:

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --live-measurement-probes --confirm-live-phase2
```

The older two-case harness entry point remains available for a quick
healthy/fail-primary smoke only:

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --live-smoke --confirm-live-phase2
```

Running either live command without `--confirm-live-phase2` exits with an error.
This guard prevents accidental SITL/Gazebo launches from a discovery command.

**Phase 3 full v1 matrix is unlocked by Phase 2 smoke but has not been run.**
Before running Phase 3, record the smoke review checklist in
`governance/runbooks/features/airspeed_failure_behavior/review.md` and obtain
explicit authorization under ADR-0004.

The clean-run and workspace-built plugin policy is in
[governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md](../../governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md).

## Unit Tests

```bash
./env/bin/python3 -m unittest tests.unit.test_airspeed_failure_phase1
```

Covers case generation, parameter schema, injection trigger metadata,
classification helpers, artifact schemas, manifest accepted-observation
counting, and no-SITL plugin construction. Passes 19 tests (Phase 2
implementation review, 2026-06-06).

## Troubleshooting

**`ModuleNotFoundError` for `sim_ard_gaw`:** run `source setup.bash` first.
`setup.bash` exports `src/` on `PYTHONPATH`.

**`--dry-run` requires `--case`:** supply a case ID from `--list-cases`.

**Live command requires `--confirm-live-phase2`:** add the flag only after
confirming authorization under ADR-0004.

**Missing workspace Gazebo plugin:** live runs check for
`build/ardupilot_gazebo/libArduPilotPlugin.so` and fail closed if it is absent.
Build the workspace Gazebo plugin before any live attempt.
