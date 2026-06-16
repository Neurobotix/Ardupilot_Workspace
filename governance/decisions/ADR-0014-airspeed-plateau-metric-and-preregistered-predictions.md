# ADR-0014: Ramp Plateau Metric And Pre-Registered Predictions

Status: Proposed — **P1 withdrawn by ADR-0015 (2026-06-16)**

> **Correction (ADR-0015):** prediction P1 below was pre-registered in good
> faith and then flown, and the flight invalidated the prediction's premise, not
> just its outcome. P1 assumed `AIRSPEED_MAX` acts on the believed-airspeed
> signal; it does not (it bounds *demanded* airspeed). The ~22 m/s plateau is the
> `AHRS_WIND_MAX` clamp (`ground_speed + AHRS_WIND_MAX`, held at 15 in every
> cell), with the sensor in use and healthy throughout (`ARSP.U=1`). Therefore
> the "max-only sweep" cannot exonerate or implicate `AIRSPEED_MAX`, and the
> "second outcome is an affirmative finding" clause does **not** apply. P1 is
> withdrawn. P2-P4 are untested (P3/P4 were defeated by the mission's hardcoded
> `DO_CHANGE_SPEED = 15`). The plateau metric and Decision rule are retained but
> must, per ADR-0015, separate raw `ARSP`, clamped `CTUN.As`, and `TECS` target,
> and gate on proof that the varied parameter moved the measured signal.

Date: 2026-06-14

Defines the measurement contract for the Envelope Sensitivity Matrix (ADR-0012).
This ADR is written and committed *before* the matrix is flown.

## Context

ADR-0012 turns on a single comparison: does the ramp plateau-onset bias move
when `AIRSPEED_MAX` moves? For that comparison to be evidence-grade, two things
must be fixed in advance, not decided after seeing the data:

1. an operational definition of "plateau" that is a measurement rule, not a
   judgment call;
2. the predictions, written as falsifiable statements with a decision rule, so
   either outcome is a finding.

The signals needed already exist. The ramp artifact `airspeed_bias_ramp.json`
carries `phase_metrics`, produced by `_schedule_metrics` in `monitor.py`. That
field is a per-step array `cycles[]`, and each cycle's `fault` block contains:

- `bias_percent` (the step's commanded bias),
- `sample_stats` (mean/std for airspeed, groundspeed, altitude over the step's
  60 s window),
- `pitch_deg` (mean/std),
- `servo_output_raw` (per-channel mean/std, i.e. elevator/ruddervator
  saturation evidence).

`altitude_speed_envelope.json` independently carries `altitude_loss_m` and
`threshold_crossings`. The plateau metric is therefore a **pure post-hoc
reduction over data already emitted** — no monitor change, no new telemetry.

## Decision

### Plateau-onset definition (operational)

Define `ramp_plateau_start_bias` as the lowest `bias_percent` step `b*` in the
ramp such that, for every subsequent step, the step-over-step change in all of
the following stays within a noise band derived from the run's own baseline:

- `sample_stats.airspeed_mps.mean` (true airspeed),
- `sample_stats.groundspeed_mps.mean`,
- `sample_stats.altitude_m.mean` (or `altitude_loss_m` slope),

where "within band" means the step-to-step delta is `<= k * sigma_step`, with
`sigma_step` estimated from the baseline-window std already present in the same
artifact, and `k` fixed at **2** for all cells before any run. If no such `b*`
exists (no plateau within the ramp), record `ramp_plateau_start_bias = null`.

This makes the plateau a computed field over `phase_metrics.cycles[]`, reusing
the band helpers (`_band_low` / `_band_high`) already in `monitor.py`. The
metric is added as an analysis-side derivation; it does not alter how cases run.

### Co-metrics recorded per cell

`ramp_true_airspeed_min`, `ramp_altitude_loss`, `pulse_detection_threshold`
(lowest pulse bias crossing `ARSPD_WIND_GATE=5`, already observed at +60 in
Phase 4A), and pitch/elevator saturation onset from
`pitch_deg` / `servo_output_raw` (to test the pitch-limit rival hypothesis).

### Pre-registered predictions (falsifiable)

P1. **[WITHDRAWN by ADR-0015 — premise invalid; see banner above.] Max-only
sweep.** If `ramp_plateau_start_bias` shifts monotonically with
`AIRSPEED_MAX` across 18/22/28, the saturation is envelope/clipping-driven and
the Phase 4A "+200 does nothing" result is a configuration artifact. If
`ramp_plateau_start_bias` is statistically indistinguishable across 18/22/28
(overlapping at n=3), `AIRSPEED_MAX` is exonerated and the dominant limit is
elsewhere (pitch/energy). The second outcome is an affirmative finding, not a
null. *(Outcome observed: indistinguishable across 18/28 at n=3 — but this does
NOT exonerate `AIRSPEED_MAX`, because `AIRSPEED_MAX` does not act on believed
airspeed. The constant was `AHRS_WIND_MAX=15`. See ADR-0015.)*

P2. **Pitch-limit rival.** If the plateau holds under P1 *and* `pitch_deg`
approaches `PTCH_LIM_MAX_DEG=20` / `TECS_PITCH_MAX=15` at the plateau step
across cells, attribute the limit to pitch authority.

P3. **Cruise-only.** Higher cruise (17 vs. 14) reduces margin below `MAX`; we
predict the plateau onset and any degradation appear at a *lower* bias percent.

P4. **Both-scaled vs. baseline.** If `18/28` and `14/22` (near-equal
`max/cruise`) behave alike, the controlling variable is envelope margin; if they
differ, absolute speed / dynamic pressure matters.

### Decision rule

The matrix is accepted as answering the confound iff: (a) the max-only cells
reach n=3 with valid injections and verified wind/reset, (b)
`ramp_plateau_start_bias` is computed by the rule above for every accepted ramp,
and (c) P1's two outcomes are reported as stated regardless of which occurs.

## Alternatives considered

- **Eyeball the plateau from plots.** Rejected: not reproducible, and it is the
  exact soft spot a reviewer attacks.
- **New per-step telemetry stream.** Rejected as unnecessary: `phase_metrics`
  already carries everything the metric needs.
- **Pick `k` after seeing the data.** Rejected: that is researcher-degrees-of-
  freedom; `k=2` is fixed here, before any flight.

## Consequences

- The plateau claim becomes a single number per ramp, comparable across cells,
  derived deterministically from existing artifacts.
- Because the predictions and the rule are recorded before the runs, the matrix
  result is honest under either branch.
- The metric implementation is analysis-side only; ADR-0013's "frozen core"
  guarantee is preserved.
