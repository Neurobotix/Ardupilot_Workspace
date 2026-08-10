# Tests

Tests for workspace-owned behavior belong here. Keep test fixtures small and
focused; runtime output from test runs belongs under `var/`, not in this tree.

## Naming

- Python test files use `test_<lower_snake_case>.py`.
- A campaign lane's unit tests **must** be named `test_<lane>_<subject>.py`,
  where `<lane>` is the registered plugin name from
  `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py`
  (`airspeed_failure`, `gps_failure`, `wind_matrix`). One convention, no
  short forms: `test_gps_failure_mechanism_gate.py`, never
  `test_gps_mechanism_gate.py`. This makes `test_<lane>_*` a complete glob for
  "which tests cover this campaign lane", which a planned conformance check
  consumes.
- `<subject>` names what the file tests, not when it was written. Migration
  phase numbers (`phase1`, `phase2_path`) are not subjects.
- Fixture files use `lower_snake_case.<ext>` unless a parser or simulator needs
  a specific external name.
- Date prefixes are not required for stable tests or fixtures.
- Historical fixture names may be preserved when the name is part of the test
  contract.

Use subdirectories such as `unit/`, `integration/`, `parity/`, and `fixtures/`
to show the test's role.
