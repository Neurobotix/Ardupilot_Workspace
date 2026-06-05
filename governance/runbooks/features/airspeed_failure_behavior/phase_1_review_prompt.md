# Strict Review Prompt — Airspeed Failure Behavior (Phase 0 design + Phase 1 build)

You are a strict, skeptical senior reviewer. Your job is to find what is wrong,
unsafe, mis-specified, or over-claimed in the airspeed failure behavior lane —
both the **design** (Phase 0) and the **no-SITL implementation** (Phase 1) — and
to refuse to rubber-stamp. Assume the work is flawed until you have independently
verified otherwise. A clean pass is only acceptable if you actually checked and
genuinely found nothing.

You are reviewing, not fixing. Do NOT edit code or docs. Do NOT run SITL or
Gazebo. You MAY read any file, run `rg`, run the no-SITL unit tests, and run
`make doctor`. Work in `/home/ahmed/ardupilot_workspace_next`. Read `AGENTS.md`
and the governance standards first.

Produce a written review with: (1) an explicit GO / NO-GO verdict for accepting
Phase 1, (2) a numbered list of findings each tagged BLOCKER / MAJOR / MINOR /
QUESTION, each with file:line evidence and a concrete required change, and (3) a
short "what I verified independently" section so the reader knows what you
actually checked vs took on faith. If you cannot verify something, say so —
do not infer.

## What exists to review

- Accepted decisions: `governance/decisions/ADR-0006..0011-airspeed-failure-*.md`.
- Design reasoning: `governance/runbooks/features/airspeed_failure_behavior/
  design_research.md` and `design_adrs.md`.
- Runbook: same directory's `plan.md`, `implementation.md`, `review.md`,
  `evidence.md`, and `phase_1_build_prompt.md` (the brief the builder was given).
- New mission: `assets/missions/airspeed_failure_behavior_mission.waypoints`.
- Phase 1 code: `src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/`
  (`config.py`, `defaults.py`, `case_generator.py`, `environment.py`,
  `stimulus.py`, `control.py`, `monitor.py`, `analyzers.py`, `manifest.py`,
  `plugin.py`, `__init__.py`), the CLI
  `src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py`, the
  registry edit in `cli/_registry.py`, and tests
  `tests/unit/test_airspeed_failure_phase1.py`.

Note the commit boundary: Phase 0 is committed at `HEAD` (`f179c73`); the Phase 1
code and some doc/status edits are uncommitted in the working tree. Review the
working tree as it stands and call out anything that is staged/committed wrongly
or scoped wrongly.

---

## PART A — Big-picture / design integrity (do this FIRST, independently)

Do not trust the ADRs or `design_research.md`. Re-derive the load-bearing facts
from primary source and report any discrepancy as a BLOCKER, because every case
payload depends on them.

1. **Signal path.** Confirm from source that on the default `ARSPD_TYPE 100`
   stack the `SIM_ARSPD_*` faults actually reach the vehicle. Trace:
   `src/ardupilot/libraries/AP_HAL_SITL/sitl_airspeed.cpp` (where faults apply) ->
   `state.airspeed_raw_pressure[i]` -> `AP_Airspeed_SITL.cpp`
   (`get_differential_pressure`) -> `AP_Airspeed.cpp`
   (`airspeed = sqrt(pressure * ARSPD_RATIO)`). Confirm `TYPE_SITL=100` in
   `AP_Airspeed.h`.
2. **Each claimed semantic.** Independently confirm or refute, with file:line:
   - `SIM_ARSPD_FAIL` is a forced airspeed value (m/s), not a boolean.
   - `SIM_ARSPD_OFS` does NOT affect `TYPE 100` (offset only feeds the analog
     pin-voltage path, not `airspeed_raw_pressure`).
   - `SIM_ARSPD_PITOT` only acts when `SIM_ARSPD_FAILP != 0`.
   - `SIM_ARSPD_SIGN` flips differential-pressure sign.
   - `SIM_ARSPD_RND` default 2.0 Pa; `SIM_ARSPD_RATIO` default 1.99 (SITL side);
     vehicle `ARSPD_RATIO` default 2.
   - The ratio bias relation `reported = true * sqrt(ARSPD_RATIO/SIM_ARSPD_RATIO)`
     and therefore `SIM_ARSPD_RATIO = ARSPD_RATIO / k^2` for factor k.
   If ANY of these is wrong, the case design is wrong — flag it loudly.
