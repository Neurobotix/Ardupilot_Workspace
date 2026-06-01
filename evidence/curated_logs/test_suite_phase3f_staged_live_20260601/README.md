# Curated live staged wind run — Phase 3F (2026-06-01)

First completed **zero-legacy staged** wind-matrix attempt run live through
SITL + Gazebo using `test_suite.cli.run_suite --attempt-strategy staged`.

- Combo: `wind_x_04_y_04` (4 m/s East, 4 m/s North), `before-arm` wind phase.
- Result: `success_full` — full square + 5-lap + loiter + land mission flown to
  disarm; analysis completed; `run_01` alias created.
- Wind injection verified live: strict gz-topic echo matched the requested
  payload (`echo_parsed_wind = {x:4.0, y:4.0, z:0.0, enable_wind:True}`).

## What is curated here

Summaries and provenance only. The raw 57 MB flight log and the large
analysis CSV/PNG artifacts remain under `var/` (runtime home) and are not
tracked as evidence.

- `manifest.json` / `manifest.csv` — campaign manifest snapshot.
- `campaign_summary.json` / `campaign_summary.csv` — accepted-run summary.
- `wind_x_04_y_04_attempt_001/run_summary.json` — curated analysis summary.
- `wind_x_04_y_04_attempt_001/run_config.json` — run provenance.
- `wind_x_04_y_04_attempt_001/wind_injection.json` — Gazebo wind injection
  result (strict echo verification).
- `wind_x_04_y_04_attempt_001/true_path_deviation/*_summary.json` and
  `square_loiter_mission_metrics/*_summary.json` — analysis summary JSONs.

## Raw runtime references (not promoted)

- Raw run directory:
  `var/runs/test_suite_phase3f_staged_complete_20260601T134207/`
- Raw BIN flight log:
  `var/runs/test_suite_phase3f_staged_complete_20260601T134207/wind_x_04_y_04/runs/attempt_001/wind_x_04_y_04__rep_01__attempt_001.BIN`
  - sha256: `e179ac1530160db86f86e1c4f1868a0e82d97ec272a239b07b5e73989dd52330`
- Stack/orchestrator logs:
  `var/runs/test_suite_phase3f_staged_complete_20260601T134207/scripts/orchestrator_logs/`

## Scope and limits

- This proves one live completed staged run. It is **not** a matched
  side-by-side legacy comparison; that remains Phase 3G work.
- Old-workspace `/home/ahmed/ardupilot_workspace` was not modified.
