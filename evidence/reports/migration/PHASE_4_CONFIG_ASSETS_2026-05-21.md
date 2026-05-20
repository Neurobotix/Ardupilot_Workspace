# Phase 4 Config And Asset Normalization

Date/time: 2026-05-21T09:24:59+03:00

Timezone: Africa/Cairo / EEST (+03:00)

## Scope

Phase 4 makes workspace-owned assets, shared config, local overlays, archived
config, and recovered historical parameter evidence explicit before campaign
refactor or cutover. This pass audited the current state first, clarified the
Phase 4 runbook, added canonical asset and config indexes, updated ownership
docs, and corrected one stale recovered-stack code path.

The old workspace was not modified. Phase 4 did not perform cutover.

## Review Remediation

Strict review on 2026-05-21 found that the initial Phase 4 closeout still had
four audit gaps. This revision:

- narrows the Mini Talon base-air-speed boundary: `plane_base.parm` keeps
  generic `AIRSPEED_*` defaults with `ARSPD_TYPE` disabled; overlays/campaign
  files introduce Gazebo sensor enablement and lane-specific or high-wind
  overrides;
- records SHA-256 provenance for the recovered old comparison stack in the
  config index and in a recovered-stack `SHA256SUMS` evidence manifest;
- makes the generated old-vs-high-wind postprocessing metadata include
  parameter-stack SHA-256 rows, not only named paths;
- classifies `run_one_og.py` as a legacy CTE compatibility caller with the same
  base -> airspeed -> optional local-override stack behavior when invoked;
- replaces shorthand command notes with replayable material scan commands and
  observed results below.

## Gap Assessment

Phase 4 work already present before this pass:

- `assets/` already separated models, worlds, and missions from code;
- `config/` already separated vehicle, overlay, campaign, and archive homes;
- historical recovered parameter stacks already lived under
  `evidence/curated_logs/recovered_param_stacks/`;
- `.private/config/plane_params.local.parm` already existed as ignored local
  state and the private-overlay policy already said private config is not shared
  truth;
- the compatibility launcher already encoded plane stack order comments and the
  `src/SIM_ARD_GAW` symlink bridge already pointed to new asset/config homes;
- Phase 2 and Phase 3 evidence/docs already proved or qualified the core runtime
  lanes and the compatibility boundary.

Missing or stale items found before Phase 4 doc/index edits:

- no canonical model/world/mission asset index existed;
- no canonical parameter/config index covered shared config, archives, local
  policy, hashes, and recovered historical stacks together;
- launch-target docs did not expose the actual base/overlay/local stack table;
- vehicle and campaign docs did not yet point at the explicit config ownership
  split for Phase 4;
- `config/README.md` still described active files as if they lived directly in
  the config root;
- the Phase 4 runbook exit gate was too short for the required hidden-local,
  stale-claim, and evidence-aware checks;
- `build_square_postprocessing_report.py` still looked for the recovered 009
  stack under active compatibility `config/` instead of curated evidence.

Ambiguities identified:

- vehicle bases, overlays, campaign files, archives, local-only overrides, and
  recovered historical stacks all affect comparisons differently and needed
  separate index categories;
- most plane compatibility launch paths append the observed local plane override
  when it exists, while `plane-rebuild` and Copter do not;
- current compatibility launcher and CTE campaign scripts still resolve many
  canonical asset/config homes through `src/SIM_ARD_GAW` symlinks;
- non-core indexed lanes remain not yet runtime verified by current evidence.

## Files Changed

- `governance/runbooks/phase_4_config_asset_normalization.md`
- `config/README.md`
- `docs/architecture/workspace_map.md`
- `docs/operations/launch_targets.md`
- `docs/vehicles/status.md`
- `docs/campaigns/wind_matrix.md`
- `.ai/index.md`
- `.ai/current.md`
- `.ai/issues/open.md`
- `src/sim_ard_gaw/compat_scripts/build_square_postprocessing_report.py`
- `evidence/indexes/asset_index.md`
- `evidence/indexes/parameter_config_index.md`
- `evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/SHA256SUMS`
- `evidence/reports/PHASE_4_CONFIG_ASSETS_2026-05-21.md`

## Commands Run

