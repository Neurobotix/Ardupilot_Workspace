# GPS Failure Behavior Feature Plan

## Purpose

Build the third behavior-characterization lane on `test_suite`, beside the CTE
wind-matrix plugin (Lane 1) and the airspeed_failure plugin (Lane 2). This lane
deliberately degrades or corrupts the GPS signal mid-flight, then records what
the aircraft — and the EKF underneath it — does.

The goal is to characterize the full response spectrum from *no visible effect*
to *loss of control*, using real-world GPS failure modes rather than
simulation-only artifacts. The lane classifies observed behavior; it does not
implement recovery logic and does not make a safety-certification claim.

GPS is a deliberately different case from airspeed. Airspeed degradation
corrupts a control input; GPS degradation corrupts the vehicle's *belief about
where it is*, which the EKF actively accepts or rejects through its own
innovation gate. That gate makes GPS the sharpest available "knee" experiment:
there is a measurable boundary — the drift rate at which the EKF flips from
silently fusing a drifting fix to rejecting it — and it is defined by
ArduPilot's own gate, not by a threshold we invent.

The platform contrast this lane completes: airspeed is *lose the input, degrade
control*; GPS spans *lose the fix and survive via dead-reckoning* (hard denial)
through *believe a lie and fly into a hill while reporting healthy* (slow
drift). The dangerous outcome is not the loudest one.

## Selected Candidate

The v3 plugin candidate is GPS failure/degradation behavior.

GPS is the right next lane because:

- It is a maximally different sensor from airspeed at the fusion level — it
  exercises the EKF position-innovation path, which airspeed never touches — so
  it re-proves the framework is sensor-agnostic on a genuinely new mechanism.
- SITL exposes a rich, real, injectable GPS fault surface (`SIM_GPS1_*`:
  glitch, enable, jam, numsats, drift, lag, accuracy, velocity error), verified
  against `src/ardupilot/libraries/SITL/SIM_GPS.cpp` (`GPSParms`).
- Prior GPS parameter research exists:
  `evidence/curated_logs/011_Sensor_Failure_Injection/`.
- The behavior story is publishable: the slow-drift-evades-the-gate phenomenon
  is a known concern in the security literature, and this lane characterizes it
  on a real autopilot as a measured campaign.

## Out Of Scope

- No recovery, fallback, or controller-hardening implementation.
- No safety certification or operational safety claim.
- No multi-sensor fault combinations in v1 (modifier layering is future work).
- No compass/IMU/baro lane in this phase.
- No code, scripts, or runtime outputs under `evidence/`.

## The Knee (measurable core)

The central experiment is finding the **knee**: the boundary between the EKF
fusing a corrupted GPS fix and rejecting it. It is measured on two tiers.

- **Mechanism tier (primary knee signal):** did the EKF admit the fix? Read from
  the position innovation test ratio `posTestRatio` and reject/glitch flags
  (`EKF_STATUS_REPORT` live; `NKF*`/`XKF*` innovations + reset events in the BIN
  log). The knee is defined as the drift rate at which `posTestRatio` crosses
  `1.0` — ArduPilot's own gate boundary, width set by `EK3_POS_I_GATE`, not a
  threshold we invented. Below the knee: `posTestRatio < 1` → fused → silent
  drift. Above: `posTestRatio >= 1` → rejected → eventually
  `posTimeout`/`EK3_GLITCH_RAD` reset.
- **Behavior tier (why it matters):** did the aircraft act on it? Read from the
  believed-vs-truth horizontal position excursion, attitude/altitude band, and
  mode/failsafe changes.

The tiers can disagree: a fix can be admitted (`posTestRatio < 1`) yet barely
move the belief because the Kalman gain is small. **Accepted is not captured** —
only sustained, cumulative drift walks the belief off. The behavior tier catches
that accumulation; the mechanism tier defines the knee.

Live gate parameters (`EK3_POS_I_GATE`, `EK3_GLITCH_RAD`) set exactly where
`1.0` lands in m/s. Reading them live is a Phase 2 must-measure, not a Phase 0
assumption.

## Behavior Vocabulary

