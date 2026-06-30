# Airspeed Failure Behavior Review

Status: Phase 1 no-SITL foundation accepted on 2026-06-05. Phase 2 live
measurement smoke accepted on 2026-06-06 from raw output only. Phase 4A
ratio/ramp/pulse characterization accepted on 2026-06-14 from the 2026-06-11
curated package. Fixed-case repetitions remain open as Phase 4B; full-lane
acceptance is not closed.

## Acceptance Gates

| Phase | Acceptance gate | Current status |
| --- | --- | --- |
| Phase 0 | Candidate is airspeed; parameter list is sourced from `011_Sensor_Failure_Injection`; mission and lane stack are named; exact case payload semantics, ratio-sweep design, reset rules, injection trigger, fixed reference wind, mission design, and behavior-class vocabulary are locked. | Design locked 2026-06-03 (`design_research.md`, `design_adrs.md`, new mission); ratio numeric values + thresholds pending Phase 2 measurement. |
| Phase 1 | Plugin constructs with no SITL; cases generate correctly; registry resolves plugin; CLI dry-run/list-cases works; runtime parameter-probe path exists; airspeed analysis artifact schema is tested; no legacy wind runner import is needed for plugin construction. | Accepted 2026-06-05 after strict no-SITL review. One real issue was found and fixed before acceptance: the documented module CLI was not reachable from a normally sourced workspace because `setup.bash` did not export the workspace Python source path. A narrow pyright test typing issue was also fixed. The parameter-probe path remains Phase-1 schema/name validation only; live SITL probing remains Phase 2. |
| Phase 2 | One `healthy_reference` run and one `fail_primary` run execute under `var/runs/`; injection and reset are confirmed by parameter readback; fixed wind is recorded; required airspeed analysis artifacts exist; a dated smoke-review decision unlocks or blocks Phase 3; no curated feature evidence claim is made yet. | Accepted 2026-06-06 after the measurement rerun closed the required `OFS` no-op and `FAILP=500` probes. Final raw root: `var/runs/airspeed_failure_behavior_20260606T164050810132Z`. |
| Phase 3A / 4A | Ratio-bias sweep, headwind pulse ladder, and headwind stepped ramps have reviewed accepted observations, curated artifacts, catalog entry, and bounded wording. | Accepted 2026-06-14 by `evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`. |
| Phase 3B / 4B | Fixed cases have three accepted observations per case; behavior classes and observation-quality classes are assigned; failures are described as behavior outcomes where observation is valid; final fixed-case/full-lane report is curated. | Open. Fixed-case repetition requirement is not satisfied. |

## Review Rules

- Do not claim full airspeed failure lane acceptance until Phase 4B is accepted
  with dated evidence or the fixed-case contract is deliberately revised.
- Do not count failed launches, pre-injection failures, or incomplete artifacts
  as behavior observations.
- Do not count failed parameter readback, failed reset, or unverified reference
  wind as accepted behavior observations.
- Do count degraded or bad aircraft behavior when the injection occurred and
  artifacts are sufficient for classification.
- Treat CTE/path-quality metrics as optional supporting context, not the primary
  scorer for this lane.
- Keep runtime output under `var/`.
- Keep curated proof under `evidence/`.
- Keep code and scripts outside `evidence/`.

## Residual Risks To Watch

- The second-plugin proof is authorized by the accepted Phase 3G gate, but the
  feature can still create a false architecture signal if it edits `core/` or
  depends on hidden wind-specific runtime delegation.
- Injection is locked to entering seq 4 (first `MISSION_CURRENT seq==4` edge
  after front-half progress) on the new mission; a missed/late edge is a
  `pre_injection_failure`, never a late injection.
- Some airspeed faults may cause behavior that is hard to classify without a
  clear observation-quality rule.
- Parameter readback failure must be preserved as evidence of failed injection,
  not silently converted into a behavior outcome.
- The default overlay `config/overlays/plane_airspeed.parm` is the conservative
  14/10/22 stack; the new mission's 15 m/s command and 100 m cruise sit inside
  that envelope, so the overlay is appropriate. (The old high-wind concern no
  longer applies; the aggressive stack lives in a separate non-default overlay.)
