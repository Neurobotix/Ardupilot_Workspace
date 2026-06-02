# Airspeed Failure Behavior Feature Plan

## Purpose

Build the first non-wind behavior plugin beside the CTE wind-matrix plugin.
This feature is a behavior-characterization lane: it deliberately degrades or
corrupts the airspeed signal, then records what the aircraft does.

The goal is to prove that `test_suite` can support a second sensor-behavior
family while preserving the same evidence discipline used for CTE. The plugin
must classify observed behavior, not implement recovery logic and not make a
safety certification claim.

The lane records outcomes such as mission completion, degraded completion,
mode containment, loss of mission progress, altitude loss, timeout, and
pre-injection failure.

## Selected Candidate

The v1 second-plugin candidate is locked as airspeed failure/degradation
behavior.

Airspeed is the best candidate for this phase because:

- CTE behavior depends on airspeed and wind behavior, so this lane is adjacent
  to the already accepted flight-engineering result.
- Existing evidence validates the airspeed chain:
  `evidence/curated_logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md`.
- Existing sensor-failure parameter research is available:
  `evidence/curated_logs/011_Sensor_Failure_Injection/sitl_sensor_failure_params.agent.json`.
- An existing airspeed mission is available:
  `assets/missions/airspeed_validation_mission.waypoints`.

## Out Of Scope

- No recovery, fallback, or controller-hardening implementation.
- No safety certification or operational safety claim.
- No multi-sensor fault combinations in v1.
- No GPS plugin in this phase.
- No broad second 23-case sensor matrix in v1.
- No code, scripts, or runtime outputs under `evidence/`.

## Behavior Vocabulary

The campaign classifies observation quality and behavior. A run can be a valid
observation even when the aircraft behavior is bad.

Behavior classes:

| Class | Meaning |
| --- | --- |
| `nominal_completion` | Mission completes without material degradation after injection. |
| `degraded_completion` | Mission completes, but with measurable degradation in tracking, speed, altitude, or timing. |
| `autopilot_contained` | Autopilot changes mode, aborts progress, or contains the situation without a clean mission completion. |
| `loss_of_control_or_timeout` | Aircraft behavior becomes uncontrolled for the lane criteria, or the attempt times out after a valid injection. |
| `pre_injection_failure` | Attempt fails before the planned injection point, so the fault was not usefully observed. |
| `analysis_incomplete` | Artifacts are insufficient for a behavior classification. |

## Default V1 Cases

| Case | Intended fault |
| --- | --- |
| `healthy_reference` | No airspeed fault; reference behavior. |
| `noise_5` | Moderate `SIM_ARSPD_RND` noise. |
| `noise_10` | Higher `SIM_ARSPD_RND` noise. |
| `ratio_1_3` | Airspeed ratio high bias. |
| `ratio_0_7` | Airspeed ratio low bias. |
| `pitot_500pa` | Pitot pressure offset fault. |
| `fail_primary` | Primary airspeed failure. |
| `sign_reversed` | Reversed airspeed sign behavior. |

## Feature Phases

### Phase 0 - Research And Case Design Lock

- Confirm airspeed as the v1 sensor candidate.
- Source the `SIM_ARSPD_*` parameter list from
  `evidence/curated_logs/011_Sensor_Failure_Injection/sitl_sensor_failure_params.agent.json`.
- Name the default mission and lane stack.
- Lock the eight v1 cases and the behavior-class vocabulary.
- Record that no accepted airspeed-failure behavior evidence exists yet.

### Phase 1 - No-SITL Plugin Foundation

- Add plugin package structure under
  `src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/`.
- Add a CLI entry point and registry entry.
- Support list-cases, dry-run, config validation, and plugin construction
  without starting SITL or Gazebo.
- Add no-SITL tests for cases, parameter schema, injection trigger metadata,
  classification, manifest accounting, and legacy wind-runner import blocking.

### Phase 2 - Live Smoke

- Run one `healthy_reference` smoke attempt under `var/runs/`.
- Run one `fail_primary` smoke attempt under `var/runs/`.
- Confirm injection by reading back every injected `SIM_ARSPD_*` parameter.
- Produce monitor and summary artifacts.
- Do not make a curated evidence claim in this phase.

### Phase 3 - Full V1 Campaign

- Run the full eight-case v1 matrix.
- Target three accepted observations per case.
- Count valid behavior observations, not only good flights.
- Assign behavior classes for each accepted observation.
- Describe failed or degraded flights as behavior outcomes when observation is
  valid.

### Phase 4 - Evidence Curation And Presentation Proof

- Curate a dated evidence package under
  `evidence/curated_logs/airspeed_failure_behavior_<date>/`.
- Add a dated evidence report under
  `evidence/reports/features/<date>_airspeed_failure_behavior.md`.
- Update the evidence catalog.
- Add only bounded presentation wording backed by the curated evidence.

## Default Stack

- Mission: `assets/missions/airspeed_validation_mission.waypoints`
- SITL target: `plane-cte`
- Gazebo target: `gazebo-plane-cte`
- Base params: `config/vehicles/plane_base.parm`
- Airspeed overlay: `config/overlays/plane_airspeed.parm`

## Injection Rule

- Publish the fixed reference wind before mission start.
- Inject the selected airspeed fault at mission sequence `4`.
- Read back every injected `SIM_ARSPD_*` parameter after injection.
- Write `airspeed_injection.json` for every attempt.

## Assumptions

- The runbook slug is `airspeed_failure_behavior`.
- Airspeed is the selected v1 sensor candidate.
- The goal is behavior characterization under degraded flight, not robust
  fallback design.
- A run can be a successful observation even when the aircraft behavior is bad.
- Raw runtime output stays in `var/`; curated proof only goes into `evidence/`.