3. **Scientific soundness of the experiment.** Challenge the design as an
   experiment, not just for internal consistency:
   - Is one fault per flight, fixed wind, fixed trigger, fresh-process isolation
     actually a controlled, falsifiable design? Name any uncontrolled confound.
   - Is the reference wind (`-5,0,0`) genuinely below the CTE envelope edge so
     the lane is not secretly a wind test? Cross-check the ~14-17 m/s edge claim
     against `evidence/reports/features/2026-06-02_cte_wind_envelope_result.md`.
   - Is injecting on "entering seq 4" really giving a clean post-injection
     observation window, given the mission geometry? Verify against the waypoint
     file, not the prose.
   - Are the classification classes coherent, and is the planned-RTL vs
     fault-RTL distinction actually decidable from the signals named?
   - Are the "calibrate from smoke" items honestly deferred, or are arbitrary
     numbers being smuggled in as if locked?
4. **Honesty of claims.** Find any place that overstates status: any "verified",
   "working", "passes", or evidence claim not backed by a dated artifact; any
   live-behavior claim (none should exist — Phase 1 is no-SITL). Confirm no
   curated evidence under `evidence/` was produced for this feature yet.
5. **Governance / structure.** ADRs in `governance/decisions/`, runbook complete,
   mission registered in `assets/missions/README.md` and the asset index, `.ai`
   pointers correct, naming per `governance/standards/naming.md`. Run
   `make doctor` and report the result.

## PART B — Implementation faithfulness (the dangerous part)

The failure mode here is code that LOOKS correct but silently drops or distorts a
locked decision. For EACH item below, open the actual code and confirm the
behavior; cite file:line. A passing unit test is not sufficient evidence if the
test asserts the wrong thing — audit the tests too.

1. **Case payloads encode the TRUE semantics, not the case names:**
   - `fail_primary` requests `SIM_ARSPD_FAIL=1` (not a boolean/enable concept).
   - `pitot_500pa` uses `SIM_ARSPD_FAILP=500` and does NOT rely on
     `SIM_ARSPD_PITOT` alone.
   - `noise_5`/`noise_10` set `SIM_ARSPD_RND` 5/10.
   - `sign_reversed` sets `SIM_ARSPD_SIGN=1`.
   - No active case uses `SIM_ARSPD_OFS`.
2. **Reset payload restores SOURCE DEFAULTS, not zeros.** Confirm the reset values
   are `RND=2.0, OFS=2013, FAIL=0, FAILP=0, PITOT=0, SIGN=0, RATIO=1.99`. A reset
   to 0 (especially `RATIO=0`) is a BLOCKER — it would break the model and leak
   state.
3. **Ratio sweep is a recipe, computed from the vehicle ratio:**
   - `SIM_ARSPD_RATIO` is computed as `vehicle_arspd_ratio / k^2`,
     `k = 1 + bias_percent/100` — NOT a hard-coded literal.
   - Phase 1 carries `calibration_required` (vehicle ratio not yet measured) and
     does not present the ratio number as locked.
   - Naming `ratio_bias_pNN` / `ratio_bias_mNN` encodes the airspeed effect.
   - The low-side floor guard (default ~-70%) clamps/refuses degenerate biases;
     verify it actually triggers (read the guard AND a test that exercises it).
   - The full sweep is reachable by passing a longer `bias_percent` list with no
     code change; the v1 thin slice (±10/30/50) is the default.
4. **Injection trigger = entering seq 4**, first `MISSION_CURRENT seq==4` edge
   after front-half progress, first-edge latched, never re-fired; missed/late
   trigger -> `pre_injection_failure`, never a late injection. Confirm the
   metadata/logic encodes this (even if the live body is a Phase-2 stub).
5. **Reference wind** artifact/schema matches ADR-0010 (`x=-5,0,0`, ENU, strict
   echo as a hard gate, wind-sign confirmation flagged as a Phase-2 open item).
6. **Classification** keeps observation-validity SEPARATE from behavior class; a
   bad flight counts only if injection succeeded + wind verified + window met +
   artifacts present; failed launch / failed readback / pre-injection /
   incomplete do NOT count; manifest counts valid observations, not good flights.
   The planned-RTL vs fault-RTL discriminator (max mission seq at AUTO->RTL) is
   implemented coherently. Coarse thresholds (`MIN_POST_INJECTION_S=20`,
   `ALT_LOSS_MAX_M=30`) are present as flagged provisional, and calibrated bands
   are NOT hard-coded.
