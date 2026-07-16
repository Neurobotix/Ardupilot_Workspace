# GPS Failure Behavior — ADR Drafts (Proposed)

Status of this file: **design detail backing five Proposed ADRs.** These were
locked with the operator on 2026-07-06 during a full Phase-0 brainstorm and are
promoted to numbered records `ADR-0017`..`ADR-0021` in `governance/decisions/`
(each `Status: Proposed` until validated through live Phase-2 measurement). The
sections below keep their `Status: Proposed` headings and hold the full draft
reasoning that the promoted records point back to.

Every claim about EKF or SITL behavior below is grounded in `design_research.md`
in this directory, which quotes the primary source verbatim. Where a value
depends on runtime state it is named as a Phase-2 must-measure item, not guessed.

Decisions locked with the operator (summary; details in each ADR):

- **ADR-0017** — GPS fault catalog and `SIM_GPS1_*` knob mapping (four headline
  faults; the rest documented-only with mechanism reasons).
- **ADR-0018** — Two-tier knee definition and behavior-class vocabulary;
  characterize-not-gate verdict model.
- **ADR-0019** — Severity-sweep design (one independent variable per fault;
  GPS-drift-has-memory → one-per-flight; pulse-with-reset dropped).
- **ADR-0020** — Mission design and injection trigger (bounded
  reciprocal/RTL mission, seq-4 first-edge latch, full-flight terminal contract).
- **ADR-0021** — GPS parameter overlay (`plane_gps.parm`, pinning the four
  knee-governing EKF params).

---

# ADR (Proposed): GPS Fault Catalog And Knob Mapping

Status: Proposed → to be promoted as ADR-0017

## Context

SITL exposes a rich `SIM_GPS1_*` fault surface (`GPSParms` in `SIM_GPS.cpp`:
`ENABLE`, `LAG_MS`, `TYPE`, `BYTELOS`, `NUMSATS`, `GLTCH`, `HZ`, `DRFTALT`,
`POS`, `NOISE`, `LCKTIME`, `ALT_OFS`, `HDG`, `ACC`, `VERR`, `JAM`). A behavior
lane must choose a small catalog of *real-world* faults with distinct
mechanisms, not sweep every knob.

## Decision

Four headline faults, all in v1:

| # | Fault | Knob(s) | Real-world case | Role |
| --- | --- | --- | --- | --- |
| 1 | `slow_drift` | `SIM_GPS1_GLTCH_{X,Y}` re-injected as a growing ramp | GPS spoofing / slow position capture | Headline — silent below-the-knee capture |
| 2 | `step_glitch` | `SIM_GPS1_GLTCH_{X,Y}` fixed offset | multipath jump / sudden position pop | Contrast — above-the-knee, caught then reset |
| 3 | `hard_denial` | `SIM_GPS1_ENABLE=0` | antenna/receiver loss, tunnel, total denial | Control anchor — resilient dead-reckoning |
| 4 | `jamming` | `SIM_GPS1_JAM=1` | RF jamming (blackout + chaotic garbage) | Headline — loud, incoherent, self-betraying |

Faults 1 and 2 share the `GLTCH` knob deliberately: `SIM_GPS.cpp` adds
`GLTCH_{X,Y}` directly to the fix latitude/longitude (in degrees), so the only
difference between a ramp and a step is onset rate. This isolates onset rate as
the single independent variable in the central knee experiment.

The remaining knobs are documented-only, each excluded for a mechanism reason
(full table in `design_research.md`): `NUMSATS` (pre-arm gate only, position
truthful mid-flight), `VERR` (self-reports matching `speed_acc` → down-weighted),
`LAG_MS` (EKF compensates lag), `ACC` (self-report only; natural first modifier),
`NOISE`/`DRFTALT` (altitude-only, baro-dominated negative controls).

## Alternatives considered

- **Sweep every knob** — rejected; most knobs are inert or self-betraying
  mid-flight, so a sweep would measure arming gates, not flight behavior.
- **`NUMSATS` as a headline degradation** — rejected; it does not drop
  `have_lock`, so position stays truthful and the innovation gate never trips.
- **Separate drift and glitch knobs** — impossible; they are the same SITL knob.

## Evidence / sources

- `SIM_GPS.cpp` `GPSParms` table and `d.latitude += glitch.x` application.
- `SIM_GPS.cpp` `simulate_jamming()` (stochastic, self-parametrizing).
- `design_research.md`, Excluded Knobs section.

## Consequences

- The catalog is four faults with four distinct mechanisms.
- Layering a modifier (e.g. `ACC` onto `slow_drift`) is future work.

## Open validation items

- Confirm `SIM_GPS1_*` spellings/units live in Phase 2 smoke.

