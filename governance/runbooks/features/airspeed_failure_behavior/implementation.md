# Airspeed Failure Behavior Implementation Runbook

## Implementation Status

Phase 1 no-SITL foundation is accepted as of 2026-06-05. The plugin package,
dry-run CLI, registry entry, case generator, parameter schema validation,
artifact schemas, classifier helpers, manifest accepted-observation counting,
and no-SITL tests exist.

Phase 2 live measurement smoke is accepted as of 2026-06-06 from raw root
`var/runs/airspeed_failure_behavior_20260606T164050810132Z/`. The implementation
owns its SITL/Gazebo process launch, workspace-built Gazebo plugin gate, MAVLink
readiness, mission upload and download verification, pre-mission fixed-wind
publish plus strict echo, boot-baseline parameter capture, seq-4 injection,
injected-parameter readback, reset-to-boot-baseline, raw attempt artifact
writing, behavior classification, wind-sign backfill, provisional healthy bands,
and the Phase 2 `OFS` no-op / `FAILP=500` measurement probes. No curated feature
evidence or Phase 4 behavior claim is made by this implementation status.

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
| `case_generator.py` | Fixed case definitions plus the ratio-sweep thin slice and invalid-case rejection. |
| `environment.py` | Plane/Gazebo launch configuration and fixed reference wind setup. |
| `stimulus.py` | Airspeed fault parameter payloads and mission-sequence injection trigger. |
| `control.py` | Mission upload/start orchestration hooks owned by the plugin. |
| `monitor.py` | Attempt observation, timeout handling, sequence tracking, and artifact writing. |
| `analyzers.py` | Airspeed-specific artifact parsing, observation-quality checks, and behavior classification. |
| `manifest.py` | Attempt summaries and accepted-observation counting. |
| `plugin.py` | Plugin factory and adapter wiring. |

The airspeed plugin must not rely on existing CTE/square analyzers as its
primary scorer. CTE/path-quality outputs may be attached only as optional
supporting analysis when an attempt flies enough route geometry.

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

The Phase 2 guarded live smoke entrypoint is:

```bash
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --live-smoke --confirm-live-phase2
```

It runs exactly `healthy_reference` and `fail_primary` under `var/runs/` and
does not promote output to curated evidence. The confirmation flag is required
so Phase 2 cannot launch SITL/Gazebo accidentally from a discovery command.

The accepted Phase 2 measurement-smoke entrypoint is:

```bash
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --live-measurement-probes --confirm-live-phase2
```

It runs `healthy_reference`, `ofs_noop_probe`, `pitot_500pa`, and
`fail_primary` under `var/runs/` and does not promote output to curated
evidence.

No-SITL construction must not require importing the legacy wind runner.
The dedicated airspeed CLI may own its own argument surface for Phase 1. Broad
de-winding of the existing generic `run_case.py` and `run_suite.py` CLIs is not
required unless implementation chooses to route live runs through them.

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
| Mission | `assets/missions/airspeed_failure_behavior_mission.waypoints` |
| SITL | `plane-cte` |
| Gazebo | `gazebo-plane-cte` |
| Base params | `config/vehicles/plane_base.parm` |
| Airspeed overlay | `config/overlays/plane_airspeed.parm` |

Mission (resolved 2026-06-03): the lane uses the new purpose-built
`airspeed_failure_behavior_mission.waypoints` (100 m cruise, 800 m reciprocal
East/West measurement legs, inject on entering seq 4, ends in RTL with no landing
sequence). The legacy `airspeed_validation_mission.waypoints` is the old
integration mission and is NOT used. See the Mission Design ADR in
`design_adrs.md`.

Overlay boundary (resolved 2026-06-03): `config/overlays/plane_airspeed.parm` is
the conservative production-like default (`AIRSPEED_CRUISE 14`, `AIRSPEED_MIN
10`, `AIRSPEED_MAX 22`). The aggressive high-wind CTE tuning is preserved
separately in `config/overlays/plane_airspeed_cte_high_wind_aggressive.parm` and
is not part of the default stack. The mission's `15 m/s` command is inside the
`14/22` envelope, so the default stack is appropriate. Record the effective stack
and hashes in `run_config.json` for every attempt. If a future case needs a
different envelope, name a dedicated shared overlay under `config/` explicitly
instead of re-aggressing the default.

## Cases

Fixed (non-ratio) cases the plugin must generate:

```text
healthy_reference          # assert source defaults
noise_5                    # SIM_ARSPD_RND=5
noise_10                   # SIM_ARSPD_RND=10
pitot_500pa                # SIM_ARSPD_FAILP=500 (NOT SIM_ARSPD_PITOT alone)
fail_primary               # SIM_ARSPD_FAIL=1 (forced ~1 m/s; single case)
sign_reversed              # SIM_ARSPD_SIGN=1
```

Ratio cases are a parameterized **signed-percentage airspeed-bias sweep**, not a
fixed pair. The generator takes a list of `bias_percent` values and emits
`ratio_bias_pNN` (reads high) / `ratio_bias_mNN` (reads low) cases. Dry-run
values use the configured `vehicle_arspd_ratio` as a planning recipe. Live
attempts must recompute `SIM_ARSPD_RATIO = ARSPD_RATIO / k^2`
(`k = 1 + bias_percent/100`) from the measured MAVLink `ARSPD_RATIO` readback
after clean SITL boot and before injection. End goal: `+10..+100%` and
`-10..~-50/-70%`. v1 thin slice: `±10/30/50`. The generator must clamp/refuse
`bias_percent` beyond a configured low-side floor (~−70%; below that the flight
is just "stuck near zero", which is the `fail_primary`/`sign_reversed` regime).
See the Case Payloads And Ratio Sweep ADR in `design_adrs.md`.

