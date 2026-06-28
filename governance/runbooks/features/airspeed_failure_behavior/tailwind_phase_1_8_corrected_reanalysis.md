# Tailwind Phase 1–8 Corrected Reanalysis (Chunk 3 Record)

Date: 2026-06-23 UTC

This is a factual Chunk 3 record. It states what the frozen Phase 1–8 tailwind
telemetry objectively shows after a corrected, deterministic, offline batch
reanalysis. It does **not** fill the locked tailwind-actual, headwind-delta,
"makes sense", suspected-defect, or residual-confounder columns of the frozen
expectations matrix; those belong to Chunk 5.

## Exact inputs

16 attempts (Phases 1–8). Phase 0 and Phase 9 remain prior-known controls and
are out of scope.

| Phase | Root | Attempts | Tier | Speed source | Stack |
| ---: | --- | --- | --- | --- | --- |
| 1 | `var/runs/tailwind_protected_cruise_follow_p200_n3` | 001,002,003 | protected | `airspeed_cruise` | S0 |
| 2 | `var/runs/tailwind_diagnostic_cruise_follow_p200_n3` | 001,002,003 | diagnostic | `airspeed_cruise` | S1 (`AHRS_WIND_MAX=0`) |
| 3 | `var/runs/tailwind_max28_speed15_p200_n3` | 001,002,003 | protected | `do_change_speed_15` | S2 |
| 4 | `var/runs/tailwind_max18_speed15_p200_n3` | 001,002,003 | protected | `do_change_speed_15` | S3 |
| 5 | `var/runs/tailwind_cruise17_speed15_p200_n1` | 001 | protected | `do_change_speed_15` | S4 |
| 6 | `var/runs/tailwind_scaled18_28_speed15_p200_n1` | 001 | protected | `do_change_speed_15` | S5 |
| 7 | `var/runs/tailwind_standard_speed15_p200_n1` | 001 | protected | `do_change_speed_15` | S0 |
| 8 | `var/runs/tailwind_standard_speed15_p100_n1` | 001 | protected | `do_change_speed_15` | S0 |

Phases 1–2 read intended airspeed from `AIRSPEED_CRUISE`; Phases 3–8 from
`DO_CHANGE_SPEED=15`.

## Method

- Window anchor: in-BIN `SIM_ARSPD_RATIO` `PARM` transitions. Wall-clock
  injection UTC is never aligned to the DataFlash/SITL clock.
- Sensor source: `CTUN.AsT==1` is authoritative for the raw-to-believed clamp
  and tracking checks. `ARSP.U` is retained separately as the parameter-level
  enable/disable state.
- Protected upper EAS: `(GPS.Spd + AHRS_WIND_MAX) / CTUN.E2T`, evaluated only on
  sensor-source rows.
- Diagnostic (`AHRS_WIND_MAX=0`): evaluate whether believed `CTUN.As` tracks raw
  `ARSP.Airspeed` while `CTUN.AsT==1`; no protected-clamp logic.
- All fault windows reached are evaluated; ramps are not reduced to a final
  window. First AHRS source rejection and first `ARSP.U` disable are reported as
  separate transitions.
- Steady-state telemetry summaries exclude the first 10 s after a transition and
  final 2 s before the next, where telemetry suffices.
- Two passes: the production evaluator (`analyze_mechanism_bin`) for the
  authoritative mechanism verdict, plus a rich trimmed per-window telemetry
  decode.

Working analysis package (additive, under `var/`, not promoted):
`var/analysis/tailwind_phase_1_8_corrected_reanalysis_20260623/`.

## Hashes

- Frozen expectations `tailwind_phase_0_9_expectations.md`:
  `ce8e9bc267b518a229505071eed23f8187100f5f1659d6373b9719a3d4e0d654`
  (verified before reading telemetry; unchanged after).
- Inventory `tailwind_run_inventory.json`:
  `a6495811ca697116091085e0d6bc1babed2cef7ac84a68f481d3aed6b9699b48`.
