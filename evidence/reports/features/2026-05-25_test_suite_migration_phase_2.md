# test_suite Migration — Feature Phase 2 (Generic Manifest)

Date/time: 2026-05-25T02:20:41+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase implementation evidence (no new runtime output)

Conclusion: PASS

Feature runbook:
`governance/runbooks/features/test_suite_migration/`

## Scope

This report records feature-level Phase 2 of the `test_suite` migration:
generic manifest / data model support.

Phase 2 adds a generic framework-level manifest view while preserving the
existing wind-matrix manifest schema and historical campaign compatibility.
It does not split `run_one.py`, retire legacy wrappers, create a second
plugin, or claim Phase 3 / Phase 4 / Phase 5 completion.

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.

## Files changed

- `src/sim_ard_gaw/campaigns/test_suite/core/models.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/manifest.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/attempt_runner.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/plugin.py`
- `tests/unit/test_test_suite_manifest_generic_view.py`
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- `docs/campaigns/wind_matrix.md`
- `governance/runbooks/features/test_suite_migration/phase_2_generic_manifest.md`
- `governance/runbooks/features/test_suite_migration/plan.md`
- `governance/runbooks/features/test_suite_migration/review.md`
- `governance/runbooks/features/test_suite_migration/evidence.md`
- `evidence/indexes/evidence_catalog.md`
- this report

## Generic manifest contract summary

The generic schema marker is `test_suite.generic_manifest.v1`.

`Manifest.legacy_view()` returns the plugin/legacy manifest shape.
`Manifest.generic_view()` returns an in-memory normalized generic view
without mutating older manifests.
`LegacyManifest.append_attempt()` takes `campaign_manifest_lock()` around
the full read/update/save transaction. Generic `finished_at` is sourced from
the strategy-provided legacy `end_time_utc` when present; the framework fills
an append-time value only when the strategy leaves `end_time_utc` empty.

Required generic attempt fields:

- `schema_version`
- `attempt_id`
- `suite_name`
- `case_id`
- `parameters`
- `stimulus_result`
- `analysis_results`
- `verdict`
- `artifacts`
- `started_at`
- `finished_at`

For legacy wind rows, `case_id` is derived from `combo_key`, parameters from
`x_wind_mps` / `y_wind_mps`, stimulus from the wind values, analysis from
`analysis_status`, verdict from `status` / `terminal_status`, artifacts from
`raw_log_path`, `attempt_dir`, and `run_alias`, and timestamps from
`start_time_utc` / `end_time_utc`.

## Backward compatibility proof

- Existing wind-specific fields are not renamed or removed.
- `LegacyManifest.append_attempt()` updates only generic fields on the
  matching attempt row. It does not overwrite legacy `status`, `combo_key`,
  wind values, analysis status, or legacy timestamps.
- The additive update uses the same campaign-root manifest lock as the legacy
  unsafe manifest writers and fails closed when another process owns that lock.
- Older manifests with no generic fields are normalized by the reader without
  changing the persisted file.
- `success_square_only` maps to generic verdict class `partial` and remains
  excluded from strict full-success acceptance by default.
- The runner-to-manifest path preserves a legacy row's `end_time_utc` as the
  generic `finished_at`.
- Historical curated comparator manifests under
  `evidence/curated_logs/017_*`, `018_*`, and
  `phase5_tiny_rr_20260521/` remain valid legacy manifests.

## Commands run

- `date --iso-8601=seconds`
- `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `git status --short`
- `git diff --stat`
- `git diff --check`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests`
- `env/bin/python3 -m unittest discover -s tests/integration`
- `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`
- `make test-parity`
- `make doctor`

## Test results

| Command | Result |
| --- | --- |
| `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py` | PASS: 7 tests |
| `env/bin/python3 -m unittest discover -s tests/unit` | PASS: 27 tests |
| `git diff --check` | PASS |
| `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests` | PASS |
| `env/bin/python3 -m unittest discover -s tests/integration` | PASS: 3 tests |
| `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py` | PASS: 8 tests |
| `make test-parity` | PASS: 8 tests |
| `make doctor` | PASS |

## Residual risks

- Direct legacy `run_one.py` / `run_matrix.py` invocations still write the
  legacy wind manifest shape only. This is intentional compatibility behavior;
  the generic reader handles those records without requiring a rewrite.
- The generic model is still proven against wind_matrix only. A second
  non-wind plugin remains Phase 4.
- Phase 3 still needs a live SITL/Gazebo single-attempt diff before changing
  the delegated strategy body.

## Strict self-review

- No legacy manifest field was renamed or removed.
- Older manifests can still be read.
- Generic fields are additive.
- Partial verdicts are preserved as partial.
- No runtime ordering, launch behavior, artifact layout, or acceptance policy
  was intentionally changed.
- Additive manifest writes are locked with `campaign_manifest_lock()`.
- Generic `finished_at` preserves strategy-provided legacy `end_time_utc`.
- No code landed in `compat_scripts/`.
- Docs, runbooks, evidence, and the evidence catalog were updated.
- Phase 3 / Phase 4 / Phase 5 were not implemented.