The campaign classifies observation quality and behavior. A run can be a valid
observation even when aircraft behavior is bad. **The ladder orders by how much
the system reacts, not by danger.** Detection and danger are separate axes: the
most dangerous cell is low-reaction-but-wrong (`silent_drift`), where the
autopilot flies the aircraft off course while reporting healthy.

| Band | Meaning (GPS terms) |
| --- | --- |
| `nominal` | No visible effect. Belief tracks truth; `posTestRatio < 1` healthy; no mode change. |
| `silent_drift` | The headline danger. Belief walks off truth, fused throughout, no alarm. |
| `detected_rejected` | Fault caught: sustained rejection, EKF variance climbs, failsafe flags. |
| `reset_captured` | EKF hit the reset path — snapped belief onto the faulted GPS. |
| `autopilot_contained` | Mode change / RTL / failsafe action fired. |
| `loss_of_control` | Attitude/altitude excursion beyond band, or crash/unexpected disarm. |
| `pre_injection_failure` | Fault never took hold before the trigger → no useful observation (discard, off-ladder). |

No single field names `silent_drift`. It is a conjunction — **fused AND
gap-growing AND no-failsafe**. Each field alone is ambiguous; only all three
together name the "accepted, moving, unnoticed" signature. This is why the
truth-vs-belief gap must be logged: it is the only field that reveals a lie the
filter itself believes is fine.

Raw signals per band:

| Band | Signals |
| --- | --- |
| `nominal` | `posTestRatio < 1` throughout; gap ~ 0; no MODE/failsafe |
| `silent_drift` | fused (`< 1`) AND gap growing large AND no failsafe/flag |
| `detected_rejected` | `posTestRatio >= 1` sustained; variance climbing; EKF STATUSTEXT/MSG |
| `reset_captured` | ResetPosition event / belief discontinuity in `NKF*`; variance snap-back |
| `autopilot_contained` | MODE/HEARTBEAT change after injection |
| `loss_of_control` | ATT/CTUN/altitude beyond control band; unexpected disarm |
| `pre_injection_failure` | injection readback absent before trigger seq |

Mechanism-tier sources: `posTestRatio` / innovations / reject flags
(`EKF_STATUS_REPORT` live, `NKF*`/`XKF*` + reset events in BIN). Behavior-tier
sources: believed-vs-truth excursion (m), attitude/altitude, num_sats/lock,
MODE/HEARTBEAT, STATUSTEXT/MSG.

## Cases (locked 2026-07-06)

Four headline faults; all four are in v1. Exact payloads and full rationale are
in `design_adrs.md`, grounded by `design_research.md`. Summary:

| # | Fault | Knob(s) | Real-world case | Role |
| --- | --- | --- | --- | --- |
| 1 | `slow_drift` | `SIM_GPS1_GLTCH_{X,Y}` re-injected as a growing ramp | GPS spoofing / slow position capture | Headline — silent, below-the-knee capture |
| 2 | `step_glitch` | `SIM_GPS1_GLTCH_{X,Y}` fixed offset | multipath jump / sudden position pop | Contrast — above-the-knee, caught then reset |
| 3 | `hard_denial` | `SIM_GPS1_ENABLE=0` | antenna/receiver loss, tunnel, total denial | Control anchor — resilient dead-reckoning |
| 4 | `jamming` | `SIM_GPS1_JAM=1` | RF jamming (blackout + chaotic garbage) | Headline — loud, incoherent, self-betraying |

Design key: faults 1 and 2 share the same knob (`GLTCH`) — the only difference
is onset rate. That is deliberate: it isolates onset rate as the single
independent variable in the central knee experiment.

### Severity envelopes (each fault, one independent variable)

| Fault | Independent variable | Sweep |
| --- | --- | --- |
| `slow_drift` | drift rate | `0.2 / 0.5 / 1.0 / 2.0 / 4.0 / 8.0` m/s, one rate per flight, each from clean baseline |
| `step_glitch` | offset magnitude | `10 / 25 / 50 / 100 / 200 / 500` m, one per flight |
| `hard_denial` | denial duration | `5 / 15 / 30 / 60` s, then restore `ENABLE=1` |
| `jamming` | (binary) repeats | `JAM=1`, 30–60 s window, 5+ repeats (stochastic) |

