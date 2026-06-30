# Phase 8 Follow-up: Compatibility Final-Removal Audit

Date/time: 2026-06-30
Conclusion: AUDIT (pre-removal inventory; removal not yet executed)

Purpose: record every live dependency on `src/sim_ard_gaw/compat_scripts/`
before the separate compatibility-removal pass deferred by
`PHASE_8_COMPAT_RETIREMENT_2026-05-24.md` ("Remove it only after a separate
compatibility-removal pass proves those old paths are no longer needed").

## Live dependency inventory (excludes externals, docs, governance, evidence)

### Category ① — `test_suite.*` shortcut imports (resolve only via the namespace shim)
Fix = repoint imports to the owned `sim_ard_gaw.campaigns.test_suite.*` path,
drop the `compat_scripts` sys.path insert.

- tests/unit/test_wind_matrix_analysis_helpers.py
- tests/unit/test_wind_matrix_wind_injection.py
- tests/unit/test_wind_matrix_mavlink_control.py
- tests/unit/test_test_suite_manifest_generic_view.py
- tests/unit/test_test_suite_phase3_staged_attempt.py

### Category ② — wrapper-parity tests (exist to test the compat layer itself)
Fix = delete with the layer (step 3, not yet done).

- tests/parity/test_phase1_parity.py
- tests/integration/test_phase5_wrapper_manifest_flow.py
- tests/unit/test_phase8_runtime_paths.py
- tests/unit/test_campaign_manifest_safety.py (sys.path insert of compat_scripts)

### Category ③ — runtime / build PYTHONPATH injections
Fix = remove after ① and ② (step 4, not yet done).

- pyproject.toml:9  (pytest pythonpath)
- Makefile:12       (parity test PYTHONPATH)
- src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/defaults.py:299
  (live Lane-2 campaign runtime env — verify against a real launch before removal)
- scripts/maintenance/validate_structure.sh:431 (lists compat_scripts as expected dep — update)

## Status
- Step 1 (this audit): DONE.
- Step 2 (repoint Category ① imports): DONE.
- Step 3 (retire wrapper-parity tests; repoint script-exec tests to owned run_one): DONE.
- Step 4 (remove PYTHONPATH injections: pyproject.toml, Makefile test-parity, airspeed defaults.py:299): DONE.
- Step 5 (delete src/sim_ard_gaw/compat_scripts/): DONE.
- Step 6 (re-prove): DONE — full suite 160 tests + 258 subtests PASS with PYTHONPATH=src only; `make doctor` PASS.

## Conclusion: PASS

The `compat_scripts/` wrapper layer is fully retired. All tests import owned
homes (`sim_ard_gaw.campaigns.wind_matrix.run_one`,
`sim_ard_gaw.campaigns.test_suite.*`). No live code, config, or test references
`compat_scripts`. The empty `tests/parity/` dir and its dead `make test-parity`
target were removed.

NOTE (separate follow-up, NOT done here): the wind_matrix plugin still DEFAULTS
to the `legacy` attempt strategy, which delegates to the retained `run_one`
monolith. Flipping default to `staged` and retiring the legacy strategy +
run_one/run_matrix monoliths is tracked as separate work.
