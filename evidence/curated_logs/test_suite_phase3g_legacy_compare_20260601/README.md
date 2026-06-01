# Curated legacy comparison run — Phase 3G (2026-06-01)

Matched **legacy-direct** baseline for the Phase 3G staged-vs-legacy
comparison. This run was launched through the retained legacy tool directly —
`compat_scripts/run_matrix.py` → `campaigns.wind_matrix.run_matrix` →
`run_one.run_one(...)` — and touches **no** `test_suite` framework code. It is
the independent reference the staged live run is compared against.

- Combo: `wind_x_04_y_04` (4 m/s East, 4 m/s North), `before-arm` wind phase
  (legacy default is `after-takeoff`; overridden to match the staged run).
- Result: `success_full` — full square + 5-lap + loiter + land flown to disarm;
  analysis completed; `run_01` alias created.
- Wind injection verified live: strict gz-topic echo matched the requested
  payload (`echo_parsed_wind = {x:4.0, y:4.0, z:0.0, enable_wind:True}`).

## Command (legacy tool, direct)

```
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts env/bin/python3 \
  src/sim_ard_gaw/compat_scripts/run_matrix.py \
  --x-values 4 --y-values 4 --runs-per-combo 1 --max-attempts-per-combo 1 \
  --campaign-root var/runs/test_suite_phase3g_legacy_direct_20260601T142339 \
  --wind-world-mode calm-runtime --auto-wind-phase before-arm \
  --no-param-local --wipe-eeprom --stack-settle-s 8 \
  --heartbeat-timeout 120 --ready-timeout 120 \
  --mission-timeout 3600 --upload-timeout 60 --arm-timeout 60 --mode-timeout 30
```

## What is curated here

Summaries and provenance only. The raw 56 MB flight log and large analysis
CSV/PNG artifacts remain under `var/` and are not tracked as evidence.

- `manifest.json` / `.csv`, `campaign_summary.json` / `.csv`
- `wind_x_04_y_04_attempt_001/{run_summary,run_config,wind_injection}.json`
- analysis summary JSONs under `true_path_deviation/` and
  `square_loiter_mission_metrics/`

## Raw runtime references (not promoted)

- Raw run directory:
  `var/runs/test_suite_phase3g_legacy_direct_20260601T142339/`
- Raw BIN flight log:
  `.../wind_x_04_y_04/runs/attempt_001/wind_x_04_y_04__rep_01__attempt_001.BIN`
  - sha256: `d152433399e95f66692d878c7b0ebd885560d39a34e6426ee32e9c9e9cdd07a5`

## Comparison

Side-by-side analysis vs the staged live run
(`evidence/curated_logs/test_suite_phase3f_staged_live_20260601/`) is recorded
in `evidence/reports/features/2026-06-01_test_suite_migration_phase_3g.md`.

The old workspace `/home/ahmed/ardupilot_workspace` was not modified.