Second instrument for `slow_drift`: one continuous ramp with no reset, which
measures accumulation/endurance ("how bad does it get as drift piles up"), not
the clean knee.

Locked semantics (do NOT infer during implementation):

- **GPS drift has memory.** An accepted drift drags the belief and the belief
  carries forward; zeroing the param does not wipe the corrupted belief. So each
  drift rate needs a clean flight from truth — one rate per flight. A later
  window in the same flight starts from an already-wrong belief and is
  contaminated. The airspeed-style in-flight pulse-with-reset schedule is
  **dropped** for GPS because the reset is not clean.
- `slow_drift` and `step_glitch` share `GLTCH`; they differ only in onset rate.
- `jamming` has no internal severity dial — the routine self-parametrizes with
  its own randomness. Severity is expressed through duration and repeats.
- `NUMSATS` does not drop `have_lock` mid-flight; it is a pre-arm readiness gate
  only and is excluded as a headline fault. See the excluded-knob table in
  `design_research.md`.

If the knee lands outside the drift bracket, extend the rate list — the ramp
generator takes a rate list, so extending is a longer input, no code change.

## Feature Phases

### Phase 0 - Research And Case Design Lock

- Confirm GPS as the v3 sensor candidate.
- Source `SIM_GPS1_*` from `src/ardupilot/libraries/SITL/SIM_GPS.cpp`
  (`GPSParms`) and prior research
  `evidence/curated_logs/011_Sensor_Failure_Injection/`.
- Lock the fault catalog, severity envelopes, the two-tier knee definition, the
  behavior-class vocabulary, injection trigger, mission geometry, control run,
  and the characterize-not-gate verdict model. (Done 2026-07-06: see
  `design_research.md` and `design_adrs.md`.)
- Record the Phase 0 baseline that no accepted GPS-failure behavior evidence
  existed before implementation and live measurement.

### Phase 1 - No-SITL Plugin Foundation

- Add plugin package under
  `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/`, built from the
  `airspeed_failure` plugin template.
- Add a CLI entry point and registry entry.
- Support list-cases, dry-run, config validation, and plugin construction
  without starting SITL or Gazebo.
- Add no-SITL tests for cases, the sweep generators (drift/step/denial ladders),
  the `SIM_GPS1_*` parameter schema, injection trigger metadata, the two-tier
  classification, and manifest accounting.
- Add a parameter-probe / dry-run path that can verify the required `SIM_GPS1_*`
  names against the SITL build before a live matrix.

### Phase 2 - Live Smoke

- Run one `nominal` (no-fault control) smoke attempt under `var/runs/`.
- Run one `slow_drift` and one `hard_denial` smoke attempt under `var/runs/`.
- Confirm injection by reading back every injected `SIM_GPS1_*` parameter.
- **Must-measure:** read live `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`,
  `FS_EKF_THRESH`, `EK3_GPS_CHECK`; confirm the realized straight-leg duration;
  locate the empirical knee bracket.
- Produce monitor and summary artifacts; record the raw run roots and gate
  decision in `review.md` before Phase 3.
- Do not make a curated feature evidence claim in this phase.

### Phase 3 - Full V1 Campaign

- Run the full v1 catalog: the `nominal` control plus all four fault sweeps.
- Target >= 3 accepted observations per case; jamming gets 5+ (stochastic).
- Count valid behavior observations, not only good flights.
- Assign a behavior band to each accepted observation.
- Report the knee: the drift rate at which the mechanism tier flips from
  `silent_drift` to `detected_rejected`.

### Phase 4 - Evidence Curation And Presentation Proof

- Curate a dated package under `evidence/curated_logs/gps_failure_behavior_<date>/`.
- Add a dated report under `evidence/reports/features/<date>_gps_failure_behavior.md`.
- Update the evidence catalog.
- Add only bounded presentation wording backed by the curated evidence.

## Default Stack

