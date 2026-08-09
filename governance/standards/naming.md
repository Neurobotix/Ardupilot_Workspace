# Naming Standard

File names in this workspace should make ownership, lifecycle, and purpose clear
without turning names into status dashboards. Use modification-time sorting or
reverse lexical sorting when a timeline view is needed; do not distort file
names just to force newest-first alphabetical display.

## Purpose

This standard gives humans and AI agents one naming model for new workspace
files. It separates stable living documentation from historical/event records,
keeps evidence provenance intact, and avoids broad cosmetic renames.

## Core Rules

1. Prefer `lower_snake_case` for new stable names.
2. Use date-first names only for historical/event records.
3. Keep tool-required names when an external tool, simulator, package format,
   or upstream convention requires them.
4. Preserve historical evidence, ADR, archive, and heavily referenced names
   unless there is a separate reviewed migration plan.
5. Before creating a new file, check the nearest `README.md` or directory
   naming guidance and this standard.

## The Word "Lane"

"Lane" alone is ambiguous in this workspace and must not be used unqualified in
new docs, code comments, or commit messages. It names two different things on
two different axes:

- **Simulation lane** — an aircraft + world + launcher + bridge combination.
  Registry: `docs/architecture/simulation_lanes.md`.
- **Campaign lane** — an end-to-end fault investigation: fault injected, cases
  swept, verdicts classified, evidence produced. Registered in
  `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py`. Registry:
  `docs/architecture/campaign_lanes.md`.

A campaign lane **runs on** a simulation lane. The two are not interchangeable
and neither is a subset of the other.

Always write the qualified form — "simulation lane" or "campaign lane" — on
first use in a document and wherever the surrounding text does not already
make the axis unambiguous. Existing unqualified uses are not renamed for
cosmetics; qualify them when the surrounding text is edited for other reasons.

Campaign lane names are `lower_snake_case` and must match the plugin directory
under `src/sim_ard_gaw/campaigns/test_suite/plugins/` and the key registered in
`cli/_registry.py`. Simulation lane target names are `kebab-case` because they
are `scripts/ops/launch.sh` arguments.

## Stable Docs

Stable living Markdown docs use `lower_snake_case.md`.

Examples:

- `change_control.md`
- `records_lifecycle.md`
- `workspace_map.md`
- `workspace_status.md`

This applies to current docs under `docs/`, current standards under
`governance/standards/`, and stable agent protocol files under `.ai/` except
for root exceptions.

## Dated Records

Historical and event records use date-first names:

```text
YYYY-MM-DD_lower_snake_case.md
```

Use dated records for audits, incidents, evidence reports, one-off review
reports, campaign reports, and dated migration reports created after this
policy.

Date-first naming makes the record's event date visible without requiring every
stable living doc to carry a date.

## ADRs

ADRs keep the existing decision style:

```text
ADR-0001-short-slug.md
```

Do not rename existing ADRs for naming-policy cleanup.

## Evidence Reports

New evidence reports use:

```text
YYYY-MM-DD_lower_snake_case.md
```

Examples:

- `2026-05-24_naming_convention_policy.md`
- `2026-05-24_campaign_result_plane_lidar.md`
- `2026-05-24_migration_phase_9_review.md`

Existing accepted evidence reports with older names are preserved for
provenance. Use `evidence/indexes/evidence_catalog.md` to route readers between
old and new report styles.

## Runbooks

Runbooks live under organized directories, not as new top-level files under
`governance/runbooks/`.

Migration and operational runbook files use `lower_snake_case.md` unless they
are historical/event records. Migration phase runbooks may use
`phase_<n>_<short_slug>.md` when the phase number is part of the durable
identity.

## Feature Runbooks

Feature runbook directories use `lower_snake_case` slugs:

```text
governance/runbooks/features/<feature_slug>/
```

Stable feature files use predictable names:

- `plan.md`
- `implementation.md`
- `review.md`
- `evidence.md`

Phased feature files may use:

```text
phase_<n>_<short_slug>.md
```

## Code, Scripts, Config, And Assets

- Python files: `lower_snake_case.py`
- Shell scripts: `lower_snake_case.sh`
- Config files: `lower_snake_case.<ext>` unless an external tool requires a
  different name.
- Tests: `test_<lower_snake_case>.py` for Python tests.
- Assets, models, worlds, missions, meshes, and package metadata: keep
  tool-required names such as `model.sdf` or `model.config`; otherwise use
  lower snake case.

Imported upstream assets, simulator package files, and legacy media may keep
their original names when renaming would risk breaking references or provenance.

## Root Exceptions

Keep these root names:

- `README.md`
- `CHANGELOG.md`
- `AGENTS.md`
- `Makefile`

Tool files such as `pyproject.toml`, `requirements.txt`, and `setup.bash` keep
their ecosystem names.

## Archive And Historical Exceptions

Do not mass rename historical files for aesthetics. This includes accepted
evidence reports, imported curated logs, archive material, raw audit packages,
and files under `docs/archive/`.

If a historical name is heavily referenced, preserve it and add index or README
guidance instead. Rename historical records only when there is a deliberate
migration with references updated in the same change.

## Sorting And Display

Files are named for clarity and lifecycle. For timelines, use editor or
file-manager latest-modified sorting, or reverse lexical sorting for date-first
records. Do not add awkward date prefixes to stable living docs just to make
alphabetical sorting show the newest file first.

## AI Agent Rule

Before creating any new file, an AI agent must check the nearest directory
`README.md` or naming guidance and this file. If the local guidance conflicts
with this standard, treat the conflict as a blocker unless an ADR or newer
standard explicitly supersedes it.