- `SIM_ARSPD_*` semantics differ from the case names and the `011` JSON: `FAIL`
  is a forced m/s value, `OFS` is a no-op on `TYPE 100`, `PITOT` needs `FAILP`,
  and ratio bias is `ARSPD_RATIO/k^2` against the measured vehicle ratio. Names
  and semantics must be re-checked against the SITL build before live evidence,
  and ratio cases cannot be numerically locked until the vehicle `ARSPD_RATIO` is
  read back in Phase 2.
- The fixed wind (`x=-5,0,0`) value, frame, and SIGN must be recorded and
  verified (`ARSP−GPS ≈ +5` Eastbound on healthy_reference); otherwise
  groundspeed-vs-airspeed interpretation is weak.
- The mission ends in RTL: the classifier must separate a planned mission-end RTL
  (completion) from a fault-triggered early RTL/failsafe (`autopilot_contained`),
  using the max mission seq at the AUTO->RTL transition.
- Presentation wording must remain bounded: Phase 4A is accepted only for the
  ratio/ramp/pulse scope until the fixed-case Phase 4B package is completed or
  the contract is deliberately revised.
- Phase 2 measured `SIM_ARSPD_OFS` no-op and `SIM_ARSPD_FAILP=500` effect size
  once. Phase 4B must still close the fixed-case matrix and pool/replace the
  single-run provisional bands.

## Phase 3/4A Evidence Audit - 2026-06-14

Scope: desk audit of the existing 2026-06-11 curated package and stale
canonical wording. No live SITL or Gazebo launch was performed.

Evidence inspected:

- `evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`
- `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/README.md`
- `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/raw_data_index.md`
- `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/manifest.json`
- Curated ratio sweep, pulse ladder, ramp, and reproducibility CSV/JSON
  summaries under `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/`

Audit result:

- The package supports an interim characterization: 44 accepted one-bias
  ratio-sweep observations, 1 accepted pulse-ladder observation, 1 accepted
  +100 stepped-ramp observation, and 1 accepted +200 stepped-ramp observation.
- The package and report originally labeled the work as interim; the same
  evidence supports bounded Phase 4A acceptance when fixed cases are split into
  Phase 4B.
- The current evidence does not satisfy the Phase 4B fixed-case repetition
  contract. Under the current contract, each fixed case needs three accepted
  observations. Phase 2 has one accepted raw measurement-smoke observation each
  for `healthy_reference`, `ofs_noop_probe`, `pitot_500pa`, and
  `fail_primary`; `noise_5` and `noise_10` have no accepted live observations
  in the current evidence set. If governance explicitly allows Phase 2
  observations to seed the Phase 4B count, the minimum remaining fixed-case work
  is two more accepted observations each for `healthy_reference`,
  `ofs_noop_probe`, `pitot_500pa`, and `fail_primary`, plus three each for
  `noise_5` and `noise_10`. Without that reuse decision, run three accepted
  dedicated Phase 3 observations for all six fixed cases.

Decision: Phase 3B/4B remains open. New live runs require explicit operator
authorization under ADR-0004 before launch.

## Phase 4A Bounded Acceptance - 2026-06-14

Scope: ratio-bias sweep, headwind pulse ladder, and headwind stepped ramps only.
No live SITL or Gazebo launch was performed for this acceptance review.

Accepted evidence:

- `evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`
- `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/`
- `evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`

Decision: Phase 4A accepted for bounded ratio/ramp/pulse characterization.
Phase 4B fixed-case repetition/full-lane acceptance remains open.

## Remaining Phase 4B Fixed-Case Gate Checklist

Before any remaining Phase 4B fixed-case live work, preserve or record a dated
review that includes:

- raw roots for the `healthy_reference` and `fail_primary` attempts;
- effective parameter stack and hashes;
- exact fixed wind vector, frame, topic, and readback/echo result;
- exact injection trigger event and actual trigger timestamp/sequence;
- `airspeed_injection.json` readback and reset status;
- presence of all required airspeed analysis artifacts;
- behavior class and observation-quality class for each smoke attempt;
- explicit decision: Phase 3 unlocked, blocked, or rerun required.

## Phase 2 Implementation Review - 2026-06-05

Scope: implementation readiness for the guarded live smoke only. No SITL or
Gazebo launch was performed in this review.

Implemented gates:

- Airspeed plugin owns Phase 2 live launch and does not delegate runtime behavior
  to the wind-matrix plugin.
- Each live attempt starts a fresh SITL process, isolated SITL state directory,
  and workspace-built Gazebo plugin path recorded in `run_config.json`.
