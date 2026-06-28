# Tailwind Phase 0–9 Realized-Results Comparison (Chunk 5)

Date: 2026-06-23 UTC

This is the **separate realized-results matrix** for Chunk 5. The frozen
preregistration record
`tailwind_phase_0_9_expectations.md`
(SHA-256 `ce8e9bc267b518a229505071eed23f8187100f5f1659d6373b9719a3d4e0d654`)
is **not modified**. This file fills the post-observation columns the frozen
record left `LOCKED UNTIL CHUNK 5`, alongside the headwind→tailwind deltas, the
makes-sense assessment, the suspected-defect classification, and the residual
confounder, so the original prediction record is preserved intact.

Working analysis package (additive, under `var/`, not promoted):
`var/analysis/tailwind_phase_0_9_comparison_20260623/`.

## Method and discipline

- Tailwind Phase 1–8 per-window telemetry consumed from the Chunk 3 corrected
  reanalysis (`window_summary.json`); Phase 0 healthy tailwind and Phase 9
  pulse decoded directly; **headwind windows re-decoded from raw BINs** with the
  preregistered headwind windowing helper. Identical window contract on both
  sides: in-BIN `SIM_ARSPD_RATIO` `PARM` transitions, +10 s/−2 s trim,
  `CTUN.AsT=1` for sensor clamp rows, `ARSP.U` kept separate.
- Comparisons are made at **matched commanded-bias windows**. The +10 % ramp
  recipe lands the "+100" anchor at the **+99** bias label after rounding; both
  directions use the same label sequence, so +99 is the matched +100 window.
- Bias labels are commanded/nominal. Measured raw magnitude is reported
  separately; commanded and measured bias are never conflated.
- Repeated phases use **median [min, max]** with attempt count; per-attempt
  endpoints are preserved (`attempt_final_window.csv`). Low-altitude aborts are
  never hidden in a mean. P200 endpoint values are never assigned to attempts
  that did not reach P200.
- Pulse and ramp results are kept separate. Phase 0 and Phase 9 are
  `prior-known`; Phases 1–8 were genuinely frozen before tailwind telemetry.

## Pairing grades

| Phase | Comparator | Grade |
| ---: | --- | --- |
| 0 | Phase 2 healthy headwind raw root (reciprocal mission) | C_contextual_reference |
| 1 | `tier1_protected_cruisefollow_n3` headwind | B_config_matched |
| 2 | `tier2_windmax0_verify` headwind | B_config_matched |
| 3 | `envelope_matrix_max28` + 2 smoke roots | B_config_matched |
| 4 | `envelope_matrix_max18` + 1 smoke root | B_config_matched |
| 5 | `envelope_matrix_cruise17` | B_config_matched |
| 6 | `envelope_matrix_scaled18_28` | B_config_matched |
| 7 | `ratio_bias_ramp_p10_to_p200_headwind` | B_config_matched |
| 8 | `ratio_bias_ramp_p10_to_p100_headwind` | B_config_matched |
| 9 | **same-mission headwind control attempt 002** (+ historical P130 root) | **A_exact_pair** |

No strong causal claim is drawn from a Grade C comparison. The single
strongest comparator is the Phase 9 Grade A same-mission pulse pair.

## Realized-results matrix

`raw`=`ARSP.Airspeed`, `believed`=`CTUN.As`, `true`=`SIM2.As`, `GPS`=`GPS.Spd`,
`demand`=`TECS.spdem` (TAS). Deltas are tailwind − headwind at the stated
window. "Highest" rows are each direction's own endpoint, labeled as a mismatch
where the other direction did not reach it.

