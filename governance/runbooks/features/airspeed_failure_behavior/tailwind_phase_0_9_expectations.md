# Tailwind Phase 0–9 Frozen Expectations

Freeze timestamp: `2026-06-23T10:53:08Z` (UTC)

Freeze scope: Phases 1–8 were frozen before their tailwind telemetry, behavior
summaries, or BINs were inspected. Phase 0 and Phase 9 are explicitly
`prior-known` because their tailwind results had already been reviewed.

Hash record: the SHA-256 of this file is recorded externally in
`var/analysis/tailwind_phase_0_9_expectations_20260623/expectations_sha256.txt`
to avoid the self-hash problem. Any later correction must be an explicitly
dated amendment; do not rewrite this matrix to fit observed results.

## Scope and evidence boundary

This is a preregistration record, not a tailwind acceptance report. Before this
freeze, inspection was limited to general flight physics, local ArduPilot
source, mission/parameter inputs, the historical headwind roots named by
`config/campaigns/airspeed_failure_tailwind_counterparts.json`, the accepted
healthy headwind raw reference, and the completed same-mission P130 headwind
control. No unreviewed Phase 1–8 tailwind artifact or BIN informed these rows.

The working headwind decode is:

`var/analysis/tailwind_phase_0_9_expectations_20260623/historical_headwind_summary.json`

It was produced with `./env/bin/python3` and `pymavlink`. Ramp and pulse windows
use logged `SIM_ARSPD_RATIO` `PARM` transitions in BIN time. Each numerical
window summary excludes the first 10 seconds after a transition and the final
2 seconds before the next transition. `ARSP.U` and `CTUN.AsT` are never treated
as synonyms.

## Fixed interpretation principles

- Healthy reversal from 5 m/s Eastbound headwind to 5 m/s Eastbound tailwind
  should add approximately 10 m/s to `GPS.Spd` while leaving aerodynamic trim
  broadly similar.
- While the sensor is the AHRS source (`CTUN.AsT=1`), the protected upper EAS
  arithmetic is `(GPS.Spd + AHRS_WIND_MAX) / CTUN.E2T`.
- Matched tailwind raises that protected upper bound by approximately
  `10 / CTUN.E2T` relative to headwind. Protected tailwind can therefore expose
  TECS to a larger false-high believed airspeed before source rejection.
- `AHRS_WIND_MAX=0` removes that clamp. Its aerodynamic response should be more
  direction-neutral, although tailwind `GPS.Spd` can misleadingly appear
  healthy while true airspeed is poor.
- `AIRSPEED_MAX` limits demanded airspeed, not believed airspeed.
- `DO_CHANGE_SPEED=15` overrides `AIRSPEED_CRUISE`. Phases 3–7 are not clean
  cruise-demand comparisons; their demand should remain 15 EAS.
- Phase 8 P100 should reproduce the +10 through +100 prefix of the matched
  Phase 7 P200 ramp, subject to ordinary run scatter and shared-history effects.
- Pulse and ramp predictions are separate. A pulse has baseline recovery
  windows; a ramp accumulates controller and airframe history without resets.
- The historical +60% `ARSP.U` disable point is not copied into blind Phase
  1–8 predictions. Initial AHRS source rejection (`CTUN.AsT != 1`) and later
  parameter disable (`ARSP.U=0`) are separate events.
- `CTUN.AsT=1` means the AHRS is using the sensor. `CTUN.AsT=3` means EKF
  synthetic airspeed. `ARSP.U` can remain enabled after the source has changed.

`TECS.spdem` is logged in TAS units. At the observed `CTUN.E2T≈1.03`, a 14 EAS
cruise demand appears near 14.4–14.5 m/s TAS and a 15 EAS mission demand near
15.5 m/s TAS.

## Historical headwind actual behavior

