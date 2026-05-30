# Phase 2 — Generic Manifest And Data Model

Scope: feature-level Phase 2 of the `test_suite` migration. This is the
"Stage 2 — generic data model" phase from
`src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`.

## What Phase 2 does

1. Adds a framework-level generic manifest view over legacy wind-matrix
   attempts.
2. Writes generic fields additively to manifest rows created through the
   `test_suite` framework path.
3. Serializes additive manifest writes with the existing
   `campaign_manifest_lock()` contract.
4. Keeps the legacy wind-specific manifest fields readable and unchanged.
5. Normalizes older manifest rows in memory when generic fields are missing.
6. Preserves strategy-provided legacy `end_time_utc` as generic
   `finished_at`; the framework fills a timestamp only when the strategy
   leaves it empty.
7. Records focused tests for old-manifest reads, new generic writes,
   round-trip compatibility, wind-matrix attempt conversion, partial verdicts,
   missing optional generic fields, locked append behavior, and runner
   timestamp preservation.

## Data model contract

The generic attempt view uses schema version
`test_suite.generic_manifest.v1`. The version marker is stored in
`schema_version` for each generic attempt view and at the root of
`Manifest.generic_view()`.

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

For legacy wind rows, `case_id` is derived from `combo_key`, `parameters`
from `x_wind_mps` / `y_wind_mps`, `stimulus_result` from the wind values,
`analysis_results` from `analysis_status`, `verdict` from `status` /
`terminal_status`, and `artifacts` from `raw_log_path`, `attempt_dir`, and
`run_alias`.

## Legacy compatibility rule

Generic fields are additive. The writer must not rename or overwrite
legacy wind-specific fields such as `attempt_id`, `combo_key`,
`x_wind_mps`, `y_wind_mps`, `status`, `analysis_status`,
`start_time_utc`, or `end_time_utc`.

Older manifests remain valid when they have no generic fields. The reader
normalizes them with `Manifest.generic_view()` and leaves the persisted
file untouched.

`success_square_only` remains a partial verdict in the generic view and
does not count as a strict full success unless the manifest is configured
with `accept_square_only=True`.

`WindMatrixManifest.append_attempt()` must take `campaign_manifest_lock()` for
the full read/update/save transaction. In Phase 2 this behavior still lived in
`LegacyManifest`; Phase 3C moved the wind-compatible implementation out of
generic core and into `plugins/wind_matrix/manifest.py`. It must fail closed
with the same lock error as legacy unsafe writers when another process already
holds the campaign root lock.

## Schema/version decision

The Phase 2 schema marker is the string
`test_suite.generic_manifest.v1`. It describes the generic view, not a
replacement for the wind-matrix legacy schema. A future incompatible
generic-view change must use a new version string and retain a reader for
this version while historical campaign evidence is still referenced.

## Files changed

- `src/sim_ard_gaw/campaigns/test_suite/core/models.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/manifest.py`
- `src/sim_ard_gaw/campaigns/test_suite/core/attempt_runner.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/plugin.py`
- `tests/unit/test_test_suite_manifest_generic_view.py`
- `src/sim_ard_gaw/campaigns/test_suite/ARCHITECTURE.md`
- `docs/campaigns/wind_matrix.md`
- this feature runbook bundle
- `evidence/reports/features/2026-05-25_test_suite_migration_phase_2.md`
- `evidence/indexes/evidence_catalog.md`

## Validation plan

Required validation:

- focused Phase 2 unit test:
  `env/bin/python3 -m unittest tests/unit/test_test_suite_manifest_generic_view.py`
- `git status --short`
- `git diff --stat`
- `git diff --check`
- `env/bin/python3 -m compileall -q src/sim_ard_gaw/campaigns/test_suite tests`
- `env/bin/python3 -m unittest discover -s tests/unit`
- `env/bin/python3 -m unittest discover -s tests/integration`
- `env/bin/python3 -m unittest tests/parity/test_phase1_parity.py`
- `make test-parity`
- `make doctor`

## Acceptance criteria

- Old legacy-style wind manifests can be read through the generic view.
- New framework records write the generic fields additively.
- Legacy wind fields round-trip unchanged.
- Wind-matrix legacy attempt rows expose a generic view.
- `success_square_only` remains `partial`, not full `success`.
- Missing optional generic fields in older manifests are tolerated.
- Phase 1 wrapper parity still passes.
- Unit, integration, parity, and doctor checks pass or blockers are
  recorded honestly.

## Explicit out of scope

- Splitting `run_one.py`.
- Retiring legacy wrappers.
- Creating a second plugin.
- Claiming Phase 3, Phase 4, or Phase 5 completion.
- Changing wind-matrix runtime ordering, launch behavior, acceptance policy,
  artifact layout, or historical campaign evidence.
- Adding implementation logic under `compat_scripts/`.
