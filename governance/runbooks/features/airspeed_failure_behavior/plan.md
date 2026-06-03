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

CTE is not the primary score for this lane. It can be retained as a supporting
path-quality metric only when an attempt completes enough route geometry to
make path analysis meaningful. The primary observations are airspeed signal
behavior, mission progress, mode containment, altitude/speed envelope, TECS or
throttle response where available, timeout/loss-of-progress behavior, and
whether the injected fault was actually applied and read back.

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
- The legacy airspeed integration mission
  (`assets/missions/airspeed_validation_mission.waypoints`) informed the design,
  but this lane uses a new purpose-built mission
  (`assets/missions/airspeed_failure_behavior_mission.waypoints`).

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

Behavior classification must be driven by explicit observation-quality rules.
At minimum, the analyzer must know whether injection occurred, whether readback
matched, how much post-injection flight was observed, the maximum mission
sequence reached, mode changes after injection, minimum altitude after
injection, timeout reason, and whether required log fields were available.

## Cases (locked with operator 2026-06-03)

Exact payloads and the full rationale are in
`governance/runbooks/features/airspeed_failure_behavior/design_adrs.md`
("ADR (Proposed): Airspeed Failure Case Payloads And Ratio Sweep"), grounded by
`design_research.md`. Summary:

Fixed (non-ratio) cases:

| Case | Fault payload |
| --- | --- |
| `healthy_reference` | none; assert source defaults |
| `noise_5` | `SIM_ARSPD_RND=5` (Pa) |
| `noise_10` | `SIM_ARSPD_RND=10` (Pa) |
| `pitot_500pa` | `SIM_ARSPD_FAILP=500` (Pa); NOT `SIM_ARSPD_PITOT` alone |
| `fail_primary` | `SIM_ARSPD_FAIL=1` (forced ~1 m/s stuck-low; single case, no variations) |
| `sign_reversed` | `SIM_ARSPD_SIGN=1` (pressure sign flip -> airspeed ~0) |

Ratio cases are a **signed-percentage reported-airspeed bias sweep**, not a
2-case pair. End goal: `+10..+100%` (reads high) and `-10..~-50/-70%` (reads
low), one bias per flight. The injected param is computed per case from the
measured vehicle ratio: `SIM_ARSPD_RATIO = ARSPD_RATIO / k^2`, `k = 1 +
bias_percent/100`. Naming `ratio_bias_pNN` / `ratio_bias_mNN` (encodes the
airspeed effect, not the param value). The case generator is a recipe: feed it a
list of `bias_percent` values. v1 flies a thin slice (e.g. ±10/30/50) to prove
the chain; the full sweep is the documented end goal the foundation is built for.

Key locked semantics (do NOT infer from case names during implementation):

- `SIM_ARSPD_FAIL` is a forced airspeed VALUE in m/s, not a boolean enable.
  `fail_primary` requests `1`.
- `SIM_ARSPD_OFS` has NO effect on `ARSPD_TYPE 100`; it is not used by any case.
- `SIM_ARSPD_RATIO` biases airspeed only via mismatch with the vehicle
  `ARSPD_RATIO` (source default 2); ratio-case numbers are computed from the
  measured vehicle ratio in Phase 2, not hard-coded.
- Reset restores SOURCE DEFAULTS (`RND=2.0, RATIO=1.99, ...`), not zeros.

Before live runs, each case must have an exact (or recipe-computed) parameter
payload, reset payload, units, and expected readback rule.

## Feature Phases

### Phase 0 - Research And Case Design Lock

- Confirm airspeed as the v1 sensor candidate.
- Source the `SIM_ARSPD_*` parameter list from
  `evidence/curated_logs/011_Sensor_Failure_Injection/sitl_sensor_failure_params.agent.json`.
- Name the default mission and lane stack.
- Lock the case design (fixed cases + ratio sweep recipe + v1 thin slice),
  injection trigger, reference wind, reset protocol, mission design, and the
  behavior-class vocabulary. (Done 2026-06-03: see `design_research.md` and
  `design_adrs.md`.)
- Record that no accepted airspeed-failure behavior evidence exists yet.

### Phase 1 - No-SITL Plugin Foundation

- Add plugin package structure under
  `src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/`.
- Add a CLI entry point and registry entry.
- Support list-cases, dry-run, config validation, and plugin construction
  without starting SITL or Gazebo.
- Add no-SITL tests for cases, parameter schema, injection trigger metadata,
  classification, manifest accounting, and legacy wind-runner import blocking.
- Add no-SITL tests for the airspeed analyzers and their required output schema.
- Add a runtime parameter-probe mode or dry-run validation path that can verify
  the required `SIM_ARSPD_*` names against the SITL build before a live matrix.

### Phase 2 - Live Smoke

- Run one `healthy_reference` smoke attempt under `var/runs/`.
- Run one `fail_primary` smoke attempt under `var/runs/`.
- Confirm injection by reading back every injected `SIM_ARSPD_*` parameter.
- Produce monitor and summary artifacts.
- Produce a dated smoke-review note in this runbook bundle, or update
  `review.md` with the exact raw run roots, artifact checklist, and gate
  decision before Phase 3 starts.
- Do not make a curated feature evidence claim in this phase.

### Phase 3 - Full V1 Campaign

- Run the v1 case set: the fixed cases plus the v1 thin ratio slice (e.g.
  `ratio_bias_p10/p30/p50` and `ratio_bias_m10/m30/m50`). The full ±10..±100
  ratio sweep is the end goal, run after v1 proves the chain.
