# Airspeed Failure Behavior Review

Status: planned / not implemented.

## Acceptance Gates

| Phase | Acceptance gate | Current status |
| --- | --- | --- |
| Phase 0 | Candidate is airspeed; parameter list is sourced from `011_Sensor_Failure_Injection`; mission and lane stack are named; behavior-class vocabulary is locked. | Planned; not accepted. |
| Phase 1 | Plugin constructs with no SITL; cases generate correctly; registry resolves plugin; CLI dry-run/list-cases works; no legacy wind runner import is needed for plugin construction. | Not implemented. |
| Phase 2 | One `healthy_reference` run and one `fail_primary` run execute under `var/runs/`; injection is confirmed by parameter readback; monitor and summary artifacts exist; no evidence claim is made yet. | Not implemented. |
| Phase 3 | Full v1 matrix runs with three accepted observations per case; campaign summary exists; behavior classes are assigned; failures are described as behavior outcomes where observation is valid. | Not implemented. |
| Phase 4 | Curated package exists under `evidence/curated_logs/`; evidence report exists under `evidence/reports/features/`; evidence catalog is updated; presentation uses bounded wording. | Not implemented. |

## Review Rules

- Do not claim an accepted airspeed failure behavior result until Phase 4 is
  accepted with dated evidence.
- Do not count failed launches, pre-injection failures, or incomplete artifacts
  as behavior observations.
- Do count degraded or bad aircraft behavior when the injection occurred and
  artifacts are sufficient for classification.
- Keep runtime output under `var/`.
- Keep curated proof under `evidence/`.
- Keep code and scripts outside `evidence/`.

## Residual Risks To Watch

- The second-plugin proof is authorized by the accepted Phase 3G gate, but the
  feature can still create a false architecture signal if it edits `core/` or
  depends on hidden wind-specific runtime delegation.
- Mission-sequence injection must be precise. Injecting before the mission is
  stable or after the critical leg may weaken the observation.
- Some airspeed faults may cause behavior that is hard to classify without a
  clear observation-quality rule.
- Parameter readback failure must be preserved as evidence of failed injection,
  not silently converted into a behavior outcome.
- Presentation wording must remain bounded until the full evidence package is
  curated and cataloged.

## Rollback / Retirement Rule

If airspeed becomes unsuitable before Phase 2, record the reason here and
supersede this runbook with a new feature runbook for the selected candidate.
Do not rewrite this runbook into a different sensor lane without preserving the
decision history.