- All 16 BIN SHA-256 match the inventory (see
  `var/analysis/.../validation.json` and per-attempt JSONs).

## Evaluator defect found, demonstrated, and fixed

Defect: `analyze_mechanism_bin` selected the **last interpretable** fault window
as the attempt representative only for `schedule_kind == "pulse_ladder"`; ramps
fell through to the **last evaluated** window. A ramp that verifies the
protected clamp (or diagnostic tracking) in an earlier window and is later
pushed into AHRS source rejection at higher bias had its verified mechanism
**erased** by the final rejected window.

Demonstration from telemetry (preserved per-window gate output):

- `tailwind_max28_speed15_p200_n3/attempt_003`: +120 window
  `clamp_verified` (65 clamp-exercised rows, mean clamp error 0.46 m/s); +130
  window `sensor_rejected_before_verification`. Old code reported the attempt as
  `sensor_rejected_before_verification`.
- `tailwind_protected_cruise_follow_p200_n3/attempt_003`: +120 window verified;
  later window rejected; old verdict `clamp_not_exercised`.

Fix (smallest correct area): in
`src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/analyzers.py`,
choose the last interpretable window as the representative for every schedule
kind, falling back to the last evaluated window only when no window was
interpretable. The per-window verdicts, the separate source-rejection and
parameter-disable thresholds, and the full window list are unchanged.

Regression test (fails pre-fix, passes post-fix):
`tests/unit/test_airspeed_mechanism_gate.py::MechanismGateScheduleExtractionTests::test_ramp_verified_window_not_erased_by_later_rejection`.

The fix was not made to match the frozen expectations; it corrects a verified
window being masked by a later rejected window, which the Chunk 3 contract
explicitly forbids.

## Old-versus-corrected evaluator dispositions

`FN` = original evaluator false negative corrected by Chunk 3. `Rej` = first
AHRS source rejection bias %. `Dis` = first `ARSP.U` disable bias %. `MaxBias`
= highest bias this attempt reached. Stop = recorded behavior-stop reason.

| Phase | Att | Tier | Original mechanism | Corrected mechanism | FN | Rej | Dis | MaxBias | Stop |
| ---: | ---: | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | 1 | protected | clamp_verified | clamp_verified | no | 119 | — | 119 | low_altitude_abort |
| 1 | 2 | protected | clamp_not_exercised | clamp_verified | yes | 119 | 129 | 139 | low_altitude_abort |
| 1 | 3 | protected | clamp_not_exercised | clamp_verified | yes | 119 | 119 | 129 | low_altitude_abort |
| 2 | 1 | diagnostic | mechanism_unverified | unclamped_tracking_verified | yes | 109 | — | 109 | low_altitude_abort |
| 2 | 2 | diagnostic | mechanism_unverified | unclamped_tracking_verified | yes | 109 | — | 109 | low_altitude_abort |
| 2 | 3 | diagnostic | mechanism_unverified | unclamped_tracking_verified | yes | — | — | 109 | low_altitude_abort |
| 3 | 1 | protected | clamp_not_exercised | clamp_verified | yes | — | — | 129 | low_altitude_abort |
| 3 | 2 | protected | clamp_not_exercised | clamp_verified | yes | — | — | 129 | low_altitude_abort |
| 3 | 3 | protected | clamp_not_exercised | clamp_verified | yes | 129 | 129 | 129 | low_altitude_abort |
| 4 | 1 | protected | clamp_not_exercised | clamp_verified | yes | — | — | 129 | low_altitude_abort |
| 4 | 2 | protected | clamp_not_exercised | clamp_verified | yes | 129 | 189 | 189 | low_altitude_abort |
| 4 | 3 | protected | clamp_verified | clamp_verified | no | 139 | — | 199 | ramp_complete |
| 5 | 1 | protected | clamp_not_exercised | clamp_verified | yes | — | — | 129 | low_altitude_abort |
| 6 | 1 | protected | clamp_verified | clamp_verified | no | 139 | — | 199 | ramp_complete |
| 7 | 1 | protected | clamp_not_exercised | clamp_verified | yes | 119 | 129 | 129 | low_altitude_abort |
| 8 | 1 | protected | clamp_not_exercised | clamp_not_exercised | no | — | — | 99 | ramp_complete |

