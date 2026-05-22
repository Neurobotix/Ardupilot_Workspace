# Phase 6 Evidence And Operations

Date/time: 2026-05-21T16:45:31+03:00

Timezone: Africa/Cairo / EEST (+03:00)

## Scope

Phase 6 establishes the day-to-day evidence workflow for
`/home/ahmed/ardupilot_workspace_next`: runtime output remains under `var/`,
reviewed proof is promoted into the existing `evidence/` system, reports and
catalog entries make the proof reviewable, and maintenance checks resist raw
runtime pollution.

The old workspace was read only as historical context already referenced by the
existing reports and docs. It was not modified. This phase does not perform
Phase 7 cutover or Phase 8 compatibility retirement.

## Current-State Gap Assessment

Assessment recorded before Phase 6 implementation edits beyond the tightened
Phase 6 runbook and evidence standard.

Phase 6 work already present:

- dated Phase 0 through Phase 5 reports under `evidence/reports/`;
- Phase 4 specialized indexes for assets and parameter/config ownership under
  `evidence/indexes/`;
- historical curated test results plus Phase 1 and Phase 5 campaign manifests
  under `evidence/curated_logs/`;
- an existing empty `evidence/manifests/` home;
- canonical operations/campaign docs that already separate `var/` runtime
  output from curated proof in several places;
- `.gitignore` coverage for `var/`, raw `.BIN`/`.bin`/`.tlog`/`.tlog.raw`
  files, raw `runs/`, and `round_robin_logs/`;
- `scripts/maintenance/validate_structure.sh` raw-log leakage checks called by
  `make doctor`.

Gaps found against the improved Phase 6 runbook:

- the evidence standard did not yet define the full lifecycle or record-type
  boundaries;
- no human promotion workflow existed under `docs/operations/`;
- no reusable Phase 6 report/promotion templates existed under `evidence/`;
- no cross-phase evidence catalog connected reports, curated artifacts,
  manifest references, raw-output references, and review status;
- maintenance covered raw log file leakage but did not yet add Phase 6 catalog,
  template, raw run-directory, or misplaced evidence checks;
- agents had no Phase 6 evidence-workflow pointer;
- the end-to-end promotion example had not yet been recorded in a Phase 6
  catalog/report entry.

## Files Changed

- `governance/runbooks/phase_6_evidence_operations.md`
- `governance/standards/evidence.md`
- `docs/operations/evidence_workflow.md`
- `docs/operations/launch_targets.md`
- `docs/operations/migration_status.md`
- `docs/campaigns/wind_matrix.md`
- `.ai/index.md`
- `.ai/current.md`
- `.ai/issues/open.md`
- `.gitignore`
- `scripts/ops/doctor.sh`
- `scripts/maintenance/README.md`
- `scripts/maintenance/validate_structure.sh`
- `scripts/maintenance/validate_evidence.sh`
- `scripts/ops/capture_round.sh`
- `evidence/indexes/evidence_catalog.md`
- `evidence/indexes/logs_README.md`
- `evidence/reports/PHASE_2_RUNTIME_PARITY_2026-05-20.md`
- `governance/runbooks/phase_2_runtime_parity.md`
- `docs/vehicles/status.md`
- `evidence/templates/launch_runtime_smoke_report.md`
- `evidence/templates/vehicle_verification_report.md`
- `evidence/templates/campaign_result_report.md`
- `evidence/templates/evidence_promotion_checklist.md`
- `evidence/reports/PHASE_6_EVIDENCE_OPS_2026-05-21.md`

Phase 2 per-target decoded summaries were moved from
`evidence/reports/phase_2_runtime_2026-05-20/` to
`evidence/curated_logs/phase_2_runtime_2026-05-20/` during review remediation.

## Commands Run

Inspection used `sed`, `rg`, and `find` reads across the Phase 6/full migration
runbooks, governance standards, `.ai` pointers, canonical operations/campaign
docs, Phase 0 through Phase 5 reports, Phase 5 ADR/audit, evidence indexes,
curated artifacts, manifests, `var/`, `.gitignore`, maintenance scripts, and
the campaign/runtime code paths relevant to output homes and provenance.

Key Phase 6 commands:

- `python3 /home/ahmed/.codex/skills/python-lsp/scripts/inspect_python_lsp.py /home/ahmed/ardupilot_workspace_next`
- `find src/SIM_ARD_GAW -maxdepth 2 -type l -ls`
- `rg -n "DEFAULT_CAMPAIGN_ROOT|campaign-root|flight_logger|var/(logs|runs)" ...`
- `scripts/maintenance/validate_evidence.sh`
- `scripts/ops/capture_round.sh plane`
- `scripts/ops/capture_round.sh --promote-reviewed plane` (expected refusal
  without a new evidence ID)
- `make doctor`
- `scripts/maintenance/validate_structure.sh`
- `git check-ignore -v var/logs/example.BIN var/runs/example.tlog .private/config/plane_params.local.parm`
- raw leakage scan:
  `find .` with `.git`, `var`, `.private`, dependency, `env`, `build`, and
  `install` homes pruned for `.BIN`/`.bin`/`.tlog`/`.tlog.raw`