---

# ADR (Proposed): Two-Tier Knee And Behavior Classification

Status: Proposed → to be promoted as ADR-0018

## Context

The central result of the lane is the **knee**: the boundary between the EKF
fusing a corrupted GPS fix and rejecting it. It must be defined on a measurable
signal, not a guessed threshold, and behavior must be classified without a
pass/fail gate.

## Decision

**Two tiers.**

- **Mechanism tier (primary knee signal):** the position innovation test ratio
  `posTestRatio`. Live telemetry derives it as
  `EKF_STATUS_REPORT.pos_horiz_variance ** 2`; decoded BIN analysis derives it
  from the selected primary core's already-scaled `XKF4.SP` as `SP ** 2`, with
  `XKF4.PI` required to identify the primary core. The knee is `posTestRatio`
  crossing `1.0` — ArduPilot's own gate (`AP_NavEKF3_PosVelFusion.cpp:824`).
  Below `1.0`: fused → belief moves toward the drifting fix. At/above `1.0`:
  rejected → not fused; the belief only moves later via `ResetPosition` when
  variance exceeds `EK3_GLITCH_RAD²` or on `posTimeout`.
- **Behavior tier (why it matters):** the believed-vs-truth horizontal position
  gap, attitude/altitude band, and mode/failsafe changes.

The tiers can disagree: a fix admitted (`posTestRatio < 1`) can barely move the
belief when the Kalman gain is small. **Accepted is not captured** — only
sustained cumulative drift walks the belief off. The mechanism tier defines the
knee; the behavior tier proves it matters.

**Seven behavior bands, ordered by reaction (not danger):**

`nominal`, `silent_drift`, `detected_rejected`, `reset_captured`,
`autopilot_contained`, `loss_of_control`, `pre_injection_failure` (discard).

Detection and danger are separate axes. `silent_drift` is behaviorally mild but
strategically the worst outcome: the autopilot flies the aircraft off course
while reporting healthy. No single field names it — it is the conjunction
**fused AND gap-growing AND no-failsafe**. This is why the truth-vs-belief gap is
a mandatory logged field: it is the only signal that reveals a lie the filter
believes is fine.

**Verdict model: characterize, not gate.** A run is never PASS/FAIL. Two
concepts:
- **Accepted** = measurement validity only (fault injected + read back, enough
  post-injection flight, required fields present, and valid terminal evidence;
  nominal also requires planned mission completion). A run with terrible
  behavior is still accepted if cleanly measured.
- **Behavior class** = which band it landed in. The `silent_drift` vs
  `detected_rejected` boundary (the knee) is the *result*, not a bar to clear.

## Alternatives considered

- **Single-tier (behavior only)** — rejected; misses the mechanism knee and
  cannot distinguish "fused but low-gain" from "rejected."
- **Single-tier (mechanism only)** — rejected; `posTestRatio` says the fix was
  admitted, not that the belief was captured.
- **Order bands by danger** — rejected; danger and reaction are orthogonal, and
  ordering by danger would bury `silent_drift` mid-ladder and hide that the
  quietest run is the worst.
- **Pass/fail gate** — rejected; the knee is the science output, not a threshold.

## Evidence / sources

- `AP_NavEKF3_PosVelFusion.cpp` ~816–871 (`posTestRatio`, reset path).
- `design_research.md`, The Knee + Accepted-is-not-captured sections.

## Consequences

- Mandatory logged fields: `posTestRatio` timeline + reject/reset flags
  (mechanism), truth-vs-belief gap (behavior).
- `reset_captured` is a discrete, observable event (`ResetPosition` reflected in
  `XKF4.OFN/OFE` reset offsets).

## Open validation items

- Live `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`, `FS_EKF_THRESH`, `EK3_GPS_CHECK`,
  and `EK3_SRC1_*`; exact checked-in knee values; complete integral source
  contract (`POSXY=3`, `VELXY=3`, `POSZ=1`, `VELZ=3`, `YAW=1`); EKF
  absolute-position status flags as the validated GPS-aiding proxy.
- Baseline `posTestRatio` and gap ranges from the `nominal` control.

---

# ADR (Proposed): Severity-Sweep Design

Status: Proposed → to be promoted as ADR-0019

## Context

Each fault needs a severity envelope that walks the aircraft from tiny
degradation to loss of control. The sweep design must respect how each fault's
severity actually varies, and must respect that GPS drift corrupts EKF *state*,
which does not clear by zeroing the injected param.

## Decision

One independent variable per fault:

| Fault | Independent variable | Sweep |
| --- | --- | --- |
| `slow_drift` | drift rate | `0.2 / 0.5 / 1.0 / 2.0 / 4.0 / 8.0` m/s, one rate per flight, each from clean baseline |
| `step_glitch` | offset magnitude | `10 / 25 / 50 / 100 / 200 / 500` m, one per flight |
| `hard_denial` | denial duration | `5 / 15 / 30 / 60` s, then restore `ENABLE=1` |
| `jamming` | (binary) repeats | `JAM=1`, 30–60 s window, 5+ repeats (stochastic) |

**One rate/magnitude/duration per clean flight**, because GPS drift has memory:
an accepted drift updates the EKF belief and that state carries forward; zeroing
`GLTCH` stops new corruption but does not un-corrupt the belief that already
moved. A later window in the same flight would start already-wrong and be
contaminated.

**Pulse-with-reset dropped** for GPS: unlike airspeed, the "reset" (zeroing the
param) is not a clean reset of the belief.

**Second instrument for `slow_drift`:** one continuous ramp with no reset,
measuring accumulation/endurance (how bad it gets as drift piles up) — a
different question from the clean per-rate knee.

The sweep bracket is a design guess; the knee's exact location is a Phase-2
result. The ramp generator takes a rate list, so extending the bracket is a
longer input, no code change.

## Alternatives considered

- **In-flight schedule (airspeed style)** — rejected; contaminated by belief
  memory.
- **Internal jam severity dial** — none exists; `simulate_jamming()` is
  stochastic. Severity is expressed via duration and repeats.
- **Single glitch magnitude** — rejected; a ladder is needed to bracket the
  single-fix rejection threshold.

## Evidence / sources

- `AP_NavEKF3_PosVelFusion.cpp` reset path (belief state persistence).
- `SIM_GPS.cpp` `simulate_jamming()` (no severity dial).

## Consequences

- Per-attempt fresh SITL process is mandatory isolation (belief memory).
- Jamming needs more repeats (distribution, not a repeatable point).

## Open validation items

- Empirical knee rate; single-fix rejection magnitude; whether v1 flies a thin
  slice or full sweep first.

---

# ADR (Proposed): Mission Design And Injection Trigger

Status: Proposed → to be promoted as ADR-0020

## Context

Airspeed used an 800 m reciprocal-leg mission because wind sign flips `ARSP−GPS`
and the reciprocal was an observability trick. GPS is a different fault and needs
different geometry: drift needs *time* to accumulate, and the truth-vs-belief gap
is observable on a single heading regardless of wind.

## Decision

`assets/missions/gps_failure_behavior_mission.waypoints` uses the practical
airspeed behavior lifecycle with GPS-owned geometry: a 500 m calm-lane settle,
2000 m Eastbound measurement leg, reciprocal return leg 500 m North, and RTL at
seq 9. The
earlier 36 km one-way candidate was retired before the nominal live gate because
it made the experiment unnecessarily long.

1. **Bounded but long enough for fault observation** — the 2000 m outbound plus
   reciprocal route provides post-injection observation while retaining a
   deterministic end state.
2. **Reciprocal plus RTL** — the reciprocal is not required for GPS physics,
   but it preserves a proven mission lifecycle and gives the monitor a planned
   RTL terminal contract.
3. **Injection stays `seq 4`** — the seq-1/3 front-half and the seq-4 injection
   edge are preserved from the airspeed mission.
4. **Minimum window is not termination** — 20 s nominal / 90 s fault are
   evidence gates. The monitor normally continues to RTL and waits 10 s for
   stabilization.

**Trigger:** inject on the first `MISSION_CURRENT` with `seq == 4` after
confirmed navigation progress (seq 1 and 3 in AUTO while armed; seq 2 is an
optional `DO_CHANGE_SPEED` current report), first-edge latched,
never re-fired. A missed/late trigger is `pre_injection_failure`, not a late
injection. Record requested vs actual.

## Alternatives considered

- **Use the 36 km one-way mission** — rejected for the first live gate; it
  removed the deterministic RTL lifecycle and made diagnosis unnecessarily
  slow.
- **Stop at the minimum evidence window** — rejected after the 2026-07-14
  nominal regression; it truncates the experiment before reciprocal/RTL
  behavior is observed.
- **Move the injection seq** — rejected; breaks first-edge-latch reuse.
- **Keep the airspeed lane's exact 300/1100 m coordinates** — rejected after
  the 2026-07-14 nominal completed its calm-lane climb around 323 m East and had
  to turn back to seq 3. V3 first moved the paired endpoints to 500/1300 m;
  v4 retains the safe 500 m settle while extending the far endpoint to 2500 m
  and widening the reciprocal separation to 500 m. Trigger ordering is
  unchanged.

## Evidence / sources

- Existing `airspeed_failure_behavior_mission.waypoints` mission shape.
- `plan.md` Default Stack + Injection Rule.

