# Phase 5 Campaign And Test Migration

Date/time: 2026-05-21T11:46:42+03:00

Timezone: Africa/Cairo / EEST (+03:00)

## Scope

Phase 5 hardens the wind-matrix campaign and the evolving `test_suite`
compatibility architecture without cutting over or retiring legacy runners.
This report was opened before campaign code edits so the current-state gap
assessment stays with the Phase 5 evidence record.

The old workspace was not modified. Phase 5 does not perform cutover or
compatibility retirement.

## Pre-Edit Current-State Gap Assessment

Reviewed before campaign code edits:

- Phase 5 and full migration runbooks plus change-control, workspace,
  documentation, and evidence standards;
- `.ai` index/current/open-issue state;
- wind-matrix, launch-target, and workspace-map docs;
- Phase 0 through Phase 4 dated evidence reports;
- compatibility runners `run_one.py`, `run_matrix.py`, and
  `run_matrix_round_robin.py`;
- the Phase-1 `test_suite` wrapper CLI/core/plugin layer;
- existing test homes and curated wind-matrix manifests.

Compatibility behaviors to preserve:

- `run_one.py`, `run_matrix.py`, and `run_matrix_round_robin.py` remain runnable
  compatibility entrypoints;
- Phase-1 `test_suite` wrappers continue delegating wind-matrix attempt bodies
  to `run_one.run_one(...)`;
- legacy manifest `status` values such as `success_full` and
  `success_square_only` remain readable and are not broken by Phase 5 fields;
- accepted-run counting and `run_XX` alias behavior remain tied to legacy
  manifest semantics until later parity evidence governs a transition.

| Phase 5 item | Assessment before edits | Evidence from inspection |
| --- | --- | --- |
| Legacy runners and wrappers | Already implemented and must be retained | `compat_scripts/` runners and `test_suite` wrapper/plugin files exist. |
| Existing tests | Incomplete | Only `tests/parity/test_phase1_parity.py` existed under `tests/`. |
| Manifest update discipline | Partially implemented | `run_one.write_text_atomic(...)` writes JSON/CSV atomically, but no campaign-root manifest lock was found. |
| Terminal status taxonomy | Partially implemented | Wrapper enums map `failed_analysis`; legacy manifests still expose legacy `status` strings with no additive canonical terminal-status field. |
| Mission contract validation | Missing | `run_one.py` hardcodes square/loiter/final sequence constants for one mission layout without pre-analysis contract validation. |
| SDF wind mutation | Unsafe | `run_matrix.write_static_wind_world(...)` uses regex substitution on `<wind><linear_velocity>`. |
| Wind verification | Incomplete for new evidence | Wind echo verification exists but defaults off unless `SIM_ARD_GAW_STRICT_WIND_ECHO_VERIFY=1`; SDF wind parsing is regex-based. |
| Parameter provenance | Incomplete | Run config records effective parameter file paths; per-attempt content hashes were not written with run config/manifest provenance. |
| Campaign architecture home | Missing owned Phase 5 modules | `src/sim_ard_gaw/campaigns/` had no owned migration modules before this pass. |
| Curated campaign references | Already present | Curated manifests exist for `017_params_old_009_matrix_r3_plugin_fixed`, `018_New_Param_Full_CTE_Matrix`, and `phase1_live_rr_parity_test`. |

## Commands Run So Far

- `git status --short`
- `rg --files ...` inventory scans across governance, docs, evidence, campaign,
  and tests homes
- `sed -n ...` reads of the Phase 5/full runbooks, standards, AI pointers,
  canonical campaign/runtime docs, prior Phase 0-4 reports, compatibility
  runners, `test_suite` wrappers, existing parity tests, wind world, mission,
  Makefile, and `pyproject.toml`
- `python3 /home/ahmed/.codex/skills/python-lsp/scripts/inspect_python_lsp.py /home/ahmed/ardupilot_workspace_next`
- `rg -n "lock|failed_analysis|status|mission|wind|sdf|xml|hash|param|manifest|verify|verification" ...`

