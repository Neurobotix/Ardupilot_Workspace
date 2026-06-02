# Airspeed Failure Behavior Implementation Runbook

## Implementation Status

This feature is planned and not implemented. This file defines the target
implementation shape for the airspeed failure behavior plugin.

## Code Homes

Implement the plugin package here:

```text
src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/
```

Planned modules:

| Module | Responsibility |
| --- | --- |
| `config.py` | Typed plugin config, path defaults, case selection, runtime-root naming. |
| `defaults.py` | Default mission, stack, params, case matrix, injection sequence, and acceptance defaults. |
| `case_generator.py` | Eight v1 case definitions and invalid-case rejection. |
| `environment.py` | Plane/Gazebo launch configuration and fixed reference wind setup. |
| `stimulus.py` | Airspeed fault parameter payloads and mission-sequence injection trigger. |
| `control.py` | Mission upload/start orchestration hooks owned by the plugin. |
| `monitor.py` | Attempt observation, timeout handling, sequence tracking, and artifact writing. |
| `analyzers.py` | Artifact parsing, observation-quality checks, and behavior classification. |
| `manifest.py` | Attempt summaries and accepted-observation counting. |
| `plugin.py` | Plugin factory and adapter wiring. |

Expose a plugin manifest from:

```text
src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/manifest.py
```

## CLI And Registry

Add the CLI:

```text
src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py
```

Add the registry key:

```text
airspeed_failure
```

in:

```text
src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py
```

The planned CLI must support at least:

```bash
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --list-cases
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --dry-run --case healthy_reference
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --dry-run --case fail_primary
```

No-SITL construction must not require importing the legacy wind runner.

## Runtime And Evidence Roots

Raw runtime output:

```text
var/runs/airspeed_failure_behavior_<timestamp>/
```

Curated evidence, after acceptance only:

```text
evidence/curated_logs/airspeed_failure_behavior_<date>/
```

Dated evidence report, after acceptance only:

```text
evidence/reports/features/<date>_airspeed_failure_behavior.md
```

Do not place plugin code, generated scripts, live runtime logs, or transient
analysis output in `evidence/`.

## Default Mission And Stack

Use:

| Item | Value |
| --- | --- |
| Mission | `assets/missions/airspeed_validation_mission.waypoints` |
| SITL | `plane-cte` |
| Gazebo | `gazebo-plane-cte` |
| Base params | `config/vehicles/plane_base.parm` |
| Airspeed overlay | `config/overlays/plane_airspeed.parm` |

## Default Cases

The v1 plugin must generate these cases:

```text
healthy_reference
noise_5
noise_10
ratio_1_3
ratio_0_7
pitot_500pa
fail_primary
sign_reversed
```

Case generation must reject unknown case IDs before launch.

## Parameter Schema

The v1 schema is sourced from:

```text
evidence/curated_logs/011_Sensor_Failure_Injection/sitl_sensor_failure_params.agent.json
```

Required `SIM_ARSPD_*` parameters:

```text
SIM_ARSPD_FAIL
SIM_ARSPD_FAILP
SIM_ARSPD_PITOT
SIM_ARSPD_OFS
SIM_ARSPD_RND
SIM_ARSPD_RATIO
SIM_ARSPD_SIGN
```

The implementation must validate the parameter payload before launch and must
record readback success or failure after injection.

## Injection Rule

For every live attempt:

1. Publish the fixed reference wind before mission start.
2. Start the mission with the default airspeed validation mission.
3. Detect mission sequence `4`.
4. Inject the selected airspeed fault by setting the relevant `SIM_ARSPD_*`
   parameters.
5. Read back every injected parameter.
6. Write `airspeed_injection.json` with requested values, readback values,
   timestamps, mission sequence, and readback status.

## Behavior Classification

The analyzer classifies observation quality and behavior, not safety.

Behavior classes:

```text
nominal_completion
degraded_completion
autopilot_contained
loss_of_control_or_timeout
pre_injection_failure
analysis_incomplete
```

The manifest must count accepted behavior observations. A degraded or failed
flight can count when the injection occurred and the artifacts are sufficient
to classify behavior.

## Required No-SITL Tests

- Case generation for all eight cases.
- Invalid case rejection.
- `SIM_ARSPD_*` parameter schema validation.
- Injection trigger metadata at mission sequence `4`.
- Parameter readback success and failure handling.
- Behavior-class classification.
- Manifest accepted-count logic counts valid observations, not only good
  flights.
- Plugin construction with legacy wind-runner imports blocked.
- CLI `--list-cases`.
- CLI `--dry-run`.

## Required Live Gates

- One `healthy_reference` smoke run.
- One `fail_primary` smoke run.
- Review of smoke artifacts before the full v1 matrix.
- Full v1 matrix only after smoke evidence is reviewed.

## Workspace Checks

Run after runbook, docs, evidence, or governance changes:

```bash
make doctor
```

Run relevant unit tests for the new plugin when implementation begins. Run
build or presentation checks only if presentation files are touched.
