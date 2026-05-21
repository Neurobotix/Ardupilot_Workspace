# Phase 6: Evidence And Operations

Purpose: establish the day-to-day workflow for running, reviewing, promoting,
and reporting simulation evidence.

Status: PASS on 2026-05-21. The dated Phase 6 report closes the checklist
below.

## Current-State Assessment

Inspect the existing evidence system before adding to it:

- prior phase reports under `evidence/reports/`;
- indexes under `evidence/indexes/`;
- manifests and selected artifacts under `evidence/manifests/` and
  `evidence/curated_logs/`;
- runtime output under `var/`;
- canonical operational/campaign docs plus `.ai/` pointers;
- existing structure, ignore, and raw-output validation.

Record the assessment in the Phase 6 evidence report. Extend the existing
reports/indexes/curated-artifact pattern; do not create a parallel evidence
taxonomy.

## Lifecycle

Use this lifecycle for new operational proof:

```text
run -> var/
review -> select
promote -> evidence/
index -> evidence/indexes/
reference -> docs/.ai/governance as needed
```

The standard and workflow docs must distinguish raw runtime output, working
analysis output, curated manifests, reports, index entries, audits/incidents,
and ADRs/decisions.

## Tasks

- Define the promotion workflow from `var/` to `evidence/`.
- Create templates for launch/runtime smoke, vehicle verification, campaign
  results, and evidence-promotion review.
- Create or update an evidence catalog that maps proof -> report -> curated
  manifest/artifact -> raw archive location.
- Confirm logger and campaign runtime outputs stay under `var/` and remain
  separate from curated evidence.
- Confirm only reviewed summaries, manifests, reports, indexes, and small
  curated artifacts are committed.
- Confirm promotion tools use new evidence IDs or versioned outputs instead of
  silently replacing curated artifacts already named by reports or indexes.
- Add maintenance checks for accidental raw evidence commits, raw run
  directories outside runtime homes, raw-looking evidence-home signatures, and
  misplaced evidence when practical.
- Demonstrate one real end-to-end promotion using existing safe proof or a
  bounded new validation artifact.

## Required Updates

- `governance/standards/evidence.md`: promotion rules and templates.
- `docs/operations/evidence_workflow.md`: human evidence workflow.
- `evidence/templates/`: reusable report and promotion templates.
- `evidence/indexes/`: catalog of reports and curated evidence.
- `scripts/maintenance/` and doctor routing if evidence checks change.
- `.ai/index.md`: point agents to evidence workflow.
- `.ai/current.md`: status of operational readiness.
- `.ai/issues/open.md`: remaining blockers and non-claims.

## Minimum Validation

- `make doctor`
- `scripts/maintenance/validate_structure.sh`
- any focused evidence/raw-output maintenance check added by this phase
- `git check-ignore` examples for `.private/config/plane_params.local.parm`,
  `var/logs/example.BIN`, and `var/runs/example.tlog`
- raw log leakage scan outside ignored/runtime areas
- evidence catalog sanity check
- retained curated-root catalog coverage check
- template inventory check
- stale canonical evidence/log claim scan where the edited docs require it

## Exit Gate Checklist

- [x] Phase 6 report names work that already existed and the gaps Phase 6
  closed.
- [x] The lifecycle, promotion rules, and operational workflow are documented.
- [x] Templates exist outside `evidence/reports/` and are clearly templates.
- [x] Evidence catalog entries answer what exists, what it proves, its scope,
  report/manifest/artifact paths, raw-output references, and review status.
- [x] Raw logs and raw run directories are ignored or rejected outside allowed
  runtime homes.
- [x] Raw-looking runtime signatures inside evidence homes are rejected unless
  reviewed bounded artifacts have exact allowlist reasons.
- [x] Reviewed promotion paths use evidence IDs or versioned outputs instead of
  silently overwriting already-cataloged curated artifacts.
- [x] Logger output path and campaign runtime-output separation are verified or
  a blocker is recorded.
- [x] One real promotion example is recorded from runtime source through catalog
  and report/docs references without fabricating evidence.
- [x] The old workspace is explicitly recorded as unmodified.
- [x] No Phase 7 cutover or Phase 8 compatibility retirement claim is made.

Create or update `evidence/reports/migration/PHASE_6_EVIDENCE_OPS_<date>.md` as the exit
gate record. Templates prove the workflow exists; they do not by themselves
prove cutover readiness.
