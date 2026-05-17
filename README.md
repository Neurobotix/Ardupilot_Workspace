# ArduPilot Workspace Next

Internal engineering workspace for ArduPilot + Gazebo Harmonic simulation.

This workspace is intentionally not a direct copy of production. It separates:

- `src/`: owned runtime code plus thin compatibility wrappers for old script
  paths.
- `assets/`: models, worlds, and missions.
- `config/`: reproducible shared parameters and campaign config.
- `docs/`: human onboarding and operations.
- `governance/`: decisions, audits, standards, runbooks.
- `.ai/`: compact agent protocol and active state only.
- `evidence/`: curated reports, manifests, hashes, and indexes.
- `var/`: disposable runtime output, ignored by git.
- `.private/`: local overlays and personal notes only, ignored by git.

Production workspace: `/home/ahmed/ardupilot_workspace_next`.

Deprecated fallback/reference: `/home/ahmed/ardupilot_workspace`.

Start here:

```bash
source setup.bash
make doctor
scripts/ops/launch.sh help
```

AI agents start at `AGENTS.md`. That file is the fixed entry point for
simulation runs, feature work, documentation changes, evidence work, and
governance updates.

Governed Gazebo runs use the workspace-built plugin at
`build/ardupilot_gazebo/libArduPilotPlugin.so` and do not use an installed
plugin fallback. Launch and campaign entrypoints also perform clean-run cleanup
before starting a new simulator stack. See
`docs/onboarding/installation.md` and
`governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`.

Phase 8 has retired the old root symlink bridge and moved launch, bridge,
analysis, wind-matrix runner, and campaign test-suite implementation ownership
into organized `src/sim_ard_gaw/` homes. `compat_scripts/` remains wrapper-only
for old import and script paths.

Phase 7 cutover passed on 2026-05-24 under
`governance/decisions/ADR-0005-workspace-next-cutover.md`,
`evidence/reports/migration/CUTOVER_2026-05-24.md`, and
`evidence/reports/migration/shadow_parity_2026-05-24.md`. The cutover does not claim full
wind-matrix readiness.

`make doctor` runs the Phase 1 structure validator at
`scripts/maintenance/validate_structure.sh`.

Migration plan:

- `governance/runbooks/migration/full_migration_plan.md`
- `docs/operations/migration_status.md`
- `governance/standards/change_control.md`

Runbooks live under organized subdirectories of `governance/runbooks/`. See
`governance/runbooks/README.md` for the layout and rules.

The 2026-05-24 shadow parity checklist is complete for the bounded cutover
scope. Future expanded claims still require dated evidence.
