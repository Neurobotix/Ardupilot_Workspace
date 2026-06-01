# test_suite Migration — Feature Phase 3G

Date/time: 2026-06-01T14:40:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature-phase live comparison evidence (staged vs legacy-direct)

Conclusion: PASS. The zero-legacy staged wind path was run live through
SITL/Gazebo and compared against a matched run of the **retained legacy tool
invoked directly** (`compat_scripts/run_matrix.py` → `run_one.run_one(...)`,
touching no `test_suite` code). Both reached `success_full`; flight metrics
agree within SITL run-to-run noise; manifest legacy fields and `run_config.json`
schema match exactly; all differences are the documented, intended ones. This
completes the Phase 3G gate. **Phase 4 (second plugin) is now unblocked.**

Feature runbook:
`governance/runbooks/features/test_suite_migration/plan.md`

## Why Phase 3G exists

Phases 3C–3F made the staged attempt path zero-legacy (environment, MAVLink
control/monitor, wind injection all plugin-owned). Phase 3G is the proof gate:
run the staged path live and show it is equivalent to the genuine legacy
runner, side by side. Critically, the legacy half must be the **real legacy
tool run directly**, not the legacy strategy routed through the new framework —
otherwise the comparison is circular (a shared wrapper bug could hide in both).

## Runs compared

Both: combo `wind_x_04_y_04` (4 m/s E, 4 m/s N), `--auto-wind-phase before-arm`,
`--wind-world-mode calm-runtime`, `--wipe-eeprom`, `--no-param-local`, single
attempt, no crippling outer timeout. Same machine, same mission, same params.

| | Staged | Legacy-direct |
| --- | --- | --- |
| Entry point | `test_suite.cli.run_suite --attempt-strategy staged` | `compat_scripts/run_matrix.py` (→ `run_one.run_one`) |
| Code path | plugin-owned env/MAVLink/wind/analysis; no `run_one` | legacy `run_matrix`/`run_one`; no `test_suite` code |
| Raw run dir | `var/runs/test_suite_phase3f_staged_complete_20260601T134207/` | `var/runs/test_suite_phase3g_legacy_direct_20260601T142339/` |
| Curated | `evidence/curated_logs/test_suite_phase3f_staged_live_20260601/` | `evidence/curated_logs/test_suite_phase3g_legacy_compare_20260601/` |
| BIN sha256 | `e179ac1530160db86f86e1c4f1868a0e82d97ec272a239b07b5e73989dd52330` | `d152433399e95f66692d878c7b0ebd885560d39a34e6426ee32e9c9e9cdd07a5` |

## Outcome parity — identical

| Field | Staged | Legacy-direct |
| --- | --- | --- |
| status | `success_full` | `success_full` |
| analysis_status | `done` | `done` |
| run_alias | `run_01` | `run_01` |
| mission_completed_full / square / loiter | True / True / True | True / True / True |
| wind echo (strict-verified) | `{x:4.0, y:4.0, z:0.0, enable_wind:True}` | `{x:4.0, y:4.0, z:0.0, enable_wind:True}` |

## Flight metrics — within SITL run-to-run nondeterminism

| Metric | Staged | Legacy-direct | Δ |
| --- | --- | --- | --- |
| square overall RMS true-path dev (m) | 58.71 | 58.57 | 0.14 |
| square overall p95 (m) | 130.99 | 131.96 | 0.96 |
| square overall max (m) | 219.34 | 218.69 | 0.65 |
| square segment_count | 20 | 20 | 0 |
| square sample_count | 13247 | 13222 | 25 |
| loiter turns_complete | True | True | — |

Sub-1% deltas on stochastic SITL flights. Two independent flights of the same
mission cannot be more equal without being the same run; the differences are
timing/EKF/scheduler jitter, not behavior.

## Schema/artifact parity

- **`run_config.json`: identical key set (zero schema diff).** The only value
  differences on shared keys are `sitl_bin_dir` and `sitl_use_dir`, which differ
  solely because the two runs used different campaign-root paths. Tautological,
  not behavioral.
- **Manifest row:** every shared legacy field matches exactly (`status`,
  `combo_key`, `x/y_wind_mps`, `target_run_index`, `attempt_index`,
  `success_class`, `mission_completed_full`, `square_completed`,
  `loiter_completed`, `analysis_status`, `run_alias`). Zero value diffs.
