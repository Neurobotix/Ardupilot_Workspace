# Evidence Standard

Raw logs, `.BIN`, `.tlog`, run directories, caches, and simulator output belong
under `var/` or external archive storage. Git-tracked evidence is limited to
manifests, summaries, reports, indexes, and small curated artifacts.

Ignored external dependency checkouts such as `src/ardupilot/` and
`src/SITL_Models/` may contain upstream fixture, firmware, bootloader, or
test-log files. Those files are allowed only because the dependency trees are
ignored and are not promoted as workspace evidence. New runtime output produced
by workspace launchers must still be routed to `var/`.

## Lifecycle

Day-to-day evidence follows one promotion path:

```text
run -> var/
review -> select
promote -> evidence/
index -> evidence/indexes/
reference -> docs/.ai/governance as needed
```

`var/` is a runtime home, not an evidence catalog. Preserve only the selected
proof needed for review and point at raw runtime or archive locations when the
raw files remain relevant.

## Record Types

| Record type | Home | Rule |
| --- | --- | --- |
| Raw runtime output | `var/` or external archive | Includes simulator state, `.BIN`, `.bin`, `.tlog`, `.tlog.raw`, caches, and raw run directories. Do not track it as curated evidence. |
| Working analysis output | `var/` until reviewed | Analysis drafts, large plots, decoded scratch tables, and rerun scratch output are not automatically evidence. |
| Curated manifest or selected artifact | `evidence/curated_logs/` or `evidence/manifests/` | Keep reviewable summaries, manifest snapshots, provenance records, and bounded artifacts needed to support a report. |
| Report | `evidence/reports/` | Dated conclusion, commands, scope, evidence references, limitations, and pass/fail/blocker statement. |
| Index entry | `evidence/indexes/` | Catalogs what the evidence proves, where the report/artifact/raw reference lives, and its review status. |
| Audit or incident | `governance/audits/` | Records findings, errata, incidents, and investigation facts that should not be hidden in runtime logs. |
| ADR or decision | `governance/decisions/` | Records durable policy or architecture choices. |

The asset and parameter indexes remain specialized evidence indexes. Cross-phase
operational proof is cataloged in `evidence/indexes/evidence_catalog.md`.

New evidence reports use `YYYY-MM-DD_lower_snake_case.md`. Existing accepted
reports with older names are preserved for provenance and routed through the
catalog instead of renamed for aesthetics. Evidence templates and active indexes
use stable `lower_snake_case.md` names.

## Promotion Rules

1. Run tools so new runtime output lands under `var/`.
2. Review the raw output and decide what claim is supported.
3. Promote only selected proof: a report, manifest snapshot, bounded summary,
   provenance record, or small curated artifact.
4. Record commands, scope, input config/assets/parameter provenance where it
   affects interpretation, output locations, and limitations.
5. Add or update an evidence index entry when a human will need to find the
   proof later.
6. Treat promoted curated artifacts as append-only once reports or catalog
   entries reference them. Create a new evidence ID or versioned artifact path
   and supersede/update the report and index record instead of overwriting
   historical proof.
7. Update canonical docs, `.ai/`, audits, or ADRs only when the reviewed proof
   changes operating truth, active work, incident history, or policy.

Never promote raw runtime trees blindly. Do not copy `.BIN`, `.bin`, `.tlog`,
`.tlog.raw`, SITL state directories, MAVProxy run trees, Gazebo run logs, or
unreviewed campaign run directories into tracked evidence. Reference their
runtime or archive path from a report or manifest when retention matters.

Generated decodes and console summaries are working output until reviewed.
Tools that can decode raw telemetry should default to `var/`; reviewed selected
summaries belong in a curated-artifact home, not the report home, unless they
are filled reports that satisfy the report contract below. A promotion tool
must not silently replace an already-promoted curated artifact from a later raw
run.

## Report Templates

Reusable templates live under `evidence/templates/`, not
`evidence/reports/`. A filled report must say whether it is launch/runtime,
vehicle, campaign, or promotion evidence and must include:

- date/time and timezone;
- scope and status;
- commands run;
- input config, assets, parameter stack, or provenance when relevant;
- raw output locations and promoted evidence references;
- risks, limitations, and blockers;
- migration-era old-workspace modification statement when the old workspace is
  in scope.

Templates make evidence consistent. They are not results and must never be used
to claim cutover readiness on their own.

Before creating evidence files, check `governance/standards/naming.md` and the
nearest `README.md` under `evidence/`.