Values are endpoint-window attempt medians shown as
`group median [minimum, maximum]`. Counts include every completed attempt under
all authoritative roots; smoke duplicates are not silently collapsed. P200
ramp endpoints are the +200 window except Phase 2, whose three attempts ended
at +110 with valid fault observation followed by loss/timeout. Phase 9 combines
the recipe's historical headwind root with the usable attempt from the new
same-mission control; the control's incomplete attempt 1 had no BIN and is not
counted as a headwind behavior sample.

| Phase | Historical source root(s) | n | Endpoint actual behavior under headwind |
| ---: | --- | ---: | --- |
| 0 | `var/runs/airspeed_failure_behavior_20260606T164050810132Z` (`healthy_reference`, reciprocal mission) | 1 | Healthy Eastbound: raw airspeed mean 15.23 m/s, GPS mean 10.81 m/s, `ARSP-GPS=+4.42`, altitude mean 99.59 m, nominal completion. This is a mission-geometry reference, not a matched 36 km control. |
| 1 | `var/runs/tier1_protected_cruisefollow_n3` | 3 | At P200: raw 38.14 [37.39, 41.14], believed 22.09 [21.74, 26.90], demand 14.46 [14.46, 14.46], true 13.16 [12.84, 14.14], GPS 7.77 [7.46, 12.85], altitude 84.33 [76.63, 84.91] m. `CTUN.AsT=1` and `ARSP.U=1` persisted; all three were valid degraded completions. |
| 2 | `var/runs/tier2_windmax0_verify_20260616T100204Z` | 3 | Runs reached P110 before loss/timeout: raw 31.72 [31.24, 32.12], believed 24.66 [21.90, 26.20], demand 14.45 [14.45, 14.45], true 15.61 [15.36, 15.77], GPS 10.26 [9.99, 10.96], altitude 73.68 [71.90, 75.47] m, pitch −19.07° [−25.23°, 0.66°], AOA 15.65° [13.41°, 16.00°]. Each endpoint still had mostly `CTUN.AsT=1`; all three were valid loss/timeout observations. |
| 3 | `var/runs/envelope_matrix_max28_n3`; `var/runs/airspeed_envelope_smoke_max28_ramp_p200_20260614T124322Z`; `var/runs/airspeed_envelope_smoke_max28_ramp_p200_20260614T121220Z` | 5 | At P200: raw 37.16 [37.15, 37.16], believed 22.12 [22.12, 22.12], demand 15.49 [15.49, 15.49], true 12.79 [12.79, 12.80], GPS 7.85 [7.85, 7.85], altitude 85.58 [85.57, 85.61] m. `CTUN.AsT=1`, `ARSP.U=1`; five degraded completions. |
| 4 | `var/runs/envelope_matrix_max18_n3`; `var/runs/envelope_matrix_max18_ramp_p200_20260615T085029Z` | 4 | At P200: raw 37.15 [37.15, 37.15], believed 22.12 [22.12, 22.12], demand 15.49 [15.49, 15.49], true 12.79 [12.79, 12.79], GPS 7.85 [7.85, 7.85], altitude 85.56 [85.51, 85.75] m. `CTUN.AsT=1`, `ARSP.U=1`; four degraded completions. |
| 5 | `var/runs/envelope_matrix_cruise17_ramp_p200_20260615T091922Z` | 1 | At P200: raw 37.15, believed 22.12, demand 15.49, true 12.79, GPS 7.85, altitude 85.58 m, `CTUN.AsT=1`, `ARSP.U=1`; degraded completion. |
| 6 | `var/runs/envelope_matrix_scaled18_28_ramp_p200_20260615T082120Z` | 1 | At P200: raw 37.16, believed 22.12, demand 15.49, true 12.80, GPS 7.85, altitude 85.79 m, `CTUN.AsT=1`, `ARSP.U=1`; degraded completion. |
| 7 | `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p200_headwind_20260610T122611Z` | 1 | At P200: raw 37.15, believed 22.12, demand 15.49, true 12.79, GPS 7.85, altitude 85.58 m, `CTUN.AsT=1`, `ARSP.U=1`; degraded completion. |
| 8 | `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p100_headwind_20260610T111134Z` | 1 | At P100: raw 24.77, believed 22.12, demand 15.49, true 12.79, GPS 7.85, altitude 85.81 m, `CTUN.AsT=1`, `ARSP.U=1`; nominal completion under the historical classifier. |
| 9 | `var/runs/airspeed_failure_behavior_ratio_bias_pulse_p10_to_p130_headwind_20260610T075155Z`; `var/runs/headwind_control_same_mission_standard_speed15_pulse_p130_n1` attempt 2 | 2 | At P130, both controls agree closely: raw median 30.47 [30.46, 30.47], believed 13.28 [13.26, 13.29], demand 15.50 [15.50, 15.50], true 13.68 [13.68, 13.68], GPS 8.75 [8.75, 8.75], altitude 99.75 [99.64, 99.86] m. Both first rejected the AHRS sensor source at +50 and disabled `ARSP.U` at +60; at P130 `CTUN.AsT=3`, `ARSP.U=0`. The same-mission control is `clamp_verified` and interpretable. |