- `git status --short`
- `rg --files evidence/reports -g 'PHASE_*.md'`
- `find evidence/indexes -maxdepth 3 -type f`
- `rg --files assets config evidence/curated_logs/recovered_param_stacks src/sim_ard_gaw/compat_scripts src/SIM_ARD_GAW`
- `find src/SIM_ARD_GAW -maxdepth 3 -type l -ls`
- `rg -n "\\.parm|\\.waypoints|assets/(models|worlds|missions)|config/(vehicles|overlays|campaigns|archive)|\\.private/config|SIM_ARD_GAW/(config|models|worlds|missions)" src/sim_ard_gaw/compat_scripts scripts docs config assets .ai --glob '!docs/archive/**'`
- `rg -n "param_file|param_files|param hash|sha256|param_hash|param_stack" src/sim_ard_gaw/compat_scripts/run_one.py src/sim_ard_gaw/compat_scripts/run_matrix.py src/sim_ard_gaw/compat_scripts/test_suite --glob '*.py'`
- `rg -n "run_one_og|run_one\\.py|run_matrix\\.py|run_matrix_round_robin" docs evidence .ai governance src/sim_ard_gaw/compat_scripts/test_suite --glob '!docs/archive/**' --glob '!governance/audits/**'`
- `find assets/models -mindepth 1 -maxdepth 1 -type d -print`
- `find assets/worlds -type f -name '*.sdf' -print`
- `find assets/missions -type f -name '*.waypoints' -print`
- `find config/vehicles config/overlays config/campaigns config/archive -type f -name '*.parm' -print`
- `sha256sum config/vehicles/plane_base.parm config/vehicles/plane_params_rebuild.parm config/vehicles/copter_params.parm config/overlays/plane_airspeed.parm config/overlays/plane_lidar.parm config/overlays/staircase_plane_params.parm config/campaigns/mini_talon_airspeed_lidar/plane_full.parm config/campaigns/mini_talon_altitude_wind/plane_full.parm`
- `find evidence/curated_logs/recovered_param_stacks -type f -print`
- `sha256sum evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/src/SIM_ARD_GAW/config/plane_base.parm evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/src/SIM_ARD_GAW/config/plane_airspeed.parm evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/private_overlay/config/plane_params.local.parm`
- `sha256sum -c SHA256SUMS` from
  `evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/`
- `find .private/config -maxdepth 3 -type f -print`
- `find config -path '*/.private' -print -o -path '*/.private/*' -print`
- `rg -n "ARSPD_TYPE[ =]+100.*plane_base|plane_base.*ARSPD_TYPE[ =]+100|\\.private/config.*(required|canonical|shared)|compatibility.*(final|new ownership model)|final.*src/SIM_ARD_GAW|src/SIM_ARD_GAW.*final" README.md docs .ai governance --glob '!docs/archive/**' --glob '!governance/audits/**' --glob '!.ai/audits/**'`
- `rg -n "Airspeed values|airspeed values|sensor-neutral|ARSPD_TYPE 100|generic AIRSPEED|plane_base\\.parm.*airspeed" docs evidence config .ai governance --glob '!docs/archive/**' --glob '!governance/audits/**'`
- `make doctor`
- `scripts/maintenance/validate_structure.sh`
- `python -m compileall -q src/sim_ard_gaw/compat_scripts/build_square_postprocessing_report.py`
- `pyright src/sim_ard_gaw/compat_scripts/build_square_postprocessing_report.py`

## Inventory Counts

Asset counts:

| Category | Count | Count basis |
| --- | ---: | --- |
| Models | 10 | First-level model directories under `assets/models/`. |
| Worlds | 14 | `.sdf` files under `assets/worlds/`. |
| Missions | 6 | `.waypoints` files under `assets/missions/`. |

Config counts:

| Category | Count | Count basis |
| --- | ---: | --- |
| Vehicle configs | 3 | `.parm` files under `config/vehicles/`. |
| Overlays | 3 | `.parm` files under `config/overlays/`. |
| Campaign configs | 2 | `.parm` files under `config/campaigns/`. |
| Archived configs | 2 | `.parm` files under `config/archive/`. |

Canonical inventories:

- `evidence/indexes/asset_index.md`
- `evidence/indexes/parameter_config_index.md`

## Parameter Stack Table

| Lane / caller | Shared stack in applied order | Local override result |
| --- | --- | --- |
| `plane` | `config/vehicles/plane_base.parm` | Local plane override appended if present. |
| `plane-cte` / `plane-airspeed` | `config/vehicles/plane_base.parm` -> `config/overlays/plane_airspeed.parm` | Local plane override appended if present. |
| `plane-lidar` | `config/vehicles/plane_base.parm` -> `config/overlays/plane_lidar.parm` | Local plane override appended if present. |
| `plane-staircase` | `config/vehicles/plane_base.parm` -> `config/overlays/plane_lidar.parm` -> `config/overlays/staircase_plane_params.parm` | Local plane override appended if present. |
| `plane-airspeed-lidar` | `config/vehicles/plane_base.parm` -> `config/campaigns/mini_talon_airspeed_lidar/plane_full.parm` | Local plane override appended if present. |
| `plane-altitude-wind` | `config/vehicles/plane_base.parm` -> `config/campaigns/mini_talon_altitude_wind/plane_full.parm` | Local plane override appended if present. |
| `plane-rebuild` | `config/vehicles/plane_params_rebuild.parm` | Local plane override skipped. |
| `copter` / `copter-lidar` | `config/vehicles/copter_params.parm` | No `.private` config append in launcher. |
| Current CTE `run_one.py` / `run_matrix.py` | `config/vehicles/plane_base.parm` -> `config/overlays/plane_airspeed.parm` | Default caller appends local plane override when present unless disabled or replaced. |
| Legacy CTE `run_one_og.py` caller | `config/vehicles/plane_base.parm` -> `config/overlays/plane_airspeed.parm` | Legacy compatibility-root peer appends local plane override when invoked. |

