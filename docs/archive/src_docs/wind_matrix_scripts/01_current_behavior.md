# Current Behavior

## Script Roles

### `run_one_og.py`

`run_one_og.py` is the older single-run script. It assumes SITL and Gazebo are already running, injects wind through `gz topic`, tells the human what to type in MAVProxy, passively monitors MAVLink until disarm or timeout, collects the newest `.BIN`, runs postprocessing, and updates the manifest.

Important traits:

- Manual control only.
- Does not upload the mission, arm, or switch modes.
- Uses the global ArduPilot log directory.
- Uses mtime/name heuristics to find the new `.BIN`.
- Runs analysis only for success statuses.
- Writes `manifest.json`, `manifest.csv`, `run_config.json`, `monitor.log`, copied `.BIN`, analysis logs, and `run_summary.json`.

### `run_one.py`

`run_one.py` is now the operational core. It contains almost everything from `run_one_og.py`, plus:

- Automated mission upload through MAVLink.
- Mission identity verification after upload.
- Vehicle readiness checks before automation.
- Arm and AUTO mode commands.
- Slot-deadline aware timeouts.
- Optional static preloaded wind world support.
- Optional strict Gazebo wind echo verification.
- Isolated SITL log directory support.
- Campaign summary output.
- `require_analysis` support that downgrades mission success to `failed_analysis` if postprocessing fails.

The public `run_one(...)` function is both an application workflow and a transaction manager. It creates attempt records, writes config artifacts, performs runtime actions, classifies the run, runs analysis, mutates aliases, saves manifests, and returns the final record.

### `run_matrix.py`

`run_matrix.py` is a sequential full-matrix orchestrator. For each wind pair, it repeatedly launches a fresh SITL/Gazebo stack and calls `run_one.run_one(...)` until the requested accepted run count is reached or a per-combo attempt limit is exceeded.

Key behavior:

- Iterates by `y`, then `x`.
- Starts SITL with `sim_vehicle.py`.
- Writes a per-attempt SDF world with static wind.
- Starts Gazebo with that generated world.
- Calls `run_one.run_one(..., manual_control=False, preloaded_wind_world=...)`.
- Cleans up the whole stack after every attempt.
- Counts accepted runs using `run_one.combo_successes(...)`.

This script does not use isolated SITL log directories. It depends on the global log-dir snapshot logic inside `run_one.py`.

### `run_matrix_round_robin.py`

`run_matrix_round_robin.py` is a scheduler on top of `run_matrix.py` and `run_one.py`. Instead of finishing one combo before moving on, it gives each pending combo one slot per pass.

Key behavior:

- Builds a pending combo list from the manifest.
- Supports `--focus-combo`.
- Computes an attempt monitor budget from `--slot-minutes` minus estimated infrastructure overhead.
- Uses isolated SITL `--use-dir` state per slot.
- Snapshots BIN names before SITL launch.
- Passes a hard monotonic slot deadline into `run_one.run_one(...)`.
- Supports `--require-analysis`.
- Cleans up stack after each slot.

This is currently the best orchestrator from a reproducibility perspective because it isolates SITL logs and ties each attempt to a slot budget.

## End-to-End Flow

For automated round-robin runs, the flow is:

1. `run_matrix_round_robin.py` loads args, loads manifest, writes campaign summary, computes slot budgets.
2. It asks `pending_combos(...)` which combos still need accepted runs.
3. For each pending combo, it creates log paths, cleanup runs, and a per-slot SITL state directory.
4. It snapshots existing `.BIN` names inside the isolated SITL log directory.
5. It launches SITL.
6. It writes a generated SDF with static wind.
7. It launches Gazebo with that SDF.
8. It calls `run_one.run_one(...)` with `manual_control=False`, `preloaded_wind_world`, isolated log inputs, and a slot deadline.
9. `run_one.run_one(...)` creates an attempt record and writes `run_config.json`.
10. It waits for heartbeat and automated readiness.
11. It validates/archive-records the preloaded wind SDF instead of publishing a wind topic.
12. It uploads the mission.
13. It verifies the mission by downloading it back item-by-item.
14. It arms, settles, switches to AUTO.
15. It monitors mission progress until disarm, timeout, invalid start, or square-loiter early stop.
16. It collects and copies the `.BIN`.
17. It classifies the run as success, failed, error, or failed-analysis.
18. It runs postprocessing for successful runs.
19. It writes `run_summary.json` and manifest/campaign summary files.
20. The orchestrator cleans up the stack, waits retry delay, then moves to the next slot.

## Main Artifacts

Per attempt:

- `run_config.json`
- `wind_injection.json`
- `monitor.log`
- copied named `.BIN`
- `true_path_deviation/`
- `square_loiter_mission_metrics/`
- `run_summary.json`
- stdout/stderr logs for analysis scripts

Per campaign:

- `manifest.json`
- `manifest.csv`
- `summary/campaign_summary.json`
- `summary/campaign_summary.csv`
- orchestrator or round-robin stack logs under `scripts/`

