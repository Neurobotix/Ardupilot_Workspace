# test_suite Phase 3C Review Findings

Date/time: 2026-05-31, Africa/Cairo / EEST (+03:00)

## Scope

This audit records the follow-up review findings against the feature Phase 3C
`test_suite` staged wind-matrix foundation work. It covers manifest durability,
crash bookkeeping, avoidable legacy helper use in stimulus config creation,
and the evidence wording boundary for staged runtime legacy dependencies.

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.

## Findings And Resolution

| ID | Finding | Resolution |
| --- | --- | --- |
| C-1 | `WindMatrixManifest` wrote `manifest.json`, `manifest.csv`, and summaries with bare `Path.write_text(...)`, losing the legacy temp-file-rename durability behavior. | Plugin-owned manifest text writes now use a sibling temp file and `Path.replace(...)`. A regression test simulates a failed temp write and verifies the existing manifest remains intact. |
| C-2 | Staged `AttemptRunner.run()` wrote no manifest row until strategy completion, so crashes during environment launch/readiness or staged execution could leave no attempt trace. Stale `running` rows were not reconciled in the test-suite path. | Staged wind attempts now prewrite a legacy-compatible `running` row before environment work, update the same row on terminal completion or ordinary failure, and reconcile stale `running` rows to `interrupted` before later attempt allocation. |
| C-3 | `WindMatrixStimulus._ensure_attempt_dir()` and `_write_run_config()` still used legacy runner constants, path helpers, mission/provenance helpers, JSON writing, BIN naming, and plugin diagnostics. | Those avoidable dependencies now use plugin-owned defaults or shared campaign helpers. Runtime wind injection still calls retained legacy helpers and remains Phase 3F scope. |
| C-4 | The Phase 3C PASS wording could be read too broadly even though staged runtime still imports/calls legacy runner helpers during execution. | The Phase 3C evidence report, runbook review, evidence pointer, and campaign doc now state explicitly that Phase 3C is no-SITL foundation proof only and not staged runtime independence. |

## Verification Record

The associated evidence report is
`evidence/reports/features/2026-05-31_test_suite_phase3c_review_fixes.md`.

## Residual Risk

Phase 3D-3G still must remove staged execution dependencies on legacy runner
helpers for environment launch/readiness/cleanup, MAVLink control/monitoring,
runtime wind injection, artifacts, analysis, summaries, and terminal helper
creation before Phase 4 can start.