`config/vehicles/plane_base.parm` is sensor-neutral for airspeed enablement: it
keeps generic `AIRSPEED_*` defaults and records `ARSPD_TYPE 0`. The airspeed
overlay or campaign lane files introduce Gazebo `ARSPD_TYPE 100` sensor
enablement and lane-specific or high-wind overrides.

## Shared Active/Campaign Hashes

| File | SHA-256 |
| --- | --- |
| `config/vehicles/plane_base.parm` | `8941fa559f762fb4111c150db04e4d36c0ad05d680f8cff2cd28219ba8ceaa01` |
| `config/vehicles/plane_params_rebuild.parm` | `c5d38923b87daed0cb495d85c72ce8023721e089313ed5d44f1ad7375b2ece3e` |
| `config/vehicles/copter_params.parm` | `fd12b0f6398de5438a1b0d3f2638c5f1b9e682bb672a03ea81fc4d005fe38579` |
| `config/overlays/plane_airspeed.parm` | `ebf99c7e5b65e24ddfacb0bafa2295579c9cb073600c8548f6050f10d778e577` |
| `config/overlays/plane_lidar.parm` | `5837ebe4c1e7e23ee7d0343de2318a2044f924ea4f8d5f22d05b01582f77210b` |
| `config/overlays/staircase_plane_params.parm` | `1b045dde27f2fae2dffbeeedaa695e2b8246a0b11a3397ffe7b6ef0f8acd24a1` |
| `config/campaigns/mini_talon_airspeed_lidar/plane_full.parm` | `32f38f58cd90dc8bd5522612a92eec747a90326108fa2d9ddc05635dca9a8b33` |
| `config/campaigns/mini_talon_altitude_wind/plane_full.parm` | `0ff9bc7610a9beb9d29bc2256abd79a8e34c2c6a09554558a37d9a1d6681fe87` |

## Recovered Comparison Hashes

Recovered old-stack comparison inputs remain historical evidence, not active
`config/`. Their evidence-side hash manifest is:

`evidence/curated_logs/recovered_param_stacks/recovered_009_param_stack_7439211/009_param_stack_7439211/SHA256SUMS`

| Historical comparison input | SHA-256 |
| --- | --- |
| `.../src/SIM_ARD_GAW/config/plane_base.parm` | `bbeab1e85c43c10065c01cf47144d8c436df9f70494ad1d10376f07c948c5038` |
| `.../src/SIM_ARD_GAW/config/plane_airspeed.parm` | `fdb665e2f19bc0025bea7c97c97509aa958d8a384164806775174dee7bb667d4` |
| `.../private_overlay/config/plane_params.local.parm` | `22cca998572217d9fc44fdc62132c842af4ed6b19fd4277804becc3a77715c4d` |

`build_square_postprocessing_report.py` now emits `param_stack_sha256` rows
with path and SHA-256 values for both `old_recovered` and `later_high_wind`
comparison stacks.

## Local Override Policy Check

Result: PASS for policy classification.

- `.private/config/plane_params.local.parm` was observed as local-only state on
  this machine.
- `docs/operations/private_overlays.md` forbids required shared config in
  `.private/`.
- The compatibility plane launcher checks whether the file exists before
  appending it; it prints a no-local-override message when absent.
- `plane-rebuild` deliberately skips the local plane override.
- Copter launcher stacks use shared Copter config only.
- Current CTE campaign callers can suppress the default local plane override via
  `--no-param-local` or replace the explicit param stack.
- Legacy `run_one_og.py` is a compatibility caller and appends the same local
  override when invoked.

## Hidden Local Dependency Findings

- Base workspace structure health is not defined by `.private/`; structure
  policy keeps that directory ignored and local-only.
- The observed local override materially can change current Plane launch and CTE
  campaign comparisons because default runtime code appends it when present.
  That is an evidence dependency/risk unless a run records the effective stack
  and hashes or opts out explicitly.
