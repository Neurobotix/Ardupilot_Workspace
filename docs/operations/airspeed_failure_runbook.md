# Airspeed Failure Behavior — Operations Runbook

How to work with the `airspeed_failure` plugin from the command line.

Current status: Phase 1 (no-SITL) and Phase 2 (live smoke) accepted. The
ratio sweep, pulse ladder, and stepped ramps are accepted as bounded Phase 4A
characterization by
`evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`.
The fixed-case repetition matrix remains open as Phase 4B. **Live SITL runs are
gated by ADR-0004 and require explicit operator authorization** — see the
live-run section below.

Tailwind counterpart support is currently **no-SITL only**. The named profile,
36 km missions, distinct case IDs, and 17-attempt recipe are implemented, but
healthy live validation has not been authorized or run. Do not describe the
tailwind lane as verified.

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

## From the unified `sim-test` wizard

Choosing `airspeed_failure` in the `sim-test` sensor-family menu runs the
sequential suite through the framework `SuiteRunner`. Alongside the case
selection it asks two separate settings that are easy to confuse:

- **Runs per case** — how many accepted runs each case needs.
- **Max attempts per case** — the retry budget before the suite gives up on a
  case. Defaults to the framework value in `core/suite_runner.py` (12).

Before 2026-08-06 the wizard silently forced the retry budget to 1, so the
first non-accepted attempt aborted the whole campaign with
`RuntimeError: exceeded max_attempts_per_case (1)`. If an older campaign
manifest shows a run ending at `attempt=1`, that is the cause.

`--round-robin` is not supported on this lane: airspeed cases run under the
sequential scheduler. Passing it exits non-zero with that message rather than
being silently ignored.

## No-SITL Commands (verified)

These commands were verified on 2026-06-05 (Phase 1 review) and re-verified on
2026-06-06 (Phase 2 implementation review). The full-ratio-sweep listing and
dry-run examples were re-verified on 2026-06-14. They do not start SITL or
Gazebo.

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
ratio_bias_p10
ratio_bias_p30
ratio_bias_p50
ratio_bias_m10
ratio_bias_m30
ratio_bias_m50
ratio_bias_ramp_p10_to_p100_headwind
ratio_bias_ramp_p10_to_p200_headwind
ratio_bias_pulse_p10_to_p130_headwind
```

The accepted Phase 4A ratio sweep also includes the full bias ladder. Use
`--full-ratio-sweep` when reproducing or dry-running those accepted cases:

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --full-ratio-sweep --list-cases
```

The full-ratio-sweep output adds these case IDs to the default list:

```text
ratio_bias_p20
ratio_bias_p40
ratio_bias_p60
ratio_bias_p70
ratio_bias_p80
ratio_bias_p90
ratio_bias_p100
ratio_bias_m20
ratio_bias_m40
```

Tailwind discovery is separate and does not alter the default headwind list:

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --wind-profile tailwind_eastbound --list-cases
```

Expected no-SITL case IDs:

```text
healthy_reference_tailwind
ratio_bias_ramp_p10_to_p100_tailwind
ratio_bias_ramp_p10_to_p200_tailwind
ratio_bias_pulse_p10_to_p130_tailwind
```

Dry-run the cruise-follow P200 counterpart without launching:

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --wind-profile tailwind_eastbound \
    --speed-source airspeed_cruise \
    --dry-run --case ratio_bias_ramp_p10_to_p200_tailwind
```

The dry-run records `x=+5`, the Eastbound `ARSP-GPS≈-5` expectation, the
36 km cruise-follow mission, and the unchanged 21-event/1260-second schedule.
It does not publish wind or start SITL.

The healthy-tailwind live gate is one-way: Eastbound sign confirmation is
required and Westbound is recorded as unobserved, not treated as a failure.
The historical healthy-reference mission remains two-way and still requires
both directions. Healthy acceptance requires successful wind publication and
echo plus every mission-required realized sign check. Schedule completion on a
long no-RTL mission must not be reported as a planned RTL transition.

Terminal live manifests record distinct attempt-start and verdict-end UTC
timestamps plus wall duration. Their stimulus verification is finalized from
the monitor's actual injection and reset readbacks. `run_config.json` records
SHA-256/size provenance for the selected mission, parameter stack, workspace
Gazebo plugin, tracked diff, and every untracked workspace input. Do not accept
a governed tailwind attempt if any of those terminal/provenance fields are
missing or contradictory.

Scheduled mechanism analysis must use the BIN-native evidence contract:

- anchor each ramp/pulse window to its `SIM_ARSPD_RATIO` `PARM` transition;
- use only `CTUN.AsT=1` rows for sensor clamp/tracking checks;
- retain `ARSP.U` separately as the later parameter-disable state;
- for pulse ladders, report the first AHRS source rejection and first parameter
  disable across all fault windows.

