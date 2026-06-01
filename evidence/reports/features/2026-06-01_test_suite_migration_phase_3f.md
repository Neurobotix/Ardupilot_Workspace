# test_suite Migration — Feature Phase 3F

Date/time: 2026-06-01T14:04:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase implementation evidence + first live staged proof

Conclusion: PASS for the Phase 3F wind-injection substage. Runtime wind
injection (Gazebo wind-topic publish + strict echo verification + preloaded SDF
artifact handling) is now test-suite-owned in plugin-owned `wind_injection.py`
with no legacy runner import. With this change the **staged attempt path is
fully zero-legacy** (environment, MAVLink control/monitor, and wind injection
are all plugin-owned). A single **live completed staged run** was captured as
direct proof. This is NOT yet a matched side-by-side legacy comparison; that
remains Phase 3G.

Feature runbook:
`governance/runbooks/features/test_suite_migration/plan.md`

## Scope

Phase 3F moves runtime wind injection out of legacy delegation:

In scope (now test-suite-owned, in `wind_injection.py`; verbatim ports of
`run_one`, import sources relocated only):

- `parse_wind_echo`, `wind_echo_matches`, `start_wind_echo`, `finish_wind_echo`,
  `capture_wind_info_snapshot`
- `inject_wind(x_mps, y_mps, *, timeout_s=None, strict_echo_verify=...)`
- `parse_sdf_world_wind`
- `preloaded_wind_artifact(x_mps, y_mps, *, source_world, archived_world,
  refresh_runtime_wind=True, refresh_strict_echo_verify=False, timeout_s=None)`

Supporting changes:

- `defaults.py`: added `WIND_ECHO_SETTLE_S`, `WIND_ECHO_TIMEOUT_S`,
  `WIND_ECHO_TOLERANCE_MPS`, `WIND_INFO_CAPTURE_TIMEOUT_S`, `CAPTURE_WIND_INFO`,
  `SDF_WIND_TOLERANCE_MPS`, `WIND_FLOAT_RE` (values verified equal to `run_one`);
  consolidated `normalize_manifest_text` here as the single home.
- `analysis_helpers.py`: uses `defaults.normalize_manifest_text`.
- `stimulus.py`: `WindMatrixStimulus.apply` calls `wind_injection.*`; the
  `from . import legacy` import was removed.

### Provenance-label correction (intentional value divergence from legacy)

`defaults.wind_injection_source()` previously returned the literal string
`"run_one.py via Gazebo wind topic ..."`, copied byte-for-byte from `run_one`.
After Phase 3F that text is misleading in staged `run_config.json` because the
injection runs through plugin-owned `wind_injection.inject_wind`, not `run_one`.
The string is now `"test_suite staged wind_matrix plugin via Gazebo wind topic
..."`. This is a deliberate **value** divergence from legacy `run_config.json`
for the `wind_injection_source` field only. The run_config **schema** (the set
of keys) is unchanged, so the schema-parity contract still holds; the
schema-parity test asserts the key is present, not its exact string value.

Out of scope (no change in this phase):

- `_legacy_run_one_body` → legacy-mode-only delegate; correct and intended.
- `run_one.py`, `run_matrix.py`, `run_matrix_round_robin.py` → unmodified.
- A matched live legacy comparison run → Phase 3G.

## Files Changed

- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/wind_injection.py` (created)
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/defaults.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/analysis_helpers.py`
- `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/stimulus.py`
- `tests/unit/test_wind_matrix_wind_injection.py` (created)
- `tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py` (Phase 3F block + label assert)
- `tests/unit/test_test_suite_phase3_staged_attempt.py` (renamed-adapter wiring)

Legacy runner scripts were not modified.

## Dependency Audit (after Phase 3F)

| Dependency | Classification | Result |
| --- | --- | --- |
| `WindMatrixStimulus` runtime wind injection (`inject_wind` / `preloaded_wind_artifact`) | Phase 3F blocker | Removed. Now `wind_injection.*`; `stimulus.py` no longer imports `legacy`. |
| `_legacy_run_one_body` → `run_one.run_one` | legacy-mode-only delegate | Unchanged. Correct. |