- Mission: a new `assets/missions/gps_failure_behavior_mission.waypoints`, based
  on the **long one-way** airspeed mission
  `airspeed_failure_eastbound_long_speed_15_mission.waypoints` (36 km WP3→WP4
  straight leg), NOT the short 800 m behavior mission. Three deliberate changes
  from the short template, with reasons:
  - **Much longer straight leg.** The 800 m airspeed leg (~80 s) was sized for a
    fast-showing fault. GPS slow-drift needs time to accumulate — at 0.5 m/s the
    belief walks only ~45 m in 90 s. A very long straight cruise lets even the
    slowest drift rate develop, and lets a fast-rejected glitch and its reset
    both be observed on the same heading.
  - **No reciprocal leg (or optional).** Airspeed needed the West leg because
    wind sign flips `ARSP−GPS` — the reciprocal was an observability trick. GPS
    does not care about wind sign; the truth-vs-belief gap is observable on a
    single heading. The one-way long mission (no RTL; the monitor stops after
    the schedule) is simpler and cleaner for drift accumulation.
  - **Injection point stays `seq 4`.** The seq-1..4 front-half and the seq-4
    injection edge are preserved from the airspeed missions, so the plugin's
    first-edge-latch logic transfers unchanged.

  Finalized in Phase 1; see the Mission Design ADR in `design_adrs.md`.
- SITL target: `plane-gps` (dedicated identity; loads `plane_base.parm ->
  plane_gps.parm` only, no airspeed overlay and no local override, wipes EEPROM).
  Corrected 2026-07-13 from `plane-cte`, which is the CTE/airspeed lane; see the
  Dedicated Launch Identities amendment in `design_adrs.md` and ADR-0021.
- Gazebo target: `gazebo-plane-gps` (dedicated identity reusing the
  sensor-neutral base `mini_talon_runway.sdf` world; GPS/NavSat, calm, no
  wind/airspeed/LiDAR). Structurally implemented, not yet live-smoke verified.
- Base params: `config/vehicles/plane_base.parm` (sets `AHRS_EKF_TYPE 3`,
  `EK3_ENABLE 1`; does NOT set the four knee params or `EK3_SRC*`).
- GPS overlay: a new `config/overlays/plane_gps.parm` — **not**
  `plane_airspeed.parm`. The airspeed overlay sets zero GPS/EKF params (verified:
  no `EK3`/`GPS`/`FS_EKF` entries), so reusing it would drag in irrelevant
  airspeed tuning and leave every GPS-relevant knob unset. The GPS overlay is a
  first-class part of the experiment, not boilerplate: it pins the four params
  that *govern the knee* to explicit, documented values (currently firmware
  defaults — verified absent from base), which makes the knee reproducible and
  enables the secondary "loosen/tighten the gate, watch the knee move" axis.
  - **Knee/gate params (pinned, documented):** `EK3_POS_I_GATE`,
    `EK3_GLITCH_RAD`, `FS_EKF_THRESH`, `EK3_GPS_CHECK`.
  - **Position source:** `EK3_SRC*` set so GPS is the EKF position source (base
    sets `AHRS_EKF_TYPE 3`/`EK3_ENABLE 1` but no `EK3_SRC*`), so the faults
    actually bite.
  - **Wind:** calm (GPS does not use wind as a variable, unlike airspeed).
  - Does **not** include the `ARSPD_*`/`AIRSPEED_*` block — the airspeed sensor
    is not the subject.

  The overlay is where the four EKF params are set; Phase-2 smoke is where they
  are read back and confirmed (already on the must-measure list).

## Injection Rule (locked 2026-07-06)

Full contracts are in `design_adrs.md` (Trigger, Sweep, Reset ADRs).

- **Trigger:** inject on entering the measurement waypoint — the first
  `MISSION_CURRENT` message with `seq == 4` after confirmed front-half progress
  (seq 1..3 in AUTO while armed), first-edge latched, never re-fired. `seq 4` is
  preserved from the airspeed missions so the plugin's first-edge-latch logic
  transfers unchanged. This places the fault at the start of the long straight
  measurement leg, so excursion is clean against a stable ground track. A
  missed/late trigger is a `pre_injection_failure`. Record requested vs actual.
