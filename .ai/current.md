# Current Work

This workspace is the active ArduPilot + Gazebo fault-injection evidence
framework for the governed simulation workflows. Runtime output belongs under
`var/`; curated proof belongs under `evidence/`; local overlays and notes belong
under `.private/`. The old workspace `/home/ahmed/ardupilot_workspace` is
deprecated fallback/reference only and must not be edited without explicit
operator authorization.

## Operating Rules

- Read `AGENTS.md` and `.ai/entrypoint.md` before choosing a workflow.
- Use `docs/operations/workspace_status.md` for current human status.
- Use `governance/standards/change_control.md` before changing docs, code,
  evidence, governance, config, or assets.
- Use only the workspace-built Gazebo plugin:
  `build/ardupilot_gazebo/libArduPilotPlugin.so`.
- Run `make doctor` after structure, docs, governance, evidence, runtime-path,
  or local-overlay-policy changes.
- Do not promote status, parity, vehicle, campaign, or cutover claims without
  dated evidence.

## Active Lanes

### Wind Matrix

The `wind_matrix` lane is the CTE/wind campaign lane. The `test_suite`
wind-matrix plugin uses the staged attempt pipeline as its only supported
framework path; the old `--attempt-strategy` choice is retired, with
`--attempt-strategy staged` accepted only as a deprecated no-op and `legacy`
rejected. Evidence:
`evidence/reports/migration/WIND_MATRIX_LEGACY_STRATEGY_RETIREMENT_2026-06-30.md`.

The standalone operator runners
`src/sim_ard_gaw/campaigns/wind_matrix/run_one.py`,
`run_matrix.py`, and `run_matrix_round_robin.py` remain live entry points.
Do not delete or refactor them as part of documentation cleanup. Full
wind-matrix campaign evidence beyond bounded proof still requires later
governed evidence.

### Airspeed Failure

The `airspeed_failure` lane characterizes behavior under degraded or corrupted
airspeed signal. Phase 2 live measurement smoke was accepted on 2026-06-06 from
`var/runs/airspeed_failure_behavior_20260606T164050810132Z/`. The 2026-06-11
curated package and the 2026-06-14 acceptance report cover bounded Phase 4A
ratio/ramp/pulse characterization only:

- `evidence/curated_logs/airspeed_failure_behavior_2026-06-11/`
- `evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`
- `evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`

Fixed-case repetition/full-lane acceptance remains open as Phase 4B. Tailwind
work has accepted healthy gate and corrected P130 pulse interpretation through
2026-06-23; Chunk 4/5 tailwind acceptance work remains separate from this
current doc cleanup.

### GPS Failure

The `gps_failure` lane characterizes behavior under degraded or corrupted GPS.
Phase 0 design lock was accepted on 2026-07-06 and Phase 1 no-SITL foundation
was accepted on 2026-07-13. Corrected raw/live validation ran through bounded
v4/v5 paths by 2026-07-16. Raw runtime root
`var/runs/gps_failure_behavior/` records v6-geometry non-jamming fault-case
runs from 2026-07-20, with one accepted repetition per case; each attempt-local
`run_config.json` records the v6 mission hash
`ba22c669c895f694e8556e0e9573e9f9dd278d159086e46706eb30a3714d7261`, matching
the current mission asset and the later 2026-07-22 commit `2051e83`. This is
raw `var/` output, not promoted evidence: no `evidence/curated_logs/gps*`
package or GPS report under `evidence/reports/features/` exists as of
2026-08-17, so Phase 2 acceptance, Phase 4 curation, and final science
campaign claims remain open.

The next live action is gated by `--preflight` and explicit operator
confirmation. Current contracts and guarded commands live in
`docs/operations/gps_failure_runbook.md`; lane architecture lives in
`docs/architecture/gps_failure_lane.md`.

### GPS-Denied Navigation Study

Home created on 2026-10-12:
`governance/runbooks/features/gps_denied_navigation/`. The study plan is
pending. The August INS-only implementation is preserved, unmerged and
unreviewed, on the branch `archive/ins-only-stash`. No GPS-denied result or
evidence exists.

## Current Pointers

- Workspace status: `docs/operations/workspace_status.md`
- Launch targets: `docs/operations/launch_targets.md`
- Evidence workflow: `docs/operations/evidence_workflow.md`
- Workspace map: `docs/architecture/workspace_map.md`
- Wind matrix campaign: `docs/campaigns/wind_matrix.md`
- Airspeed failure runbook: `docs/operations/airspeed_failure_runbook.md`
- GPS failure runbook: `docs/operations/gps_failure_runbook.md`
- GPS-denied navigation study: `governance/runbooks/features/gps_denied_navigation/`
- Historical migration plan and records:
  `governance/runbooks/migration/full_migration_plan.md` and
  `evidence/reports/migration/`
