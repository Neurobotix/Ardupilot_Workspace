# Current Work

Status: Phase 7 cutover is PASS as of 2026-05-24. `workspace_next` is the
production workspace for the governed ArduPilot + Gazebo simulation workflows
covered by `governance/decisions/ADR-0005-workspace-next-cutover.md`. The old
workspace `/home/ahmed/ardupilot_workspace` is deprecated fallback/reference
and must not be edited without explicit operator authorization.

`ADR-0004` remains the clean-run and workspace-plugin policy: broad pre-run
cleanup is required for governed runs, and Gazebo runtime must use only the
workspace-built plugin. Launch and wind-matrix entrypoints fail closed when
that plugin build is missing. Phase 6 evidence and operations, Phase 5
campaign/test migration, Phase 4 config and asset normalization, Phase 3
documentation rebuild, and Phase 2 runtime parity remain PASS.
Phase 8 retired the old root compatibility symlink bridge from live runtime
path resolution and moved launch, bridge, analysis, wind-matrix runner, and
campaign test-suite implementation ownership into organized
`src/sim_ard_gaw/` homes. `compat_scripts/` remains wrapper-only for old imports
and script paths. Evidence:
`evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-24.md`.

A unified interactive CLI entry point (`sim-test`) was added on 2026-06-07 via
`src/sim_ard_gaw/campaigns/test_suite/cli/run.py` and
`src/sim_ard_gaw/campaigns/test_suite/cli/interactive.py`. It covers both
`wind_matrix` (single case / sequential suite / round-robin) and
`airspeed_failure` (sequential suite). No existing CLI modules were modified.
`questionary` is now a declared dependency in `requirements.txt`. Activate with
`env/bin/pip install -e .` then `sim-test`.

Active feature work: the airspeed failure behavior lane has a Phase 1 no-SITL
plugin foundation accepted after strict review on 2026-06-05: plugin package,
dry-run CLI, registry key, case generator, parameter schema validation,
artifact schemas, classifier helpers, manifest accepted-observation counting,
and no-SITL tests. The 2026-06-05 review fixed the sourced-workspace Python
module path for the documented CLI and found no remaining blocker, critical, or
high Phase 1 findings. Phase 2 live measurement smoke was accepted on
2026-06-06 from raw root
`var/runs/airspeed_failure_behavior_20260606T164050810132Z/`: the guarded run
verified fixed-wind echo, `SIM_ARSPD_*` boot defaults, vehicle
`ARSPD_RATIO/USE/TYPE`, seq-4 injection timing, injection/reset readback,
required artifacts, planned RTL discrimination, `OFS` no-op behavior,
`FAILP=500` effect size, and behavior summaries
(`healthy_reference=nominal_completion`, `ofs_noop_probe=nominal_completion`,
`pitot_500pa=degraded_completion`, `fail_primary=degraded_completion`).
On 2026-06-11 an operator-directed analysis was reviewed, curated, and reported
from 47 accepted observations (signed ratio-bias sweep +10..+100/−10..−50 on
2026-06-08/09, pulse ladder +10..+130 and stepped ramps +100/+200 on
2026-06-10): report
`evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`,
curated package `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/`.
On 2026-06-14 the same package was accepted for **bounded Phase 4A**
ratio/ramp/pulse characterization by
`evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`.
Headline: abrupt bias pulses ≥+60% trip `ARSPD_WIND_GATE=5` and disable the
sensor; the same biases reached by slow +10% steps stay accepted while the
aircraft settles into a degraded equilibrium; past ~+80..+100 the realized
state saturates around `AIRSPEED_MAX=22`/TECS limits. Phase 4B fixed-case
repetition/full-lane acceptance remains open; the generating plugin/doc changes
are still uncommitted working-tree state. See
`governance/runbooks/features/airspeed_failure_behavior/`.
The lane now also includes headwind stepped-ramp and pulse-ladder cases with
their own 100 m AGL long Eastbound missions and no RTL waypoint.
`ratio_bias_ramp_p10_to_p100_headwind` verifies baseline once, then applies
60 s windows from +10 through +100 reported-airspeed bias without resets; it is
accumulating drift evidence, not an independent dose-response sweep.
`ratio_bias_ramp_p10_to_p200_headwind` uses the same mission and schedule shape
but continues through +200 as a stronger failure-boundary probe after +100
showed a stable degraded equilibrium.
`ratio_bias_pulse_p10_to_p130_headwind` verifies baseline, alternates 60 s
baseline/fault windows from +10 through +130, resets params after the final
observation, and treats the result as threshold/transient evidence rather than
a replacement for the independent fixed-bias sweep.