Do not align a long SITL BIN directly to wall-clock injection UTC. SITL and
wall time drift, and doing so can mix a fault window with its reset window.

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

Example for an accepted full-sweep case:

```bash
./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure \
    --full-ratio-sweep --dry-run --case ratio_bias_m40
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

The headwind stepped-ramp and pulse-ladder cases are exceptions to the default
mission file. They use `assets/missions/airspeed_failure_headwind_ramp_mission.waypoints`
and `assets/missions/airspeed_failure_headwind_pulse_ladder_mission.waypoints`,
respectively: 100 m AGL, long Eastbound headwind missions with no RTL waypoint.
Existing fixed and one-bias ratio cases continue to use the reciprocal East/West
behavior mission.

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

For `ratio_bias_ramp_p10_to_p100_headwind` and
`ratio_bias_ramp_p10_to_p200_headwind`, `airspeed_injection.json` also contains
`injection_schedule` and `injection_events`; the attempt also writes
`airspeed_bias_ramp.json`. These cases are continuous stepped ramps with no
reset between levels. The +100 case is the standard characterization ramp; the
+200 case is the stronger failure-boundary probe.

For `ratio_bias_pulse_p10_to_p130_headwind`, `airspeed_injection.json` also
contains `injection_schedule` and `injection_events`; the attempt also writes
`airspeed_bias_pulse_ladder.json`. This case alternates baseline reset and fault
windows through +130.

`airspeed_signal_metrics` and `tecs_response` include per-phase summaries when
enough MAVLink samples are available. Use the vehicle `.BIN`/UAV log for final
TECS and elevator/servo interpretation; the JSON TECS artifact remains a MAVLink
proxy.

The Phase 2 measurement smoke accepted raw root is:
`var/runs/airspeed_failure_behavior_20260606T164050810132Z/`

**Nothing is promoted to `evidence/` automatically.** Promotion to
`evidence/curated_logs/airspeed_failure_behavior_<date>/` and an evidence report
under `evidence/reports/features/` happen only after explicit operator
direction. The first operator-directed interim promotion is
`evidence/curated_logs/airspeed_failure_behavior_2026-06-11/` with report
`evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`
and bounded acceptance report
`evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`
(Phase 4A ratio/ramp/pulse characterization accepted; fixed-case Phase 4B
remains open).

## Live SITL Runs — Gated

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

**Phase 4A is accepted for ratio/ramp/pulse characterization only.** The
2026-06-11 package covers 47 accepted observations from the signed ratio sweep,
headwind pulse ladder, and headwind stepped ramps. It does not close fixed-case
repetition coverage or full-lane acceptance.

Remaining fixed-case repetition work under the current contract:

| Case | Current accepted evidence | Minimum remaining accepted observations |
| --- | --- | --- |
| `healthy_reference` | 1 Phase 2 measurement-smoke observation | 2 if Phase 2 is explicitly reused for Phase 3; otherwise 3 dedicated Phase 3 observations |
| `ofs_noop_probe` | 1 Phase 2 measurement-smoke observation | 2 if Phase 2 is explicitly reused for Phase 3; otherwise 3 dedicated Phase 3 observations |
| `noise_5` | none | 3 |
| `noise_10` | none | 3 |
| `pitot_500pa` | 1 Phase 2 measurement-smoke observation | 2 if Phase 2 is explicitly reused for Phase 3; otherwise 3 dedicated Phase 3 observations |
| `fail_primary` | 1 Phase 2 measurement-smoke observation | 2 if Phase 2 is explicitly reused for Phase 3; otherwise 3 dedicated Phase 3 observations |

Before launching any remaining fixed-case Phase 4B live work, obtain explicit
authorization under ADR-0004 and record whether Phase 2 observations may be
reused toward the three-observation fixed-case count or whether the fixed
matrix must be rerun as a dedicated campaign.

The clean-run and workspace-built plugin policy is in
[governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md](../../governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md).

## Unit Tests

```bash
./env/bin/python3 -m unittest tests.unit.test_airspeed_failure_phase1
```

Covers case generation, parameter schema, injection trigger metadata,
classification helpers, artifact schemas, manifest accepted-observation
counting, no-SITL plugin construction, and the headwind ramp/pulse schedules.
Passes 27 tests as of the extended stepped-ramp implementation.

## Troubleshooting

**`ModuleNotFoundError` for `sim_ard_gaw`:** run `source setup.bash` first.
`setup.bash` exports `src/` on `PYTHONPATH`.

**`--dry-run` requires `--case`:** supply a case ID from `--list-cases`.

**Live command requires `--confirm-live-phase2`:** add the flag only after
confirming authorization under ADR-0004.

**Missing workspace Gazebo plugin:** live runs check for
`build/ardupilot_gazebo/libArduPilotPlugin.so` and fail closed if it is absent.
Build the workspace Gazebo plugin before any live attempt.