- Clean boot captures `SIM_ARSPD_*` source-default baseline and vehicle
  `ARSPD_RATIO/USE/TYPE` before wind, mission start, or injection.
- Baseline mismatch, missing source parameters, missing workspace Gazebo plugin,
  failed wind echo, stale mission identity, missed seq-4 trigger, or failed
  injection readback block accepted observation.
- Reference wind is published before mission start and strict-echo verified.
- Mission upload is followed by a mission-count and per-item download
  verification before arming.
- Injection is latched on the first `MISSION_CURRENT seq==4` after front-half
  progress while armed in AUTO.
- Injected parameters are read back, then reset to the captured boot baseline;
  reset status is preserved in `airspeed_injection.json`.
- Required Phase 2 smoke artifacts are written under the raw attempt directory,
  with `airspeed_behavior_summary.json` classifying behavior and observation
  quality.

Checks:

- `./env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py tests/unit/test_airspeed_failure_phase1.py`:
  PASS.
- `./env/bin/python3 -m unittest tests.unit.test_airspeed_failure_phase1`:
  PASS, 18 tests.
- `/home/ahmed/.local/bin/pyright src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py tests/unit/test_airspeed_failure_phase1.py`:
  PASS, 0 errors.
- `python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --list-cases`:
  PASS.
- `python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --dry-run --case fail_primary`:
  PASS; plugin constructs without live launch and preserves the
  `SIM_ARSPD_FAIL=1.0` payload plus source-default reset payload.
- `python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --live-smoke`:
  PASS as a negative guard; exits with the expected error requiring
  `--confirm-live-phase2`.
- `git diff --check`: PASS.
- `make doctor`: PASS.

Decision: Phase 2 is implemented and ready for an explicitly authorized live
smoke attempt. Phase 2 is not accepted and Phase 3 is not unlocked until the
live `healthy_reference` and `fail_primary` raw runs are reviewed with the
checklist above.

## Phase 2 Smoke Review - 2026-06-06

Scope: raw two-case live smoke only. No curated evidence was promoted.

Corrected accepted raw root:

```text
var/runs/airspeed_failure_behavior_20260606T100147466177Z/
```

Superseded diagnostic roots:

- `var/runs/airspeed_failure_behavior_20260606T094542320608Z/`: blocked before
  arming because mission verification treated ArduPlane's RTL row frame
  normalization (`3` downloaded as `0`) as stale mission state. Fixed by making
  mission verification command-aware for `MAV_CMD_NAV_RETURN_TO_LAUNCH`.
- `var/runs/airspeed_failure_behavior_20260606T094728776700Z/`: blocked on
  heartbeat after a failed run left xterm-wrapped ArduPlane children. Fixed by
  extending airspeed-owned cleanup to remove those wrappers.
- `var/runs/airspeed_failure_behavior_20260606T094958847616Z/`: produced valid
  raw flight artifacts, but was superseded because the first classifier pass
  mislabeled visible `fail_primary` fault behavior as `nominal_completion`.
  Fixed by marking large fault-induced airspeed deviation or airspeed-sensor
  failure text as degraded completion when the mission still reaches planned
  RTL.

Corrected raw attempt roots:

- `var/runs/airspeed_failure_behavior_20260606T100147466177Z/healthy_reference/runs/attempt_001/`
- `var/runs/airspeed_failure_behavior_20260606T100147466177Z/fail_primary/runs/attempt_001/`

Source snapshot recorded in both `run_config.json` files:

- `git_head`: `61fa07e7e2e94edb09bf46867ba0234131d6dd71`
- `dirty`: `true`
- `diff_sha256`: `ea5e50968bb9bf728e32fdcd41fb1659e14972cbadd6cb3a2c0a42019c3ee01e`
- untracked live modules: `src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/mavlink.py`,
  `src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/runtime.py`

Smoke ledger:

| Check | `healthy_reference` | `fail_primary` |
| --- | --- | --- |
| `SIM_ARSPD_*` boot baseline | matched source defaults | matched source defaults |
| Vehicle airspeed params | `ARSPD_RATIO=2.0`, `ARSPD_TYPE=100`, `ARSPD_USE=1` | `ARSPD_RATIO=2.0`, `ARSPD_TYPE=100`, `ARSPD_USE=1` |
| Fixed wind echo | verified `x=-5,y=0,z=0`, `enable_wind=true` | verified `x=-5,y=0,z=0`, `enable_wind=true` |
| Trigger | seq 4, armed AUTO, front-half seen, `t_s=20.19` | seq 4, armed AUTO, front-half seen, `t_s=20.22` |
| Seq 3 to seq 4 | `5.05 s` | `4.78 s` |
| Injection readback | all source-default `SIM_ARSPD_*` values read back, no mismatches | `SIM_ARSPD_FAIL=1.0` plus remaining source defaults read back, no mismatches |
| Reset | reset to boot baseline, no mismatches | reset to boot baseline, no mismatches |
| Mission discriminator | max seq 9, AUTO to RTL at seq 8, planned RTL stabilized | max seq 9, AUTO to RTL at seq 8, planned RTL stabilized |
| Wind sign sanity | East `ARSP-GPS=+4.40 m/s`, West `ARSP-GPS=-5.29 m/s` | faulted airspeed invalidates sign sanity, but wind echo remained verified |
| Airspeed behavior | post-injection ARSP mean `15.17 m/s` | post-injection ARSP mean `1.09 m/s`, GPS mean `13.13 m/s` |
| TECS fields | MAVLink throttle/pitch available; BIN TECS/CTUN not parsed | MAVLink throttle/pitch available; BIN TECS/CTUN not parsed |
| Behavior summary | `nominal_completion`, `valid_nominal_completion`, accepted | `degraded_completion`, `valid_degraded_completion`, accepted |

Required artifact presence:

- Both corrected attempts include `run_config.json`, `sim_arspd_boot_baseline.json`,
  `vehicle_airspeed_params.json`, `reference_wind.json`,
  `airspeed_injection.json`, `airspeed_behavior_summary.json`,
  `airspeed_signal_metrics.json`, `mission_progress.json`,
  `mode_timeline.json`, `altitude_speed_envelope.json`, and
  `tecs_response.json`.
- `healthy_reference` additionally includes `reference_baseline.json`.
- Raw logs remain under `var/runs/.../_sitl_state/...` and stack logs under
  `var/runs/.../scripts/airspeed_failure_stack/`.

Limitations:

- `SIM_ARSPD_OFS` no-op and `SIM_ARSPD_FAILP=500` effect size were not measured
  by the two-case smoke and must be covered by Phase 3 full-matrix calibration.
- TECS/CTUN BIN fields were not parsed; smoke classification used MAVLink
  throttle, pitch, airspeed, groundspeed, altitude, mode, mission, and
  STATUSTEXT telemetry.
- This is raw evidence only. Nothing was promoted into `evidence/`, and this is
  not a Phase 4A or Phase 4B feature-evidence claim by itself.

Decision: the two-case smoke proved the live harness but did not by itself
unlock Phase 3 because `SIM_ARSPD_OFS` no-op and `SIM_ARSPD_FAILP=500` effect
size were still missing. Phase 3 remained blocked until the measurement rerun
below.

## Phase 2 Measurement Rerun - 2026-06-06

Scope: raw measurement smoke covering the missing Phase 2 ledger items. No
curated evidence was promoted.

Accepted raw root:

```text
var/runs/airspeed_failure_behavior_20260606T164050810132Z/
```

Accepted attempt roots:

- `healthy_reference/runs/attempt_001/`
- `ofs_noop_probe/runs/attempt_001/`
- `pitot_500pa/runs/attempt_001/`
- `fail_primary/runs/attempt_002/`

Interrupted partial attempt:

- `fail_primary/runs/attempt_001/` was interrupted manually after launch and
  before a valid injection/mission-completion observation. Final failure
  artifacts were written, but it is not counted as an accepted observation and is
  superseded by `fail_primary/runs/attempt_002/`.

Measurement ledger:

| Check | Result |
| --- | --- |
| Reset baseline | Confirmed on every accepted attempt; `SIM_ARSPD_*` matched source defaults at boot and reset readback returned to boot baseline. |
| Vehicle ratio | Confirmed `ARSPD_RATIO=2.0`, `ARSPD_TYPE=100`, `ARSPD_USE=1`. |
| Wind sign/frame | Confirmed on healthy reference: echo `x=-5,y=0,z=0`, East `ARSP-GPS=+4.42 m/s`, West `ARSP-GPS=-5.29 m/s`, sign status `confirmed`. |
| `OFS` no-op probe | Confirmed. Injected/read back `SIM_ARSPD_OFS=2500.0`; post-injection ARSP mean `15.16 m/s`, comparable to healthy `15.15 m/s`; behavior `nominal_completion`. |
| `FAILP=500` effect size | Confirmed. Injected/read back `SIM_ARSPD_FAILP=500.0`; post-injection ARSP mean `344.02 m/s`, ARSP delta `+322.40 m/s`, altitude loss `23.96 m`; behavior `degraded_completion`. |
| Trigger timing/window | Confirmed seq 4 trigger while armed in AUTO after front-half progress. Healthy seq-4 trigger `t_s=20.76`; OFS `20.48`; FAILP `19.64`; fail-primary attempt 002 `20.85`. |
| `fail_primary` behavior | Confirmed on attempt 002. Injected/read back `SIM_ARSPD_FAIL=1.0`; post-injection ARSP mean `1.05 m/s`; altitude loss `6.24 m`; planned RTL reached. |
| RTL discriminator | Confirmed for all accepted attempts: max seq 9, AUTO->RTL at seq 8, stop reason `planned_rtl_stabilized`. |
| Healthy baseline bands | Confirmed and stored as `single_run_provisional` in `reference_baseline.json`: mean/std bands for East ARSP, ARSP-GPS, altitude, throttle, and time-to-RTL. |

Artifact improvements confirmed in this rerun:

- `reference_wind.json` backfills realized healthy East/West `ARSP-GPS` and
  marks sign confirmation `confirmed`.
- `airspeed_behavior_summary.json` reason strings include measured ARSP/GPS,
  altitude loss, AUTO->RTL sequence, and max mission sequence.
- `reference_baseline.json` stores provisional mean/std bands instead of only
  loose means.

Decision: Phase 2 measurement smoke accepted. Phase 3 full v1 matrix is
unblocked. Phase 4 remains blocked until curated evidence is promoted and
reviewed.

## Phase 2 Follow-up Fix Review - 2026-06-06

Scope: post-review fixes for the Phase 2 codebase and current documentation. No
SITL or Gazebo launch was performed in this review.

Fixes:

- Live ratio-bias attempts now recompute `SIM_ARSPD_RATIO` from the measured
  MAVLink `ARSPD_RATIO` readback after clean SITL boot and before
  stimulus/monitor injection. Dry-runs still show the configured planning recipe.
- Current docs, `.ai`, and asset indexes now point to the accepted measurement
  raw root `var/runs/airspeed_failure_behavior_20260606T164050810132Z/` instead
  of the superseded two-case smoke root.
- Operator docs now expose `--live-measurement-probes --confirm-live-phase2` as
  the accepted Phase 2 measurement-smoke command.
- The active mission inventory now includes
  `assets/missions/quad_star_showcase_mission.waypoints`.
- The interrupted `fail_primary/attempt_001` note now says final failure
  artifacts were written, but the attempt is rejected because it did not produce
  a valid injection/mission-completion observation.

Checks:

- `./env/bin/python3 -m unittest tests.unit.test_airspeed_failure_phase1`:
  PASS, 19 tests.
- `/home/ahmed/.local/bin/pyright src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py tests/unit/test_airspeed_failure_phase1.py`:
  PASS, 0 errors.
- `./env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py tests/unit/test_airspeed_failure_phase1.py`:
  PASS.
- `source setup.bash && ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --list-cases`:
  PASS.
- `source setup.bash && ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --dry-run --case ofs_noop_probe`:
  PASS; payload `SIM_ARSPD_OFS=2500.0`, no launch.
- `source setup.bash && ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --probe-schema`:
  PASS.
- `source setup.bash && ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --live-measurement-probes`:
  PASS as a negative guard; exits with the expected error requiring
  `--confirm-live-phase2`.
- `git diff --check`: PASS.
- `make doctor`: PASS.

## Phase 1 Strict Review - 2026-06-05

Scope: no-SITL Phase 1 foundation only. No SITL or Gazebo launch was performed.

Findings:

- High: documented `python -m sim_ard_gaw...run_airspeed_failure` commands were
  not reachable after `source setup.bash` because `setup.bash` did not export
  `src/` on `PYTHONPATH`. Fixed by exporting
  `src/` and `src/sim_ard_gaw/compat_scripts` from `setup.bash`.
- Low: pyright could not index a nested test artifact field because the
  reference-wind artifact helper returned `dict[str, object]`. Fixed by
  returning `dict[str, Any]`.

No remaining blocker, critical, or high findings were found in the Phase 1
surface after remediation.