Tailwind counterpart extension: Phase 0 inventory and Phase 1 design were
operator-approved on 2026-06-21. Phase 2 no-SITL implementation adds named
headwind/tailwind profiles, distinct tailwind ramp/pulse cases, two
direction-neutral 36 km Eastbound missions preserving DO15 versus
`AIRSPEED_CRUISE` semantics, an approved 17-attempt configuration recipe, and
a time-aligned source-arithmetic mechanism gate. Historical headwind defaults
remain unchanged. That 2026-06-21 Phase 2 state had no tailwind SITL run or
evidence/status claim; live tailwind commands require a separate Phase 3
confirmation flag.

The first authorized healthy-tailwind gate attempt ran on 2026-06-22 under
`var/runs/tailwind_phase3_healthy_speed15_gate_20260622/`. Its flight data were
nominal and the live geometry retained ample distance, but review found that
the historical two-direction wind-sign classifier incorrectly required an
absent Westbound sample from the one-way mission. The 2026-06-22 correction
makes required sign directions mission-aware, makes healthy acceptance consume
the completed sign result, separates schedule completion from actual planned
RTL, and records the configured mechanism tier/wind limit. The original raw
attempt is preserved. Attempt 2 exercised that correction successfully, but a
strict review found three inherited evidence defects also present in historical
headwind roots: terminal-time-only manifest timestamps, a stale no-SITL
stimulus-verification marker on live attempts, and missing mission/untracked-file
content hashes. The 2026-06-22 follow-up fixes all three for future attempts;
historical raw manifests remain unchanged. One final post-fix healthy gate is
required before starting the 17-attempt matrix. Attempt 3 then completed on
2026-06-22 with `success` / `valid_nominal_completion`, distinct start/end
timestamps, finalized live verification, and hashed mission/untracked-input
provenance; the healthy gate is satisfied for the bounded matrix work.

The protected DO15 tailwind P130 pulse case subsequently ran twice under
`var/runs/tailwind_standard_speed15_pulse_p130_n1/`. A 2026-06-23 strict review
found evaluator-only false negatives: wall UTC was incorrectly aligned to the
drifting BIN clock, `ARSP.U` was used instead of the actual `CTUN.AsT` source,
and only the final pulse was judged. The corrected evaluator uses BIN `PARM`
transitions, `CTUN.AsT=1`, and all 13 fault windows. Additive reanalysis marks
both preserved attempts `clamp_verified` (0.462/0.390 m/s mean clamp error),
with AHRS source rejection beginning at +50% and `ARSP.U` disable at +60%.
No rerun is required for these two attempts. Evidence:
`evidence/reports/features/2026-06-23_tailwind_pulse_evaluator_correction.md`.

Chunk 2 coverage reconciliation on 2026-06-23 froze Phase 0–9 expectations
before inspecting unreviewed Phase 1–8 tailwind telemetry, then inventoried the
raw run set without performing corrected behavior analysis. All 17 approved
Phase 1–9 fault-matrix attempts exist with matching configuration, required
artifacts, BINs, applied-event readbacks, and reset readbacks; Phase 9 has one
additional valid repetition. The final healthy gate attempt is usable, while
its two superseded predecessors retain known provenance defects. Sixteen
Phase 1–8 attempts are ready for Chunk 3 corrected offline analysis; no rerun
is currently justified. Frozen expectations and inventory:
`governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_0_9_expectations.md`
and `tailwind_phase_0_9_inventory.md` in the same feature bundle.

Chunk 3 corrected offline reanalysis of all 16 Phase 1–8 tailwind attempts
completed on 2026-06-23. The frozen expectations hash was verified unchanged
before and after; all 16 BIN hashes match the inventory; raw run trees are
unchanged; zero schedule-matching errors. A second evaluator defect was found
and fixed: `analyze_mechanism_bin` only applied the last-interpretable
representative window for `schedule_kind="pulse_ladder"`, so ramp attempts had a
verified pre-rejection clamp/tracking window erased by a later rejected window.
The fix applies last-interpretable selection to every schedule kind (pulse_ladder
behavior unchanged, so the Phase 9 additive reanalysis is unaffected and was not
touched), with regression test
`MechanismGateScheduleExtractionTests::test_ramp_verified_window_not_erased_by_later_rejection`.
After the fix, 12 of 15 historical Phase 1–8 mechanism verdicts were false
negatives; 15/16 attempts are now mechanism-interpretable (Phase 8 P100 stays a
genuine `clamp_not_exercised`). No genuine raw-data defect was found and no rerun
is justified. This is working analysis only; the locked Chunk 5 expectation
columns and curated evidence are untouched. Working package:
`var/analysis/tailwind_phase_1_8_corrected_reanalysis_20260623/`; factual record:
`governance/runbooks/features/airspeed_failure_behavior/tailwind_phase_1_8_corrected_reanalysis.md`.
Chunk 4 and Chunk 5 are not yet performed.

