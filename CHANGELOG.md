# Changelog

## 2026-10-12

- Workspace cleanup on branch `chore/workspace-cleanup`, from an approved
  inventory. Safety net first: stash `c873af0` (INS-only implementation) is
  preserved as branch `archive/ins-only-stash`, the pre-cleanup state is
  tagged `pre-cleanup-2026-10-12`, and untracked material was backed up
  outside the workspace.
- New feature bundle `governance/runbooks/features/gps_denied_navigation/`
  gathers the INS-only plan (now `ins_only_plan.md`), the SITL IMU source
  validation, the BMI270 extract, and the EKF paper notes (now
  `design_research.md`). Pointers stay at the old `gps_failure_behavior/`
  paths. `plan.md` is an outline awaiting the study plan.
- Real-flight analysis code moved out of ignored `var/analysis/` into
  `src/sim_ard_gaw/analysis/real_flight/`, with its test in
  `tests/unit/test_real_flight_analysis_core.py`. Raw logs moved from
  `var/Real-Flights/` to `var/real_flights/` with space-free names. The
  `real_flight_imu_analysis` runbook bundle is now tracked.
- The Markdown-to-PDF renderer moved from `var/reports/report generation/` to
  `scripts/dev/report_generation/`.
- Removed the seven compatibility symlinks at `config/` root; nothing live
  used them.
- Deleted about 4.9 GB of untracked or ignored output: SITL scratch BINs for
  `plane-gps`, `plane-gps` MAVProxy telemetry, converted real-flight `.log`
  dumps, presentation `node_modules/` and `dist/`, cheat-sheet drafts v1-v3,
  July GPS planning prompts, `_audit/`, a stray image, Python caches, and
  empty sandbox stub folders.

## 2026-08-10

- The workspace cutover rollback runbook no longer sends an operator to a file
  that does not exist. Steps 2 and "Status After Rollback" named
  `docs/operations/migration_status.md`, which was removed and replaced by
  `docs/operations/workspace_status.md`; both now name the current file. This
  was a live operational instruction, not tidiness — the stale path would have
  been followed mid-incident. Found by the 2026-08-10 document inventory audit.
  Not fixed here: the same runbook lists `make test-parity` as a rollback
  signal, and that target does not exist in the `Makefile` (reported, out of
  scope). `evidence/indexes/evidence_catalog.md` carries the same stale
  reference and was deliberately left alone pending an evidence-index policy
  decision.
- `docs/presentations/` is documented as local-only and deliberately untracked,
  which it always was. `.gitignore` is correct and unchanged; the documents
  describing that tree as canonical were wrong. The presentation-template
  feature plan now states that the tooling exists only on an operator's machine
  and is absent from a fresh clone, keeping the `npm` steps as local workflow
  rather than repository build steps. `docs/README.md` and `.ai/index.md` said
  the same thing implicitly and were corrected; the `.ai/index.md` entry pointed
  at `docs/presentations/README.md`, a file no clone contains, and now points at
  the plan.
- The CTE wind-envelope brief cited from
  `governance/runbooks/features/airspeed_failure_behavior/design_research.md` is
  labelled local-only rather than repointed. Its content is already carried by
  the tracked evidence report cited beside it, and the brief is a derived
  briefing artifact of that report; dropping the citation would have erased
  provenance. This follows the existing labelling precedent in
  `evidence/reports/features/2026-06-02_pillar_a_flight_results.md`.

- Campaign-lane unit tests now follow one naming convention,
  `test_<lane>_<subject>.py`, where `<lane>` is the registered plugin name in
  `cli/_registry.py`. Previously both `test_gps_failure_*` and `test_gps_*`
  named the same lane, so no glob could answer "which tests cover lane X";
  `test_<lane>_*` is now a complete answer, which the planned per-lane
  conformance check consumes. Renames (via `git mv`, history preserved):
  - `test_airspeed_failure_phase1.py` → `test_airspeed_failure_campaign_contract.py`
  - `test_airspeed_mechanism_gate.py` → `test_airspeed_failure_mechanism_gate.py`
  - `test_airspeed_tailwind_phase2.py` → `test_airspeed_failure_tailwind.py`
  - `test_gps_failure_phase1.py` → `test_gps_failure_campaign_contract.py`
  - `test_gps_failure_phase2_path.py` → `test_gps_failure_runtime_path.py`
  - `test_gps_mechanism_gate.py` → `test_gps_failure_mechanism_gate.py`
  - `test_gps_launch_targets.py` → `test_gps_failure_launch_targets.py`
  - `test_wind_world_safety.py` → `test_wind_matrix_world_safety.py`
- Migration-phase names are replaced by subject names, because a phase number
  records when a file was written, not what it tests. The phase-labelled test
  classes inside the renamed files were renamed to match.
- The convention is recorded as a "must" in `tests/README.md`.
- `PHASE_H_GATE_PROOFS` in `plugins/gps_failure/readiness.py` cites test files
  by path as proof references; those strings were updated so the readiness
  report keeps pointing at files that exist. No behavior change.