Checks:

- `./env/bin/python3 -m unittest tests.unit.test_airspeed_failure_phase1`:
  PASS, 15 tests.
- `/home/ahmed/.local/bin/pyright src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py tests/unit/test_airspeed_failure_phase1.py`:
  PASS, 0 errors.
- `source setup.bash >/tmp/airspeed_phase1_setup.out && ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --list-cases`:
  PASS; listed `healthy_reference`, fixed fault cases, and v1 ratio cases.
- `source setup.bash >/tmp/airspeed_phase1_setup.out && ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --dry-run --case fail_primary`:
  PASS; plugin constructed, launch not performed, payload
  `SIM_ARSPD_FAIL=1.0`, reset source defaults retained.
- `source setup.bash >/tmp/airspeed_phase1_setup.out && ./env/bin/python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --probe-schema`:
  PASS; required `SIM_ARSPD_*` names and source defaults emitted.

Decision: Phase 1 accepted. Phase 2 live smoke may start only under the
authorization and clean-run gates in `plan.md`, `implementation.md`, this
review, `.ai/entrypoint.md`, and ADR-0004.

## Tailwind Counterpart Phase 2 Review - 2026-06-21

Scope: no-SITL implementation only. No SITL or Gazebo launch was performed,
and no tailwind evidence or acceptance status was promoted.

Implemented review points:

- Named headwind and tailwind wind profiles with direction-neutral expected
  airspeed-minus-groundspeed arithmetic.
- Four distinct tailwind case IDs covering healthy, +100 ramp, +200 ramp, and
  +130 pulse schedules without changing historical headwind defaults.
- Two 36 km Eastbound mission assets preserving paired DO15 and
  `AIRSPEED_CRUISE` speed-source semantics.
- A governed 17-attempt recipe that records source roots, duplicate aliases,
  and the approved exclusion of the incomplete 2026-06-09 P100 root.
- Time-aligned source-arithmetic mechanism classification with separate clamp,
  unclamped tracking, rejection-before-verification, and unverified outcomes.
- A separate `--confirm-live-tailwind-phase3` guard for every live tailwind
  attempt.

Checks:

- Airspeed tailwind, mechanism-gate, and historical Phase 1 unit suites:
  PASS, 49 tests.
- Targeted pyright over the plugin, CLIs, and test modules: PASS, 0 errors.
- Targeted `compileall`: PASS.
- Tailwind `--list-cases` and representative `--dry-run`: PASS; no launch.
- `git diff --check`: PASS.
- `make doctor`: PASS.

Decision: Phase 2 no-SITL implementation is complete. Phase 3 remains blocked
pending explicit operator approval for the healthy-tailwind validation run.

## Tailwind Healthy Gate Attempt 1 Review - 2026-06-22

Raw runtime root:
`var/runs/tailwind_phase3_healthy_speed15_gate_20260622/`.

The authorized healthy-tailwind attempt produced a nominal flight observation:
the Gazebo wind publication and echo were `x=+5 m/s`, realized Eastbound
`ARSP-GPS` was `-5.525 m/s` against a `-5.0 ± 1.25 m/s` requirement, mean
airspeed was `15.002 m/s`, mean groundspeed was `20.527 m/s`, altitude loss was
`0.154 m`, all 1,573 BIN `ARSP.U` samples remained enabled, and the BIN contained
no `ERR` or `EV` messages. The gate stopped with approximately 34.8 km remaining
on the long leg. No simulator processes remained after cleanup.

Review nevertheless blocked the matrix because the generated
`reference_wind.json` reported `out_of_band`. Root cause: the historical
two-direction healthy classifier required both Eastbound and Westbound samples,
while the new 36 km mission is intentionally one-way. Acceptance also consumed
publication/echo verification before the realized-sign result was backfilled.

The correction:

- requires only Eastbound sign confirmation for the one-way tailwind gate while
  preserving both-direction requirements for the historical mission;
- makes final healthy acceptance consume publication/echo plus the completed
  required-direction sign result;
- reports planned RTL only after an actual qualifying AUTO-to-RTL transition;
- records configured mechanism tier and expected `AHRS_WIND_MAX` in healthy
  case/run provenance.

The original raw attempt and its original artifact are intentionally preserved.
Offline replay of its values through the corrected classifier returns
`confirmed`, overall wind verification `true`, and planned RTL `false`; this is
a code-path check, not replacement live evidence. A post-fix healthy-tailwind
attempt is required before the 17-attempt matrix begins.

