# Wind Matrix Campaign

This page is the canonical status note for the wind-matrix campaign. Archived
wind-matrix studies remain useful historical analysis, but they are not the
operating truth for the current workspace.

## Current boundary

The campaign runtime owns the wind-matrix runners under
`src/sim_ard_gaw/campaigns/wind_matrix/` and the campaign test-suite package
under `src/sim_ard_gaw/campaigns/test_suite/`. Campaign hardening helpers live
under `src/sim_ard_gaw/campaigns/` for manifest locking,
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

The 2026-05-24 cutover accepted a fresh x=4, y=4 square-and-loiter
campaign proof under
`var/runs/phase7_final_20260524/tiny_rr_x4_y4_square/`, recorded in
`evidence/reports/migration/CUTOVER_2026-05-24.md` and accepted by
`governance/decisions/ADR-0005-workspace-next-cutover.md`. It does not claim
full wind-matrix readiness or full landing/disarm completion.

## What is trusted now

- Use `docs/operations/launch_targets.md` for current launch-target status.
- Treat `var/` as the raw runtime-output home and promote only curated proof to
  `evidence/`.
- Use `docs/operations/evidence_workflow.md` and
  `evidence/indexes/evidence_catalog.md` when a campaign result needs a
  reviewed manifest, report, raw-output reference, and review status.
- Treat archived wind-matrix investigations as design and history references
  only when reconciling historical results.

## Parameter Stack Boundary

The current CTE launch and campaign callers use the shared stack
`config/vehicles/plane_base.parm` then
`config/overlays/plane_airspeed.parm`. The launcher and current
`run_one.py` / `run_matrix.py` path append
`.private/config/plane_params.local.parm` when that local file exists unless a
campaign caller opts out. That file is a local override, not canonical campaign
config.

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
sim-test case      --x 0 --y 4 --rep 1
sim-test suite     --x-values 0,4,8,12 --y-values 0,4,8,12
sim-test rr        --x-values 0,4,8,12
sim-test airspeed  --list-cases
sim-test gps       --list-cases
```

The wizard selects sensor family (`wind_matrix`, `airspeed_failure`, or
`gps_failure`), run mode, case parameters, and optionally advanced timeouts.
For `wind_matrix` it mirrors the full flag surface of `run_case`, `run_suite`,
and `run_round_robin`. For `airspeed_failure` it asks which fixed fault cases
to include, ratio bias percents, vehicle `ARSPD_RATIO`, whether the ratio is
already verified, and the max attempts per case. For `gps_failure` it asks for
an action rather than a run mode; see
`docs/operations/gps_failure_runbook.md`.

The wizard does not reimplement any runner. It builds an argparse namespace and
hands it to the same `run_from_args` function the flag path calls, so the two
paths cannot resolve settings differently.

### Inspection actions

Every lane supports the same two no-SITL actions. Neither launches a stack,
writes a manifest, or validates the mission contract:

```bash
sim-test suite --x-values 0,4 --y-values 0 --list-cases
sim-test suite --x-values 0,4 --y-values 0 --dry-run
```

`--list-cases` prints the case ids the invocation would run. `--dry-run` prints
a resolved-settings dump plus that case list, which is also how to compare a
wizard run against a flag run.

`--plugin` on `run_case`, `run_suite`, and `run_round_robin` accepts
`wind_matrix` only. Those runners take wind case coordinates
(`--x`/`--y`/`--x-values`/`--y-values`) and validate the square-wind mission
contract, so they cannot drive another lane. Passing `--plugin gps_failure`
exits non-zero and names the entry point that works. Use `sim-test airspeed`
and `sim-test gps` for the other lanes.

Source: `src/sim_ard_gaw/campaigns/test_suite/cli/run.py`,
`src/sim_ard_gaw/campaigns/test_suite/cli/interactive.py`, and
`src/sim_ard_gaw/campaigns/test_suite/cli/_plugin_select.py`.

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
- The `test_suite.cli.*` wind-matrix entry points now use the staged attempt
  pipeline directly. The retired attempt-strategy choice is retained only as a
  deprecated CLI compatibility surface:
  older commands that still pass `--attempt-strategy staged` are accepted with
  a deprecation warning, and `legacy` is rejected with a retired-flag message.
  Phase 3G accepted the zero-legacy staged wind proof on 2026-06-01; retained
  direct wind runners remain separate operator entry points, not a `test_suite`
  strategy choice.
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

Full-matrix evidence still requires later governed evidence. Current platform
status lives in `docs/operations/workspace_status.md`.