## Frozen Phase 0–9 expectation matrix

Abbreviations: `protected` means `AHRS_WIND_MAX=15`; `diagnostic` means
`AHRS_WIND_MAX=0`; `raw` means `ARSP.Airspeed`; `believed` means `CTUN.As`;
`true` means `SIM2.As`; and `GPS` means `GPS.Spd`. P200 ramps contain baseline
then +10…+200; P100 stops at +100; P130 pulses alternate baseline and
+10…+130 fault windows.

| Phase | Configuration | Mission | Speed-demand source | Mechanism tier | Historical headwind source root | Headwind sample count | How it actually behaved under headwind | Physics-only tailwind expectation | ArduPilot/controller tailwind expectation | Expected raw `ARSP.Airspeed` | Expected believed `CTUN.As` | Expected demand `TECS.spdem` | Expected true airspeed `SIM2.As` | Expected `GPS.Spd` | Expected `CTUN.AsT` behavior | Expected `ARSP.U/H/Hp/TR` behavior | Expected altitude/throttle/pitch/AOA response | What would make physical/controller sense | What would be suspicious | Prior-knowledge status | Tailwind actually observed | Headwind-to-tailwind delta | Makes sense: yes/no/partly | Explanation | Suspected implementation defect | Residual confounder |
| ---: | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Healthy tailwind, standard 14/10/22 overlay | 36 km Eastbound DO15 | `DO_CHANGE_SPEED=15` | protected | Phase 2 healthy raw root; reciprocal mission caveat | 1 | Healthy headwind Eastbound raw 15.23, GPS 10.81, altitude 99.59 m | Same ~15 m/s aerodynamic trim; GPS should rise by ~10 m/s to ~20–21 | No clamp or rejection should be exercised; nominal altitude hold | ~15 EAS | ~15 EAS | ~15.5 TAS | ~15–15.5 TAS | ~20–21 | Remain 1 | `U/H≈1`, `Hp` high, `TR` low | Near 100 m; throttle/pitch/AOA broadly like healthy headwind | Similar true/raw/believed speed with GPS shifted upward by wind reversal | Large aerodynamic-trim change, source rejection, disable, or GPS not ~10 m/s above matched headwind | `prior-known` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 1 | P200, standard 14/10/22 | 36 km Eastbound cruise-follow | `AIRSPEED_CRUISE=14` | protected | `var/runs/tier1_protected_cruisefollow_n3` | 3 | P200 median raw 38.14, believed 22.09, true 13.16, GPS 7.77, altitude 84.33; AsT1/U1 persisted | Raw lie initially pushes controller toward lower true speed; tailwind GPS remains true+~5 and may look benign | Protected upper bound is ~9.7 EAS higher than matched headwind, so believed speed may climb beyond the headwind plateau before source rejection/recovery | Rise roughly as `k×true`; endpoint plausibly 30–45 depending true-speed reduction and rejection | While AsT1, no higher than `(GPS+15)/E2T`; after rejection, synthetic near true EAS | ~14.4–14.5 TAS | Fall below healthy while lie is believed; recover toward trim after rejection | Approximately true+5; about 10 above matched headwind for equal true speed | Begin at 1; may change to 3 before U disables; no blind threshold | Health probability may fall and TR rise; U may disable later than AsT switch, but threshold is not preregistered | More altitude loss / lower throttle or nose-down response as believed speed rises; recovery after rejection is plausible | Larger false-high believed plateau than headwind, declining true speed, GPS offset by +5 | Believed exceeds protected arithmetic while AsT1, demand follows raw, or U is used to infer source | `blind/frozen before tailwind analysis` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 2 | P200, standard 14/10/22 except `AHRS_WIND_MAX=0` | 36 km Eastbound cruise-follow | `AIRSPEED_CRUISE=14` | diagnostic | `var/runs/tier2_windmax0_verify_20260616T100204Z` | 3 | All ended around P110 with loss/timeout; median raw 31.72, believed 24.66, altitude 73.68, pitch −19.07°, AOA 15.65° | Direction-neutral aerodynamic damage: controller should reduce true speed toward demand/k; tailwind GPS=true+5 can mask low TAS | No AHRS clamp; believed should track raw only while AsT1. EKF rejection may still switch to synthetic | Track `k×true`; may become very high before rejection or loss | Approximately raw while AsT1; synthetic near true after AsT3 | ~14.4–14.5 TAS | Strong fall, possible stall/loss before P200; recovery only if rejection occurs in time | True+~5 and potentially deceptively near 14–15 even when true speed is unsafe | 1 until EKF rejection, then 3; exact bias not preregistered | H/Hp degrade and TR rise; U may lag AsT or remain 1; no copied +60 threshold | Greatest expected altitude loss and extreme pitch/AOA/throttle transients; loss/timeout physically plausible | Similar aerodynamic severity to headwind at a matched bias despite GPS being ~10 higher | A protected plateau with `AHRS_WIND_MAX=0`, healthy aerodynamics inferred from GPS alone, or full P200 completion claimed with missing windows | `blind/frozen before tailwind analysis` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 3 | P200, max28 overlay (14/10/28) | 36 km Eastbound DO15 | `DO_CHANGE_SPEED=15` | protected | max28 n3 plus two smoke roots | 5 | P200 was essentially identical across five samples: raw 37.16, believed 22.12, true 12.79, GPS 7.85, altitude 85.58; AsT1/U1 | Similar to other protected DO15 ramps; wind reversal raises GPS and protected believed bound | AIRSPEED_MAX=28 cannot raise the DO15 demand and does not cap believed airspeed; tailwind clamp/source logic should dominate | `k×true`, plausibly higher endpoint raw than headwind if a larger lie survives | Protected formula while AsT1; synthetic after rejection; may exceed headwind 22.12 plateau | ~15.5 TAS, not 28 | Likely below healthy and potentially lower than headwind before rejection | True+~5 | 1 then possibly 3; threshold unknown | Degrading H/Hp/TR, U possibly later 0; no threshold prediction | Altitude loss and controller transients; max28 alone should not create a 28 m/s demand | Similarity to other DO15 protected cells, with larger tailwind clamp room | `TECS.spdem≈28`, believed clipped at AIRSPEED_MAX, or interpreting overlay as cruise demand | `blind/frozen before tailwind analysis` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 4 | P200, max18 overlay (14/10/18) | 36 km Eastbound DO15 | `DO_CHANGE_SPEED=15` | protected | max18 n3 plus one smoke root | 4 | P200 raw 37.15, believed 22.12, true 12.79, GPS 7.85, altitude 85.56; AsT1/U1 | Same aerodynamic expectation as other DO15 protected ramps | AIRSPEED_MAX=18 caps demand, not believed; DO15 is still inside the envelope | `k×true`; not capped at 18 | Protected formula while AsT1, potentially above 18; synthetic after rejection | ~15.5 TAS | Fall below healthy during accepted lie; possible recovery after rejection | True+~5 | 1 then possibly 3; threshold unknown | Health degrades; U can lag source switch | Altitude loss and pitch/AOA/throttle response similar to other DO15 cells | Believed airspeed above 18 is allowed and expected if clamp permits it | Believed hard-clipped to 18 solely because AIRSPEED_MAX=18, or demand differs from DO15 | `blind/frozen before tailwind analysis` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 5 | P200, cruise17 overlay (17/10/22) | 36 km Eastbound DO15 | `DO_CHANGE_SPEED=15` | protected | `var/runs/envelope_matrix_cruise17_ramp_p200_20260615T091922Z` | 1 | P200 raw 37.15, believed 22.12, true 12.79, GPS 7.85, altitude 85.58; AsT1/U1 | Same as standard DO15 protected ramp | AIRSPEED_CRUISE=17 is overridden by DO15; only fallback/controller secondary effects may differ | `k×true` | Protected formula while AsT1; synthetic after rejection | ~15.5 TAS, not 17.6 | Similar to Phase 7, not a clean 17 EAS operating point | True+~5 | 1 then possibly 3; threshold unknown | Degrade/later disable possible; no threshold prediction | Similar altitude/throttle/pitch/AOA to Phase 7 within run scatter | Near-equivalence with standard DO15 is expected | Demand at 17 EAS or calling this a cruise-demand test | `blind/frozen before tailwind analysis` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 6 | P200, scaled18/28 overlay (18/10/28) | 36 km Eastbound DO15 | `DO_CHANGE_SPEED=15` | protected | `var/runs/envelope_matrix_scaled18_28_ramp_p200_20260615T082120Z` | 1 | P200 raw 37.16, believed 22.12, true 12.80, GPS 7.85, altitude 85.79; AsT1/U1 | Same protected DO15 physics | Cruise18 is overridden and max28 limits demand only; protected bound/source rejection dominate | `k×true` | Protected formula while AsT1; synthetic after rejection | ~15.5 TAS | Similar to Phase 7 unless fallback after rejection exposes cruise setting | True+~5 | 1 then possibly 3; threshold unknown | Health degradation; U can lag | Similar degradation to standard DO15, with possible post-rejection fallback nuance | Strong similarity to Phases 3–7 before source rejection | Demand 18 or 28, or treating believed plateau as AIRSPEED_MAX | `blind/frozen before tailwind analysis` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 7 | P200, standard 14/10/22 | 36 km Eastbound DO15 | `DO_CHANGE_SPEED=15` | protected | `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p200_headwind_20260610T122611Z` | 1 | P200 raw 37.15, believed 22.12, true 12.79, GPS 7.85, altitude 85.58; AsT1/U1 | Tailwind permits a higher protected believed-air bound and may allow deeper true-speed degradation before rejection | Clamp arithmetic, not AIRSPEED_MAX, should set the accepted false-high bound while AsT1 | `k×true`, perhaps 30–45 at P200 | Up to `(GPS+15)/E2T` while AsT1; synthetic after rejection | ~15.5 TAS | Decline through ramp, with possible later recovery | True+~5 | 1 then possibly 3; threshold unknown | H/Hp fall, TR rise, U may later disable | Accumulated altitude loss and increasing control effort; recovery need not erase earlier loss | Smooth P10…P200 progression with controller history retained | Baseline resets between ramp levels, wall-clock windowing, or a hard 22 cap attributed to AIRSPEED_MAX | `blind/frozen before tailwind analysis` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 8 | P100, standard 14/10/22 | 36 km Eastbound DO15 | `DO_CHANGE_SPEED=15` | protected | `var/runs/airspeed_failure_behavior_ratio_bias_ramp_p10_to_p100_headwind_20260610T111134Z` | 1 | P100 raw 24.77, believed 22.12, true 12.79, GPS 7.85, altitude 85.81; AsT1/U1 | Must match Phase 7's P10…P100 prefix in direction and approximate magnitude | Same clamp/source rules as Phase 7; stopping at P100 should not change the earlier windows | Match Phase 7 prefix; endpoint about `2×true` | Match Phase 7 prefix and protected bound | ~15.5 TAS | Match Phase 7 prefix | True+~5; match Phase 7 prefix | Match Phase 7 prefix | Match Phase 7 prefix; no threshold copied from pulse | Similar early accumulated altitude/control response as Phase 7 through P100 | Prefix agreement with P200 within run scatter | Material prefix divergence, different mission/config provenance, or pulse-like reset behavior | `blind/frozen before tailwind analysis` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |
| 9 | P10–P130 pulse, standard 14/10/22 | 36 km Eastbound DO15 | `DO_CHANGE_SPEED=15` | protected | historical P130 root plus same-mission control root | 2 | Both headwind samples rejected AHRS source at +50 and disabled U at +60; P130 raw ~30.47 but believed synthetic ~13.28, true 13.68, GPS 8.75, altitude ~99.75 | Each fault pulse should temporarily raise raw; tailwind raises protected bound; baseline resets should restore near-healthy aerodynamics between pulses | Source rejection can precede U disable. Because this cell is prior-known, the already-reviewed tailwind mechanism result is not treated as blind evidence, but actual values remain locked for Chunk 5 | During each pulse ~`k×true`; baseline returns near true | Protected formula only while AsT1; synthetic near true after rejection | ~15.5 TAS throughout | Dip during accepted pulses and recover during baselines; less cumulative loss than ramp | True+~5; baseline near ~20 | 1 in healthy baselines; may switch 3 in fault windows before U changes | Health/TR respond per pulse; U may disable after repeated inconsistency and later recover/reset; source and U remain distinct | Transient throttle/pitch/AOA and altitude excursions with inter-pulse recovery; smaller cumulative drift than ramp | All 13 fault windows aligned by BIN PARM transitions, plus distinct rejection and disable thresholds | Applying ramp expectations, evaluating only P130, using wall UTC, or equating U1 with AsT1 | `prior-known` | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — | — `LOCKED UNTIL CHUNK 5` — |

