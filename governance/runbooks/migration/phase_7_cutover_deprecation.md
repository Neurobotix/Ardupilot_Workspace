# Phase 7: Cutover And Old Workspace Deprecation

Purpose: decide whether `workspace_next` can become the production workspace
and whether the old workspace can move from production reference to a governed
deprecated stage.

Phase 7 is a decision gate, not a forced promotion. Work only in
`/home/ahmed/ardupilot_workspace_next`. The old workspace may be read as the
production reference or rollback fallback, but it must not be edited here.
Compatibility paths stay in place until Phase 8.

## Status Semantics

- `PASS`: every cutover prerequisite is supported by dated evidence, the final
  Phase 7 checks pass, a cutover ADR is accepted, and the docs match that
  decision.
- `FAIL`: a required Phase 7 validation or governed decision proves the cutover
  should not proceed until a defect is fixed.
- `BLOCKED`: readiness cannot be proven because a prerequisite, required
  runtime/evidence workflow, or unresolved production-safety blocker remains
  open without an explicit accepted governance decision.

Do not replace a blocker with a note to make the cutover look green.

## Readiness Audit

Before editing production-status docs:

1. Confirm the latest Phase 0 through Phase 6 reports exist and record each
   conclusion.
2. Review `.ai/issues/open.md`, prior phase reports, audits/incidents, and any
   canonical docs that qualify a status as reference-only or not yet tested.
3. Decide whether final cutover can proceed or whether Phase 7 must conclude
   `BLOCKED`.

Cutover is allowed only when evidence shows:

- structural validation passes;
- runtime parity prerequisites are sufficient;
- campaign/test migration blockers that threaten production safety are resolved
  or explicitly accepted by ADR;
- the evidence workflow is operational;
- onboarding and operations docs are accurate;
- vehicle and campaign status docs do not overclaim;
- the old-workspace fallback and rollback procedure is documented.

The governed runtime policy for this gate is in
`governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`:
broad clean-run cleanup is an intentional pre-run safety measure, and the
workspace-built Gazebo plugin is the only allowed plugin path.

## Final Proof Work

- Run final shadow parity from `governance/runbooks/operations/shadow_parity.md`.
- Record setup/environment checks, doctor/structure/parity checks, relevant
  launch smoke state, output-home behavior, evidence-promotion behavior, and
  cleanup/process hygiene under the clean-run policy.
- Verify final proof uses
  `build/ardupilot_gazebo/libArduPilotPlugin.so` and fails closed if that
  workspace build is missing. Installed plugin fallback is not an accepted
  runtime path.
- Run or verify one bounded representative vehicle workflow with command path,
  environment setup, runtime outcome, output location, cleanup, and evidence
  link.
- Run or verify one bounded representative campaign/evidence workflow with
  command path, config or parameter provenance, `var/` raw output location,
  curated evidence/index state, and cleanup.
- Do not run a large uncontrolled campaign.

If a required final-proof step cannot be executed, record `BLOCKED`. It is not a
cutover pass unless an accepted ADR explicitly accepts the risk.

## Minimum Validation

- `make doctor`
- `scripts/maintenance/validate_structure.sh`
- `scripts/maintenance/validate_evidence.sh`
- `make test-parity`
- final shadow parity commands required by
  `governance/runbooks/operations/shadow_parity.md`
- raw log leakage and cleanup/process-hygiene checks
- docs/status consistency scan
- prior-phase report existence and conclusion check

## Decision Path

If readiness passes:

- create `governance/decisions/ADR-xxxx-workspace-next-cutover.md`;
- state the decision, evidence used, accepted risks, rollback path, old
  workspace deprecation stage, and the Phase 8 compatibility-retirement
  boundary;
- update docs and `.ai` state so production entrypoints, deprecated old-workspace
  policy, compatibility remaining until Phase 8, and accepted risks agree with
  the ADR;
- update the evidence catalog if new proof is promoted.

If readiness fails:

- do not create an accepted cutover ADR;
- create the Phase 7 cutover report with a `BLOCKED` or `FAIL` decision and an
  explicit blocker list;
- update `.ai/current.md`, `.ai/issues/open.md`, and migration docs with the
  blocker state;
- verify no doc accidentally claims production promotion or old-workspace
  deprecation.

## Required Updates

Always update:

- `governance/runbooks/migration/phase_7_cutover_deprecation.md`
- rollback guidance under `governance/runbooks/operations/`
- `evidence/reports/migration/CUTOVER_<date>.md`
- `.ai/current.md`
- `.ai/issues/open.md`
- `docs/operations/migration_status.md`

Update on a cutover pass when the claim changes:

- `README.md`
- `docs/onboarding/quick_start.md`
- `docs/operations/launch_targets.md`
- `docs/vehicles/status.md`
- `docs/campaigns/wind_matrix.md`
- `.ai/index.md`
- `governance/decisions/ADR-xxxx-workspace-next-cutover.md`
- `evidence/indexes/evidence_catalog.md`

## Cutover Report Contract

`evidence/reports/migration/CUTOVER_<date>.md` must include date/time and timezone,
scope, readiness audit results, prior-phase summary, open-blocker review,
commands run, shadow parity result, representative vehicle and campaign/evidence
workflow results, structure/parity/test results, cleanup/process hygiene,
output/evidence policy, docs/AI/governance updates, the cutover decision, old
workspace deprecation status, accepted risks for a pass, unresolved blockers,
and explicit statements that the old workspace was not modified and Phase 8
still owns compatibility retirement.

## Exit Gate

Re-read this runbook, `governance/runbooks/operations/shadow_parity.md`, and the Phase 7
cutover report before closing the phase. Re-check each gate above and rerun safe
validation checks after the docs and evidence updates.

Old workspace may be called deprecated only after a passing cutover report and
an accepted cutover ADR exist. A blocked Phase 7 report keeps the old workspace
as production reference/fallback policy input, not as a deprecated workspace.

## 2026-05-24 Closure

Phase 7 closed as PASS with accepted residuals in
`evidence/reports/migration/CUTOVER_2026-05-24.md` and
`governance/decisions/ADR-0005-workspace-next-cutover.md`. The old workspace is
deprecated fallback/reference after that decision. Phase 8 remains responsible
for compatibility retirement.