Case generation must reject unknown case IDs before launch.

Each generated case must include:

- exact (or recipe-computed) `SIM_ARSPD_*` injection payload;
- exact reset/default payload (SOURCE DEFAULTS, not zeros);
- units and semantic notes for each parameter;
- expected readback rule and tolerance;
- trigger point metadata (entering seq 4);
- acceptance thresholds or expected observation-quality requirements.

Locked semantics the generator must encode (do not infer from names):
`SIM_ARSPD_FAIL` is a forced m/s value (`fail_primary`=1), `SIM_ARSPD_OFS` is a
no-op on `TYPE 100`, `SIM_ARSPD_PITOT` needs `FAILP!=0`, and ratio bias is the
`ARSPD_RATIO/k^2` recipe computed from the measured vehicle ratio.

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
Before live campaign use, verify these parameter names against the SITL build
under test. The Phase 2 live path reads all required names from the clean booted
vehicle before wind/mission/injection and fails closed on missing, renamed, or
source-default-mismatched values. A missing or renamed parameter blocks live
evidence.

## Injection Rule

For every live attempt:

1. Publish the fixed reference wind (`x=-5, y=0, z=0` m/s, Gazebo ENU) before
   mission start and write `reference_wind.json` with requested vector, frame,
   topic, readback/echo, tolerance, and success or failure. Strict echo is a hard
   gate.
2. Start the mission with `airspeed_failure_behavior_mission.waypoints`.
3. Detect the locked injection trigger: **entering seq 4** — the first
   `MISSION_CURRENT` message with `seq == 4` after confirmed front-half progress
   (seq 1..3, AUTO, armed), first-edge latched. A missed/late trigger is a
   `pre_injection_failure`, never a late injection. See the Injection Trigger ADR
   in `design_adrs.md`.
4. Inject the selected airspeed fault by setting the relevant `SIM_ARSPD_*`
   parameters.
5. Read back every injected parameter.
6. Write `airspeed_injection.json` with requested values, readback values,
   timestamps, trigger event, mission sequence, readback status, and reset
   payload.
7. Reset injected parameters before or after each attempt and preserve reset
   status in artifacts or cleanup logs.

## Required Analysis Artifacts

The plugin analyzer must produce airspeed-specific outputs under the attempt
directory. Required outputs are:

| Artifact | Purpose |
| --- | --- |
| `airspeed_behavior_summary.json` | Behavior class, observation-quality class, acceptance decision, and reason. |
| `airspeed_signal_metrics.json` or `.csv` | Pre/post injection airspeed, groundspeed, airspeed-minus-groundspeed, and fault-visible deltas. |
| `mission_progress.json` | Injection seq, max seq reached, completion (planned seq-9 RTL reached + stabilized), AUTO->RTL transition seq (planned vs fault-triggered), timeout, and loss-of-progress markers. |
| `mode_timeline.json` or `.csv` | Mode changes and relevant status text after injection. |
| `altitude_speed_envelope.json` | Post-injection altitude and speed envelope, threshold crossings, altitude loss, and excursions. |
| `tecs_response.json` | Throttle, pitch, and speed/height-control summaries when log fields are available. |

The analyzer must mark an attempt `analysis_incomplete` when required artifacts
or required log fields are missing. Optional TECS outputs may be omitted only
when the summary records that the source fields were unavailable and the
remaining artifacts still support behavior classification.

Phase 2 live smoke writes TECS response from MAVLink `VFR_HUD` throttle,
`ATTITUDE` pitch, and speed/height samples. BIN `TECS`/`CTUN` field parsing is
not required for smoke acceptance unless the dated smoke review decides the
MAVLink fields are insufficient for classification; in that case the smoke
review must block Phase 3 or require a rerun with expanded log extraction.

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

Observation-quality logic must be separate from behavior class. A bad flight is
accepted as an observation only when injection succeeded, enough post-injection
flight was observed, and required artifacts exist. Failed launch, failed
readback, pre-injection failure, and incomplete analysis do not count as
accepted behavior observations.

## Required No-SITL Tests

- Case generation for the fixed cases and the ratio-sweep recipe (including the
  v1 thin slice and the low-side clamp/refusal guard).
- Invalid case rejection.
- `SIM_ARSPD_*` parameter schema validation.
- Runtime parameter-probe path for the required `SIM_ARSPD_*` names.
- Exact case payload and reset payload serialization.
- Injection trigger metadata for entering seq `4` (first `MISSION_CURRENT`
  `seq==4` edge after front-half progress).
- Parameter readback success and failure handling.
- Fixed-wind artifact schema.
- Airspeed analysis artifact schema.
- Behavior-class classification.
- Observation-quality classification and accepted-observation gating.
- Manifest accepted-count logic counts valid observations, not only good
  flights.
- Plugin construction with legacy wind-runner imports blocked.
- CLI `--list-cases`.
- CLI `--dry-run`.

## Required Live Gates

- One `healthy_reference` smoke run.
- One `ofs_noop_probe` measurement run.
- One `pitot_500pa` measurement run.
- One `fail_primary` smoke run.
- Review of measurement-smoke artifacts before the full v1 matrix.
- A dated smoke-review note or `review.md` update with raw run roots, artifact
  checklist, and Phase 3 gate decision.
- Full v1 matrix only after smoke evidence is reviewed.

## Workspace Checks

Run after runbook, docs, evidence, or governance changes:

```bash
make doctor
```

Run relevant unit tests for the new plugin when implementation begins. Run
build or presentation checks only if presentation files are touched.
