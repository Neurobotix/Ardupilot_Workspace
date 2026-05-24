# Evidence Workflow

Use this workflow when a run, validation, comparison, or incident needs proof
that survives a `var/` cleanup.

## Lifecycle

```text
run -> var/
review -> select
promote -> evidence/
index -> evidence/indexes/
reference -> docs/.ai/governance as needed
```

The evidence standard is `governance/standards/evidence.md`. This page is the
operator procedure for applying it.

## Runtime And Evidence Homes

`var/` is the default runtime home:

- SITL state lives under `var/runs/sitl/`.
- MAVProxy telemetry lives under `var/logs/mavproxy/`.
- Flight logger output lives under `var/logs/flight_logger/`.
- New campaign roots should be passed under `var/runs/` when the caller accepts
  a campaign-root override.
- Compatibility wind-matrix defaults route directly into `var/logs/`; that is
  runtime output, not curated evidence.

`evidence/` is the reviewed proof home:

- reports go under `evidence/reports/`;
- selected campaign manifests and small curated artifacts stay under
  `evidence/curated_logs/` or `evidence/manifests/`;
- indexes live under `evidence/indexes/`;
- reusable blank templates live under `evidence/templates/`.

## Promotion Steps

1. Run the tool and keep raw output under `var/`.
2. Review the raw output before making a claim. Decide whether the supported
   claim is a smoke result, vehicle verification, campaign result, incident, or
   policy decision.
3. Select the smallest reviewable proof. Prefer a report, manifest snapshot,
   bounded summary, provenance record, or a small curated artifact over a raw
   runtime tree.
4. Give each newly promoted curated artifact a new evidence ID or versioned
   output path. Supersede and re-index older proof when needed; do not silently
   overwrite an artifact that a dated report or catalog row already references.
5. Fill the matching template or update an existing report. Record commands,
   date/time, timezone, scope, relevant config/assets/parameter provenance,
   raw-output references, promoted evidence references, status, and
   limitations.
6. Add or update `evidence/indexes/evidence_catalog.md` when the evidence
   should be discoverable later.
7. Update canonical docs and `.ai/` only when reviewed evidence changes current
   operating truth or active work.

## What Not To Promote Blindly

Do not copy these into tracked evidence just because a run produced them:

- `.BIN`, `.bin`, `.tlog`, and `.tlog.raw` files;
- raw SITL, MAVProxy, Gazebo, bridge, or logger run trees;
- campaign `runs/`, `round_robin_logs/`, or orchestrator scratch logs;
- caches, terrain state, EEPROM state, screenshots, plots, and decoded scratch
  tables that have not been reviewed;
- generated decoded tlog summaries before report/catalog review;
- a whole `var/` subtree.

If raw data must remain findable, reference the path under `var/` or the
external archive path from the report or manifest. Say whether the raw path is
disposable runtime output or a retained archive location.

## Report, Index, Audit, Decision

Create or update a report when evidence supports a result claim, changes a
phase gate, or needs a dated review record.

Update the evidence catalog when a reviewer should be able to answer what proof
exists, what it proves, which report supports it, where its curated artifact or
manifest lives, and where raw output was kept.

Create a governance audit or incident record when the important fact is an
investigation, erratum, failure analysis, or unsafe operational finding.

Create an ADR when the important fact is a durable policy or architecture
decision. Evidence may support an ADR, but the ADR is not a raw run log.

## Structural And Campaign Evidence

Structural validation evidence usually points at commands such as `make doctor`,
maintenance validators, scans, indexes, hashes, and docs checks. It normally
promotes a dated report and perhaps an index update; it should not manufacture
simulator artifacts.

Campaign evidence is different. Campaign claims depend on the run scope,
mission, wind/plugin/runtime assumptions, effective parameter stack, manifest
status, analysis status, and provenance fields. Promote the reviewed manifest
snapshot and selected attempt summaries needed for review. Keep raw campaign
run directories and raw telemetry under `var/`.

## Existing Example

Phase 2 already contains a safe logger promotion:

- runtime source: `var/logs/flight_logger/flight_20260521_065708.log` plus the
  raw console under `var/logs/flight_logger/`;
- promoted summary:
  `evidence/curated_logs/phase_2_runtime_2026-05-20/logger_evidence.txt`;
- report reference:
  `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`;
- catalog entry: `phase2-logger-promotion` in
  `evidence/indexes/evidence_catalog.md`.

The raw logger output stays under `var/`; the small curated summary and dated
report carry the reviewable claim. For Phase 2 smoke tlogs,
`scripts/ops/capture_round.sh` writes working captures under `var/` by default;
its reviewed mode requires
`--promote-reviewed --evidence-id <new-id>` and writes a new versioned curated
summary path for the report/catalog update.