## Implementation Summary

Campaign architecture before Phase 5:

- wind-matrix execution was owned by compatibility runners and Phase-1
  `test_suite` wrappers that delegate attempt bodies to `run_one.run_one(...)`;
- `src/sim_ard_gaw/campaigns/` contained compatibility links for the runners,
  but no owned safety helpers;
- the legacy runner already had atomic manifest file replacement and an
  analysis downgrade path that could set `failed_analysis`.

Campaign architecture after Phase 5:

- compatibility runners and Phase-1 wrappers remain the runnable boundary;
- owned helpers under `src/sim_ard_gaw/campaigns/` provide manifest locking,
  canonical terminal taxonomy, parameter-file provenance, mission-contract
  validation, and XML/SDF world wind handling;
- legacy manifest `status` values stay intact while `terminal_status`,
  `mission_contract`, and `param_file_provenance` are additive manifest fields;
- matrix and wrapper CLIs validate the mission contract before stack launch,
  and the delegated attempt validates again before relying on the known layout.

## Files Changed

Primary code and tests:

- `src/sim_ard_gaw/campaigns/{manifest_safety,status,provenance,mission_contract,wind_world}.py`
- `src/sim_ard_gaw/compat_scripts/run_one.py`
- `src/sim_ard_gaw/compat_scripts/run_matrix.py`
- `src/sim_ard_gaw/compat_scripts/run_matrix_round_robin.py`
- `src/sim_ard_gaw/compat_scripts/test_suite/cli/run_suite.py`
- `src/sim_ard_gaw/compat_scripts/test_suite/cli/run_round_robin.py`
- `src/sim_ard_gaw/compat_scripts/test_suite/plugins/wind_matrix/plugin.py`
- `src/sim_ard_gaw/compat_scripts/test_suite/ARCHITECTURE.md`
- `tests/unit/test_campaign_manifest_safety.py`
- `tests/unit/test_campaign_contracts.py`
- `tests/unit/test_wind_world_safety.py`
- `tests/integration/test_phase5_wrapper_manifest_flow.py`
- `tests/parity/test_phase1_parity.py`
- `tests/fixtures/campaigns/`
- `pyproject.toml`

Docs, governance, AI, and evidence:

- `docs/campaigns/wind_matrix.md`
- `docs/architecture/workspace_map.md`
- `docs/operations/launch_targets.md`
- `docs/operations/migration_status.md`
- `docs/operations/sitl_gazebo_runtime.md`
- `src/sim_ard_gaw/README.md`
- `.ai/index.md`
- `.ai/current.md`
- `.ai/issues/open.md`
- `governance/runbooks/phase_5_campaign_test_migration.md`
- `governance/decisions/ADR-0003-phase5-campaign-safety-contract.md`
- `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`
- `evidence/curated_logs/phase5_tiny_rr_20260521/`
- `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/`
- `evidence/reports/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`

## Compatibility Runner Status

| Surface | Phase 5 status |
| --- | --- |
| `run_one.py` | Retained; now locks attempt manifest work, validates the mission contract, records additive terminal/provenance metadata, and uses XML SDF wind parsing. |
| `run_matrix.py` | Retained; XML/SDF static world wind transform replaces regex mutation and startup validates mission contract. |
| `run_matrix_round_robin.py` | Retained; startup validates mission contract and initial manifest update is lock-guarded. |
| Phase-1 `test_suite` wrappers | Retained; wrapper startup validates mission contract and lock-guards initial manifest update. |

No Phase 7 cutover or Phase 8 compatibility retirement occurred.

## Safety Results