- focused stale evidence/log wording scan across edited canonical docs, `.ai`,
  runbooks, standards, and evidence indexes.

An initial `make doctor` and direct `validate_structure.sh` pass found ignored
CMake compiler ABI probe files under `build/ardupilot_gazebo/` whose `.bin`
suffix matched the Phase 1 flight-log leakage glob. The structure validator was
updated to prune ignored build/install/runtime-dependency homes before the final
passing validation set.

## Review Remediation

The first Phase 6 closeout was reviewed on 2026-05-21 and failed on three
evidence-system gaps:

- the logger promotion example and the live capture script still placed decoded
  summaries under the report home;
- guardrails did not inspect approved evidence subtrees for enough raw runtime
  signatures;
- the catalog did not account for every retained curated evidence root.

This revision fixes those findings. Phase 2 decoded summaries are curated
artifacts under `evidence/curated_logs/`, `capture_round.sh` writes working
captures to `var/` unless `--promote-reviewed` is explicit, evidence-home
runtime signatures and report-home shape are validated, and retained curated
roots must be cataloged.

A follow-up strict review found that explicit reviewed promotion still targeted
stable Phase 2 summary filenames. The capture script now requires a new
`--evidence-id` for reviewed promotion, writes a versioned curated artifact
path, and refuses an existing destination instead of silently replacing proof
already named by a dated report or catalog row.

## Evidence Lifecycle Implemented

The standard and operator workflow now use one lifecycle:

```text
run -> var/
review -> select
promote -> evidence/
index -> evidence/indexes/
reference -> docs/.ai/governance as needed
```

`governance/standards/evidence.md` now distinguishes raw runtime output,
working analysis output, curated manifests/artifacts, reports, index entries,
audits/incidents, and ADRs/decisions. It also says templates are not results
and raw runtime trees must not be promoted blindly.

`docs/operations/evidence_workflow.md` turns that standard into the human
workflow: what belongs in `var/`, what may be promoted, when a report/catalog
entry/audit/ADR is needed, how campaign evidence differs from structural
validation evidence, and how to preserve raw archive references without tracking
raw logs.

Phase 6 review remediation also clarified that generated decoded summaries are
working output until reviewed. They become curated artifacts or filled reports
only after the selected promotion path is explicit.

## Templates Created

Reusable templates were added outside `evidence/reports/`:

- `evidence/templates/launch_runtime_smoke_report.md`
- `evidence/templates/vehicle_verification_report.md`
- `evidence/templates/campaign_result_report.md`
- `evidence/templates/evidence_promotion_checklist.md`

Each template includes date/time, timezone, scope, commands, provenance fields,
output locations, status, risks/limitations, old-workspace statement, and
promoted evidence references appropriate to its role.

## Evidence Catalog And Existing Indexes

`evidence/indexes/evidence_catalog.md` is the cross-phase catalog. It maps
proof to phase/scope, result claim, report, curated manifest/artifact, raw
runtime or archive reference, and review status. It now also names every
retained first-level curated evidence root. The Phase 4 specialized asset and
parameter/config indexes were retained rather than replaced.

The existing historical curated-log index in `evidence/indexes/logs_README.md`
was corrected so new runtime flight logs point to `var/` and new reviewed proof
points to the Phase 6 workflow/catalog rather than a stale `flights/` claim.

## Raw Evidence Guardrails

Guardrails now combine ignore policy and maintenance validation:

- `.gitignore` already ignored `var/`, raw `.BIN`/`.bin`/`.tlog`/`.tlog.raw`,
  raw `runs/`, and `round_robin_logs/`; Phase 6 also ignores
  `orchestrator_logs/` and `*_sitl_state/` raw simulator output directories.
- `scripts/maintenance/validate_evidence.sh` checks raw log leakage, raw run
  directory leakage, raw-looking files and runtime-tree shapes inside
  `evidence/`, exact allowlist reasons for reviewed bounded console captures,
  the report-home shape, approved `evidence/` top-level homes, phase-report
  placement, required template metadata fields, evidence catalog markers, and
  curated-root catalog coverage.
- `scripts/ops/doctor.sh` now calls both the Phase 1 structure validator and
  the Phase 6 evidence validator.
- `scripts/maintenance/validate_structure.sh` still owns structure/raw-log
  baseline checks and now prunes ignored build/install/runtime-dependency homes
  so compiler ABI `.bin` files are not misclassified as raw flight logs.

Final guardrail result: PASS for `make doctor`,
`scripts/maintenance/validate_structure.sh`, and
`scripts/maintenance/validate_evidence.sh`.

## Runtime Output Default Verification

Result: PASS for the Phase 6 runtime-output boundary.

- Logger code already points `LOG_DIR` at `var/logs/flight_logger/`, and Phase
  2 logger evidence records a real log at
  `var/logs/flight_logger/flight_20260521_065708.log`.
