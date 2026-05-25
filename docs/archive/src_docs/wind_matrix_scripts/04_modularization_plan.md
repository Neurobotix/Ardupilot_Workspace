# Modularization Plan

## Target Package

Create a package under:

```text
src/SIM_ARD_GAW/scripts/wind_matrix/
```

The existing top-level scripts should stay as CLIs during migration:

```text
run_one.py
run_matrix.py
run_matrix_round_robin.py
```

Eventually they should only parse CLI args, build config objects, call the package, and exit.

## Proposed Modules

### `config.py`

Owns paths, constants, and dataclasses.

Suggested objects:

- `WorkspacePaths`
- `MissionContract`
- `WindMatrixConfig`
- `TimeoutConfig`
- `AttemptConfig`
- `StackConfig`

Test target: instantiate configs with temporary roots and verify derived paths.

### `naming.py`

Owns pure naming helpers:

- `combo_key(x, y)`
- `attempt_key(n)`
- `run_alias(n)`
- `attempt_id(combo, rep, attempt_idx)`
- `named_bin_filename(combo, rep, attempt_idx)`
- `parse_focus_combo(text)`
- `parse_wind_values(text, allowed_values)`

Test target: pure unit tests, no files or SITL.

### `env.py`

Owns runtime environment construction:

- `preferred_python(paths)`
- `runtime_env(paths, base_env=None)`

Important change: merge Gazebo paths with any existing environment values instead of using `setdefault`.

Test target: feed fake existing env and assert required paths are present exactly once.

### `filesystem.py`

Owns atomic JSON/text writes and simple file readers:

- `write_json_atomic(path, data)`
- `read_json(path, default)`
- `write_text_atomic(path, text)`
- `csv_rows(path)`

Test target: `tmp_path` tests for atomic output and CSV parsing.

### `manifest.py`

Owns manifest state and acceptance queries:

- `load_manifest(root)`
- `save_manifest(root, manifest)`
- `reconcile_manifest_bookkeeping(root, manifest)`
- `combo_successes(manifest, combo, require_analysis=False)`
- `next_attempt_index(root, manifest, combo)`
- `save_campaign_summary(root, manifest, matrix_values=None)`

Add:

- `AttemptStatus` enum or constants object.
- `ManifestLock` context manager.
- Explicit terminal status sets including `failed_analysis`.

Test target: synthetic manifests in `tmp_path`; duplicates, stale running, alias fixes, subset summary, require-analysis acceptance.

### `layout.py`

Owns directory creation:

- `ensure_campaign_scaffold(root, matrix_values)`
- `combo_runs_dir(root, combo)`
- `ensure_run_alias_link(link, target)`

Test target: symlink behavior and scaffold creation in `tmp_path`.

### `wind.py`

Owns wind payloads and verification:

- `build_wind_payload(x, y)`
- `parse_wind_echo(stdout)`
- `wind_echo_matches(parsed, x, y, tolerance)`
- `publish_wind(topic, x, y, runner, strict_echo)`
- `render_static_wind_world(source_sdf, x, y)`
- `parse_sdf_world_wind(path_or_text)`
- `validate_sdf_world_wind(...)`

Dependency inversion: accept a command runner instead of calling `subprocess.run` directly.

Test target: pure parser/render tests plus fake command runner tests. No Gazebo needed.

### `processes.py`

Owns local process launch and cleanup:

- `launch_process(cmd, cwd, env, log_path)`
- `ensure_process_alive(name, proc, log_path)`
- `cleanup_stack(launch_script, env, timeout)`
- `tail_text(path, max_chars)`

Test target: fake/exited subprocess objects where possible; small local command smoke tests if needed.

### `stack.py`

Owns SITL/Gazebo launch commands:

- `build_sitl_command(config)`
- `launch_sitl(config, log_path, use_dir=None)`
- `write_and_launch_gazebo(config, wind, log_path, world_out_path)`
- `sitl_bin_dir(use_dir)`

Test target: command list construction with no process launch; generated SDF path handling.

### `mavlink_connection.py`

Owns connection and readiness:

- `wait_for_heartbeat(mavlink_addr, timeout, mavlink_factory)`
- `wait_for_vehicle_ready(master, timeout, force_arm)`

Dependency inversion: pass a MAVLink connection/fake object.

Test target: fake message streams for heartbeat, GPS, EKF, prearm text, timeout.

### `mission_upload.py`

Owns mission parsing, upload, and verification:

- `mission_item_count(mission_file)`
- `load_mission_items(mission_file, target_system, target_component)`
- `upload_mission(master, mission_file, timeout)`
- `verify_mission(master, uploaded_items, timeout)`

Test target: use fixture waypoint files and fake MAVLink request/response streams. This module is critical and should have the most protocol tests.

### `vehicle_control.py`

Owns vehicle commands:

- `arm_vehicle(master, timeout, force_arm)`
- `set_auto_mode(master, timeout)`
- `settle_after_arm_before_auto(master, settle_s)`

Test target: fake MAVLink ACK and heartbeat streams.

### `monitor.py`

Owns passive mission classification:

- `monitor_until_disarm(master, monitor_log, timeout_s, mission_contract, mission_pre_loaded=False, stop_on_square_loiter=False)`
- `MissionMonitorState`

Important change: accept `MissionContract` instead of reading hardcoded globals.

Test target: synthetic MAVLink messages proving full mission success, square-only success, timeout, invalid jump, entry waypoint too far, and manual-vs-auto late monitor behavior.

### `logs.py`

Owns BIN discovery/copy:

- `collect_bin_log(before_names, started_wall, log_dir, strict_new_names)`
- `copy_bin_to_attempt(source, attempt_dir, final_name)`

Test target: `tmp_path` with fake `.BIN` files and controlled mtimes.

### `analysis.py`

Owns postprocessing subprocess invocation:

- `build_analysis_commands(bin_path, attempt_dir, position_source)`
- `run_analysis(bin_path, attempt_dir, runner, deadline=None)`

Test target: command construction and fake runner behavior for success, failure, timeout.

### `run_summary.py`

Owns `run_summary.json` synthesis:

- `build_run_summary(record, bin_path, attempt_dir, mission_contract)`

Test target: fixture CSV/JSON analysis outputs. Include missing-file and NaN cases.

### `attempt_runner.py`

Owns the high-level attempt state machine:

- `run_attempt(attempt_config, services) -> AttemptRecord`

This is where the current `run_one(...)` workflow should land, but with dependencies injected:

- wind service
- MAVLink service
- mission uploader
- monitor
- log collector
- analyzer
- manifest repository

Test target: fake all services and assert state transitions, artifact writes, status classification, and manifest updates.

### `scheduler.py`

Owns campaign selection logic:

- `combo_order(x_values, y_values)`
- `pending_combos(manifest, values, runs_per_combo, require_analysis)`
- `sequential_campaign(...)`
- `round_robin_campaign(...)`

Test target: pure scheduling with synthetic manifests. No SITL.

## Migration Order

1. Extract pure helpers first: `naming.py`, `filesystem.py`, `env.py`.
2. Extract manifest and layout: `manifest.py`, `layout.py`.
3. Extract wind parsing/rendering: `wind.py`.
4. Extract log collection and analysis command construction: `logs.py`, `analysis.py`.
5. Extract monitor with a `MissionContract`.
6. Extract mission upload and vehicle control behind fakeable MAVLink adapters.
7. Move SITL/Gazebo command construction into `stack.py`.
8. Create `attempt_runner.py` and make `run_one.py` call it.
9. Create `scheduler.py` and make both matrix scripts call it.
10. Delete `run_one_og.py` only after equivalent manual-mode behavior is covered by tests and `run_one.py` remains backward-compatible.

## Compatibility Strategy

Do not change CLI behavior in the first extraction pass.

For each migration step:

1. Move code into the new module.
2. Import it from the old script.
3. Add tests for the new module.
4. Run a lightweight CLI parse/import check.
5. Only then move the next responsibility.

This prevents the refactor from becoming another giant operational change.