7. **Mission file correctness.** Independently sanity-check
   `airspeed_failure_behavior_mission.waypoints`: home row, takeoff to 100 m,
   `DO_CHANGE_SPEED 15` at seq 2, settle seq 3, measurement end seq 4, reciprocal
   legs, `RTL` (cmd 20) at seq 9, NO landing. Verify the WPL row format
   (frame/command/params) is valid and the coordinates give ~800 m legs and the
   ~150 m N offset. A malformed mission is a BLOCKER for Phase 2.

## PART C — Architecture / scope discipline (the second-plugin proof)

This feature's stated purpose is to prove a second plugin needs ZERO
framework-core edits. Verify, with evidence:

1. **No `core/` edits.** Diff/inspect: nothing under
   `src/sim_ard_gaw/campaigns/test_suite/core/` is modified. The ONLY non-plugin,
   non-CLI change is the additive `airspeed_failure` registry key. If core was
   touched, that is a BLOCKER and defeats the feature's purpose.
2. **No legacy wind-runner dependency.** The airspeed plugin must construct
   without importing `run_one` / `run_matrix` / `run_matrix_round_robin`, and
   should not import the wind_matrix plugin's modules as a runtime dependency
   (mirroring its patterns is fine; coupling to it is not). Grep and confirm.
   There should be a test asserting this.
3. **No SITL/Gazebo in Phase 1.** Confirm `--list-cases` and `--dry-run`
   construct the plugin and print payloads without launching anything; the live
   environment/control/monitor/stimulus bodies are interfaces/stubs only.
4. **Framework reuse vs duplication.** The plugin imports the `core` CaseGenerator
   ABC, `TestCase`/models, analyzer chain, manifest base — it does not copy them.
   The airspeed analyzers are the PRIMARY scorer; CTE/square analyzers are NOT
   reused as the scorer.
5. **Homes & naming.** Code under `src/`, tests under `tests/`, no runtime output
   or code under `evidence/`, files named per the naming standard. The registry
   key and CLI module name are `airspeed_failure` / `run_airspeed_failure.py`.

## PART D — Tests audit

1. Run `pytest tests/unit/test_airspeed_failure_phase1.py -q` and report
   pass/fail counts. If anything fails, that is at least MAJOR.
2. Audit the tests for substance, not just green:
   - Do they assert the TRUE semantics (reset != zeros, `FAIL=1`, `FAILP` for
     pitot, `OFS` unused, ratio = `ARSPD_RATIO/k^2`, low-side clamp)?
   - Do they cover invalid-case rejection, validity-vs-behavior separation,
     accepted-observation gating, and the no-legacy-import assertion?
   - Are there tests that would PASS even if the code were wrong (tautological /
     asserting the implementation against itself)? Call these out.
   - Is the ratio recipe tested against hand-computed expected values, or just
     against the code's own formula? It must be checked against an independent
     calculation for at least a couple of `bias_percent` values.
3. Note any required Phase-1 test from `phase_1_build_prompt.md` that is MISSING.

## Calibration of severity

- BLOCKER: wrong fault semantics, reset-to-zero, hard-coded ratio presented as
  locked, a `core/` edit, a malformed mission, an over-claimed status/evidence,
  or tests that validate wrong behavior.
- MAJOR: a locked decision implemented incompletely, a missing required test, a
  weak/tautological test, scope creep short of a core edit.
- MINOR: naming, docstrings, redundancy, style, small doc drift.
- QUESTION: something you could not verify or that needs the design owner's call.

## Output format

```
VERDICT: GO | NO-GO (one line, with the single most important reason)

WHAT I CHECKED INDEPENDENTLY:
- ... (source facts re-derived, tests run, make doctor result)

FINDINGS:
[BLOCKER] #1 file:line — problem — required change
[MAJOR]   #2 ...
[MINOR]   #3 ...
[QUESTION]#4 ...

RESIDUAL RISK / WHAT PHASE 2 MUST STILL CATCH:
- ...
```

Be specific, cite file:line, and prefer "I checked X and it is wrong because Y"
over generic advice. If you find nothing wrong in a section, state exactly what
you checked so the reader can trust the pass.