- No test was added, removed, weakened, or skipped: 553 passed / 506 subtests
  before and after.

## 2026-08-09

- Round-robin scheduling is reachable through one path for every campaign
  lane, so a method capability does not differ between lanes:
  - `gps_failure` runs its live campaign on `core.scheduler`'s
    `RoundRobinScheduler` via `SuiteRunner`.
  - `Manifest.progress_count` is the progress rule schedulers ask for. It
    counts accepted runs by default; `gps_failure` overrides it to count
    workflow-complete runs, because a GPS run that flew and injected cleanly
    is a spent physical repetition even when its behavior was not accepted.
    Core learns no plugin name.
  - The round-robin slot budget is optional. `per_attempt_budget_s=None`
    gives fair ordering with no deadline published, for a lane whose attempt
    length is governed by its own mission timeout; a set budget publishes a
    deadline that `clamp_timeout_to_slot` applies to per-phase timeouts.
  - `SuiteRunSettings.on_attempt_complete` is the lane hook for campaigns with
    fatal stop rules. GPS runs with zero automatic retries, stops on workflow
    failure, and tolerates a workflow-complete unaccepted run.
  - `tests/unit/test_scheduler_lane_parity.py` pins the schedule the lanes
    produce across acceptance, non-acceptance, and fatal-failure cases.
  - `airspeed_failure` stays on `SequentialScheduler` and its `--round-robin`
    flag reports the lane as sequential. Nothing was found in its case model
    that would forbid round-robin; it was not adopted because the lane has no
    slot-budget concept, which is what makes round-robin worth using.

## 2026-08-06

- Unified the test-suite CLI so every lane is reachable and behaves
  identically regardless of entry point:
  - Fixed the interactive wizard aborting `airspeed_failure` campaigns on the
    first non-accepted attempt. `cli/run.py` hardcoded
    `max_attempts_per_case=1` against a framework default of 12, so
    `RuntimeError: exceeded max_attempts_per_case (1)` ended the campaign at
    `attempt=1`. The wizard now sources the retry budget from
    `SuiteRunSettings` and asks "Max attempts per case".
  - Replaced the four `_run_*_body` helpers in `cli/run.py` (hand-copies of
    each runner's `main()` that had drifted apart) with delegation to a shared
    `run_from_args(args)` in each runner. `cli/run.py` drops 382 to 85 lines.
  - Replaced the `Phase-1 supports only wind_matrix` guards with registry-based
    plugin resolution in `cli/_plugin_select.py`.
  - Added `gps_failure` to the `sim-test` wizard (safe action subset:
    list-cases, dry-run, preflight, and the non-jamming live round-robin
    campaign with its confirmation gates intact and re-asserted by the runner).
  - Added `--list-cases` and `--dry-run` to the wind-matrix runners, which had
    neither; all three lanes now share both. `--round-robin` on
    `airspeed_failure` reports that the lane is sequential instead of silently
    lacking the flag.
  - Not done, reported instead: `--plugin` on the generic runners was not
    opened to the other lanes. Those runners take wind case coordinates,
    validate the square-wind mission contract, and build a `WindMatrixConfig`;
    only 12 of ~29 config fields are shared across lanes and both other lanes'
    missions fail that contract. A lane-neutral runner needs a design decision.
- Reframed the workspace's present-tense documentation around the active
  fault-injection evidence framework, moved live status to
  `docs/operations/workspace_status.md`, and reduced completed migration facts
  to dated historical pointers.
- Retired migration-era test-suite attempt-strategy scaffolding: removed the
  dead delegate strategy, removed `WindMatrixConfig.attempt_strategy`
  thread-through, and kept old `--attempt-strategy staged` CLI input as a
  hidden deprecated no-op.

## 2026-06-07

- Added unified interactive CLI entry point `sim-test`
  (`src/sim_ard_gaw/campaigns/test_suite/cli/run.py`).
- Added interactive wizard
  (`src/sim_ard_gaw/campaigns/test_suite/cli/interactive.py`) covering both
  `wind_matrix` (single case / sequential suite / round-robin) and
  `airspeed_failure` (sequential suite) sensor families.
- `questionary` added to `requirements.txt` and installed into `env/`.
- `pyproject.toml` is ready for a `sim-test` console-scripts entry; run
  `env/bin/pip install -e .` after adding the entry to activate it.
- Existing `run_case.py`, `run_suite.py`, `run_round_robin.py` are untouched;
  `sim-test case|suite|rr` passes straight through to them flag-for-flag.

## 2026-05-19

- Bootstrapped corporate restructure workspace from production read-only source.
- Migrated runtime assets/config/scripts through a compatibility layer.
- Added governance, docs, `.ai`, evidence, private-overlay, and `var/` boundaries.
- Imported truth audit and curated evidence only; raw runtime logs remain ignored.
