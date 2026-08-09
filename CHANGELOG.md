# Changelog

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