Follow-up review fixes on 2026-06-06 aligned current docs with the accepted
measurement-smoke root and made live ratio-bias attempts recompute
`SIM_ARSPD_RATIO` from the measured MAVLink `ARSPD_RATIO` readback before
injection. A 2026-06-07 blocker review removed the former sign-flip case from the v1
case set because default `ARSPD_TUBE_ORDR=2`/AUTO uses absolute pressure, so
that payload is not a sustained collapse fault on this stack.

GPS failure behavior lane (Lane 3): Phase 0 design is locked (2026-07-06; five
Proposed ADRs 0017–0021). The Phase 1 no-SITL foundation (Chunks 1–6: scaffold,
payload semantics, static mission/overlay, synthetic mechanism gate,
runtime/MAVLink contract, `--preflight` integration readiness) is implemented.
On 2026-07-13 a strict Phase 1 review's six confirmed BLOCKERs were resolved
no-SITL with regression tests: (2) executable live injection plans are now gated
by ADR-0020 trigger evidence validated through the canonical monitor helper,
with preview strictly non-executable; (3) the analyzer requires substantive
behavior-tier evidence, not a marker boolean; (4) manifest acceptance requires
verdict/analysis behavior agreement and fails closed on contradictions;
(5) `gps_injection.json` is in the artifact schema and reported by readiness;
(6) MAVLink batch writes are atomically prevalidated (zero writes on any invalid
entry). Also on 2026-07-13, before Phase 2, dedicated launch identities
`plane-gps` and `gazebo-plane-gps` were added (structural only) to replace the
earlier incorrect `plane-cte` / `gazebo-plane-cte` GPS references: `plane-gps`
loads `plane_base.parm -> plane_gps.parm` only (no airspeed overlay, local
override excluded unconditionally, wipes EEPROM). The original
`gazebo-plane-gps` base-world reuse was corrected on 2026-07-14 after a rejected
nominal run proved its spawn heading did not match the mission; the target now
uses the dedicated sensor-neutral `mini_talon_gps_runway.sdf` with the proven
east-facing pose. Covered by no-SITL structural tests
(`tests/unit/test_gps_launch_targets.py`) and recorded in ADR-0021's 2026-07-13
amendment; existing CTE/airspeed targets are unchanged. On 2026-07-13 a final
no-SITL review re-verified every prior finding in code and found no new
BLOCKER/HIGH/MEDIUM/substantiated-LOW issue, and the **Phase 1 no-SITL
foundation was accepted** (163 GPS tests + 41 airspeed regressions passed,
pyright 0 errors, `make doctor` pass, worktree clean). This is a no-SITL
acceptance of the plugin foundation only. Pre-smoke Phase 2 implementation code
now exists for later authorized smoke (source-contract helpers, live telemetry
normalization and proven Plane data-stream requests, explicit
connection/launch/mission adapters, production mission-adapter installation from
the live MAVLink master, source-contract-gated monitor acceptance, cleanup
wait/kill behavior, a guarded protected smoke-case live CLI, post-injection
monitor/artifact emission, and decoded-record BIN analysis helpers). At that
point Phase 2 live smoke remained unverified. A 2026-07-13 strict pre-smoke review rejected the
initial live path; the working tree now remediates every reported finding
no-live (ordered launch cleanup, cleanup-gated terminal persistence, fresh
one-shot trigger evidence, operation-gated acceptance, post-trigger behavior
and reset-segmented BIN analysis, strict atomic JSON/source validation, and
stop-on-non-success CLI handling). A fresh strict no-live review on 2026-07-14
found no remaining BLOCKER or HIGH finding and accepted the exact corrected diff
for the single nominal live smoke. The one authorized attempt ran on 2026-07-14
at HEAD `f21395c` and was **NOMINAL_SMOKE_REJECTED** before arming: ArduPlane was
still `INITIALISING` when mission upload returned `MAV_MISSION_NO_SPACE`; no
mission verification, AUTO/trigger, observation window, live source readback,
or BIN analysis occurred. The attempt cleanup also detected three surviving
MAVProxy children; canonical cleanup afterward succeeded and the final process
scan was clean. No retry or faulted case ran. Raw root:
`var/runs/gps_failure_behavior_phase2_nominal_20260714T073957200424999Z/`.
The working tree now implements no-live remediation for all three blockers:
AUTO/non-INITIALISING/GPS/EKF readiness before mission control, canonical
governed cleanup followed by an independent survivor scan, and cleanup-before-
terminal-error persistence that preserves both cleanup proof and the primary
failure. GPS terminal rows now explicitly persist framework status and monitor
result. A second nominal attempt at the same HEAD reached readiness, verified
the five-item mission, armed, and entered AUTO, then was
**NOMINAL_SMOKE_REJECTED** before trigger/source readback/90 s observation. The
GPS monitor had incorrectly replaced airspeed's proven stream setup with
per-message interval commands and mandatory ACKs; the event-driven
`STATUSTEXT` request was denied. Canonical cleanup also missed `mavproxy.py`
because it matched only `mavproxy`; the corrected terminal row did persist the
cleanup failure and monitor result. Raw root:
`var/runs/gps_failure_behavior_phase2_nominal_20260714T080120722888267Z/`.
The working tree now provides GPS-owned stream, readiness, mission-protocol,
and workspace-owned cleanup helpers, gates on required messages actually
observed, and explicitly matches `[m]avproxy.py` in canonical cleanup. A
structural test forbids GPS imports from sibling plugins. Focused no-live tests
cover both real failure shapes. A later operator-started, unaccepted diagnostic
emitted mission-current progress `0 -> 1 -> 3 -> 4`: ArduPlane did not publish
seq 2 because it is a `DO_CHANGE_SPEED` command. ADR-0020 and the trigger now
require fresh armed/AUTO navigation seqs 1 and 3, permit optional seq 2, and
still latch only the first seq-4 edge. Phase 2 remains open
pending fresh strict no-live review and separate operator authorization. See
`governance/runbooks/features/gps_failure_behavior/`.