## Local source anchors

- `src/ardupilot/libraries/AP_AHRS/AP_AHRS.cpp`: sensor and synthetic EAS
  paths, source rejection, and `groundspeed ± AHRS_WIND_MAX` TAS constraints.
- `src/ardupilot/libraries/AP_Airspeed/AP_Airspeed_Health.cpp`: EKF
  consistency, health probability, and delayed parameter disable/re-enable.
- `src/ardupilot/ArduPlane/navigation.cpp`: `DO_CHANGE_SPEED` precedence,
  `AIRSPEED_CRUISE` fallback, and demand limiting by `AIRSPEED_MAX`.
- `src/ardupilot/libraries/AP_TECS/AP_TECS.cpp`: EAS/TAS conversion and TECS
  airspeed state/limit handling.
- `src/ardupilot/ArduPlane/Log.cpp`: `CTUN.As`, `CTUN.AsT`, and `CTUN.E2T`
  logging semantics.

## Freeze rule

Phases 1–8 are now blind-frozen. Later observations may confirm, contradict,
or complicate these expectations, but may not retroactively alter them. A
mistake discovered before Chunk 5 must be recorded as a dated amendment with
its own reason and hash.

## Amendment record

`2026-06-23T11:03:31Z`: formatting-only amendment after the initial freeze.
Markdown hard-break trailing spaces were replaced with blank lines so workspace
whitespace validation remains clean. No expectation, value, phase status,
historical input, or interpretation changed. The initial and final hashes are
both retained in the sidecar freeze record.