| Phase | Config | Grade | Frozen expectation (short) | Historical headwind actual | Tailwind actual | Matched window | rawΔ | believedΔ | demandΔ | trueΔ | GPSΔ | source/reject Δ | alt/thr/pitch/AOA Δ | Result | Physical explanation | Controller explanation | Suspected defect | Residual confounder | Evidence |
| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | :---: | --- | --- | --- | --- | --- |
| 0 | healthy 14/10/22 DO15 | C | GPS rises ~+10, trim unchanged, no clamp/rejection | raw 14.98, believed 14.99, true 15.47, GPS 10.57, alt 99.97, thr 64.2, pitch −1.57 | raw 14.99, believed 15.00, true 15.47, GPS 20.55, alt 99.98, thr 64.2, pitch −1.52 | healthy cruise | +0.02 | +0.00 | n/a | +0.0001 | **+9.98** | none (AsT1/U1 both) | alt +0.02, thr +0.06, pitch +0.05, AOA +0.07 | **yes** | Wind reversal shifts only ground-relative GPS by ~10; airmass-relative trim is direction-independent | No clamp or rejection exercised; demand/trim identical | no_defect_evidence | Grade C reciprocal-mission reference; robust because steady cruise, same heading/demand | strong |
| 1 | protected cruise-follow P200, `AIRSPEED_CRUISE=14` | B | Higher protected ceiling; believed plateau exceeds headwind before rejection | P200 median raw 38.14, believed 22.09, true 13.16, GPS 7.77, alt 84.33; AsT1/U1 to +199 | final-valid +119 median: raw ~29.6, believed ~29, true ~13.5, GPS ~15.5, alt ~70; reject +119 median (max bias 119/139/129), low-alt abort | baseline / +10 / +50 | +0.0 (+50: +0.01) | +0.0 | +0.0 | +0.0 | **+10.0** | tailwind rejects +119; headwind never rejects | matched +10/+50 ~identical; tailwind believed ceiling ~+8 higher at endpoint | **yes** | Higher tailwind GPS raises clamp ceiling; deeper degradation before rejection | Clamp = `(GPS+15)/E2T`: tw ~30 vs hw ~22. Demand held ~14.4 TAS. Reject (AsT≠1) ≤ U disable | expected_controller_behavior | Grade B geometry; endpoints differ (tw abort vs hw +199 plateau) reported separately | strong |
| 2 | diagnostic cruise-follow P200, `AHRS_WIND_MAX=0` | B | No clamp; believed tracks raw; direction-neutral aero; possible loss | P200/+109 median raw 31.72, believed 24.66, true 15.61, GPS 10.26, alt 73.68, pitch −19°, AOA 15.6° | +109 median raw ~26.9, believed ~28.4, true ~13.3, GPS ~14.2, alt ~72.7; reject +109, low-alt abort | baseline / +10 / +50 / +109 | +50: +0.0; +109: −4.8 | +109: +3.8 | +0.0 | +109: −2.3 | **+10.0** | tw reject +109, U mostly stays 1 (reject without disable in 2/3); hw similar | believed tracks raw unbounded (no clamp); aborts slightly earlier than protected P1 | **yes** | `wind_max>0` clamp guard skipped (`AP_AHRS.cpp:985`); believed = raw sensor EAS | Disable here is EKF-consistency-driven; `data_is_implausible` needs `wind_max>0` so cannot fire | expected_controller_behavior | Grade B geometry; "worse than P1" is mechanism-different, not monotone; both unsafe | strong |
| 3 | max28 DO15 P200 | B | Like other protected DO15; demand not 28; believed not capped at 28 | P200 raw 37.16, believed 22.12, true 12.79, GPS 7.85, alt 85.58 (n=5); AsT1/U1 to +199 | +119 final-valid raw ~30.9, believed ~30.4, true ~14.5, GPS ~16.6, alt ~68; reject/abort +129 (n=3) | baseline / +10 / +50 | +0.0 | +0.0 | +0.0 | +0.0 | **+10.0** | tw reject ~+129; hw none | believed rode to ~30, not capped at 28; demand ~15.5 TAS, not 28 | **yes** | Same protected DO15 physics; clamp ceiling set by GPS, not AIRSPEED_MAX | `AIRSPEED_MAX=28` limits demand only and did not engage; believed > 28 allowed | expected_controller_behavior | Grade B; 5 hw vs 3 tw attempts | strong |
| 4 | max18 DO15 P200 | B | Believed not hard-capped at 18; like other DO15 | P200 raw 37.15, believed 22.12, true 12.79, GPS 7.85, alt 85.56 (n=4) | endpoints scatter: att1 +129, att2 +189, att3 **+199** (believed ~32.7, true ~15.5, GPS ~18.8, alt ~60) | baseline / +10 / +50 | +0.0 | +0.0 | +0.0 | +0.0 | **+10.0** | reject 129/189/139; one completer | believed rode to ~32.7 (>>18); demand ~15.5 TAS | **yes** | DO15 inside the 18 envelope; AIRSPEED_MAX caps neither believed nor (lower) demand | believed > 18 allowed; endpoint scatter is threshold-crossing timing, not config | run_history_or_timing_confounder | Grade B; large within-phase endpoint scatter (129/189/199), reported per-attempt | moderate |
| 5 | cruise17 DO15 P200 | B | cruise17 overridden by DO15; like standard | P200 raw 37.15, believed 22.12, true 12.79, GPS 7.85, alt 85.58 (n=1) | +119 final-valid raw ~30.6, believed ~30.2, true ~14.4, GPS ~16.2, alt ~68; abort +129 (n=1) | baseline / +10 / +50 | +0.0 | +0.0 | +0.0 | +0.0 | **+10.0** | reject ~+129; hw none | standard DO15 protected behavior | demand ~15.5 TAS (not 17.6): DO15 overrides `AIRSPEED_CRUISE=17` | expected_controller_behavior | Grade B; n=1 each, no repetition scatter | moderate |
| 6 | scaled18/28 DO15 P200 | B | Like standard DO15; demand not 18/28 | P200 raw 37.16, believed 22.12, true 12.80, GPS 7.85, alt 85.79 (n=1) | **ramp complete +199**: raw ~43.3, believed ~31.4, true ~14.9, GPS ~17.5, alt ~63; reject +139 | baseline / +10 / +50 | +0.0 | +0.0 | +0.0 | +0.0 | **+10.0** | reject +139, no abort (completed) | one of two tailwind ramp-completers, like P4 att3 | demand ~15.5 TAS; cruise18 overridden, max28 demand-only | run_history_or_timing_confounder | Grade B; n=1. Reached +199 while P3/5/7 aborted ~+129 — timing/accumulated-state scatter | moderate |
| 7 | standard DO15 P200 | B | Higher believed ceiling; deeper degradation before rejection; smooth P10→P200, no resets | P200 raw 37.15, believed 22.12 (pinned to ceiling from +99), true 12.79, GPS 7.85, alt 85.58, rode flat to +199 | believed climbs to ~30.2 by +119, collapses to 21 (synthetic) at +129, alt sinks; reject +119, abort | baseline / +10 / +50 | +0.0 | +0.0 | +0.0 | +0.0 | **+10.0** | tw reject +119, U disable +129; hw never rejects | **canonical case**: hw believed pins at 22.1 plateau; tw rides to ~30 then rejects | **yes** | hw upper=`(7.85+15)/1.03=22.1`; tw upper=`(16.6+15)/1.03≈30.7` (+8.6). Higher tw ceiling → past plausibility → reject | Demand ~15.5 TAS throughout; no resets; `believed−protected_upper`→0 at clamp; `AIRSPEED_MAX` not a cap | expected_controller_behavior | Grade B; n=1 each. Endpoint mismatch is the finding, clearly labeled | strong |
| 8 | standard DO15 P100 | B | Reproduce Phase 7 +10…+100 prefix | P100 raw 24.77, believed 22.12, true 12.79, GPS 7.85, alt 85.81 | ramp complete +99: raw ~27.9, believed ~27.8, true ~14.4, GPS ~17.0, alt ~76.8 | baseline / +10 / +50 / +99 | +0.0 (+99 endpoint differs by climb) | +0.0 | +0.0 | +0.0 | **+10.0** | no rejection either side at +99 | matched +10/+50 prefix agrees; believed still climbing, clamp not yet engaged | **yes** | Same clamp/source rules; +99 prefix below clamp engagement | `clamp_not_exercised` genuine (not a false negative): believed not yet past protected upper at +99 | expected_controller_behavior | Grade B; n=1; prefix agreement within scatter | moderate |
| 9 | standard DO15 P130 pulse | **A** | Per-pulse dip + baseline recovery; tw raises ceiling; reject can precede U; prior-known | same-mission control + historical: reject AHRS **+50**, U disable **+60**; P130 believed synthetic ~13.3, true 13.68, GPS 8.75, alt ~99.75 | reject AHRS **+60**, U disable **+60**; per-pulse dips recover to baseline; GPS ~18 | baseline / +10 / +50 / +60 / +130 | +50: −0.6 | +50: +2.3 | +0.0 | +50: −0.4 | **+10.0** | **tw reject +60 vs hw +50 (one step later)**; U disable +60 both | each pulse transient, baselines recover; less cumulative drift than ramp | **yes** | Same-mission pair: only wind differs; tw +10 GPS raises implausibility margin → reject one step later | Pulse +50/+60 ≪ ramp +119–139: abrupt step spikes EKF innovation through `ARSPD_WIND_GATE=5`; slow ramp keeps innovation under gate | expected_controller_behavior | Grade A pair; minimal confounder | strong |

