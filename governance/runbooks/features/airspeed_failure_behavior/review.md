# Airspeed Failure Behavior Review

Status: planned / not implemented.

## Acceptance Gates

| Phase | Acceptance gate | Current status |
| --- | --- | --- |
| Phase 0 | Candidate is airspeed; parameter list is sourced from `011_Sensor_Failure_Injection`; mission and lane stack are named; exact case payload semantics, ratio-sweep design, reset rules, injection trigger, fixed reference wind, mission design, and behavior-class vocabulary are locked. | Design locked 2026-06-03 (`design_research.md`, `design_adrs.md`, new mission); ratio numeric values + thresholds pending Phase 2 measurement. |
| Phase 1 | Plugin constructs with no SITL; cases generate correctly; registry resolves plugin; CLI dry-run/list-cases works; runtime parameter-probe path exists; airspeed analysis artifact schema is tested; no legacy wind runner import is needed for plugin construction. | Not implemented. |
| Phase 2 | One `healthy_reference` run and one `fail_primary` run execute under `var/runs/`; injection and reset are confirmed by parameter readback; fixed wind is recorded; required airspeed analysis artifacts exist; a dated smoke-review decision unlocks or blocks Phase 3; no curated feature evidence claim is made yet. | Not implemented. |
| Phase 3 | Full v1 matrix runs with three accepted observations per case; campaign summary exists; behavior classes and observation-quality classes are assigned; failures are described as behavior outcomes where observation is valid. | Not implemented. |
| Phase 4 | Curated package exists under `evidence/curated_logs/`; evidence report exists under `evidence/reports/features/`; evidence catalog is updated; presentation uses bounded wording. | Not implemented. |

## Review Rules

- Do not claim an accepted airspeed failure behavior result until Phase 4 is
  accepted with dated evidence.
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
- Presentation wording must remain bounded until the full evidence package is
  curated and cataloged.

## Required Smoke Review Checklist

Before Phase 3 starts, record a dated smoke review that includes:

- raw roots for the `healthy_reference` and `fail_primary` attempts;
- effective parameter stack and hashes;
- exact fixed wind vector, frame, topic, and readback/echo result;
- exact injection trigger event and actual trigger timestamp/sequence;
- `airspeed_injection.json` readback and reset status;
- presence of all required airspeed analysis artifacts;
- behavior class and observation-quality class for each smoke attempt;
- explicit decision: Phase 3 unlocked, blocked, or rerun required.

## Rollback / Retirement Rule

If airspeed becomes unsuitable before Phase 2, record the reason here and
supersede this runbook with a new feature runbook for the selected candidate.
Do not rewrite this runbook into a different sensor lane without preserving the
decision history.
