# Phase 3: Documentation Rebuild

Purpose: replace archived/stale docs with clean human docs that match the new
workspace and verified behavior.

## Status

Status: PASS after the 2026-05-21 completion pass and audit remediation.

Evidence:

- `evidence/reports/migration/PHASE_3_DOCS_2026-05-20.md`
- `governance/audits/2026-05-20_phase3_docs_errata.md`

## Tasks

- [x] Review `docs/archive/src_docs/` file by file.
- [x] Rewrite trusted installation/setup content into `docs/onboarding/`.
- [x] Rewrite launch and troubleshooting content into `docs/operations/`.
- [x] Rewrite architecture/data-flow content into `docs/architecture/`.
- [x] Rewrite vehicle-specific status and procedures into `docs/vehicles/`.
- [x] Rewrite campaign operating procedures into `docs/campaigns/`.
- [x] Leave stale or historical material in archive with errata notes.
- [x] Remove or qualify known bad refs:
  - the legacy flight-log directory name,
  - the retired LiDAR runway world name,
  - the removed altitude-wind log checker script,
  - the obsolete airspeed parameter claim for the base plane stack.

## Required Updates

- [x] `.ai/index.md`: point agents to new canonical docs.
- [x] `.ai/current.md`: mark doc rebuild progress.
- [x] `governance/audits/`: add errata when old docs are intentionally contradicted.
- [x] `evidence/reports/`: include stale-reference scan output.

## Exit Gate

Create `evidence/reports/migration/PHASE_3_DOCS_<date>.md` showing canonical docs have
no unqualified stale references and each archived old doc has a disposition:
promoted, rewritten, archived, or dropped.

Exit gate result: PASS in `evidence/reports/migration/PHASE_3_DOCS_2026-05-20.md`.