## Assessment summary

All ten phases: **yes**. The central frozen physical and controller predictions
are confirmed in every phase. No phase produced a `partly` or `no` because no
observed behavior contradicted an important prediction without a supported
physics/controller explanation.

Note for safety reading: a `yes` here means the behavior *makes physical and
controller sense*, not that it is safe. Protected tailwind exposes TECS to a
larger false-high believed airspeed (~+8 m/s higher clamp ceiling) and deeper
true-speed/altitude degradation before rejection than the matched headwind
plateau. The tailwind ramps end in low-altitude aborts; that is dangerous *and*
explainable.

## Answers to the expected key questions

1. **Healthy reversal ≈ +10 m/s GPS without trim change?** Yes — +9.98 m/s GPS,
   raw/believed/true/alt/throttle/pitch/AOA unchanged (Phase 0); +10.0 m/s at
   every ramp/pulse baseline.
2. **Protected tailwind raised the believed-airspeed clamp ceiling?** Yes —
   from `(GPS+15)/E2T≈22` (headwind) to `≈31` (tailwind), ~+8–9 m/s, matching
   the predicted `10/E2T`.
3. **Higher ceiling → more dangerous degradation before rejection?** Yes —
   tailwind believed reached ~30 and the aircraft lost altitude into a
   low-altitude abort; matched headwind held the 22 plateau and rode to +200.