- Target three accepted observations per case.
- Count valid behavior observations, not only good flights.
- Assign behavior classes for each accepted observation.
- Describe failed or degraded flights as behavior outcomes when observation is
  valid.
- Require the airspeed-specific analysis artifacts for every accepted
  observation. CTE/square analysis may be attached only as supporting context.

### Phase 4 - Evidence Curation And Presentation Proof

- Curate a dated evidence package under
  `evidence/curated_logs/airspeed_failure_behavior_<date>/`.
- Add a dated evidence report under
  `evidence/reports/features/<date>_airspeed_failure_behavior.md`.
- Update the evidence catalog.
- Add only bounded presentation wording backed by the curated evidence.

## Default Stack

- Mission: `assets/missions/airspeed_failure_behavior_mission.waypoints`
  (new purpose-built mission: 100 m cruise, 800 m reciprocal East/West
  measurement legs, inject on entering seq 4, ends in RTL with no landing. The
  old `airspeed_validation_mission.waypoints` is the legacy integration mission
  and is NOT used here. See the Mission Design ADR in `design_adrs.md`.)
- SITL target: `plane-cte`
- Gazebo target: `gazebo-plane-cte`
- Base params: `config/vehicles/plane_base.parm`
- Airspeed overlay: `config/overlays/plane_airspeed.parm`

Overlay boundary (resolved 2026-06-03): `config/overlays/plane_airspeed.parm` is
now the conservative production-like default (`AIRSPEED_CRUISE 14`,
`AIRSPEED_MIN 10`, `AIRSPEED_MAX 22`), matching the recovered production-era
overlay and the accepted CTE wind-envelope evidence. The aggressive high-wind
CTE tuning that previously lived in this file was moved to the separately named
`config/overlays/plane_airspeed_cte_high_wind_aggressive.parm` (a stress profile
that is not wired into any default stack). The validation mission's `15 m/s`
command sits inside the conservative `14/22` envelope, so the prior high-wind
coupling concern no longer applies to the default stack. The run config must
still record the effective parameter-file list and hashes for each attempt. If
a future case needs a different airspeed envelope, name a dedicated shared
overlay under `config/` explicitly rather than re-aggressing the default.

## Injection Rule (locked with operator 2026-06-03)

Full contracts are in `design_adrs.md` (Trigger, Reference Wind, Reset ADRs).

- **Reference wind:** fixed Gazebo world-frame ENU `x=-5, y=0, z=0` m/s,
  published before mission start, verified by strict `gz topic` echo (hard gate;
  unverified wind = not an accepted observation). Confirm the wind sign in smoke
  (`ARSP−GPS ≈ +5` Eastbound). Record vector, topic, tolerance, readback in
  `reference_wind.json`.
- **Trigger:** inject on **entering seq 4** — the first `MISSION_CURRENT` message
  with `seq == 4` after confirmed front-half progress (seq 1..3 in AUTO while
  armed), first-edge latched, never re-fired. This places the fault at the start
  of the 800 m East headwind measurement leg. A missed/late trigger is a
  `pre_injection_failure`, not a late injection. Record requested vs actual.
- Read back every injected `SIM_ARSPD_*` parameter after injection.
- Write `airspeed_injection.json` for every attempt (incl. the computed
  `SIM_ARSPD_RATIO` and `bias_percent`/`k`/`vehicle_arspd_ratio` for ratio cases).
- **Reset:** per-attempt fresh SITL process is the primary isolation; reset
  restores the captured boot baseline (SOURCE DEFAULTS, not zeros) and is read
  back. Reset result visible in artifacts/cleanup logs.
- **Completion:** the mission ends in RTL. Completion = front-half progress +
  both measurement legs + planned seq-9 RTL reached and stabilized. A
  fault-triggered early RTL/failsafe (before the legs finish) is
  `autopilot_contained`, not completion.

## Required Analysis Outputs

The plugin needs airspeed-specific analysis. Existing CTE/square scripts are
not sufficient as the primary scorer.

Required attempt-level outputs:

- `airspeed_injection.json`: requested payload, trigger event, readback values,
  reset/default values, success or failure, and timestamps.
- `reference_wind.json`: requested fixed wind, publication method, readback or
  echo result, tolerance, and frame note.
- `airspeed_behavior_summary.json`: behavior class, observation-quality class,
  acceptance decision, and human-readable reason.
- `airspeed_signal_metrics.csv` and/or `.json`: pre/post-injection airspeed,
  groundspeed, airspeed-minus-groundspeed, and fault-visible deltas.
- `mission_progress.json`: injection sequence, max sequence reached,
  completion (planned seq-9 RTL reached + stabilized), AUTO->RTL transition seq
  (planned vs fault-triggered), timeout, and loss-of-progress markers.
- `mode_timeline.csv` and/or `.json`: mode changes and relevant status text
  after injection.
- `altitude_speed_envelope.json`: post-injection altitude minimum, altitude
  loss, climb/sink excursions, groundspeed/airspeed excursions, and threshold
  crossings.
- `tecs_response.json` when log fields are available: throttle, pitch, and
  speed/height-control response summaries.

Missing required outputs make an attempt `analysis_incomplete` unless the
missing field is explicitly marked optional for the case and the remaining
artifacts are sufficient for classification.

## Assumptions

- The runbook slug is `airspeed_failure_behavior`.
- Airspeed is the selected v1 sensor candidate.
- The goal is behavior characterization under degraded flight, not robust
  fallback design.
- A run can be a successful observation even when the aircraft behavior is bad.
- Raw runtime output stays in `var/`; curated proof only goes into `evidence/`.
