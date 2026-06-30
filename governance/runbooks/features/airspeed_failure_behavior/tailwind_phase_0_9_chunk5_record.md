# Tailwind Phase 0–9 Chunk 5 Record

Date: 2026-06-23 UTC

Factual record for Chunk 5 (strict expectation-versus-observation and
headwind-versus-tailwind comparison, Phases 0–9). The realized-results matrix
and full per-phase reasoning live in
`tailwind_phase_0_9_results_comparison.md`; the working analysis package is
`var/analysis/tailwind_phase_0_9_comparison_20260623/`.

## Chunk 4 decision (operator)

The operator decided that Chunk 4 requires **no rerun**. Recorded here:

- all required raw evidence exists;
- all BIN hashes match the inventory
  (`tailwind_run_inventory.json`, SHA-256
  `a6495811ca697116091085e0d6bc1babed2cef7ac84a68f481d3aed6b9699b48`);
- no schedule-matching failures exist (zero across all decoded attempts);
- low-altitude aborts are valid aircraft behavior after valid injection, not
  missing evidence (cross-checked `POS.RelHomeAlt` vs `−SIM2.PD`);
- no experiment rerun is authorized or required.

No SITL or Gazebo was launched in Chunk 5.

## Preregistration integrity

The frozen expectations file
`tailwind_phase_0_9_expectations.md` was hash-verified
`ce8e9bc267b518a229505071eed23f8187100f5f1659d6373b9719a3d4e0d654`
before and after Chunk 5 and is **unmodified**. The locked post-observation
columns were filled in a **separate** realized-results matrix
(`tailwind_phase_0_9_results_comparison.md`), preserving the original prediction
record.

## Result

All ten phases assessed **yes** (observed behavior agrees with the central
frozen physical and controller predictions). Headlines:

1. Healthy wind reversal added **+9.98 m/s** to GPS with unchanged
   raw/believed/true airspeed, altitude, throttle, pitch, AOA (Phase 0); +10.0
   m/s GPS shift at every ramp/pulse baseline.
2. Protected tailwind raised the believed-airspeed clamp ceiling from
   `(GPS+15)/E2T≈22` (headwind) to `≈31` (tailwind), ~+8–9 m/s, matching the
   predicted `10/E2T`.
3. That higher ceiling allowed believed airspeed to reach ~30 and the aircraft
   to degrade into a low-altitude abort, whereas the matched headwind pinned
   believed at the ~22 plateau and rode to +200 — explaining why tailwind ramps
   stop near +120–140 while protected headwind ramps reached +200.
4. `AHRS_WIND_MAX=0` (Phase 2) removed the clamp; believed tracked raw directly.
5. `DO_CHANGE_SPEED=15` held TECS demand at ~15.5 TAS in Phases 3–7 regardless
   of overlay; `AIRSPEED_MAX` capped neither demand nor believed.
6. Phase 9 same-mission Grade A pair: tailwind rejected the AHRS source one bias
   step later than headwind (+60 vs +50) with GPS shifted +10 — direct support
   for the wind-direction mechanism. Pulse rejection (+50/+60) ≪ ramp rejection
   (+119–139) because abrupt steps spike EKF innovation through
   `ARSPD_WIND_GATE`.

## Implementation-defect verdict

No runtime/flight-controller implementation defect was demonstrated. Every
headwind→tailwind difference is explained by verified ArduPilot source: the AHRS
protected-clamp arithmetic (`AP_AHRS.cpp:982-996`), the source-rejection path
(`AP_AHRS.cpp:954-972`), and the airspeed-health disable logic
(`AP_Airspeed_Health.cpp:54-101`). The only defects in this campaign were
analysis/evaluator defects already demonstrated and fixed in Chunks 1–3 (no-SITL
mechanism gate corrections). Residual non-defect items are an experiment-design
geometry limitation (Grade B pairs for Phases 1–8) and run-history/timing
scatter in the exact ramp rejection bias (Phases 4 and 6).

Full per-check classification:
`var/analysis/tailwind_phase_0_9_comparison_20260623/implementation_defect_review.json`.

## Validation

Programmatic gate (`validation.json`) — all true: ten phases represented and
assessed; every numerical comparison links to source attempts/windows; commanded
and effective bias not conflated; pairing grades populated; expectations and
inventory hashes unchanged; no `var/runs/` git change; no sim process running;
every assessment carries explanation and confounder fields; every suspected
defect check carries concrete supporting evidence.

Targeted suites, `git diff --check`, and `make doctor` were run; see the Chunk 5
final report for results. **No production code was changed in Chunk 5.**

## Readiness for Chunk 6

The comparison is complete, internally consistent, and source-grounded, with the
preregistration preserved and the Chunk 4 no-rerun decision recorded. The
evidence is ready for Chunk 6 consolidation. Chunk 6 (final evidence promotion
and campaign closure) is **not** performed here.