- The launcher builds SITL runtime arguments under `var/runs/sitl/<target>/`
  and MAVProxy telemetry under `var/logs/mavproxy/<target>/`.
- Wind-matrix compatibility defaults still name the temporary campaign log
  bridge, which resolves through the workspace symlink into `var/logs/`.
- Phase 5 evidence-producing bounded campaigns explicitly used campaign roots
  under `var/runs/`.
- Campaign curated manifests and selected attempt summaries remain under
  `evidence/curated_logs/`, separate from raw campaign run output.
- `scripts/ops/capture_round.sh` now writes decoded tlog summaries to
  `var/working/runtime_capture/` by default and needs
  `--promote-reviewed --evidence-id <new-id>` before selected Phase 2 summaries
  enter a new versioned curated artifact path.

No Phase 6 runtime writer was found writing raw output into a tracked evidence
home. The compatibility campaign default is documented rather than refactored
here because it already resolves to `var/`.

## End-To-End Promotion Example

Phase 6 reuses an existing real Phase 2 logger promotion rather than fabricating
a new result:

| Step | Path or record |
| --- | --- |
| Runtime source artifact | `var/logs/flight_logger/flight_20260521_065708.log` and raw console `var/logs/flight_logger/logger_console_20260521.txt` |
| Reviewed/promoted evidence | `evidence/curated_logs/phase_2_runtime_2026-05-20/logger_evidence.txt` |
| Catalog entry | `phase2-logger-promotion` in `evidence/indexes/evidence_catalog.md` |
| Report reference | `evidence/reports/PHASE_2_RUNTIME_PARITY_2026-05-20.md` |
| Docs/AI routing | `docs/operations/evidence_workflow.md` names the example; `.ai/index.md` points agents to the workflow and catalog. |

The promoted logger summary preserves a bounded excerpt, raw source path, size,
line count, and SHA-256 for the logger log. The raw logger output remains under
`var/`.

## Docs, AI, And Governance Updates

- Governance: improved the Phase 6 runbook before execution and expanded the
  evidence standard around lifecycle, record types, promotion rules, and
  templates.
- Human docs: added the evidence workflow, documented campaign/runtime output
  separation in launch targets and wind-matrix docs, and updated migration
  status.
- AI pointers: `.ai/index.md` now points at the workflow, catalog, templates,
  Phase 6 runbook/report, and evidence validator; `.ai/current.md` records the
  Phase 6 operating state; `.ai/issues/open.md` closes the Phase 6 items while
  keeping later migration blockers open.

No ADR was required because Phase 6 extends the evidence policy already owned by
the evidence standard and full migration plan.

## Validation Results

| Check | Result |
| --- | --- |
| `make doctor` | PASS. Structure validation and evidence validation both passed. |
| `scripts/maintenance/validate_structure.sh` | PASS. Raw-log leakage, stale reference, ignore, and migration-link checks passed. |
| `scripts/maintenance/validate_evidence.sh` | PASS. Raw-output leakage, evidence-home runtime signatures, raw run directories, report-home shape, evidence homes, report placement, template inventory, catalog sanity, and curated-root catalog coverage passed. |
| `scripts/ops/capture_round.sh plane` | PASS. The default decoded-tlog capture wrote working output to `var/working/runtime_capture/` and required explicit `--promote-reviewed --evidence-id <new-id>` for curated evidence. |
| `scripts/ops/capture_round.sh --promote-reviewed plane` | PASS. The promotion guard refused an unversioned reviewed promotion before evidence could be replaced. |
| `git check-ignore` examples | PASS for `var/logs/example.BIN`, `var/runs/example.tlog`, and `.private/config/plane_params.local.parm`. |
| Raw leakage scan outside allowed runtime/ignored areas | PASS. No `.BIN`, `.bin`, `.tlog`, or `.tlog.raw` path returned after allowed homes were pruned. |
| Evidence catalog sanity and retained curated-root coverage | PASS through `validate_evidence.sh`. |
| Template inventory check | PASS through `validate_evidence.sh`. |
| Focused stale evidence/log wording scan | PASS for edited canonical docs/indexes after correcting the legacy `flights/` wording in `evidence/indexes/logs_README.md`. |

## Unresolved Blockers

No Phase 6 evidence-workflow blocker remains.

Later migration blockers remain open in `.ai/issues/open.md`: non-core launch
target verification, Copter LiDAR obstacle-return proof, cleanup process
scoping, the wind-matrix workspace-plugin fail-closed gap, production dirty
state, cutover/deprecation, and compatibility retirement.

## Conclusion

Phase 6 status: PASS.

The existing report/index/curated-artifact system was extended with a human
promotion workflow, reusable templates, a cross-phase catalog, and evidence
guardrails. Raw runtime output remains under `var/`; reviewed proof is promoted
selectively into `evidence/` and indexed for review. The old workspace was not
modified. Phase 6 did not perform cutover or compatibility retirement.
