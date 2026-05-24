# Phase 8 Compatibility Retirement

Date/time: 2026-05-22T02:33:46+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Conclusion: PARTIAL PASS WITH RETAINED COMPATIBILITY

## Scope

Phase 8 audited the migration compatibility surfaces in
`/home/ahmed/ardupilot_workspace_next`, hardened the Phase 8 runbook before
runtime edits, retired the root legacy symlink bridge from active runtime path
resolution, updated docs and AI state for the narrower compatibility boundary,
and kept the still-unproven campaign and organized runtime views in place with
explicit blockers.

The old workspace was not modified.

## Review Remediation

The first Phase 8 closeout did not pass review. The review found that retained
manual and sequential wind-matrix routes could still discover SITL `.BIN`
output through `src/ardupilot/logs`, launcher help still printed commands from
the retired co-located script layout, canonical docs still described the
removed campaign log bridge, and stale-reference validation still allowlisted
retired current-truth bridge claims.

This report was updated after remediation. Retained manual/default CTE BIN
discovery now follows the launcher's `var/runs/sitl/plane-cte/` `--use-dir`,
sequential `run_matrix.py` and suite wind-matrix defaults launch SITL with
explicit isolated `var/` state, help-surface tests pin governed operator
commands, canonical docs describe direct `var/` routing, and the obsolete
validator allowlist claims are removed.

## Prior Phase 7 Status

Phase 7 cutover remains `BLOCKED` in
`evidence/reports/CUTOVER_2026-05-21.md`. The 2026-05-22 policy update in that
report and `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`
requires fresh shadow-parity and representative workflow proof before cutover
can be reconsidered. No accepted cutover ADR exists.

That boundary makes Phase 8 conservative: this pass retires runtime path
dependencies that are directly replaceable now and does not claim that retained
campaign runner ownership is already replaced.

## Compatibility Audit

### Bridge Inventory Before Edits

| Surface | Before state | Dependency finding | Phase 8 classification |
| --- | --- | --- | --- |
| root config bridge | symlink to `config/` | launcher and campaign path constants used it | retire after direct config paths |
| root model bridge | symlink to `assets/models/` | launcher and wind runtime resource paths used it | retire after direct asset paths |
| root world bridge | symlink to `assets/worlds/` | launcher and matrix world paths used it | retire after direct asset paths |
| root mission bridge | symlink to `assets/missions/` | launcher and CTE mission path used it | retire after direct asset paths |
| root scripts bridge | symlink to `src/sim_ard_gaw/compat_scripts/` | launcher and runners used helper script paths through it | retire after owned runtime-facing helper paths |
| root logs bridge | symlink to `var/logs/` | campaign and analysis defaults used it | retire after direct `var/` routing |
| `compat_scripts/` | real retained implementation tree | wind-matrix runners, `test_suite`, launch implementation, bridge and analysis implementations still live here | retain with blocker |
| organized launch view | symlink to compatibility launcher | operator entrypoint already routes through this view | retain view until implementation ownership is moved |
| organized bridge views | symlinks to compatibility bridge scripts | launch now targets bridge view paths directly | retain with blocker |
| organized analysis views | symlinks to compatibility analysis scripts | runners now target analysis view paths directly | retain with blocker |
| organized wind-matrix campaign views | symlinks to compatibility runners | Phase 5 parity still treats runners as compatibility owners | retain with blocker |
| organized `test_suite` campaign view | symlink to compatibility suite | wrappers still import legacy runners through compatibility chokepoint | retain with blocker |

### Dependency Scan Summary

Before edits, direct old-root runtime dependencies were found in:

- `src/sim_ard_gaw/compat_scripts/launch.sh`;
- `src/sim_ard_gaw/compat_scripts/run_one.py`;
- `src/sim_ard_gaw/compat_scripts/run_matrix.py`;
- `src/sim_ard_gaw/compat_scripts/run_one_og.py`;
- `src/sim_ard_gaw/compat_scripts/compare_campaign_mission_window.py`;
- `src/sim_ard_gaw/compat_scripts/audit_bin_internal_wind.py`;
- `src/sim_ard_gaw/compat_scripts/build_square_postprocessing_report.py`;
- `src/sim_ard_gaw/compat_scripts/square_loiter_mission_metrics.py`.

Canonical docs and AI state also described the root bridge as still current.
Phase 2 comparison commands, Phase 0 dirty-state notes, migration gates, and
recovered evidence paths intentionally retain historical old-root text.

## Retirement Order Used

1. Harden `governance/runbooks/phase_8_compatibility_retirement.md` so the
   removal gate requires audit, subsystem order, retained blockers, and
   evidence.
2. Refactor launch/runtime path constants away from the root bridge:
   assets and missions use `assets/`, parameters use `config/`, campaign and
   analysis output defaults use `var/`, and helper calls use organized
   `src/sim_ard_gaw/{launch,bridges,analysis}` paths.
3. Add focused Phase 8 unit coverage for owned wind-matrix and launcher paths.
4. Run targeted import, CLI, compile, and unit checks before removal.
5. Remove only the root compatibility symlink tree after the runtime scan shows
   no remaining active dependency on it.