A governed nominal attempt at
`var/runs/gps_failure_behavior_phase2_nominal_20260714T083812969855707Z/`
then proved GPS-owned readiness, mission upload/identity, arming/AUTO,
telemetry, and cleanup live. It was deliberately interrupted after diagnosis,
not accepted: leading home-row `MISSION_CURRENT seq=0` had entered the trigger
trace and permanently invalidated later `1 -> 3 -> 4` progress. The terminal
row is `interrupted`; `gps_cleanup.json` is `ok=true`, canonical cleanup exited
0, and the final process scan is empty. The monitor now ignores only leading
seq 0 before evidence begins and still rejects seq-0 regression after seq 1.

A later nominal run at
`var/runs/gps_failure_behavior_live_nominal_codex_20260714T095246Z/` declared
`success` / `valid_nominal`, but strict review on 2026-07-14 rejected it as
evidence. The staged analyzer decoded a still-growing BIN before cleanup,
anchored on a mission-upload CMD row, and double-scaled pymavlink-decoded XKF4
and SIM/POS fields. The case/monitor duration contracts disagreed, terminal
injection registration/state was incomplete, and run/input/source provenance
was absent. No-live remediation now places staged analysis/verdict after
framework cleanup, records the live seq-4 boot timestamp, excludes CMD upload
rows from anchoring, consumes decoded engineering units correctly, makes
per-case metadata authoritative for duration, synchronizes terminal artifacts,
and provides shared campaign-level provenance without any GPS-to-airspeed
import. Phase 2 remains open and requires a fresh governed run.

The subsequent nominal root
`var/runs/gps_failure_behavior_20260714T113259746238Z/` is also rejected. It
spawned approximately north against the eastbound mission, stopped at seq 4
plus the 20 s minimum observation window, anchored BIN analysis to the last of
many repeated seq-4 reports instead of the immutable first injection event, and
declared `valid_nominal` without mission completion. The working tree now owns
an east-facing calm GPS world, treats 20/90 s as minimum evidence only, tracks
real reached-waypoint and AUTO-to-RTL progress, waits 10 s after planned RTL,
uses the authorized first edge as the analysis anchor, and requires terminal
mission evidence for nominal summary/manifest acceptance. Focused no-live tests
cover these regressions.

