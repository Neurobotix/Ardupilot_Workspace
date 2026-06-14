# Wind Matrix Campaign

This page is the canonical status note for the wind-matrix campaign. The
archived wind-matrix script study under `docs/archive/src_docs/` remains useful
historical analysis, but it is not the operating truth for `workspace_next`.

## Current boundary

The migrated campaign runtime now owns the wind-matrix runners under
`src/sim_ard_gaw/campaigns/wind_matrix/` and the campaign test-suite package
under `src/sim_ard_gaw/campaigns/test_suite/`. Old `compat_scripts/` imports and
script paths are thin wrappers into those owned homes. Phase 5 hardening helpers
remain under `src/sim_ard_gaw/campaigns/` for manifest locking,
terminal-status taxonomy, mission-contract validation, XML/SDF wind handling,
and input provenance. Mission, world, parameter, analysis, and campaign-output
defaults resolve through owned `assets/`, `config/`, `src/sim_ard_gaw/analysis/`,
and `var/` homes.

Phase 2 runtime parity proved the fixed-wing CTE launch lane with
`plane-cte` plus `gazebo-plane-cte`. Phase 5 then proved a bounded
`test_suite.cli.run_round_robin` tiny campaign case with curated evidence and
the hardening policy below. The first Phase 5 one-case `4,4`
production-reference comparison remediation used only the installed Gazebo
plugin fallback and is not ArduPilot-side wind parity proof; a corrected
workspace-plugin recheck restored the known-good estimated wind behavior.
Current policy forbids that fallback. That is still a bounded comparison, not a
full matrix or cutover claim.

Phase 7 cutover passed on 2026-05-24 with a fresh x=4, y=4 square-and-loiter
campaign proof under
`var/runs/phase7_final_20260524/tiny_rr_x4_y4_square/`, recorded in
`evidence/reports/migration/CUTOVER_2026-05-24.md` and accepted by
`governance/decisions/ADR-0005-workspace-next-cutover.md`. This closes the
representative campaign gate for Phase 7 only. It does not claim full
wind-matrix readiness or full landing/disarm completion.

## What is trusted now

- Use `docs/operations/launch_targets.md` for current launch-target status.
- Treat `var/` as the raw runtime-output home and promote only curated proof to
  `evidence/`.
- Use `docs/operations/evidence_workflow.md` and
  `evidence/indexes/evidence_catalog.md` when a campaign result needs a
  reviewed manifest, report, raw-output reference, and review status.
- Treat archived wind-matrix investigations as design and history references
  only when reconciling the compatibility runtime.

## Parameter Stack Boundary

The current CTE launch and campaign callers use the shared stack
`config/vehicles/plane_base.parm` then
`config/overlays/plane_airspeed.parm`. The launcher and current
`run_one.py` / `run_matrix.py` path append
`.private/config/plane_params.local.parm` when that local file exists unless a
campaign caller opts out. The retained legacy `run_one_og.py` peer appends the
same local override when it is invoked. That file is a local override, not
canonical campaign config.

Historical comparisons must keep the effective parameter file list and
parameter content hashes with their run evidence. Recovered production-era
parameter stacks belong under `evidence/curated_logs/recovered_param_stacks/`;
they are provenance and comparison evidence, not active `config/`.

Phase 5 writes per-attempt parameter-file provenance into campaign run config
and manifest records. Comparisons must use parameter content hashes, not infer
equivalence from path names.

## Unified CLI (`sim-test`)

The `test_suite` now has a single entry point that covers all plugins and run
modes. Run it with no arguments for an interactive wizard:

```bash
sim-test
```

Or pass sub-commands to use the existing flag surface directly:

```bash
sim-test case   --x 0 --y 4 --rep 1
sim-test suite  --x-values 0,4,8,12 --y-values 0,4,8,12
sim-test rr     --x-values 0,4,8,12
```