After this phase the only live `legacy.run_one_module()` call in the whole
plugin is `_legacy_run_one_body` (the legacy strategy). The staged path imports
no legacy runner module for any stage.

## Live Proof (first completed staged run)

Command (no crippling outer timeout; the run owns its mission budget):

```
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 \
  -m sim_ard_gaw.campaigns.test_suite.cli.run_suite \
  --attempt-strategy staged --auto-wind-phase before-arm \
  --x-values 4 --y-values 4 --runs-per-combo 1 --max-attempts-per-combo 1 \
  --campaign-root var/runs/test_suite_phase3f_staged_complete_20260601T134207 \
  --wind-world-mode calm-runtime --no-param-local --wipe-eeprom \
  --stack-settle-s 8 --heartbeat-timeout 120 --ready-timeout 120 \
  --upload-timeout 60 --arm-timeout 60 --mode-timeout 30 --mission-timeout 3600
```

Result:

- Manifest: `wind_x_04_y_04__rep_01__attempt_001` → `status=success_full`,
  `analysis_status=done`, `run_alias=run_01`, `mission_completed_full=True`.
- Wind injection (live): `status=ok`, `strict_echo_verification=True`,
  `echo_parsed_wind={x:4.0, y:4.0, z:0.0, enable_wind:True}`, 1 attempt.
- Analysis (live): `true_path_deviation` and `square_loiter_mission_metrics`
  ran; `run_summary.json` produced. Square overall RMS true-path deviation
  58.71 m (p95 130.99 m, max 219.34 m, 20 segments, 13247 samples); loiter
  turns_complete=True.
- The full staged lifecycle executed: wind injection → heartbeat/ready →
  upload/verify/arm/AUTO → monitor to disarm → BIN collection → analysis →
  run_summary → manifest `success_full`.

Curated evidence:
`evidence/curated_logs/test_suite_phase3f_staged_live_20260601/`
(summaries + provenance; raw 57 MB BIN stays under `var/`, sha256
`e179ac1530160db86f86e1c4f1868a0e82d97ec272a239b07b5e73989dd52330`).

Raw runtime:
`var/runs/test_suite_phase3f_staged_complete_20260601T134207/`.

### Live-run operational note

Two earlier bounded attempts on 2026-06-01 were cut off mid-flight by an outer
`timeout 600s` wrapper that was shorter than the run's own mission budget. When
the orchestrator is killed by an external signal, SITL/Gazebo/MAVProxy children
launched with `start_new_session=True` are orphaned because `cleanup_stack()`
runs only in the Python `finally`. This matches legacy `run_matrix.py` behavior
and is not a Phase 3F regression. The accepted run above was launched without a
crippling outer timeout and tore its stack down on its own completion. A
SIGTERM-driven cleanup handler is a possible future hardening item.

## Commands Run

```
env/bin/python3 -m unittest tests/unit/test_wind_matrix_wind_injection.py
env/bin/python3 -m unittest tests/unit/test_test_suite_phase3c_zero_legacy_foundation.py
env/bin/python3 -m unittest discover -s tests/unit
env/bin/python3 -m unittest tests/parity/test_phase1_parity.py
make test-parity
make doctor
```

## Validation Results

| Check | Result |
| --- | --- |
| `test_wind_matrix_wind_injection` (6 tests) | PASS |
| `test_test_suite_phase3c_zero_legacy_foundation` (6 tests, incl. Phase 3F) | PASS |
| `unittest discover -s tests/unit` (100 tests) | PASS |
| `test_phase1_parity.py` (9 tests) | PASS |
| `make test-parity` (9 tests) | PASS |
| `make doctor` | PASS |
| Live completed staged run | PASS (`success_full`, see Live Proof) |

## Residual Risk / Claim Boundaries

- One live completed staged run was captured. A **matched side-by-side legacy
  comparison run** is not part of this report and remains Phase 3G.
- Live proof was captured on this workstation. It is a single combo
  (`wind_x_04_y_04`), not a full matrix.
- The SIGTERM/orphan-cleanup gap above is shared with legacy and is not closed.
- Phase 4 (second plugin) remains blocked until Phase 3G is accepted.
- No second plugin was added; no legacy script was retired; the old workspace
  was not modified.