The fresh protected nominal root
`var/runs/gps_failure_behavior_20260714T120212630044Z/` then completed reviewed
raw validation on 2026-07-14: approximately 89.27-degree initial yaw, immutable
seq-4 boot anchor at 56.487 s, max mission seq 9, reached rows 2–8, planned RTL
at seq 8 plus 10 s stabilization, accepted source/BIN/behavior analysis, and
clean cleanup. A preceding readiness-only timeout led to five-second idempotent
stream refresh and detailed readiness-state diagnostics. This is raw output
only; no fault run, evidence promotion, empirical-knee result, or Phase-2
acceptance is claimed.

Read-only path review of that nominal then found the visible pre-trigger loop:
takeoff completed at 98.22 m AGL around 323 m East, so the copied 300 m seq-3
settle waypoint was behind the calm-lane aircraft. Mission v3 moves seq 3/7 to
500 m East and seq 4/5/6 to 1300 m East, preserving both 800 m legs, sequence
numbers, and trigger/RTL contracts. Its validation hash is `3d111b32351a...`; the
successful raw nominal remains tied to historical v2 hash `c372bf6253c9...`.
The fresh v3 nominal root
`var/runs/gps_failure_behavior_20260714T122459635208Z/` completed the full
mission through seq 9 and planned RTL with the active hash. From takeoff
completion to seq 3, East displacement was monotonic, waypoint distance fell
from about 180 m to less than 1 m, and maximum absolute roll was 2.1 degrees;
the pre-injection loop is removed. This remains raw validation only. No fault
case or curated-evidence claim has been made.

The active mission is now v6, the shorter final-science candidate authorized on
2026-07-16: 1000 m controlled baseline, seq-4 injection onto a 6000 m straight
fault-observation leg, 1000 m straight recovery/continuation, 30 s terminal
loiter, seq-8 terminal gate, and seq-9 RTL. Active hash:
`ba22c669c895f694e8556e0e9573e9f9dd278d159086e46706eb30a3714d7261`.
Targeted no-live structural tests cover the baseline/fault/recovery/terminal
geometry and the default mission timeout is now 1800 s. V6 has not yet been
flown; final science campaign claims remain blocked pending dated live
validation and curated evidence.

On 2026-07-15, no-live campaign-readiness work added a guarded protected
round-robin command for `nominal`, `slow_drift_0p5_mps`, and
`hard_denial_15s`. It writes `campaign_contract.json`, uses zero automatic
retries, and stops on workflow/cleanup/raw-log failure. GPS manifest logic now
separates workflow-complete counting from strict accepted-observation counting,
and the source contract validates pre-injection EKF/GPS aiding flags while
recording post-fault flags as behavior context. Phase H later superseded the
next live step with a one-run-per-case validation rerun. Focused no-live tests
passed; no new live campaign result is claimed.

On 2026-07-16, no-live Phase B stimulus-fidelity work added required
`stimulus_fidelity.json` plus terminal `stimulus_fidelity_status` fields. The
post-cleanup BIN pass now checks nominal no-fault preservation, slow-drift
realized GLTCH slope against the requested vehicle-time rate, and hard-denial
disable/degrade/restore/recover timing separately from behavior classification.
Missing, malformed, non-finite, absent, or unanchored BIN evidence fails
stimulus fidelity closed. Focused synthetic decoded-record tests cover the
0.61 m/s bad-dose regression for the 0.5 m/s case. No live result or historical
campaign final-science claim is made.

On 2026-07-16, no-live Phase C manifest work separated GPS terminal verdicts
into `workflow_status`, `stimulus_fidelity_status`, and `behavior_status`, with
distinct `accepted_observation` and `accepted_repetition` fields. GPS scheduler
acceptance now counts accepted repetitions; the protected round-robin campaign
continues to count workflow-complete physical attempts by name. Bad-dose runs
can remain behavior observations only when workflow and behavior evidence are
complete, but they do not count as requested-recipe repetitions. No live result
or historical campaign final-science claim is made.

On 2026-07-16, no-live Phase D lifecycle-window work added required
`gps_lifecycle_windows.json` for live/post-cleanup analyzed attempts. The
artifact is the ordered evidence authority for pre-trigger baseline, trigger,
injection, fault-active, EKF response, recovery/continuation, and terminal
state, with per-window timing, source, status, metrics, and evidence refs.
Missing lifecycle evidence now fails closed instead of being hidden behind a
broad behavior summary. No live result or historical campaign final-science
claim is made.