## Consequences

- The GPS plugin owns its trigger implementation while preserving the proven
  first-edge mission contract; it does not import the airspeed plugin.
- Nominal acceptance requires planned RTL completion; adverse fault terminals
  remain characterizable when cleanly measured.

## Open validation items

- Realized complete-flight timing and east-facing spawn alignment.

---

# ADR (Proposed): GPS Parameter Overlay

Status: Proposed → to be promoted as ADR-0021

## Context

The knee is governed by four EKF params (`EK3_POS_I_GATE`, `EK3_GLITCH_RAD`,
`FS_EKF_THRESH`, `EK3_GPS_CHECK`). Verified against source: `plane_base.parm`
sets none of them (they run at firmware defaults), and `plane_airspeed.parm` sets
zero GPS/EKF params (it is entirely `ARSPD_*`/`AIRSPEED_*`/wind). Reusing the
airspeed overlay would drag in irrelevant airspeed tuning and leave every
GPS-relevant knob unset.

## Decision

`plane_base.parm` (unchanged) + a new `config/overlays/plane_gps.parm`. The
overlay is a **first-class part of the experiment**, not boilerplate:

- **Pin the four knee params** to explicit, documented values. This makes the
  knee reproducible and enables the secondary "loosen/tighten the gate, watch the
  knee move" axis. `EK3_POS_I_GATE` is in centi-sigma
  (`AP_NavEKF3_PosVelFusion.cpp:820`, `0.01 *` multiplier), so it directly sets
  where `posTestRatio = 1.0` lands in metres of innovation — and therefore where
  the knee lands in m/s of drift.
- **Set `EK3_SRC*`** so GPS is the EKF position source. Base sets
  `AHRS_EKF_TYPE 3` / `EK3_ENABLE 1` but no `EK3_SRC*`, so the overlay must pin
  the source so the faults actually bite.
- **Calm wind** (GPS does not use wind as a variable).
- **No `ARSPD_*`/`AIRSPEED_*` block** — the airspeed sensor is not the subject.

## Alternatives considered

- **Reuse `plane_airspeed.parm`** — rejected; zero GPS/EKF coverage, irrelevant
  airspeed tuning.
- **Leave the four params at firmware defaults** — rejected; the knee would be
  neither pinned nor documented, and the gate-sensitivity axis would be
  impossible.

## Evidence / sources

- Verified: `plane_airspeed.parm` has no `EK3`/`GPS`/`FS_EKF` entries;
  `plane_base.parm` has none of the four knee params and no `EK3_SRC*`.
- `AP_NavEKF3_PosVelFusion.cpp:820` (centi-sigma gate).

## Consequences

- The overlay is where the four EKF params are set; Phase-2 smoke reads them
  back and confirms them.
- The gate-sensitivity secondary axis becomes available by editing one overlay.

## Open validation items

- Chosen pinned values for the four params; live readback in Phase 2.

## Amendment 2026-07-13: Dedicated GPS launch identities

This overlay decision originally left the launch target unspecified, and the
design pointed at `plane-cte` / `gazebo-plane-cte`. That is a contract mismatch:
`plane-cte` is the CTE/airspeed lane and loads
`plane_base.parm -> plane_airspeed.parm -> .private/config/plane_params.local.parm`,
i.e. the airspeed overlay this ADR rejects plus an uncontrolled local override.

The correction (mirrored verbatim in the promoted record
`governance/decisions/ADR-0021-gps-failure-parameter-overlay.md`):

- New dedicated identities `plane-gps` and `gazebo-plane-gps`; the plugin
  defaults, docs, and any future plugin-owned launcher use these, never
  `plane-cte`.
- `plane-gps` loads exactly `config/vehicles/plane_base.parm ->
  config/overlays/plane_gps.parm` and nothing else — no airspeed overlay and no
  local override (the launcher uses a dedicated `build_plane_gps_param_args()`
  that never appends `.private/config/plane_params.local.parm`, and prints that
  the override was intentionally excluded). It wipes EEPROM, uses
  `var/runs/sitl/plane-gps` and a `plane-gps` MAVProxy identity, and emits
  `udp:127.0.0.1:14551`.
- `gazebo-plane-gps` uses the dedicated sensor-neutral
  `assets/worlds/mini_talon_gps_runway.sdf`. It provides the JSON FDM path and
  NavSat/GPS with no wind publisher, `WindEffects`, airspeed sensor, or LiDAR
  bridge, and owns the east-facing pose required by the mission. The shared
  `gazebo-plane` world is not modified.

No live claim: the targets are structurally implemented with no-SITL structural
tests only. Phase 2 smoke must read back the realized stack live.
