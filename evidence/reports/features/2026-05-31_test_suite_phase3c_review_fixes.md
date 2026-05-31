# test_suite Phase 3C Review Fixes

Date/time: 2026-05-31T11:11:03+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature review remediation

Conclusion: PASS for the 2026-05-31 Phase 3C review fixes. This is not live
zero-legacy staged runtime proof, and Phase 4 remains blocked until Phase 3G.

Feature runbook:
`governance/runbooks/features/test_suite_migration/plan.md`

Audit record:
`governance/audits/2026-05-31_test_suite_phase3c_review_findings.md`

## Scope

This report records remediation for four review findings:

- plugin-owned wind manifest writes must be atomic like the legacy runner;
- staged attempts must persist a durable `running` row before environment work
  and terminalize ordinary failures;
- stale staged `running` rows must be recoverable as `interrupted` before later
  attempt allocation;
- avoidable `run_one` helper use in `WindMatrixStimulus` attempt-directory and
  `run_config.json` creation must move to plugin-owned defaults or shared
  campaign helpers.

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.

## Files Changed

- `src/sim_ard_gaw/campaigns/test_suite/core/attempt_runner.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/defaults.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/manifest.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/plugin.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/stimulus.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/analyzers.py`
- `tests/unit/test_test_suite_manifest_generic_view.py`
- `tests/unit/test_test_suite_phase3_staged_attempt.py`
- `tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py`
- `docs/campaigns/wind_matrix.md`
- `governance/runbooks/features/test_suite_migration/plan.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `evidence/reports/features/2026-05-29_test_suite_migration_phase_3c.md`
- `governance/audits/2026-05-31_test_suite_phase3c_review_findings.md`
- `evidence/indexes/evidence_catalog.md`
- `.ai/index.md`

## Implementation Summary

- `WindMatrixManifest` now writes manifest and summary text through a sibling
  temp file followed by `Path.replace(...)`.
- Staged wind plugin runners prewrite a legacy-compatible `running` row before
  `prepare_case`, `launch`, or `assert_ready`; terminal records update the same
  row, and environment/runtime exceptions produce terminal `error` rows.
- `WindMatrixManifest` reconciles stale `running` rows to `interrupted` before
  accepted-count and next-attempt allocation.
- `WindMatrixStimulus._ensure_attempt_dir()` and `_write_run_config()` now use
  plugin-owned defaults plus shared mission/provenance helpers for avoidable
  constants, path naming, JSON writing, mission validation, parameter hashes,
  SITL BIN path, and plugin diagnostics.
- The Phase 3C docs and evidence now state plainly that staged runtime still
  calls legacy helpers during environment, MAVLink, wind injection, artifact,
  analysis, summary, and terminal-helper execution until Phase 3D-3G.

## Validation Results

| Command | Result |
| --- | --- |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py` | PASS: 9 tests |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3_staged_attempt.py` | PASS: 23 tests |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py` | PASS: 3 tests |
| `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests` | PASS |
| `env/bin/python3 -m unittest discover -s tests/unit` | PASS: 55 tests |
| `env/bin/python3 -m unittest discover -s tests/integration` | PASS: 3 tests |
| `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py` | PASS: 8 tests |
| `make test-parity` | PASS: 8 tests |
| `/home/ahmed/.local/bin/pyright ...` focused modified code/tests | PASS: 0 errors |
| `git diff --check` | PASS |
| `make doctor` | PASS: structure and evidence validators passed |

## Residual Risk

- Live zero-legacy staged runtime remains unproven.
- Runtime environment launch/readiness/cleanup still reaches
  `run_matrix.*` / `run_one.*` and remains Phase 3D.
- Staged MAVLink control/monitor execution remains Phase 3E.
- Runtime wind injection, artifacts, analysis, summaries, and remaining
  terminal helper cleanup remain Phase 3F.
- Phase 3G still must prove the full zero-legacy staged wind system live beside
  the retained legacy path before Phase 4 can start.

## Phase 4 / Wrapper / Workspace Statements

- Phase 4 was not started.
- No second plugin was added.
- Legacy scripts and wrappers were not retired.
- The old workspace `/home/ahmed/ardupilot_workspace` was not modified.