6. Update docs, AI state, and this report for the retained runner boundary.

The organized symlink views and compatibility runner implementations are not
retired in this pass because moving them would cross Phase 5 campaign parity
and legacy-runner ownership boundaries without replacement evidence.

## Code Ownership Before And After

| Area | Before | After |
| --- | --- | --- |
| launch assets/config paths | compatibility root symlinks | direct `assets/` and `config/` paths |
| launch helper calls | compatibility root `scripts/` link | organized bridge and analysis runtime-facing paths |
| wind-matrix mission/world/config defaults | compatibility root symlinks | direct `assets/`, `config/`, and `var/` paths |
| retained wind-matrix SITL BIN discovery | implicit `src/ardupilot/logs` fallback for manual and sequential routes | explicit launcher or per-attempt `var/` SITL `--use-dir` homes |
| wind-matrix analysis helpers | compatibility root `scripts/` link | organized analysis runtime-facing paths |
| analysis/report output defaults touched here | compatibility root log link | direct `var/logs/` routing |
| campaign runner implementation ownership | `compat_scripts/` | retained `compat_scripts/` blocker boundary |
| bridge/analysis implementation ownership | symlink-backed organized views into `compat_scripts/` | retained symlink-backed blocker boundary |

## Compatibility Paths Before And After

Removed:

- the root compatibility symlink tree and its `config`, `models`, `worlds`,
  `missions`, `scripts`, and `logs` links.

Retained:

- `src/sim_ard_gaw/compat_scripts/`;
- organized symlink-backed launch, bridge, analysis, wind-matrix, and
  `test_suite` views under `src/sim_ard_gaw/`.

`src/SIM_ARD_GAW` still exists: NO.

`compat_scripts/` still exists: YES.

## Runner Retirement Decisions

| Runner | Decision | Reason |
| --- | --- | --- |
| `run_one.py` | retained real compatibility entrypoint | Phase 5 wrappers and parity still delegate attempt work to it; owned paths and default CTE BIN discovery now follow the launcher `var/` state |
| `run_matrix.py` | retained real compatibility entrypoint | full orchestration replacement ownership is not yet proven; retained sequential SITL attempts now receive isolated `var/` state |
| `run_matrix_round_robin.py` | retained real compatibility entrypoint | Phase 5 tiny campaign proof uses this shape through wrapper parity |
| `test_suite` entrypoints | retained wrapper layer | Phase 5 architecture still uses the compatibility runner chokepoint |
| `run_one_og.py` | retained legacy compatibility caller | legacy path defaults were moved off the root bridge, but replacement/retirement policy is not yet evidenced |

## Files Changed

Runtime and tests:

- `src/sim_ard_gaw/compat_scripts/launch.sh`
- `src/sim_ard_gaw/compat_scripts/run_one.py`
- `src/sim_ard_gaw/compat_scripts/run_matrix.py`
- `src/sim_ard_gaw/compat_scripts/run_one_og.py`
- `src/sim_ard_gaw/compat_scripts/test_suite/cli/run_case.py`
- `src/sim_ard_gaw/compat_scripts/test_suite/cli/run_suite.py`
- `src/sim_ard_gaw/compat_scripts/test_suite/plugins/wind_matrix/config.py`
- `src/sim_ard_gaw/compat_scripts/compare_campaign_mission_window.py`
- `src/sim_ard_gaw/compat_scripts/audit_bin_internal_wind.py`
- `src/sim_ard_gaw/compat_scripts/build_square_postprocessing_report.py`
- `src/sim_ard_gaw/compat_scripts/square_loiter_mission_metrics.py`
- `tests/unit/test_phase8_runtime_paths.py`
- removed root compatibility symlink paths under `src/`

Docs, AI, governance, and evidence:

- `README.md`
- `docs/architecture/workspace_map.md`
- `docs/operations/evidence_workflow.md`
- `docs/operations/launch_targets.md`
- `docs/operations/migration_status.md`
- `docs/operations/troubleshooting.md`
- `docs/campaigns/wind_matrix.md`
- `src/sim_ard_gaw/README.md`
- `scripts/maintenance/validate_structure.sh`
- `.ai/index.md`
- `.ai/current.md`
- `.ai/issues/open.md`
- `governance/runbooks/phase_8_compatibility_retirement.md`
- this report

## Commands Run

Inspection and audit:

- `sed -n ...` reads of the Phase 8/full/Phase 7 runbooks, governance
  standards, Phase 0 through Phase 7 reports, docs, AI state, runtime scripts,
  test files, and runtime policy ADR;
- `python3 /home/ahmed/.codex/skills/python-lsp/scripts/inspect_python_lsp.py /home/ahmed/ardupilot_workspace_next`;
- `find src/SIM_ARD_GAW ...` and `find src/sim_ard_gaw ... -type l ...` for
  compatibility inventory;
- `rg -n ...` scans for old-root references, `SIM_ARD_GAW_DIR`,
  `compat_scripts`, asset/config/log assumptions, helper references, and test
  import paths;