12 of 15 historical Phase 1–8 mechanism verdicts were false negatives. The
corrected mechanism is interpretable for 15/16 attempts.

Phase 8 P100 remains `clamp_not_exercised` and is **not** a false negative: it
stopped at +100 before the raw lie pushed believed airspeed far enough past the
protected upper bound to exercise the clamp (raw believed plateau ≈ the +100
prefix of the protected DO15 ramps). This is a genuine non-exercise, consistent
with frozen expectation row 8's "must match Phase 7's P10…P100 prefix".

## Objective corrected results

- Protected ramps (Phases 1, 3–7): the protected clamp was verified in at least
  one pre-rejection fault window in every attempt that exercised it. First AHRS
  source rejection was observed in the ~+119 to +139 range where it occurred,
  with the `ARSP.U` parameter disable occurring at the same or a higher bias
  (source rejection precedes or coincides with parameter disable; the two are
  never equated).
- Diagnostic Phase 2: believed `CTUN.As` tracks raw `ARSP.Airspeed` while
  `CTUN.AsT==1`; all three attempts are `unclamped_tracking_verified`. They
  reached +110 and stopped on low-altitude abort, matching the recorded
  loss/timeout behavior.
- Per-attempt endpoints vary (max bias 99–199); the phase summaries report
  median [min, max] and per-attempt highest bias rather than assuming every
  P200 cell reached P200.
- 14 of 16 attempts stopped on `low_altitude_abort` after valid injection; both
  ramp-complete attempts are Phase 4 attempt 3 and Phase 6 attempt 1 (plus Phase
  8 P100). Aborted windows are marked `partial_behavior_window`.

These are mechanism-interpretability and telemetry facts only. Whether the
tailwind behavior agrees with physics, the controller model, or headwind is
deferred to Chunk 5; the locked columns are untouched.

## Raw-data adequacy for Chunk 4

- No genuine raw-data defect found. Every BIN decoded; every fault window
  PARM-anchored with zero schedule-matching errors; every applied fault event
  accounted for; all 16 BIN hashes match inventory.
- The low-altitude aborts are valid flight behavior after valid injection, not
  missing evidence. Post-abort altitude sink produces some negative window-median
  altitudes; `POS.RelHomeAlt` and `-SIM2.PD` agree within noise, so this is real
  post-loss telemetry, not a decode error.
- No rerun is justified by this batch.

## Limitations

- This is working analysis under `var/`, not curated evidence.
- Diagnostic tracking and protected-clamp verification confirm the
  measurement/mechanism path; they are not a behavior-acceptance claim.
- Window steady-state summaries use medians over the trimmed window; the
  authoritative per-row clamp arithmetic lives in the production gate signals in
  each per-attempt JSON.
- Chunk 4 (rerun adjudication) and Chunk 5 (cross-comparison and locked-column
  fill) are not performed here.

## References

- Working package:
  `var/analysis/tailwind_phase_1_8_corrected_reanalysis_20260623/`
  (`README.md`, `reanalyze.py`, `provenance.json`, `validation.json`, summary
  tables, `attempts/`).
- Frozen expectations:
  `governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_0_9_expectations.md`.
- Inventory:
  `governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_0_9_inventory.md`
  and
  `var/analysis/tailwind_phase_0_9_expectations_20260623/tailwind_run_inventory.json`.
- Evaluator: `analyze_mechanism_bin` in
  `src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/analyzers.py`;
  `src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/mechanism_gate.py`.
- Prior tailwind P130 pulse correction (same evaluator family):
  `evidence/reports/features/2026-06-23_tailwind_pulse_evaluator_correction.md`.
