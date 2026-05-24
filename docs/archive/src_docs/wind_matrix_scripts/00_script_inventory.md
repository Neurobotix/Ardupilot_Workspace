# Script Inventory

## File Sizes

At the time of this study:

| Script | Lines | Main role |
| --- | ---: | --- |
| `run_matrix_round_robin.py` | 362 | Slot scheduler and campaign pass loop |
| `run_matrix.py` | 308 | Sequential matrix orchestrator and process launcher |
| `run_one_og.py` | 1265 | Legacy manual single-attempt runner |
| `run_one.py` | 2422 | Current single-attempt runner plus most shared campaign logic |

The main mass is in `run_one.py`. Any sane refactor starts there, but the orchestrators also need cleanup because they currently reach into `run_one.py` internals.

## `run_one.py` Functional Map

Path and environment:

- `preferred_python`
- `cte_param_file_stack`
- `runtime_env`
- `sitl_bin_dir`
- `cleanup_stack_for_analysis`

Generic data/file helpers:

- `write_json`
- `read_json`
- `csv_rows`
- `write_text_atomic`
- numeric cleaners and text normalizers

Naming and layout:

- `combo_key`
- `attempt_key`
- `run_alias`
- `attempt_id`
- `named_bin_filename`
- `combo_runs_dir`
- `ensure_run_alias_link`
- `ensure_scaffold`

Manifest and campaign summary:

- `load_manifest`
- `save_manifest`
- `save_campaign_summary`
- `reconcile_manifest_bookkeeping`
- `combo_successes`
- `next_attempt_index`

Wind:

- `parse_wind_echo`
- `wind_echo_matches`
- `start_wind_echo`
- `finish_wind_echo`
- `inject_wind`
- `parse_sdf_world_wind`
- `preloaded_wind_artifact`

MAVLink connection and readiness:

- `wait_for_heartbeat`
- `wait_for_vehicle_ready`

Mission upload and verification:

- `mission_item_count`
- `mission_item_int`
- `upload_mission`
- `verify_mission`

Vehicle control:

- `arm_vehicle`
- `settle_after_arm_before_auto`
- `set_auto_mode`

Mission monitor:

- `monitor_until_disarm`

Log collection:

- `collect_bin_log`

Analysis:

- `run_analysis`
- `build_run_summary`

Attempt workflow and CLI:

- `run_one`
- `main`

This is the exact problem: almost every one of those groups is a module boundary, but all of them are in one import namespace and share globals.

## `run_one_og.py` Functional Map

`run_one_og.py` has the same broad skeleton as `run_one.py` but lacks the newer automated-control and slot-aware pieces.

Present:

- path/env helpers
- manifest helpers
- wind topic publishing
- passive heartbeat wait
- passive mission monitor
- global BIN discovery
- postprocessing
- run summary
- manual-only attempt workflow
- CLI

Missing compared with `run_one.py`:

- mission upload
- mission verification
- vehicle readiness check
- arm command
- AUTO mode command
- slot deadline clamping
- isolated SITL log directory support
- static preloaded SDF wind artifact support
- campaign summary writer
- `require_analysis`
- richer loiter and NTUN summary fields

This file should be treated as historical reference, not as a second implementation to keep modifying.

## `run_matrix.py` Functional Map

Parsing and ordering:

- `parse_wind_values`
- `combo_order`
- `parse_args`

Process handling:

- `cleanup_stack`
- `tail_text`
- `ensure_process_alive`
- `launch_process`
- `launch_sitl`
- `launch_gazebo`

Wind world generation:

- `write_static_wind_world`

Campaign loop:

- `main`

`run_matrix.py` is short, but it owns important process launch behavior that `run_matrix_round_robin.py` imports directly. That should become `stack.py` or `processes.py`.

## `run_matrix_round_robin.py` Functional Map

Parsing and selection:

- `parse_focus_combo`
- `parse_args`
- `pending_combos`

Slot loop:

- `main`

It mostly composes functions from `run_matrix.py` and `run_one.py`. That composition is the correct idea, but the imports point at scripts instead of stable library modules.

## Current Dependency Shape

```text
run_matrix_round_robin.py
  imports run_matrix.py
  imports run_one.py

run_matrix.py
  imports run_one.py

run_one.py
  imports pymavlink, matplotlib/numpy, subprocess, filesystem, analysis scripts

run_one_og.py
  standalone old sibling of run_one.py
```

Desired shape:

```text
thin CLI scripts
  call wind_matrix package modules

wind_matrix.scheduler
  calls wind_matrix.attempt_runner and wind_matrix.stack

wind_matrix.attempt_runner
  composes manifest, wind, mavlink, monitor, logs, analysis

leaf modules
  own pure parsing, naming, layout, config, and command construction
```

