# Phase 4: Config And Asset Normalization

Purpose: make parameters, models, worlds, and missions explicit, indexed, and
free of hidden local dependencies.

## Execution Notes

- Audit existing docs, indexes, evidence, config homes, assets, local overlays,
  and compatibility references before editing. Record the gap assessment in the
  Phase 4 evidence report rather than creating a competing plan.
- Preserve runtime compatibility bridges until their references, docs, checks,
  and evidence can move together. Phase 4 documents those bridges; it does not
  perform the Phase 7 cutover or the Phase 8 retirement.
- Treat `.private/config/` as optional local overlay space only. Shared truth
  belongs under `config/`; historical recovered parameter stacks belong under
  `evidence/`.
- Do not claim an asset, stack, or launch lane is verified unless dated evidence
  supports that status.

## Tasks

- Create or update canonical asset indexes for `assets/models`, `assets/worlds`,
  and `assets/missions`. Record path, purpose, status, known references, and
  evidence-aware verification state.
- Create or update a canonical config/parameter index covering
  `config/vehicles`, `config/overlays`, `config/campaigns`, `config/archive`,
  `.private/config/` policy, and recovered historical parameter evidence.
- Record SHA-256 hashes for shared active and campaign parameter files used in
  current runtime or documented comparison stacks.
- Document actual parameter stack membership for launch lanes that still route
  through the compatibility launcher, including base, overlay, campaign, local
  override, and rebuild distinctions.
- Verify local override behavior is documented but not required for base
  workspace health. Record any parity or campaign result that materially depends
  on a local override as a dependency or risk.
- Confirm historical parameter evidence is outside active `config/`, and scan
  active `config/` for nested `.private` state.
- Confirm launch scripts reference new homes through compatibility paths or
  explicit variables, then document remaining compatibility reliance.

## Required Updates

- `docs/architecture/workspace_map.md`: asset/config ownership.
- `docs/operations/launch_targets.md`: parameter stacks per launch target.
- `docs/vehicles/status.md`: vehicle config references.
- `docs/campaigns/wind_matrix.md`: campaign param hashing requirements.
- `evidence/indexes/`: asset and param indexes.
- `.ai/current.md` and `.ai/issues/open.md`: blockers and status.

## Required Validation

- `make doctor`.
- `scripts/maintenance/validate_structure.sh`.
- Inventory assets under `assets/models`, `assets/worlds`, and
  `assets/missions`, and inventory config categories under `config/`.
- Hash shared active and campaign parameter files named by the runtime stack
  audit.
- Inspect runtime parameter references in
  `src/sim_ard_gaw/compat_scripts/launch.sh` and relevant campaign scripts.
- Scan active `config/` for nested `.private`, inspect `.private/config/`
  policy, and scan canonical docs for stale base-airspeed, unqualified
  local-override, and final-architecture compatibility claims.

## Exit Gate

Create `evidence/reports/migration/PHASE_4_CONFIG_ASSETS_<date>.md` with:

- scope, commands, files changed, pre-existing Phase 4 work, and the gap
  assessment;
- asset inventory counts,
- config inventory counts,
- parameter stack table,
- SHA-256 file hashes for shared active and campaign parameter files,
- local override policy check,
- hidden-local dependency findings,
- active `config/` nested `.private` check result,
- references/docs updated,
- unresolved ambiguity and blocker list,
- PASS / FAIL / BLOCKED conclusion,
- an explicit statement that the old workspace was not modified,
- and an explicit statement that Phase 4 did not perform cutover.