- **Complete artifact set both sides:** named BIN, `true_path_deviation/` and
  `square_loiter_mission_metrics/` outputs, `run_summary.json`, `run_01` alias.

## Documented accepted differences (intended, not failures)

1. **Additive generic manifest fields.** Staged rows carry the Phase 2 generic
   fields (`schema_version`, `case_id`, `parameters`, `verdict`,
   `stimulus_result`, `analysis_results`, `artifacts`, `suite_name`,
   `started_at`, `finished_at`) written additively next to the legacy fields.
   Legacy rows do not. By design (Phase 2 contract).
2. **Provenance field placement.** Legacy embeds `mission_contract` and
   `param_file_provenance` in the manifest row; the staged path writes them in
   `run_config.json`. Present in both; relocated only. No information lost.
3. **`accept_square_only` counting policy.** The staged/new orchestrator excludes
   `success_square_only` from accepted counts unless `accept_square_only=True`;
   legacy `combo_successes` counts it. Irrelevant for this `success_full` run
   (both count it). See review.md "Post-legacy acceptance policy".
4. **`wind_injection_source` string.** Going forward staged writes
   `"test_suite staged wind_matrix plugin ..."` and legacy writes
   `"run_one.py ..."`. The curated staged artifact here predates that code fix
   and still shows the legacy string; it is preserved as-captured (see the
   Phase 3F report). Value-only divergence; run_config schema unchanged.

## Operational notes

- Both runs were launched without a crippling outer `timeout`; each tore down
  its own stack on completion via the orchestrator `finally`. An external
  signal kill (e.g. a short `timeout` wrapper) orphans SITL/Gazebo/MAVProxy
  children because cleanup is only in the Python `finally`; this is shared with
  legacy `run_matrix.py` and is a known, non-blocking hardening item.
- Each completed run left a detached MAVProxy survivor that was cleaned
  manually after exit; same root cause as above.

## Commands

```
# staged live (Phase 3F report)
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 \
  -m sim_ard_gaw.campaigns.test_suite.cli.run_suite --attempt-strategy staged \
  --auto-wind-phase before-arm --x-values 4 --y-values 4 \
  --runs-per-combo 1 --max-attempts-per-combo 1 \
  --campaign-root var/runs/test_suite_phase3f_staged_complete_20260601T134207 \
  --wind-world-mode calm-runtime --no-param-local --wipe-eeprom \
  --stack-settle-s 8 --heartbeat-timeout 120 --ready-timeout 120 \
  --upload-timeout 60 --arm-timeout 60 --mode-timeout 30 --mission-timeout 3600

# legacy-direct (this report's baseline)
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 \
  src/sim_ard_gaw/compat_scripts/run_matrix.py \
  --x-values 4 --y-values 4 --runs-per-combo 1 --max-attempts-per-combo 1 \
  --campaign-root var/runs/test_suite_phase3g_legacy_direct_20260601T142339 \
  --wind-world-mode calm-runtime --auto-wind-phase before-arm \
  --no-param-local --wipe-eeprom --stack-settle-s 8 \
  --heartbeat-timeout 120 --ready-timeout 120 \
  --mission-timeout 3600 --upload-timeout 60 --arm-timeout 60 --mode-timeout 30
```

## Acceptance

| Criterion | Result |
| --- | --- |
| Hard no-legacy staged tests pass (no-SITL) | PASS (import-blocker suite; 100 unit tests) |
| Bounded live staged wind case completes | PASS (`success_full`, Phase 3F) |
| Matching live legacy case run (legacy tool direct) | PASS (`success_full`, this report) |
| Staged/legacy manifests + artifacts compared, differences documented | PASS (this report) |
| Staged remains opt-in; legacy default unchanged | PASS |
| No second plugin added; no legacy script retired | PASS |

## Claim Boundaries

- This is one bounded combo (`wind_x_04_y_04`), not a full matrix. It proves
  staged/legacy equivalence for the proven scope, not a campaign-wide guarantee.
- Live proof was captured on this workstation.
- The orphan-on-signal-kill gap above is not closed.
- Phase 3G acceptance unblocks Phase 4 (one second non-wind plugin, zero
  framework-core edits). It does not by itself authorize Phase 5 (legacy
  retirement), which still requires Phase 4 acceptance.
- The old workspace `/home/ahmed/ardupilot_workspace` was not modified.
