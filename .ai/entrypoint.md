# Agent Task Entrypoint

Use this file after reading `AGENTS.md`.

## Universal Start

Read these before doing any work:

1. `AGENTS.md`
2. `.ai/current.md`
3. `.ai/index.md`
4. `governance/standards/change_control.md`
5. `governance/standards/naming.md`
6. `governance/standards/evidence.md`
7. The relevant human doc under `docs/`

## Run A Simulation

Read:

- `docs/onboarding/quick_start.md`
- `docs/operations/launch_targets.md`
- `docs/operations/sitl_gazebo_runtime.md`
- `docs/operations/evidence_workflow.md`
- `docs/vehicles/status.md`

Rules:

- Use `scripts/ops/launch.sh` unless a canonical doc says otherwise.
- Runtime output starts under `var/`.
- Curated proof is promoted to `evidence/`.
- Update vehicle or campaign status only with dated evidence.
- Respect the clean-run and workspace-built plugin policy in
  `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`.

Minimum checks:

- Run the documented launch help or target command.
- Record command, date, output location, and evidence disposition.

## Add A Feature

Read:

- `docs/architecture/workspace_map.md`
- `docs/operations/workspace_status.md`
- relevant existing feature docs under `docs/`
- relevant tests under `tests/`

Rules:

- Owned runtime code goes under `src/sim_ard_gaw/`.
- Assets go under `assets/`.
- Shared reproducible config goes under `config/`.
- Local-only tuning goes under `.private/`.
- Tests go under `tests/`.
- Add or update docs, `.ai` pointers, evidence, and governance records as needed.
- Create an ADR only for a durable architectural or policy decision.
- Name new files according to `governance/standards/naming.md` and the nearest
  directory README.

Minimum checks:

- Run targeted tests for the feature.
- Run `make doctor` if structure, docs, governance, evidence, runtime paths, or
  local overlay policy changed.

## Update An Existing Feature

Read:

- current docs for the feature
- current evidence reports and indexes
- related issues or audits
- related tests

Rules:

- Preserve old evidence as history; do not overwrite it to make a new claim.
- Update the canonical doc, evidence index, `.ai` pointer, and issue/status
  record if the feature state changed.
- Preserve historical evidence names unless a deliberate migration updates
  references in the same change.

Minimum checks:

- Run the narrowest reliable test or parity check for the changed behavior.
- Record any skipped checks as blockers or residual risk.

## Wind Matrix Or Campaign Work

Read:

- `docs/campaigns/wind_matrix.md`
- `governance/runbooks/migration/phase_5_campaign_test_migration.md`
- `governance/decisions/ADR-0003-phase5-campaign-safety-contract.md`
- `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`
- `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`
- `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-22.md`

Rules:

- Compatibility runners are still retained where Phase 8 says they are retained.
- A tiny case is not a full matrix.
- Raw campaign output belongs in `var/`; curated summaries and manifests belong
  in `evidence/`.
- New campaign reports under `evidence/reports/` use
  `YYYY-MM-DD_lower_snake_case.md`.

Minimum checks:

- Prove at least the requested campaign path or clearly document why it is
  blocked.

## Change Config Or Assets

Read:

- `evidence/indexes/asset_index.md`
- `evidence/indexes/parameter_config_index.md`
- `docs/architecture/workspace_map.md`
- `docs/operations/launch_targets.md`

Rules:

- Active shared config lives in `config/`.
- Historical config evidence lives in `evidence/`.
- Local machine overlays live in `.private/`.
- Update indexes and hashes when promoted assets or config change.
- New shared config uses lower snake case unless an external tool requires
  another name.

Minimum checks:

- Run `make doctor`.
- Validate the affected launch or config path if practical.

## Change Docs Or Governance

Read:

- `governance/standards/documentation.md`
- `governance/standards/records_lifecycle.md`
- `governance/audits/2026-05-20_phase3_docs_errata.md`

Rules:

- `docs/` is for humans doing work.
- `.ai/` is for protocol, routing, active state, and pointers.
- `governance/` is for decisions, audits, standards, and runbooks.
- Archived docs are historical and non-canonical unless rewritten into current
  docs with fresh verification.
- Stable docs use `lower_snake_case.md`; audits, incidents, one-off reports,
  and evidence reports use `YYYY-MM-DD_lower_snake_case.md`.

Minimum checks:

- Run `make doctor`.
- Check new links and paths.

## Commit Or Push

Read:

- `governance/standards/git_commit_style.md`

Rules:

- Treat commit style as canonical workspace governance, not private memory.
- Before committing, check `git status --short`, stage only the requested
  scope, inspect `git diff --staged`, and use one exact prefix from the commit
  style standard.
- Before pushing, verify the local branch/status, confirm the committed scope
  excludes unrelated workspace changes, and use the commit style standard for
  any new commit created during the workflow.
- Do not push unless the user explicitly authorizes the push.
- Do not commit broad untracked workspace contents just because they exist.

Minimum checks:

- Run the checks required for the change being committed.
- If no safe staged or committable scope exists, report that instead of
  creating a test commit.

## Refactor Runtime Or Compatibility Code

Read:

- `evidence/reports/migration/PHASE_8_COMPAT_RETIREMENT_2026-05-22.md`
- `governance/runbooks/migration/phase_8_compatibility_retirement.md`
- `docs/architecture/workspace_map.md`
- `src/sim_ard_gaw/README.md`

Rules:

- Do not introduce duplicate runnable implementations.
- Retire compatibility only when tests, docs, evidence, and blockers support it.
- Keep compatibility wrappers where current evidence says they are still needed.

Minimum checks:

- Run targeted tests.
- Run `make doctor`.
- Update Phase 8 evidence or a new report if compatibility status changed.

## End-Of-Task Checklist

- Code/config/assets are in the correct homes.
- New files comply with `governance/standards/naming.md` or have a documented
  tool/provenance exception.
- Docs state only verified commands and paths.
- `.ai/current.md` or `.ai/index.md` changed only when agent-facing state or
  routing changed.
- Evidence claims have dated paths, reports, commands, hashes, or decisions.
- Governance records exist for policy, audit, incident, or durable decision
  changes.
- Raw logs and disposable runtime outputs stayed out of git.
- Checks were run, or blockers were recorded honestly.
