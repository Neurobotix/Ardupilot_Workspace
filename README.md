# ArduPilot Fault-Injection Evidence Framework

This workspace is a multi-sensor fault-injection and evidence framework for
ArduPilot + Gazebo Harmonic simulation. It currently supports three working
lanes: `wind_matrix`, `airspeed_failure`, and `gps_failure`.

The platform's defining contract is that campaign results become dated,
hash-manifested evidence packages instead of free-floating reports. Runtime
output stays disposable under `var/`; reviewed proof is promoted under
`evidence/` with reports, manifests, hashes, and indexes.

This workspace separates:

- `src/`: owned runtime code.
- `assets/`: models, worlds, and missions.
- `config/`: reproducible shared parameters and campaign config.
- `docs/`: human onboarding and operations.
- `governance/`: decisions, audits, standards, runbooks.
- `.ai/`: compact agent protocol and active state only.
- `evidence/`: curated reports, manifests, hashes, and indexes.
- `var/`: disposable runtime output, ignored by git.
- `.private/`: local overlays and personal notes only, ignored by git.

Production workspace: `/home/ahmed/ardupilot_workspace_next`.

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

`make doctor` runs the structure and evidence validators through
`scripts/ops/doctor.sh`, including
`scripts/maintenance/validate_structure.sh`.

Current status and operating entry points:

- `docs/operations/workspace_status.md`
- `docs/operations/launch_targets.md`
- `docs/operations/evidence_workflow.md`
- `governance/standards/change_control.md`

Runbooks live under organized subdirectories of `governance/runbooks/`. See
`governance/runbooks/README.md` for the layout and rules.

## History

The workspace migration completed on 2026-05-24 under
`governance/decisions/ADR-0005-workspace-next-cutover.md`,
`evidence/reports/migration/CUTOVER_2026-05-24.md`, and
`evidence/reports/migration/shadow_parity_2026-05-24.md`. The compatibility
wrapper layer was fully removed on 2026-06-30 under
`evidence/reports/migration/PHASE_8_COMPAT_FINAL_REMOVAL_AUDIT_2026-06-30.md`,
and the wind-matrix legacy attempt strategy was retired the same day under
`evidence/reports/migration/WIND_MATRIX_LEGACY_STRATEGY_RETIREMENT_2026-06-30.md`.
