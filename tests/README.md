# Tests

Tests for workspace-owned behavior belong here. Keep test fixtures small and
focused; runtime output from test runs belongs under `var/`, not in this tree.

## Naming

- Python test files use `test_<lower_snake_case>.py`.
- Fixture files use `lower_snake_case.<ext>` unless a parser or simulator needs
  a specific external name.
- Date prefixes are not required for stable tests or fixtures.
- Historical fixture names may be preserved when the name is part of the test
  contract.

Use subdirectories such as `unit/`, `integration/`, `parity/`, and `fixtures/`
to show the test's role.
