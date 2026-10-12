# Real-Flight IMU Analysis Review

Review date: 2026-09-01

## Scope Decision

The five supplied normal GPS-aided flights were analyzed as a working baseline.
No result was promoted to `evidence/`, and no GPS-denied performance claim was
made.

## Reviewed Findings

- Every airborne IMU/axis VIBE p95 is below the ArduPilot 30 m/s² guidance
  level.
- Shahin electrical has the lowest worst-axis p95 (1.33 m/s²); B73 flight 2 has
  the highest (21.56 m/s²) without clipping.
- Shahin fuel is materially more vibratory than Shahin electrical (worst p95
  15.62 versus 1.33 m/s²), with no airborne clips.
- B73 flight 1 clipping is localized to takeoff and terminal flight, not a
  regularly increasing cruise counter.
- Shaba7 has a two-record terminal clip burst on both IMUs, reaching 111.76
  m/s². `EKF3 lane switch 1` follows the first burst by about 0.50 s and the
  next EKF record crosses the velocity test-ratio boundary on both cores. This
  is a high-priority correlated event, not a proven causal diagnosis.
- In all three logs with EKF3 data, GPS aiding is continuously present and
  position/velocity consistency is strong outside the Shaba7 terminal event.
- B73 flight 1 and Shaba7 show independent airspeed rejection/failure evidence
  that should be investigated separately.
- Post-filter batch spectra on B73 flight 2 show a 97–99 Hz acceleration family
  with high-frequency peak/throttle correlation of 0.84–0.87, supporting a
  propulsion-order interpretation without identifying a component.

## Verification

- Pure numerical unit tests cover window selection, data bounds, counters,
  finite statistics, effective rate, and recovery of a known-frequency sine.
- The analyzer completed against all five input files and produced five
  provenance records.
- Every batch accepted for FFT had complete sequence and advertised sample
  count; no invalid airborne batch was reported.
- Representative fleet, VIBE, EKF, and spectral figures were inspected after
  generation.

## Residual Risks

- No controlled repetitions exist for a matched condition.
- Shahin logs lack EKF3 and high-rate batch data.
- Spectra are post-filter only.
- Airborne selection uses GPS speed and intentionally includes terminal context.
- Independent truth is absent, so GPS-denied drift cannot be evaluated.

## Next Gate

A GPS-denied claim requires a separately governed experiment with independent
truth, controlled/repeated denial windows, standardized logging, and
pre-registered error-versus-time metrics. The current working package is the
baseline and experiment-design input only.