On 2026-07-16, no-live Phase E hard-denial transient visibility work added a
top-level `hard_denial_transient` section to `gps_lifecycle_windows.json` and
the final `gps_behavior_summary.json`. Hard-denial artifacts now expose denial
start/end, restore, GPS status/satellites before/during/after, reset
times/offsets, full post-trigger max truth-vs-belief gap, active-segment gap
summary, and explicit sample-scope labels. Reset-segmented active samples
remain the classifier input; missing reset details fail the transient section
closed. No live result or historical campaign final-science claim is made.

On 2026-07-16, no-live Phase F source-contract reframing made proof levels
explicit: `exact_internal_proof`, `bin_observable_proof`, and
`validated_proxy_proof`. `PV_AidingMode == AID_ABSOLUTE` remains internal and
not directly logged, so exact internal proof stays false; EK3 readbacks are
configuration proof, decoded XKF4/GPS fields are BIN-observable context, and
the live pre-injection source gate is validated proxy proof. No live result or
historical campaign final-science claim is made.

On 2026-07-16, no-live Phase G altitude/attitude envelope authority work made
`attitude_altitude_envelope.json` explicitly label `source`, altitude source,
attitude source, sampling limits, and evidence quality. Live telemetry remains
the pre-cleanup runtime guard; post-cleanup analysis prefers BIN-derived
`POS.RelHomeAlt` or `CTUN.Alt` achieved altitude plus `ATT` attitude for final
evidence, and fails closed on absolute `POS.Alt`, desired `CTUN.DAlt`, missing
final sources, or BIN/live mismatches. The envelope can block reviewability but
is not the primary GPS behavior classifier. No live result or historical
campaign final-science claim is made.

On 2026-07-16, no-live Phase H validation-rerun readiness work added an
explicit Phase A-G gate report to `--preflight` and a plan-only
`--phase2-validation-rerun-plan`. The next live validation path is exactly
`nominal`, `slow_drift_0p5_mps`, and `hard_denial_15s`, one run each, zero
automatic retries, and strict stop on workflow, stimulus fidelity,
lifecycle-window, raw-log archival, or cleanup failure. The guarded live action
requires both `--confirm-live-phase2` and `--confirm-validation-rerun`. This is
framework validation only and does not authorize the full science campaign.

On 2026-07-22, a no-live GPS lane cleanup removed transitional Phase-1/smoke
surfaces that contradicted the current state: the superseded
`--phase2-smoke-plan` and `--live-phase2-smoke` CLI actions (superseded by
`--preflight` and the Phase H validation rerun; `--live-case` and the guarded
campaign/rerun actions remain), the stale readiness `LIVE_BLOCKERS`
list/`live_blockers` field (readiness is now exactly the Phase A-G gate
result), the unused `stop_on_first_non_accepted_record` flag, a dead
sequence-only trigger helper, the unused `build_live_plan_preview` wrapper,
and the dead `mechanism_fields_present` legacy alias plus the
`legacy_behavior_classifier_still_emitted` marker in analysis axes. Stale
"phase1"/"smoke" naming was updated (`static_param_stack`,
`nominal_observation_s`, `no_live_preflight`, `no_sitl_dry_run`) and the GPS
lane doc/runbook were corrected to the current v6/Phase-H state. No scientific
behavior changed; all GPS suites and pyright pass.

Additional active feature work: the `test_suite` migration completed its Phase 3 sequence
(3A–3G) on 2026-06-01. The staged `wind_matrix` plugin is fully zero-legacy
(environment, MAVLink control/monitor, and wind injection all plugin-owned) and
was live-proven against the retained legacy tool run directly; the Phase 3G gate
is accepted and Phase 4 (one second non-wind plugin, zero framework-core edits)
is unblocked. Phase 5 (legacy script retirement) still requires Phase 4. See
`governance/runbooks/features/test_suite_migration/` and
`evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md`.

Active plan:

- `governance/runbooks/migration/full_migration_plan.md`
- `governance/standards/change_control.md`
- `docs/operations/migration_status.md`

Next required work:

1. Smoke-test the non-core launch targets (`plane-airspeed-lidar`,
   `plane-altitude-wind`, `plane-rebuild`, `plane-staircase`).
2. Capture a `copter-lidar` LiDAR obstacle return (handshake already proven).
3. Capture full wind-matrix evidence if that broader claim is needed.
4. Remove thin compatibility wrappers only if old import/script paths are no
   longer needed.

