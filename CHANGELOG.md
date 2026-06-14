# Changelog

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
