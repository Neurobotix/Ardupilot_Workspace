# Testing Plan

## Test Layers

Use three layers:

1. Pure unit tests: no SITL, no Gazebo, no MAVLink socket, no real subprocess.
2. Component tests with fakes: fake MAVLink streams and fake command runners.
3. Integration smoke tests: real SITL/Gazebo only for a small number of controlled cases.

Most bugs should be caught in layers 1 and 2.

## Unit Tests

### Naming

Test:

- `combo_key(0, 4) == "wind_x_00_y_04"`
- `attempt_key(1) == "attempt_001"`
- `run_alias(3) == "run_03"`
- focus combo parser accepts `wind_x_08_y_12` and `x_08_y_12`
- invalid focus combos fail with useful errors
- wind value parser rejects values outside the matrix

### Manifest

Use `tmp_path`.

Test:

- missing manifest creates default manifest.
- save writes both JSON and CSV.
- stale `running` record becomes `interrupted`.
- duplicate `attempt_id` raises.
- duplicate successful `target_run_index` raises.
- success gets correct `run_alias`.
- non-success loses stale `run_alias`.
- `require_analysis=True` counts only `analysis_status == "done"`.
- campaign summary respects a subset matrix when provided.

### Wind

Test:

- wind payload formatting for `(12, 8)`.
- echo parser extracts `x`, `y`, `z`, and `enable_wind`.
- echo matcher rejects wrong axis, missing z, disabled wind, and values outside tolerance.
- SDF static wind rendering changes exactly one wind vector.
- SDF parser rejects missing wind.
- SDF validator rejects mismatched archived wind.

### Timeout Budget

Test:

- timeout passes through without slot deadline.
- timeout clamps to remaining slot.
- timeout raises when remaining time is exhausted.
- reserve time is honored.

### Log Collection

Use fake `.BIN` files in `tmp_path`.

Test:

- strict isolated mode returns exactly one new name.
- strict isolated mode fails on multiple new names.
- global fallback picks latest new file.
- global fallback can use mtime when names existed before.
- no candidates returns `None`.

### Analysis Command Builder

Test:

- true-path command uses `--position-source sim`.
- square-loiter command uses the expected output directory.
- command runner failure records stdout/stderr and raises.
- deadline timeout raises a timeout-specific error.

### Run Summary

Use fixture analysis JSON/CSV files.

Test:

- square metrics are square-only by active leg seq range.
- NTUN comparison uses square-only rows.
- loiter `full_window` and `tracking_after_capture` fields are separated.
- NaN/inf values become `None`.
- missing optional loiter data results in `"loiter": null`.

## MAVLink Component Tests

Build a fake `master` object with:

- `target_system`
- `target_component`
- `recv_match(...)`
- `wait_heartbeat(...)`
- `mode_mapping()`
- `mav` object that records sent messages
- `set_mode_apm(...)`

### Monitor Tests

Feed synthetic message streams.

Test:

- full mission: arm, front-half progress, final seq, disarm.
- square-loiter early: reaches loiter-to-alt and stops with `completed_square_loiter_early`.
- timeout: no disarm before timeout.
- invalid start: mission jumps to loiter before front-half progress.
- manual mode rejects late-joining front-half miss.
- auto mode with preloaded mission does not misclassify a late monitor.
- entry waypoint pass distance beyond limit creates invalid start.

### Mission Upload Tests

Feed request/ack streams.

Test:

- normal upload serves every requested item and returns items.
- early `MISSION_ACK` before all items is ignored.
- invalid requested seq raises.
- non-accepted final ack raises.
- upload timeout reports sent count.
- verification rejects count mismatch.
- verification rejects command/frame/coordinate/alt mismatches.
- verification allows seq 0 home-row normalization.
- verification handles LAND param4 normalization.
- verification handles LOITER_TO_ALT preserved params.

### Vehicle Control Tests

Test:

- arm succeeds when armed heartbeat appears.
- arm rejects unexpected command result.
- arm times out.
- AUTO mode succeeds when heartbeat mode becomes `AUTO`.
- AUTO mode rejects unexpected ACK.
- settle drains relevant STATUSTEXT without sending commands.

## Attempt Runner Tests

Once `attempt_runner.py` exists, fake every external service.

Test:

- happy full mission success writes manifest, alias, analysis, and summary.
- square-loiter-only success requires `accept_square_only=True`.
- failed mission skips analysis.
- invalid start records failure notes.
- analysis failure keeps mission success when `require_analysis=False`.
- analysis failure downgrades to `failed_analysis` when `require_analysis=True`.
- wind failure records `error` and `analysis_status=not_run`.
- no BIN log records `error`.
- slot deadline exhaustion records the phase that timed out.

## Scheduler Tests

Use synthetic manifests only.

Test:

- sequential order is y-major then x.
- completed combos are skipped.
- failed attempts do not count as accepted.
- `require_analysis` changes pending set.
- focus combo restricts values.
- round-robin rep stays tied to accepted count plus one.
- max-passes stops cleanly.
- max-attempts-per-combo is enforced for sequential scheduler.

## Integration Smoke Tests

Keep these few and explicit because they are expensive.

Suggested smoke set:

- Import all CLIs: `python -m py_compile` on the package and wrappers.
- CLI help works for all wrappers.
- Dry command-construction test for SITL and Gazebo with no process launch.
- One real calm-wind SITL/Gazebo auto attempt in a temporary campaign root.
- One `--accept-square-only` attempt if the full mission is too slow.

For real simulations, assert only infrastructure facts first:

- manifest exists.
- attempt record exists.
- `run_config.json` exists.
- `wind_injection.json` exists.
- monitor log exists.
- copied `.BIN` exists for completed attempts.
- success attempts have analysis artifacts and `run_summary.json`.

Do not make every unit test depend on this. SITL should prove the stack still works, not carry all correctness.