| Gate | Implementation and test result |
| --- | --- |
| Manifest lock | `campaign_manifest_lock(...)` uses a non-blocking campaign-root `flock` lock around unsafe compatibility attempt and initial manifest transactions. Unit coverage now drives two processes through the real read/mutate/save manifest transaction and proves the conflicting writer raises instead of allocating a second attempt. |
| Manifest update behavior | Existing atomic JSON/CSV replacement remains in `run_one.write_text_atomic(...)`; Phase 5 lock guards read/mutate/save attempt work. |
| Terminal taxonomy | Added canonical `terminal_status` taxonomy with `success`, `partial`, `failed`, `failed_analysis`, `error`, and `interrupted` without breaking legacy `status`. Wrapper translation now treats only legacy analysis status `done` as successful, so `failed:*`, `partial:*`, and `not_run` analysis records do not hide analysis failure. Unit and integration tests cover the mapping. |
| Mission contract | Added the explicit square mission contract with required item count, analyzer-sensitive sequence commands, supported location frames, 20 square segments at 500 m +/- 25 m, and mission SHA-256. Unit tests cover valid and invalid layout, geometry, and frame cases; matrix/wrapper startup validates before stack launch. |
| XML/SDF wind transform | Static world mutation and SDF wind parsing use structured XML. Unit tests cover target mutation, missing/ambiguous target failure, and nested wrong-node preservation; parity test covers the known world. |
| Strict wind verification | Runtime topic echo verification now defaults strict for campaign runs. Unit test covers parsing and policy; the tiny campaign `wind_injection.json` records `strict_echo_verification: true`. |
| Parameter provenance | Effective param files are hashed into run config and manifest rows with path, size, and SHA-256. Unit test covers hashing; the tiny proof records the shared base and airspeed overlay hashes, and the invalidated first `4,4` comparison still records the read-only local overlay hash used by that audit-gap remediation attempt. |

## Test And Validation Results

| Check | Result |
| --- | --- |
| Targeted unit tests | PASS: `/home/ahmed/ardupilot_workspace/env/bin/python3 -m unittest tests/unit/test_campaign_manifest_safety.py tests/unit/test_campaign_contracts.py tests/unit/test_wind_world_safety.py` ran 13 tests. |
| Targeted integration tests | PASS: `/home/ahmed/ardupilot_workspace/env/bin/python3 -m unittest tests/integration/test_phase5_wrapper_manifest_flow.py` ran 3 tests. |
| Parity tests | PASS: `make test-parity` ran 4 tests, including known-world XML static-wind parity. |
| Focused pyright | PASS for the touched campaign helper modules, wrapper plugin, and Phase 5 unit/integration tests with `/home/ahmed/.local/bin/pyright`. |
| Python compile | PASS: `python3 -m compileall -q` on the new campaign helpers, touched compatibility scripts, and tests. |
| CLI help/import | PASS for `run_matrix.py --help`, `test_suite.cli.run_round_robin --help`, and direct imports of compatibility runners, wrapper CLI modules, and the XML wind helper. |
| `make doctor` | PASS: structure validator completed with the expected allowlisted canonical references. |
| `scripts/maintenance/validate_structure.sh` | PASS. |
| Raw log leakage scan | PASS: explicit scan outside `.git`, `var`, `.private`, `src/ardupilot`, and `src/SITL_Models` returned no raw `.BIN`, `.tlog`, or `.tlog.raw` files. |
| Stale wind-matrix claims scan | PASS: focused `rg` review of canonical docs/AI found Phase 5 state and no cutover/full-matrix claim. |

`python3` from the system interpreter does not have `pymavlink`, so focused
tests that import `run_one.py` were rerun with the workspace dependency-bearing
virtualenv selected by the Makefile fallback:
`/home/ahmed/ardupilot_workspace/env/bin/python3`.

## Tiny Campaign Parity

Result: PASS.

Bounded successful command:

```text
timeout 2400s bash -lc "PYTHONPATH=src:src/sim_ard_gaw/compat_scripts /home/ahmed/ardupilot_workspace/env/bin/python3 -m test_suite.cli.run_round_robin --x-values 0 --y-values 0 --focus-combo wind_x_00_y_00 --runs-per-combo 1 --max-passes 1 --slot-minutes 30 --accept-square-only --require-analysis --no-param-local --campaign-root var/runs/phase5_tiny_rr_20260521_escalated"
```

