# ADR-0012: Airspeed Envelope Sensitivity Matrix

Status: Proposed — **partially corrected by ADR-0015 (2026-06-16)**

> **Correction (ADR-0015):** the `AIRSPEED_MAX` axis of this matrix did not test
> what it intended. `AIRSPEED_MAX` bounds the *demanded* airspeed, not the
> *believed* airspeed; the believed-airspeed plateau seen in the runs is the
> `AHRS_WIND_MAX` clamp (`ground_speed + AHRS_WIND_MAX`), which was held constant
> at 15 across all cells. The max18/max28 runs are retained as valid
> protected-stack evidence but support no `AIRSPEED_MAX` conclusion. The cruise
> axis was also defeated by a hardcoded mission `DO_CHANGE_SPEED = 15`. The
> redesign makes `AHRS_WIND_MAX` a first-class variable and fixes the mission
> target. Read ADR-0015 before acting on this ADR.

Date: 2026-06-14

Supersedes: none. Extends the bounded Phase 4A characterization accepted in
`evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`.

## Context

The accepted ratio/ramp/pulse characterization (Phase 4A) was produced under a
single aircraft configuration: `AIRSPEED_CRUISE=14`, `AIRSPEED_MIN=10`,
`AIRSPEED_MAX=22` (verified per attempt; see the acceptance report "Stack, Wind,
And Payloads"). Its primary recorded finding includes a control-envelope
saturation: the extended +200 ramp shows raw reported airspeed continuing to
rise while true airspeed, groundspeed, altitude, throttle, and pitch/elevator
response flatten after roughly **+80..+100% bias**.

That single configuration leaves a confound unresolved, and the acceptance
report names it as the top limitation: *"One SITL configuration only."* The
plateau near +80..+100% has at least two rival causes that one configuration
cannot separate:

1. **Envelope/clipping** — `AIRSPEED_MAX=22` bounds the controller's response,
   so the damage saturates because of configuration, not because the fault
   stopped mattering.
2. **Elsewhere** — pitch/energy limits dominate. The same stack runs
   `TECS_PITCH_MAX=15` and `PTCH_LIM_MAX_DEG=20` (both verified per attempt),
   which can saturate the pitch authority independent of `AIRSPEED_MAX`.

## Architecture

Design diagrams for this ADR family are kept as local-only working assets under
`.private/assets/` (git-ignored per `.private/README.md`); they are not part of
the committed record:

- `01_envelope_matrix_architecture` — outer loop over envelopes, inner loop is
  the unchanged fault experiment;
- `02_plateau_decision_logic` — hypothesis discriminator: does the plateau move
  with `AIRSPEED_MAX`?
- `03_implementation_delta` — zero-core-edit implementation delta;
- `04_run_matrix_budget` — run matrix and flight budget.

The decision content below is self-contained and does not depend on the
diagrams.

## Decision

Introduce an **Envelope Sensitivity Matrix** as Phase 4C. The matrix varies the
aircraft speed envelope across campaigns while re-running the *unchanged*
fault-injection experiment within each. This is an **outer loop over
configurations** with the existing fault experiment as the **inner loop**.

The envelope is a whole-campaign property applied once at SITL boot via the
parameter overlay file; it is never injected in flight. The fault
(`SIM_ARSPD_RATIO` bias on the seq-4 schedule) is injected in flight exactly as
in Phase 4A. The two knobs stay decoupled. See ADR-0013 for the overlay/param
mechanism and ADR-0014 for the plateau metric and pre-registered predictions.

### Envelope cells

All values are cruise / max in m/s, `AIRSPEED_MIN=10` held constant so it is not
a hidden third variable. Baseline is the real accepted configuration `14/22`,
not the `15/22` that an earlier brainstorm assumed.

| Cell           | CRUISE | MAX | max/cruise | max-cruise | Overlay file                          | Role                          |
| -------------- | ------ | --- | ---------- | ---------- | ------------------------------------- | ----------------------------- |
| Baseline       | 14     | 22  | 1.571      | 8          | `plane_airspeed.parm` (reuse)         | anchor / control              |
| Cruise-only    | 17     | 22  | 1.294      | 5          | `plane_airspeed_cruise17.parm`        | operating-point effect        |
| Max-only (low) | 14     | 18  | 1.286      | 4          | `plane_airspeed_max18.parm`           | headline: plateau vs. max     |
| Max-only (high)| 14     | 28  | 2.000      | 14         | `plane_airspeed_max28.parm`           | headline: plateau vs. max     |
| Both-scaled    | 18     | 28  | 1.556      | 10         | `plane_airspeed_scaled18_28.parm`     | absolute speed vs. margin     |

The both-scaled pair preserves the baseline `max/cruise` (1.571 vs. 1.556), so
comparing baseline `14/22` against `18/28` separates absolute-speed effects
(higher dynamic pressure, more kinetic energy) from envelope-margin effects.

### Inner experiment per cell

Run only the two diagnostic probes that carry the saturation claim, not the full
ratio sweep, to avoid a 5x cost blow-up:

- `ratio_bias_ramp_p10_to_p200_headwind` (the extended +200 ramp that showed
  saturation);
- `ratio_bias_pulse_p10_to_p130_headwind` (to confirm the sudden-vs-gradual
  story holds at each envelope).

### Replication

Replication is concentrated where the headline hypothesis lives. The two
max-only cells run the +200 ramp at **n=3**; all other ramp/pulse cells run at
n=1. This directly addresses the Phase 4A limitation that every ramp/pulse
conclusion to date is a single accepted attempt. `runs_per_case` already
supports this with no code change.

### Flight budget

| Cell            | +200 ramp | pulse ladder | new flights |
| --------------- | --------- | ------------ | ----------- |
| Baseline 14/22  | reuse     | reuse        | 0           |
| Cruise-only     | n=1       | n=1          | 2           |
| Max-only (low)  | n=3       | n=1          | 4           |
| Max-only (high) | n=3       | n=1          | 4           |
| Both-scaled     | n=1       | n=1          | 2           |
| **Total**       |           |              | **12**      |

Plus one throwaway flyability smoke for `14/28` before its reps are spent (see
Consequences).

## Alternatives considered

- **Full grid (4 cruise x 4 max x pulse/ramp = 32 flights).** Rejected for
  discovery: the diagnostic value is in the targeted comparisons, not the grid.
  The full grid remains a possible later phase once the targeted matrix
  identifies which axis matters.
- **Re-run the entire ratio sweep under each envelope.** Rejected: 5x cost for
  little marginal diagnostic value over the two probe cases.
- **Per-case envelope variation inside the case generator.** Rejected as an
  architecture error: the envelope is a boot-time vehicle configuration, not a
  per-case `SIM_ARSPD_*` stimulus. The case generator must stay envelope-blind
  (see ADR-0013).

## Consequences

- New artifacts are config overlays + a thin driver + this ADR family; the
  fault-injection core is unchanged (ADR-0013).
- The matrix produces a falsifiable, pre-registered answer to the saturation
  confound (ADR-0014). Either branch (plateau moves / plateau holds) is a
  publishable finding, not a null result.
- **Open validation item:** `AIRSPEED_MAX=28` with `cruise=14` is an untested
  regime for this airframe. The repo documents 28 as an aggressive *cruise*
  value, not a *ceiling with low cruise*. One flyability smoke flight must pass
  for `14/28` before its n=3 reps are spent; if it is not flyable in a tuned
  envelope, substitute a lower high-max value and record the substitution here.
- This ADR does not make any safety, hardware, cross-airframe, or real-world
  claim. It extends a bounded SITL characterization only.
