# test_suite Phase 3C Follow-up Fixes (H-1 .. H-9)

Date/time: 2026-05-31T14:45:48+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature review remediation

Conclusion: PASS for the 2026-05-31 follow-up review fixes (findings H-1 .. H-9)
and for migrating the staged-analysis substage of Phase 3F to plugin-owned
code. This is **not** live zero-legacy staged runtime proof. No SITL/Gazebo
staged wind case was run. Phase 4 remains blocked until Phase 3G.

Correction (same date): the H-7 wording in this report overclaimed exact staged
`run_config.json` parity. Exact schema/value parity for the migrated staged
fields was completed and evidenced later in
`evidence/reports/features/2026-05-31_test_suite_phase3c_manifest_run_config_parity_fixes.md`.

Feature runbook:
`governance/runbooks/features/test_suite_migration/plan.md`

Audit record:
`governance/audits/2026-05-31_test_suite_phase3c_followup_findings.md`

Predecessor remediation:
`evidence/reports/features/2026-05-31_test_suite_phase3c_review_fixes.md`

## Scope

This report records remediation for nine follow-up findings:

- H-1: canonical attempt-directory derivation for staged running/terminal rows;
- H-2: stimulus attempt-directory helper no longer duplicates legacy path helpers;
- H-3: plugin manifest caches the reconciled manifest for repeated bookkeeping reads;
- H-4: `defaults.mission_item_count` matches the legacy `mavwp.MAVWPLoader` count;
- H-5: parity test asserts `run_suite` does not adopt round-robin-only flags;
- H-6: the staged analyzer is plugin-owned and proven under a legacy-runner import blocker;
- H-7: staged `run_config.json` field-set parity was partially addressed here
  but exact migrated-field schema/value parity is evidenced in the later strict
  fix report noted above;
- H-8: f-string code-block test bodies escape literal braces;
- H-9: analysis-helper mocks patch the namespace the analyzer actually uses.

It also migrates the **analysis substage of Phase 3F** (BIN collection,
`run_analysis`, `build_run_summary`, analysis cleanup, run-alias linking, and
the slot-timeout helper) out of the legacy runner and into
`plugins/wind_matrix/analysis_helpers.py`.

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.

## Files Changed

- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/analysis_helpers.py` (new)
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/analyzers.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/plugin.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/stimulus.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/defaults.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/manifest.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/attempt_runner.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/suite_runner.py`
- `src/sim_ard_gaw/campaigns/test_suite/cli/run_case.py`
- `tests/unit/test_test_suite_phase3_staged_attempt.py`
- `tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py`
- `tests/parity/test_phase1_parity.py`
- `governance/audits/2026-05-31_test_suite_phase3c_followup_findings.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `evidence/reports/features/2026-05-29_test_suite_migration_phase_3c.md`
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- `evidence/indexes/evidence_catalog.md`
- `.ai/index.md`
- this report

## Implementation Summary

- `attempt_dir_factory` returns the full `attempt_NNN` path. The staged running
  record (`build_wind_matrix_running_record`) and the staged error record
  (`build_wind_matrix_error_fields`) re-derive the canonical `attempt_NNN`
  directory from the attempt index and set `ctx.attempt_dir`, so a failure in
  the environment prepare/launch/ready stages records the same canonical
  attempt directory the success path would.
- `plugins/wind_matrix/analysis_helpers.py` owns BIN flush/collection, analysis
  invocation, run-summary building, analysis-cleanup, run-alias linking, and the
  slot-timeout clamp helper. `analyzers.py` imports these from the plugin and no
  longer imports `run_one`.
- The Phase 3C import-blocker hard test now executes `WindMatrixAnalyzer.analyze()`
  to a successful verdict while `run_one`, `run_matrix`, and
  `run_matrix_round_robin` imports are blocked, by mocking the plugin-owned
  analysis helpers in the `analyzers` namespace.
- `tests/parity/test_phase1_parity.py` adds a check that `run_suite` does not
  expose `--require-analysis` while `run_round_robin` does.
- Two test files had f-string code blocks with unescaped literal braces and
  helper mocks aimed at the wrong namespace; both are corrected.

## Remaining Staged-Runtime Legacy Dependencies (unchanged)

- `WindMatrixEnvironment` launch/readiness/cleanup -> `run_matrix.*` / `run_one.*` (Phase 3D).
- `_LazyLegacyAutoMissionControl` mission upload/arm/mode -> `run_one.*` (Phase 3E).
- `_LazyLegacyDisarmMonitor` -> `run_one.monitor_until_disarm` (Phase 3E).
- `WindMatrixStimulus` runtime wind injection -> `run_one.inject_wind` / `preloaded_wind_artifact` (Phase 3F wind-injection substage).
- `_legacy_run_one_body` -> `run_one.run_one` (legacy-mode-only delegate; correct).

## Commands Run

- `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `env/bin/python3 -m unittest discover -s tests/integration`
- `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`
- `make test-parity`
- CLI help smoke for `run_case`, `run_suite`, `run_round_robin` (owned module path)
- `/home/ahmed/.local/bin/pyright` on the changed plugin modules
- `make doctor`

## Validation Results

| Command | Result |
| --- | --- |
| `tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py` | PASS: 3 tests |
| `tests/unit/test_test_suite_phase3_staged_attempt.py` | PASS: 23 tests |
| `tests/unit/test_test_suite_manifest_generic_view.py` | PASS: 9 tests |
| `compileall -q src/sim_ard_gaw/campaigns/test_suite tests` | PASS |
| `unittest discover -s tests/unit` | PASS: 55 tests |
| `unittest discover -s tests/integration` | PASS: 3 tests |
| `make test-parity` / `tests/parity/test_phase1_parity.py` | PASS: 9 tests |
| CLI help smoke (`run_case`, `run_suite`, `run_round_robin`) | PASS |
| focused `pyright` on changed plugin modules | PASS: 0 errors |
| `make doctor` | PASS: structure and evidence validators passed |

## Residual Risk

- Live zero-legacy staged runtime remains unproven.
- Runtime environment launch/readiness/cleanup still reaches
  `run_matrix.*` / `run_one.*` and remains Phase 3D.
- Staged MAVLink control/monitor execution still imports `run_one` at execute
  time and remains Phase 3E; those execute-time paths are therefore not yet
  exercised with legacy imports blocked.
- Runtime wind injection still calls `run_one.inject_wind` /
  `preloaded_wind_artifact` and remains the Phase 3F wind-injection substage.
- Phase 3G still must prove the full zero-legacy staged wind system live beside
  the retained legacy path before Phase 4 can start.

## Phase 4 / Wrapper / Workspace Statements

- Phase 4 was not started.
- No second plugin was added.
- Legacy scripts and wrappers were not retired.
- The old workspace `/home/ahmed/ardupilot_workspace` was not modified.
