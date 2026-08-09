# Changelog

## 2026-08-09

- Made round-robin scheduling reachable through one path for every campaign
  lane, so a method capability stops differing between lanes:
  - `gps_failure` now runs its live campaign on `core.scheduler`'s
    `RoundRobinScheduler` via `SuiteRunner`. It previously reimplemented
    scheduling as a hand-rolled loop in `cli/run_gps_failure.py` that never
    touched core; "round robin" was a shared name over two implementations.
  - Generalized the scheduler's progress rule instead of forcing GPS onto
    core's. `Manifest.progress_count` is what schedulers now ask, defaulting
    to `accepted_count`; `gps_failure` overrides it to
    `workflow_complete_count`. Core learns no plugin name, and lanes that do
    not override it schedule exactly as before. The distinction is load-bearing:
    a GPS run that flew and injected cleanly but whose behavior was not
    accepted is a spent physical repetition, and scheduling it on
    `accepted_count` would have re-flown it.
  - Made the round-robin slot budget optional. `per_attempt_budget_s=None`
    gives fair ordering with no deadline published, because GPS attempt length
    is governed by the lane's mission timeout; publishing a deadline would have
    newly clamped live phase timeouts through `clamp_timeout_to_slot`.
  - Added `SuiteRunSettings.on_attempt_complete`, a lane hook for campaigns
    with fatal stop rules. GPS keeps zero automatic retries and stops on
    workflow failure while tolerating a workflow-complete unaccepted run.
  - Confirmation gates (`--confirm-live-phase2`, `--confirm-validation-rerun`,
    `--confirm-live-campaign`), the non-jamming case-set restriction, and the
    campaign contract payload are unchanged.
  - Added `tests/unit/test_scheduler_lane_parity.py`, which replays the
    pre-change GPS loop as an oracle and asserts the scheduler reproduces its
    exact schedule across acceptance, non-acceptance, and fatal-failure cases.
  - Not done, reported instead: `airspeed_failure` did not gain round-robin.
    Its `--round-robin` flag already reported the lane as sequential; the
    lane's wizard campaign path is deliberately `SequentialScheduler`, and
    nothing in this change alters that.

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
