# ADR-0019: GPS Failure Severity-Sweep Design

Status: Proposed

Date: 2026-07-06

Each GPS fault gets a severity envelope that walks the aircraft from tiny
degradation to loss of control, with a sweep shape that respects how each
fault's severity actually varies and that respects EKF belief memory.

Decision:

- One independent variable per fault:
  - `slow_drift`: drift rate `0.2 / 0.5 / 1.0 / 2.0 / 4.0 / 8.0` m/s, one rate
    per flight, each from clean baseline.
  - `step_glitch`: offset magnitude `10 / 25 / 50 / 100 / 200 / 500` m, one per
    flight.
  - `hard_denial`: denial duration `5 / 15 / 30 / 60` s, then restore
    `ENABLE=1`.
  - `jamming`: binary `JAM=1`, 30–60 s window, 5+ repeats (stochastic, so
    characterize a distribution, not a repeatable point).
- One rate/magnitude/duration per clean flight, because GPS drift has memory: an
  accepted drift updates the EKF belief and that state carries forward; zeroing
  `GLTCH` stops new corruption but does not un-corrupt the belief that already
  moved. A later window in the same flight would start already-wrong and be
  contaminated.
- The airspeed-style in-flight pulse-with-reset schedule is dropped for GPS,
  because zeroing the param is not a clean reset of the belief.
- Second instrument for `slow_drift`: one continuous ramp with no reset, which
  measures accumulation/endurance (how bad it gets as drift piles up) — a
  different question from the clean per-rate knee.
- The sweep bracket is a design guess; the knee's exact location is a Phase-2
  result. The ramp generator takes a rate list, so extending the bracket is a
  longer input, not a code change.

Consequence: per-attempt fresh SITL process is mandatory isolation.

Full reasoning and alternatives:
`governance/runbooks/features/gps_failure_behavior/design_adrs.md`
("ADR (Proposed): Severity-Sweep Design").

Open validation (Phase 2 smoke): empirical knee rate; single-fix rejection
magnitude; whether v1 flies a thin slice or the full sweep first.