Phase 7 facts:

- Cutover report:
  `evidence/reports/migration/CUTOVER_2026-05-24.md`
- Final shadow parity record:
  `evidence/reports/migration/shadow_parity_2026-05-24.md`
- Cutover ADR:
  `governance/decisions/ADR-0005-workspace-next-cutover.md`
- Post-policy reproof review:
  `evidence/reports/migration/PHASE_7_REPROOF_2026-05-24.md`.
- Rollback guidance now lives at
  `governance/runbooks/operations/workspace_cutover_rollback.md`.
- Runtime policy decision:
  `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`.
- Superseded blocked records:
  `evidence/reports/migration/CUTOVER_2026-05-21.md` and
  `evidence/reports/migration/shadow_parity_2026-05-21.md`.
- The old workspace was not modified during cutover.

Phase 8 facts:

- Launch and wind-matrix path constants now resolve directly through owned
  `assets/`, `config/`, `var/`, and `src/sim_ard_gaw/` homes.
- Retained manual, sequential, and suite wind-matrix SITL paths now use
  explicit `var/` state for BIN discovery instead of falling back to
  `src/ardupilot/logs`.
- The root legacy symlink bridge is removed after the direct-path refactor and
  targeted checks.
- `src/sim_ard_gaw/compat_scripts/` is now wrapper-only; implementation
  ownership lives under `launch/`, `bridges/`, `analysis/`,
  `campaigns/wind_matrix/`, and `campaigns/test_suite/`.

Phase 6 facts:

- `docs/operations/evidence_workflow.md` defines the operator path from raw
  runtime output under `var/` to selected proof under `evidence/`.
- `evidence/indexes/evidence_catalog.md` is the cross-phase proof catalog; the
  Phase 4 asset and parameter/config indexes remain specialized indexes.
- Reusable launch/runtime, vehicle, campaign, and promotion templates live
  under `evidence/templates/`, not `evidence/reports/`.
- `make doctor` now runs both the structure validator and
  `scripts/maintenance/validate_evidence.sh`; the Phase 6 check covers raw log
  leakage, raw run-directory leakage, raw-looking signatures inside evidence
  homes, report-home shape, evidence homes, template inventory, catalog sanity,
  and retained curated-root catalog coverage.
- The Phase 6 example reuses the real Phase 2 logger promotion: raw logger
  output stays under `var/logs/flight_logger/`, while the curated logger
  summary under `evidence/curated_logs/` and Phase 2 report remain the promoted
  proof.

Phase 5 facts:

- Compatibility runners and Phase-1 `test_suite` wrappers are retained.
- Owned campaign hardening helpers now cover manifest locking, additive
  terminal-status taxonomy, mission-contract validation, XML/SDF world-wind
  handling, and parameter-file hash provenance.
- `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md` records the pre-edit
  assessment, unit/integration/parity validation, tiny campaign PASS, the
  invalidated first `4,4` comparison, and the corrected workspace-plugin
  recheck.
- Curated tiny result artifacts live under
  `evidence/curated_logs/phase5_tiny_rr_20260521/`; raw simulator output stays
  under `var/`.
- `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/` is
  retained as diagnostic proof of the Phase 5 audit-gap remediation path, not
  ArduPilot-side wind parity proof. The raw corrected comparison attempt is
  `var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/wind_x_04_y_04/runs/attempt_002/`.
- The detailed Gazebo plugin fallback incident record is
  `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`.

Phase 4 facts:

- Canonical asset and parameter indexes now live under `evidence/indexes/`.
- Shared config categories are explicit: vehicle bases and standalone stacks
  under `config/vehicles/`, feature overlays under `config/overlays/`,
  campaign lane files under `config/campaigns/`, archives under
  `config/archive/`.
- Plane launch compatibility still appends
  `.private/config/plane_params.local.parm` for most plane lanes when present.
  That local override is not shared canonical config; the shared assets and
  config paths now resolve directly through owned workspace homes.
- Recovered production-era parameter stacks are indexed as historical evidence
  under `evidence/curated_logs/recovered_param_stacks/`.
- `plane_base.parm` remains sensor-neutral for enablement: it keeps generic
  `AIRSPEED_*` defaults while the airspeed overlay or campaign lane files enable
  the Gazebo sensor path and add lane-specific/high-wind overrides.

Phase 3 facts:

- Canonical docs rebuilt: `docs/onboarding/installation.md`,
  `docs/operations/troubleshooting.md`,
  `docs/architecture/simulation_lanes.md`, and the evidence-aware campaign
  boundary in `docs/campaigns/wind_matrix.md`.