- `rg --files ...` runtime, report, docs, and test inventory scans;
- `wc -l ...` on compatibility launch/bridge/analysis scripts.

Pre-removal targeted verification:

- `env/bin/python3 -m unittest tests/unit/test_phase8_runtime_paths.py tests/unit/test_campaign_contracts.py tests/unit/test_wind_world_safety.py`;
- `scripts/ops/launch.sh help`;
- `env/bin/python3 src/sim_ard_gaw/compat_scripts/run_matrix.py --help`;
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/compat_scripts tests/unit/test_phase8_runtime_paths.py`.

Review-remediation verification:

- `env/bin/python3 -m unittest tests/unit/test_phase8_runtime_paths.py`;
- `scripts/ops/launch.sh help`;
- focused `rg -n ...` scans for old SITL log fallbacks, retired help commands,
  the removed campaign log bridge claim, and obsolete validator allowlist text.

Final validation commands and results are recorded below.

## Validation Results

| Check | Result |
| --- | --- |
| focused Phase 8 runtime path tests | PASS: 4 tests including retained `var/` SITL-state and operator-help coverage |
| focused Phase 8/unit safety tests | PASS in the pre-removal pass: 10 tests |
| launcher help | PASS after direct path refactor and stable operator command remediation |
| wind-matrix CLI help | PASS after direct path refactor |
| Python compile for touched compatibility scripts/tests | PASS |
| required final unit tests | PASS: `env/bin/python3 -m unittest discover -s tests/unit` ran 17 tests |
| required integration tests | PASS: `env/bin/python3 -m unittest discover -s tests/integration` ran 3 tests |
| `make test-parity` | PASS: 6 parity tests |
| `make doctor` | PASS: structure and evidence validators passed |
| `scripts/maintenance/validate_structure.sh` | PASS after obsolete retired-bridge allowlist entries were pruned |
| focused pyright | PASS: `pyright tests/unit/test_phase8_runtime_paths.py` |
| import checks | PASS for `run_one`, `run_matrix`, `run_matrix_round_robin`, and `test_suite.cli.run_round_robin` with the retained compatibility `PYTHONPATH` |
| CLI checks | PASS for launcher help, `run_matrix.py --help`, and `test_suite.cli.run_round_robin --help` with the retained compatibility `PYTHONPATH` |
| broken symlink check | PASS: `find -L . -type l -print` returned no broken symlinks |
| raw-log leakage scan | PASS: explicit `.BIN`/`.bin`/`.tlog`/`.tlog.raw` scan outside allowed homes returned no paths |
| stale compatibility dependency scan | PASS for no active runtime old-root dependency: the focused runtime scan returned only the Phase 8 test assertion guarding `SIM_ARD_GAW_DIR` |
| retained SITL log fallback scan | PASS for active retained runtime code: no `src/ardupilot/logs` or `ARDUPILOT_LOG_DIR` fallback remains outside archived docs |
| hardcoded old workspace root scan | PASS for active runtime code: focused source/test scan returned only validator allowlist patterns |
| docs/AI/governance compatibility-claim scan | PASS: retained compatibility claims name `compat_scripts`/organized views, and structure validation allows only explicit Phase 0/2/8 old-root text |

One direct `env/bin/python3 -m test_suite.cli.run_round_robin --help` smoke
check failed first with `ModuleNotFoundError: No module named 'test_suite'`
because the retained compatibility suite is not on that interpreter path by
default. The governed compatibility smoke check reran with
`PYTHONPATH=src:src/sim_ard_gaw/compat_scripts` and passed. That result is part
of the retained `test_suite` blocker boundary above.

Bounded runtime smoke: not run. This slice changes path resolution and CLI
helper routing but does not change runtime control behavior; targeted CLI,
import, test, and structure validation are used for this retirement pass.

## Retained Blockers And Exit Conditions

| Retained surface | Blocker | Exit condition |
| --- | --- | --- |
| campaign runners in `compat_scripts/` | Phase 5 parity and wrapper flows still delegate the real attempt/orchestration behavior there | move runner ownership into `src/sim_ard_gaw/campaigns/`, keep only governed wrappers if needed, and rerun campaign parity |
| `test_suite` compatibility tree | wrapper/plugin code still imports legacy runners through `_legacy.py` | replace the legacy chokepoint with owned campaign APIs and pass wrapper parity/integration tests |
| symlink-backed launch/bridge/analysis views | implementations have not yet been moved without duplicate runnable logic | move each subsystem implementation into its organized home or prove a wrapper-only boundary with focused tests and docs |
| Phase 7 production boundary | cutover remains blocked without fresh final proof under `ADR-0004` | complete Phase 7 proof and decision path before any doc claims production promotion |

## Phase 8 Conclusion

PARTIAL PASS WITH RETAINED COMPATIBILITY.

The active root compatibility path is retired and removed after direct owned
path resolution, retained-runner `var/` routing remediation, tests, and docs
were updated. The remaining compatibility runner and symlink-backed
organized-view work stays named, evidenced, and blocked on replacement
ownership plus parity checks rather than being deleted prematurely.