4. **`AHRS_WIND_MAX=0` removed the clamp?** Yes — Phase 2 believed tracked raw
   directly (`unclamped_tracking_verified`).
5. **`DO_CHANGE_SPEED=15` made the cruise/max variants behave similarly?** Yes —
   Phases 3–7 all held TECS demand ~15.5 TAS regardless of cruise17/cruise18/
   max18/max28; matched prefixes agree.
6. **Why most tailwind ramps stopped near +120–140 while protected headwind
   reached +200?** The higher tailwind believed ceiling lets believed climb
   until it exceeds EKF/`|believed−GPS|` plausibility (~+119–139), triggering
   source rejection and altitude loss; the lower headwind ceiling pins believed
   at ~22, a stable degraded equilibrium that never trips rejection.
7. **Why did Phase 4 and Phase 6 sometimes reach +200 while similar protected
   cases aborted earlier?** Run-history/timing scatter: the exact bias at which
   the EKF-consistency gate and `|believed−GPS|` implausibility cross threshold
   depends on accumulated airframe/EKF state, not on the overlay. Endpoints
   129/189/199 (Phase 4) and +199 (Phase 6) are reported per-attempt.
8. **Did Phase 8 reproduce Phase 7 through +100?** Yes — matched +10/+50 windows
   agree and Phase 8 stops at +99 with believed still climbing
   (`clamp_not_exercised`), consistent with the Phase 7 +99 prefix.
9. **Why pulse rejection ~+50/+60 but ramp rejection much later?** Abrupt pulse
   steps spike the EKF airspeed innovation through `ARSPD_WIND_GATE=5`
   immediately; slow ramps keep innovation under the gate and the airframe
   decelerates so GPS falls too, delaying the implausibility crossing.
10. **Any evidence the tailwind implementation/wind sign/mission/schedule/
    evaluator/controller interpretation was wrong?** No runtime/flight-controller
    defect. Wind sign, raw scaling, mission/stack identity (Grade A for Phase 9),
    clamp arithmetic, demand source, `AIRSPEED_MAX` semantics, and
    `CTUN.AsT`/`ARSP.U` distinction all check out against local source. The only
    defects were analysis/evaluator defects already demonstrated and fixed in
    Chunks 1–3.

## Local source anchors used

- `src/ardupilot/libraries/AP_AHRS/AP_AHRS.cpp:982-996` — sensor EAS path and
  the `(gnd_speed ± AHRS_WIND_MAX)` TAS constraint (the protected clamp).
- `src/ardupilot/libraries/AP_AHRS/AP_AHRS.cpp:954-972` —
  `_should_use_airspeed_sensor`: EKF `rejecting_airspeed` switches the source
  (`CTUN.AsT≠1`) independently of the parameter disable.
- `src/ardupilot/libraries/AP_Airspeed/AP_Airspeed_Health.cpp:54-101` —
  `data_is_implausible` (`|airspeed − gps_speed| > AHRS_WIND_MAX`) and
  `data_is_inconsistent` (EKF test_ratio > `ARSPD_WIND_GATE`), health-probability
  decay, and the `ARSP.U` disable.

## Boundaries honored

No SITL/Gazebo launched; no `var/runs/` tree modified; no original manifests or
historical artifacts modified; the frozen expectations file is unchanged
(hash re-verified); no production flight/runtime code changed; nothing promoted
to `evidence/` and the campaign is not closed. Chunk 6 consolidation is **not**
performed here.