- Historical recovered local override evidence is preserved under
  `evidence/curated_logs/recovered_param_stacks/.../private_overlay/`, not as a
  canonical `.private` default.

Active `config/` nested `.private` scan:

- Command: `find config -path '*/.private' -print -o -path '*/.private/*' -print`
- Result: PASS; no nested `.private` paths were returned.

## Runtime Compatibility References

- `src/SIM_ARD_GAW/config`, `models`, `worlds`, and `missions` are compatibility
  symlinks back to `config/` and `assets/`.
- `src/sim_ard_gaw/compat_scripts/launch.sh` still names
  `SIM_ARD_GAW_DIR` for plane config, worlds, models, missions, and helper
  scripts.
- Current CTE campaign scripts `run_one.py` and `run_matrix.py`, plus legacy
  peer `run_one_og.py`, still name compatibility asset/config roots while their
  canonical owners are indexed here.
- Phase 4 documented the bridge; it did not retire it.

## References And Docs Updated

- Workspace map now links the asset and parameter indexes and explains historical
  evidence vs local override homes.
- Launch-target docs now expose stack order for relevant launch lanes and CTE
  campaign callers.
- Vehicle status docs separate base vehicle config, overlays, campaign config,
  rebuild config, and local plane overrides.
- Wind-matrix docs retain the parameter hash requirement and state the local
  override boundary for comparisons.
- Recovered old-stack comparison inputs now carry an evidence-side SHA-256
  manifest and generated report metadata records per-file stack hashes.
- AI entry points now link the Phase 4 indexes and report.

## Validation Results

- `make doctor`: PASS - `STRUCTURE VALIDATION PASSED`.
- `scripts/maintenance/validate_structure.sh`: PASS - same structure and stale
  reference result.
- `python -m compileall -q src/sim_ard_gaw/compat_scripts/build_square_postprocessing_report.py`:
  PASS.
- Recovered stack manifest check:
  `sha256sum -c SHA256SUMS` from the recovered `009_param_stack_7439211`
  root: PASS for all three comparison input files.
- Optional Python diagnostic check:
  `pyright src/sim_ard_gaw/compat_scripts/build_square_postprocessing_report.py`
  reported existing missing-import diagnostics for `matplotlib`/`numpy` plus
  pre-existing type diagnostics elsewhere in the postprocessing script. No
  diagnostic pointed at the new parameter-stack SHA metadata helper.
- Focused stale-claim scan command:

  ```bash
  rg -n "ARSPD_TYPE[ =]+100.*plane_base|plane_base.*ARSPD_TYPE[ =]+100|\.private/config.*(required|canonical|shared)|compatibility.*(final|new ownership model)|final.*src/SIM_ARD_GAW|src/SIM_ARD_GAW.*final" README.md docs .ai governance --glob '!docs/archive/**' --glob '!governance/audits/**' --glob '!.ai/audits/**'
  ```

  Result: one qualified negative hit,
  `docs/campaigns/wind_matrix.md:12:a compatibility state, not the final campaign architecture.`
- Focused Plane base/airspeed truth scan command:

  ```bash
  rg -n "Airspeed values|airspeed values|sensor-neutral|ARSPD_TYPE 100|generic AIRSPEED|plane_base\.parm.*airspeed" docs evidence config .ai governance --glob '!docs/archive/**' --glob '!governance/audits/**'
  ```

  Result: the Phase 4 sources now state the generic-base-default vs
  sensor-enablement/override boundary explicitly; no broad "all airspeed
  values live in overlays" Phase 4 claim remains.
- First validation pass caught two extra literal legacy-path mentions added to
  canonical AI/launch docs; those lines were narrowed to point back to the
  workspace-map compatibility explanation before the final passing validation.

## Unresolved Ambiguities And Blockers

- Non-core launch assets and config stacks for `plane-staircase`,
  `plane-airspeed-lidar`, `plane-altitude-wind`, and `plane-rebuild` remain
  indexed but not runtime verified by current evidence.
- `mini_talon_landing_gear` remains present without a current launch-lane
  reference found in this pass.
- Compatibility asset/config access through `src/SIM_ARD_GAW` remains until the
  later compatibility-retirement phase.
- Current CTE campaign param hashing is still a hardening blocker; Phase 4
  indexed shared and recovered comparison hashes but did not perform Phase 5
  campaign refactor.

## Conclusion

Phase 4 status: PASS.

The inventories, config categories, stack boundaries, hashes, local override
policy, hidden dependency risk, and remaining compatibility references are now
explicit. Phase 4 closes with indexed assets and parameter stacks without
claiming Phase 5 campaign parity, Phase 7 cutover, or Phase 8 compatibility
retirement.