Scope and outcome:

- one wrapper-driven `wind_x_00_y_00` round-robin case;
- one target run, one pass, shared param stack only;
- mission upload and mission identity verification passed for 30 items;
- runtime topic wind strict echo verification passed;
- square and loiter acceptance completed early before landing;
- analysis completed and wrote `run_summary.json`;
- final manifest status is legacy `success_square_only` with additive terminal
  status `partial`;
- duration was 812.7 s and the suite reported `all_cases_complete`.

The same bounded command was first attempted inside the restricted sandbox at
`var/runs/phase5_tiny_rr_20260521/`. It stopped during SITL bring-up before an
attempt row was allocated because MAVProxy could not open the local SITL TCP
link (`Operation not permitted`). The successful retry ran outside that sandbox
network boundary and remains bounded by the same one-case scope and timeout.

Production-reference comparison remediation: INVALIDATED FOR WIND PARITY.

The strict-review audit-gap remediation also ran the matching bounded Phase 1
live round-robin shape against the new workspace:

```text
timeout 2700s bash -lc 'PYTHONPATH=src:src/sim_ard_gaw/compat_scripts /home/ahmed/ardupilot_workspace/env/bin/python3 -m test_suite.cli.run_round_robin --x-values 4 --y-values 4 --focus-combo wind_x_04_y_04 --runs-per-combo 1 --max-passes 1 --slot-minutes 40 --param-local /home/ahmed/ardupilot_workspace/.private/config/plane_params.local.parm --campaign-root var/runs/phase5_live_rr_parity_remediation_20260521'
```

The command still exercises the Phase 5 audit-gap hardening work: one wrapper
case completed with legacy `success_full`, analysis status `done`, a canonical
terminal status, strict Gazebo topic echo verification, and parameter-stack
hash provenance. It is not valid wind-parity proof. Its
`wind_x_04_y_04/runs/attempt_001/run_config.json` records only
`/usr/local/lib/ardupilot_gazebo` in `GZ_SIM_SYSTEM_PLUGIN_PATH` and records
the workspace plugin
`build/ardupilot_gazebo/libArduPilotPlugin.so` as absent at run time. Gazebo
therefore used the stale installed plugin fallback. The resulting BIN reports
`XKF2 C=0` mean wind `VWN=0.364`, `VWE=0.382` for the requested `4,4` case,
not the known-good production plugin-fixed behavior.

The read-only comparison anchors were the promoted Phase 1 manifest at
`evidence/curated_logs/phase1_live_rr_parity_test/manifest.json` and the old
workspace run config inspected under
`/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/phase1_live_rr_parity_test/`.
The manifest-shape comparison remains useful for the Phase 5 runtime-contract
audit, but it did not prove ArduPilot-side injected-wind parity. The invalidated
comparison output and its curated copy are retained as diagnostic evidence so
future reviews can see the fallback failure instead of mistaking Gazebo topic
echo for end-to-end wind proof.

Workspace-plugin recheck: PASS.

After the fallback was diagnosed, `build/ardupilot_gazebo` was configured and
built in `workspace_next`:

```text
cmake -S src/ardupilot_gazebo -B build/ardupilot_gazebo -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build/ardupilot_gazebo -j2
```

The corrected bounded recheck used the same `4,4` one-case shape with the next
workspace interpreter and the same read-only local parameter overlay:

```text
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts /home/ahmed/ardupilot_workspace_next/env/bin/python3 -m test_suite.cli.run_round_robin --x-values 4 --y-values 4 --focus-combo wind_x_04_y_04 --runs-per-combo 1 --max-passes 1 --slot-minutes 40 --param-local /home/ahmed/ardupilot_workspace/.private/config/plane_params.local.parm --campaign-root var/runs/phase5_live_rr_workspace_plugin_recheck_20260521
```