The wizard selects sensor family (`wind_matrix` or `airspeed_failure`), run
mode, case parameters, and optionally advanced timeouts. For `wind_matrix` it
mirrors the full flag surface of `run_case`, `run_suite`, and `run_round_robin`.
For `airspeed_failure` it asks which fixed fault cases to include, ratio bias
percents, vehicle `ARSPD_RATIO`, and whether the ratio is already verified.

Source: `src/sim_ard_gaw/campaigns/test_suite/cli/run.py` and
`src/sim_ard_gaw/campaigns/test_suite/cli/interactive.py`.

## Phase 5 Safety Policy

- Matrix launchers take a campaign-root manifest lock before unsafe manifest
  transactions and one-attempt writes.
- Legacy manifest `status` values remain compatible; Phase 5 adds canonical
  `terminal_status` values (`success`, `partial`, `failed`, `failed_analysis`,
  `error`, `interrupted`) additively.
- The `test_suite` framework manifest view adds generic fields additively
  (`schema_version`, `case_id`, `suite_name`, `parameters`,
  `stimulus_result`, `analysis_results`, `verdict`, `artifacts`,
  `attempt_id`, `started_at`, `finished_at`). The schema marker is
  `test_suite.generic_manifest.v1`. Older wind manifests without those fields
  remain readable through the generic view and the legacy wind-specific fields
  remain the compatibility surface. Framework additive writes use the same
  campaign manifest lock as the legacy unsafe manifest transactions.
- Feature Phase 3 adds an opt-in staged attempt path for the new
  `test_suite.cli.*` entry points through `--attempt-strategy staged`.
  The default remains `--attempt-strategy legacy`, which delegates to the
  proven `run_one.run_one(...)` body. Do not treat staged mode as campaign
  parity evidence until a dated live SITL/Gazebo comparison exists. Feature
  Phase 3B proved the staged wind boundary is not hidden behind
  `run_one.run_one(...)`, but it also found staged mode still depends on
  legacy runner helper code. Phase 3C-3G must build the full zero-legacy
  staged wind system before staged mode is treated as replacement or generic
  runtime proof. The 2026-05-31 Phase 3C follow-up restored atomic plugin
  manifest writes, staged `running`/terminal manifest persistence, stale
  running-record reconciliation, and plugin-owned stimulus run-config/path
  helpers; staged environment launch/readiness, MAVLink control/monitoring,
  runtime wind injection, analysis, summary, and terminal helper execution
  still remain Phase 3D-3G legacy-dependency work.
- The square campaign validates its mission contract before a matrix launcher
  starts a stack and again before the delegated attempt relies on square,
  loiter, and landing sequence assumptions. The contract includes the
  analyzer-sensitive square waypoint commands, supported location frames, and
  500 m square-side geometry instead of trusting sequence numbers alone.
- Static Gazebo wind-world copies are transformed and parsed through XML/SDF
  structure; nested or ambiguous wind nodes are rejected.
- Runtime wind topic echo verification defaults to strict for campaign runs.
  `SIM_ARD_GAW_STRICT_WIND_ECHO_VERIFY=0` is an explicit non-evidence override
  that must be recorded if used.
- Wind evidence also has to record Gazebo plugin selection. The only allowed
  plugin binary is `build/ardupilot_gazebo/libArduPilotPlugin.so`. Current
  runtime fails closed if that workspace build is missing; the
  Phase 5 incident shows why an installed-plugin fallback cannot support an
  evidence claim even when Gazebo topic echo verification passes.
- Campaign launchers run the governed broad cleanup path before attempts so
  stale simulator state cannot contaminate the next evidence run.

Use the dated Phase 5 report for the hardening, bounded tiny campaign proof,
invalidated first `4,4` comparison, and corrected workspace-plugin recheck:

`evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`

The detailed Gazebo plugin fallback incident record is:

`governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`

Full-matrix evidence still requires later governed evidence. The open migration
blocker list lives in `.ai/issues/open.md`.