## Tailwind Healthy Gate Attempt 2 Strict Review - 2026-06-22

Attempt 2 under the same raw root exercised the mission-aware sign correction
successfully. Publication/echo and overall wind verification were true,
Eastbound `ARSP-GPS` was `-5.525 m/s`, mean airspeed was `15.001 m/s`, mean
groundspeed was `20.526 m/s`, altitude loss was `0.198 m`, planned RTL was
false, all 1,586 BIN `ARSP.U` samples remained enabled, and the BIN contained no
`ERR` or `EV` messages. Required artifacts, parameter/reset readbacks, isolated
SITL state, remaining mission distance, and cleanup passed review.

Strict provenance review still blocked the matrix because:

- generic staged manifests derived the start timestamp at terminalization, so
  start and finish were identical;
- the manifest retained the stimulus adapter's pre-monitor
  `phase1_no_sitl`/`live_readback_performed=false` marker despite successful
  live injection/reset readbacks;
- run provenance named untracked inputs and the mission but did not hash their
  content.

All three behaviors predated the tailwind lane and are visible in historical
headwind roots. The correction captures attempt start before environment
launch, terminal end after verdict, and wall duration; replaces pending live
stimulus verification with terminal injection/reset truth; and records
SHA-256/size provenance for the selected mission and every untracked workspace
file. Historical raw manifests, including attempts 1 and 2, remain unchanged.
A final post-fix healthy-tailwind attempt is required before the matrix gate can
be accepted.

Post-fix checks:

- Core lifecycle/manifest, campaign provenance, and airspeed unit suites:
  PASS, 117 tests.
- Targeted pyright: PASS, 0 errors.
- Targeted `compileall`: PASS.
- No-SITL provenance-shape inspection: PASS; mission and all five current
  untracked inputs carry SHA-256 and size.
- Representative cruise-follow tailwind dry-run: PASS; no launch.
- `git diff --check`: PASS.
- `make doctor`: PASS.

## Tailwind Healthy Gate Attempt 3 - 2026-06-22

Attempt 3 under
`var/runs/tailwind_phase3_healthy_speed15_gate_20260622/` exercised the final
provenance/lifecycle correction and completed as `success` with
`valid_nominal_completion`. Its manifest records start
`2026-06-22T11:24:51Z`, finish `2026-06-22T11:28:06Z`, mean airspeed
15.00 m/s, mean groundspeed 20.53 m/s, altitude loss 0.14 m, and max mission
sequence 4. The healthy gate is therefore satisfied for the bounded tailwind
matrix work.

## Tailwind P130 Pulse Reanalysis - 2026-06-23

Two live attempts under
`var/runs/tailwind_standard_speed15_pulse_p130_n1/` completed all 26 scheduled
events, but their original manifests were false-negative
`sensor_rejected_before_verification` results. Strict review found that the
evaluator aligned wall-clock schedule UTC directly to the drifting SITL BIN
clock, treated `ARSP.U=1` as proof of the active AHRS source, and evaluated only
the final pulse.

The corrected evaluator now:

- anchors windows to logged `SIM_ARSPD_RATIO` `PARM` transitions;
- requires `CTUN.AsT=1` for sensor-derived clamp/tracking rows;
- evaluates all 13 fault windows and reports separate AHRS source-rejection
  and `ARSP.U` parameter-disable thresholds.

Additive offline reanalysis preserves the raw attempts and historical
manifests. Both attempts are now interpretable `clamp_verified` observations:
mean clamp error is 0.462 m/s and 0.390 m/s against the 2.0 m/s tolerance; AHRS
first switches away from the sensor at +50%, while the parameter-disable path
first activates at +60%. No rerun is required for these two attempts.

Evidence:
`evidence/reports/features/2026-06-23_tailwind_pulse_evaluator_correction.md`;
curated summary:
`evidence/curated_logs/airspeed_failure_tailwind_pulse_reanalysis_2026-06-23/`.

Post-correction checks: 28 mechanism/tailwind tests and 90 broader regression
tests passed; targeted pyright reported 0 errors; compileall, diff check, and
`make doctor` passed.

## Rollback / Retirement Rule

If airspeed becomes unsuitable before Phase 2, record the reason here and
supersede this runbook with a new feature runbook for the selected candidate.
Do not rewrite this runbook into a different sensor lane without preserving the
decision history.