The user-completed successful attempt is
`var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/wind_x_04_y_04/runs/attempt_002/`.
Its `run_config.json` records
`/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo` before the
`/usr/local/lib/ardupilot_gazebo` fallback and records the workspace plugin
hash `1d4089bb6306ecc602e484e9b4e3e77dfb7ecf6649a4292ba872f6d420415fc0`.
Its BIN reports `XKF2 C=0` mean wind `VWN=3.845`, `VWE=3.882`; the production
plugin-fixed `4,4` reference reports `VWN=3.909`, `VWE=3.965`.

The detailed failure analysis, file paths, hashes, and recheck comparison are
recorded in
`governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`.

## Output And Evidence Locations

- Raw successful run output:
  `var/runs/phase5_tiny_rr_20260521_escalated/`
- Restricted-sandbox failed bring-up output:
  `var/runs/phase5_tiny_rr_20260521/`
- Curated tiny result:
  `evidence/curated_logs/phase5_tiny_rr_20260521/`
- Raw production-reference comparison remediation output:
  `var/runs/phase5_live_rr_parity_remediation_20260521/` (invalidated as
  wind-parity proof; retained as plugin-fallback diagnostic evidence)
- Curated production-reference comparison remediation artifacts:
  `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/`
  (invalidated as wind-parity proof)
- Raw corrected workspace-plugin recheck output:
  `var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/`
- Corrected workspace-plugin recheck attempt used for comparison:
  `var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/wind_x_04_y_04/runs/attempt_002/`
- Production-reference comparison manifest:
  `evidence/curated_logs/phase1_live_rr_parity_test/manifest.json`
- Plugin fallback incident audit:
  `governance/audits/2026-05-21_phase5_gazebo_plugin_fallback_incident.md`
- Phase 5 report:
  `evidence/reports/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`

Raw `.BIN`, `.tlog`, simulator logs, and SITL state remain under `var/`.

## Commands Run

Key Phase 5 commands were:

- the pre-edit `sed`, `rg`, and `find` inspection commands listed above;
- `python3 /home/ahmed/.codex/skills/python-lsp/scripts/inspect_python_lsp.py /home/ahmed/ardupilot_workspace_next`;
- focused new unit, integration, parity, compile, pyright, CLI help, and import
  checks recorded in the validation table;
- read-only production-reference manifest/run-config comparison checks and
  `git -C /home/ahmed/ardupilot_workspace status --short`, which still showed
  only the pre-existing `.private/backup.log` dirty state;
- `make doctor`;
- `scripts/maintenance/validate_structure.sh`;
- `make test-parity`;
- explicit raw-log leakage scan and focused canonical wind-matrix claim scan;
- bounded tiny campaign commands, the bounded production-reference comparison
  remediation command, the workspace-plugin build and corrected recheck, and
  `scripts/ops/launch.sh cleanup`;
- curated evidence promotion from the successful `var/` result into
  `evidence/curated_logs/phase5_tiny_rr_20260521/` and
  `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/`;
  the latter is retained as invalidated plugin-fallback diagnostic evidence.

## Unresolved Blockers

- Full wind-matrix campaign evidence beyond the bounded one-case Phase 5 tiny
  result is still future work.
- The campaign can still fall back to the stale installed Gazebo plugin under
  `/usr/local/lib/ardupilot_gazebo` when
  `build/ardupilot_gazebo/libArduPilotPlugin.so` is absent. The corrected
  recheck proves the workspace plugin selection fixes the observed `4,4` wind
  mismatch, but Phase 5 does not yet fail closed on missing workspace plugin
  builds.
- Existing non-Phase-5 migration issues remain in `.ai/issues/open.md`,
  including cleanup process scoping, non-core launch target verification, the
  Copter LiDAR obstacle-return gap, production dirty state, cutover, and
  compatibility retirement.

## Conclusion

Phase 5 status: PASS.

The exit gate is met with code, unit/integration/parity coverage, validation,
bounded tiny campaign evidence, and curated proof. The old workspace was not
modified. Phase 5 did not perform cutover or compatibility retirement.