- Every archived doc under `docs/archive/src_docs/` has a recorded disposition
  (`PROMOTED`, `REWRITTEN`, `ARCHIVED_ONLY`, or
  `DROPPED_FROM_CANONICAL_USE`) in
  `governance/audits/2026-05-20_phase3_docs_errata.md`.
- Archived docs that are intentionally contradicted carry an ARCHIVED errata
  banner pointing to the canonical replacement.
- Known bad refs (legacy flight-log dir, retired LiDAR runway world, retired
  altitude-wind log checker, obsolete base-plane airspeed param) are absent
  from or qualified in canonical docs.
- Completion pass reconciled the Copter LiDAR lane map with the Phase 2
  2026-05-21 handshake evidence without claiming an obstacle return.
- Audit remediation removed duplicate install guidance from runtime notes,
  narrowed install evidence wording, and closed the Phase 3 runbook checklist.

Latest evidence:

- Phase 6 evidence and operations:
  `evidence/reports/migration/PHASE_6_EVIDENCE_OPS_2026-05-21.md`
- Phase 4 config and asset normalization:
  `evidence/reports/migration/PHASE_4_CONFIG_ASSETS_2026-05-21.md`
- Phase 3 documentation rebuild:
  `evidence/reports/migration/PHASE_3_DOCS_2026-05-20.md`
- Phase 2 runtime parity:
  `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`
- Phase 2 per-target curated runtime evidence:
  `evidence/curated_logs/phase_2_runtime_2026-05-20/`
- Phase 1 structure hardening:
  `evidence/reports/migration/PHASE_1_STRUCTURE_2026-05-20.md`
- Phase 0 baseline: `evidence/reports/migration/PHASE_0_BASELINE_2026-05-20.md`

Phase 2 facts:

- Production and new launch target names match exactly, with one intentional
  difference: `wind-check-altitude` is retired in `workspace_next`.
- `make doctor`, `make test-parity`, and structure validation pass. `make
  doctor` requires `ripgrep`; it was installed during this phase.
- `plane`, `plane-cte`, `plane-lidar`, and `copter` each proved a full
  SITL/Gazebo/MAVLink handshake (GPS fix, EKF3, arming, Gazebo physics
  coupling). `plane-cte`, `plane-lidar`, and `copter` flew (46.9 m, 52.5 m,
  10.0 m).
- `bridge-plane` proved an end-to-end LiDAR path: Gazebo `/lidar` -> bridge ->
  MAVLink -> ArduPilot, with `AGL` readings tracking the plane's climb.
- Two runtime defects were found and fixed in
  `src/sim_ard_gaw/compat_scripts/launch.sh`: copter launchers now load
  `config/vehicles/copter_params.parm` with `--wipe-eeprom` (frame class/type),
  and bridge launchers run `python3 -u` so bridge status is observable.
- `scripts/ops/capture_round.sh` decodes raw tlogs into working output under
  `var/` by default; reviewed selected summaries require explicit
  `--promote-reviewed --evidence-id <new-id>` promotion into a versioned
  curated artifact. Historical Phase 2 evidence that predated root commits is
  now represented by tracked curated reports and indexes.
- All required runtime smoke targets ran with direct evidence, including
  `copter-lidar`, `bridge-copter`, and `logger` (run 2026-05-21). `copter-lidar`
  proved the handshake but not a LiDAR obstacle return.
- The old workspace was read for production comparison only during Phase 2 and
  was not modified. It became deprecated fallback/reference after ADR-0005.

Phase 1 facts:

- `make doctor` calls `scripts/maintenance/validate_structure.sh`.
- Required top-level homes, symlinks, raw log leakage, nested private state,
  `.private/` policy, gitignore coverage, stale canonical references, and
  required migration-plan links are validated.
- Phase 1 is not a runtime parity claim.

Known Phase 0 baseline facts:

- Phase 0 production reference was `/home/ahmed/ardupilot_workspace`; after
  ADR-0005 it is deprecated fallback/reference.
- Production root commit: `a483a534fac1755ea9ba9a007f062981913366d6`.
- At Phase 0, `workspace_next` had no root `HEAD` commit yet. Later tracked
  migration commits supersede that bootstrap state.
- Raw logs were not copied into `workspace_next`.
- `workspace_next` basic structural checks passed during Phase 0.

Do not edit the old workspace without explicit operator authorization.
