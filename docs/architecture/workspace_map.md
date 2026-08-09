# Workspace Map

Top-level homes are enforced by `scripts/maintenance/validate_structure.sh`,
which is called by `make doctor`.

- `README.md` and `setup.bash` are the root entry points.
- `assets/` contains simulator models, worlds, and waypoint missions.
- `config/` contains reproducible shared vehicle parameters, feature overlays,
  campaign config, and explicit archives.
- `docs/` contains human-facing onboarding, operations, architecture,
  campaign, vehicle documentation, and presentation templates.
- `governance/` contains standards, decisions, audits, and phase runbooks.
- `.ai/` contains compact agent pointers and active state.
- `src/` contains owned runtime code.
- `tests/` contains unit, integration, and parity checks.
- `evidence/` contains curated reports, manifests, indexes, and small proof
  artifacts.
- `scripts/` contains operator, developer, and maintenance entry points.
- `var/` is disposable runtime output and is ignored by git.
- `.private/` is ignored local overlay space and must not become canonical.

Canonical inventory lives with evidence:

- `evidence/indexes/asset_index.md` records model, world, and mission status.
- `evidence/indexes/parameter_config_index.md` records shared config categories,
  stack membership, hashes, local-overlay policy, and recovered historical
  parameter evidence.

Historical recovered parameter stacks stay under
`evidence/curated_logs/recovered_param_stacks/`. They are comparison evidence,
not runtime defaults. Local overrides stay under `.private/`; they may affect a
local run only when a launcher explicitly appends them.

Launch, bridge, analysis, wind-matrix runner, and campaign `test_suite`
implementations live under organized homes in `src/sim_ard_gaw/`. Runtime
paths resolve directly to `assets/`, `config/`, `var/`, and owned runtime
directories.