- Read back every injected `SIM_GPS1_*` parameter after injection.
- Write a `gps_injection.json` for every attempt (fault, sweep value, knob
  payload, trigger event, readback).
- **Isolation:** per-attempt fresh SITL process is the primary isolation. This
  matters more for GPS than airspeed because GPS drift corrupts the EKF belief,
  which does not clear by zeroing the param. One rate/magnitude/duration per
  clean flight.
- **Observation window:** >= 90 s post-injection on the straight leg (at
  0.5 m/s that is ~45 m excursion, clearly above the control noise band). The
  one-way long leg provides trailing observation on a single heading; there is
  no reciprocal leg or RTL. Denial/jam windows (5–60 s) sit inside the window.
  The continuous-ramp case runs the whole leg.
- **Control:** a `nominal` no-fault run per campaign, flying the identical
  mission with all fault knobs at defaults. Every threshold is defined relative
  to this control (baseline `posTestRatio` range, baseline gap ~ sensor noise,
  baseline attitude/altitude envelope), not to absolute guessed numbers.

## Verdict Model (characterize, not gate)

A run is never PASS/FAIL. Two distinct concepts:

- **Accepted** (counts toward repeats?) = measurement validity only: the fault
  was injected and read back, enough post-injection flight was observed, and the
  required log fields are present. A run with terrible behavior is still accepted
  if it was cleanly measured.
- **Behavior class** (the science output) = which band the run landed in —
  characterized, not gated.

The `silent_drift` vs `detected_rejected` boundary (the knee) is the *result* of
the campaign, not a bar to clear.

## Required Analysis Outputs

Required attempt-level outputs:

- `gps_injection.json`: fault, sweep value, requested payload, trigger event,
  readback values, reset values, success/failure, timestamps.
- `gps_behavior_summary.json`: behavior band, observation-quality/acceptance
  decision, and human-readable reason.
- `ekf_innovation_metrics.csv` and/or `.json`: `posTestRatio` timeline, reject/
  glitch flags, variance, reset events (the mechanism tier).
- `truth_vs_belief.csv` and/or `.json`: believed-vs-truth horizontal position
  gap over time (the single field that reveals `silent_drift`).
- `mode_timeline.csv` and/or `.json`: mode changes and status text after
  injection.
- `attitude_altitude_envelope.json`: post-injection attitude/altitude band,
  excursions, threshold crossings, unexpected disarm.

Missing required outputs make an attempt `analysis_incomplete` unless the
missing field is explicitly optional for the case and the remaining artifacts
are sufficient for classification.

## Excluded Knobs (documented-only, with reasons)

Every knob is documented; excluded ones state why. Layering (a headline fault
with a modifier) is future work, not this lane. Full table in
`design_research.md`.

| Knob | What it does | Why not a headline experiment |
| --- | --- | --- |
| `NUMSATS` | sets reported sat count; does not drop `have_lock` | pre-arm gate only; position stays truthful mid-flight, never trips the innovation gate |
| `VERR` | corrupts velocity but auto-reports matching `speed_acc` | self-betrays → down-weighted; honest degradation, self-limiting |
| `LAG_MS` | delays the fix (staleness) | EKF compensates lag; huge lag is just a weaker `step_glitch` |
| `ACC` | changes claimed accuracy only; position stays truth | pure self-report; natural first modifier if layering, inert standalone |
| `NOISE` / `DRFTALT` | altitude-only sines | baro dominates height; negative controls only |

## Assumptions

- The runbook slug is `gps_failure_behavior`.
- GPS is the selected v3 sensor candidate; the lane is built from the
  `airspeed_failure` plugin template.
- The goal is behavior characterization across degradation → loss of control,
  not robust fallback design.
- A run can be a valid observation even when aircraft behavior is bad.
- Raw runtime output stays in `var/`; curated proof only goes into `evidence/`.
- Source is authoritative for Phase 0 design (the build under test is the
  source); live knob verification is deferred to Phase 2 smoke.
