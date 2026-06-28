# Tailwind Pulse Corrected Reanalysis

Date: 2026-06-23 UTC

This curated summary records additive offline reanalysis of the two preserved
attempts under `var/runs/tailwind_standard_speed15_pulse_p130_n1/`. No live
simulation was launched and no raw run artifact or historical manifest was
modified.

The corrected evaluator anchors every fault window to the in-BIN
`SIM_ARSPD_RATIO` `PARM` transition, uses `CTUN.AsT=1` as the authoritative
sensor-derived airspeed source, and evaluates all 13 pulse windows. Both
attempts are interpretable `clamp_verified` observations. AHRS first switches
away from the sensor at +50%; the separate `ARSP.U` parameter-disable path
first activates at +60%.

| Attempt | Original manifest | Corrected result | Clamp rows | Mean clamp error | AHRS source rejection | ARSP disable |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | rejected | `clamp_verified` | 10 | 0.462 m/s | +50% | +60% |
| 2 | rejected | `clamp_verified` | 11 | 0.390 m/s | +50% | +60% |

The clamp tolerance is 2.0 m/s. Both runs also pass the 15 m/s commanded-cruise
check, the `AHRS_WIND_MAX=15` readback, and the minimum aligned-source sample
requirement. All 13 fault windows matched without error.

## Provenance

- Working reanalysis:
  `var/analysis/tailwind_standard_speed15_pulse_p130_reanalysis_20260623/`
- Preserved raw manifest SHA-256:
  `964598e3a1f7ef5c729869dd93ea3dffefbe24252a20686dd5469822d694a53e`
- Attempt 1 BIN SHA-256:
  `5da89257c8ce42892b2ce4b86b1d737222b0203678c8c80d0fca4e042f9d8fb2`
- Attempt 2 BIN SHA-256:
  `202889bda27a3654f79b307257597f4642904060515061d49c3552c0080fe920`
- The full corrected per-window JSON remains working analysis under `var/`;
  tracked evidence promotes only this bounded result summary.

Limit: this corrects the mechanism interpretation of these two attempts. It
does not certify aircraft safety or complete the remaining tailwind matrix.
