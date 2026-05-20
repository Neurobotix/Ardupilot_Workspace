# Phase 5: Campaign And Test Migration

Purpose: move the wind matrix and test-suite work from compatibility mode toward
the new architecture without losing production behavior.

Status: PASS on 2026-05-21. Evidence:
`evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`.

## Completion Checklist

- [x] Current-state gap assessment recorded before campaign code edits.
- [x] Compatibility runners and Phase-1 `test_suite` wrappers retained.
- [x] Manifest lock, terminal taxonomy, mission contract, XML/SDF transform,
      strict wind verification, and parameter provenance implemented and tested.
- [x] Unit, integration, parity, CLI/import, structure, raw-log, and
      stale-claim checks recorded.
- [x] Bounded tiny campaign result promoted from `var/` to `evidence/`.
- [x] First production-reference one-case comparison remediation invalidated as
      wind-parity proof after the installed Gazebo plugin fallback was found;
      corrected workspace-plugin recheck and incident audit recorded.
- [x] No Phase 7 cutover or Phase 8 compatibility retirement performed.

## Safety Boundary

- Work only in `ardupilot_workspace_next`; the old production workspace is a
  read-only comparison source.
- Keep `run_one.py`, `run_matrix.py`, `run_matrix_round_robin.py`, and the
  Phase-1 `test_suite` wrappers as compatibility surfaces until parity evidence
  governs a later transition.
- Inspect current campaign code, tests, manifests, docs, and prior phase
  evidence before changing behavior. Do not duplicate migration work that is
  already present.
- Route new campaign hardening modules through `src/sim_ard_gaw/campaigns/`,
  tests through `tests/`, fixtures through `tests/fixtures/`, raw runs through
  `var/`, and curated proof through `evidence/`.
- Added manifest fields must be backward-compatible. Breaking schema changes,
  cutover, and compatibility retirement are out of scope.

## Current-State Assessment

Before campaign code edits:

1. Record which legacy runners, wrappers, schedulers, analyzers, manifests,
   fixtures, tests, and curated campaign logs already exist.
2. Classify each hardening gate as already implemented and tested, implemented
   but untested, missing, or unsafe/incorrect.
3. Name the production behaviors that remain compatibility contracts.
4. Record the assessment in the Phase 5 evidence report or a governance audit
   note instead of creating a competing planning file.

## Tasks

- Keep legacy runners in `compat_scripts/` until parity evidence allows replacement.
- Add unit tests for:
  - manifest status taxonomy,
  - parameter hashing,
  - mission contract validation,
  - SDF/XML wind transform,
  - wind verification parsing.
- Add integration tests for `test_suite` CLI behavior with fixtures.
- Implement campaign manifest locking before concurrent runs.
- Make `failed_analysis` a first-class terminal status.
- Keep legacy manifest `status` values compatible while adding any canonical
  terminal-status view additively.
- Validate the wind-matrix mission contract before analysis depends on the
  known square/loiter/landing waypoint layout.
- Replace regex SDF wind mutation with XML/SDF transform.
- Enable strict wind verification by default for new campaign evidence.
- Record parameter-file content hashes with campaign run provenance and require
  comparison evidence to use them, not path names alone.
- Run tiny campaign parity against production behavior.

## Minimum Validation

- `make doctor`
- `scripts/maintenance/validate_structure.sh`
- `make test-parity`
- targeted Phase 5 unit tests
- targeted Phase 5 integration tests
- relevant compatibility and `test_suite` CLI help/import checks
- raw log leakage scan
- stale canonical-doc/AI scan for open or closed wind-matrix claims
- a bounded tiny campaign parity run when runtime dependencies permit it

Any campaign command beyond a cheap help/import/test check must record command,
scope, output location, and cleanup in the Phase 5 evidence report.

The Phase 5 report must not treat Gazebo wind topic echo alone as end-to-end
wind parity proof. Wind-comparison evidence must also record the selected
Gazebo plugin path. Current policy permits only the workspace plugin build and
requires campaign runtime to fail closed when
`build/ardupilot_gazebo/libArduPilotPlugin.so` is missing; the earlier
installed-plugin fallback remains incident evidence, not an allowed runtime
path.

## Required Updates

- `src/sim_ard_gaw/campaigns/`: new implementation modules.
- `tests/unit`, `tests/integration`, `tests/parity`: matching coverage.
- `docs/campaigns/wind_matrix.md`: current operator procedure.
- `governance/decisions/`: ADRs for manifest/status/wind verification policy if needed.
- `evidence/reports/`: parity and campaign validation reports.
- `.ai/issues/open.md`: close or update WM blockers.

## Exit Gate

Create `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_<date>.md` showing:

- the current-state gap assessment,
- which compatibility runners remain and whether any changed,
- unit/integration/parity tests passed,
- manifest locking and deterministic terminal status handling including
  `failed_analysis`,
- mission-contract validation,
- XML/SDF wind transform and strict wind-verification behavior,
- parameter hashes/provenance recorded for campaign comparison,
- tiny matrix parity result as `PASS`, `FAIL`, or `BLOCKED`,
- unresolved blockers and output/evidence locations,
- an explicit Phase 5 conclusion of `PASS`, `FAIL`, or `BLOCKED`,
- an explicit statement that the old workspace was not modified,
- and an explicit statement that Phase 5 did not perform cutover or
  compatibility retirement.
