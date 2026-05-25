# Common vs Different

## Common Concepts

All four scripts share the same campaign vocabulary:

- Wind combinations are `(x_wind_mps, y_wind_mps)` in Gazebo ENU world frame.
- Combo keys are `wind_x_XX_y_YY`.
- Runs target numbered repetitions, written as aliases like `run_01`.
- Attempts are durable directories like `attempt_001`.
- Success means either full mission completion or square-plus-loiter completion when explicitly accepted.
- The campaign manifest is the source of truth for accepted runs.

## Common Code Between `run_one_og.py` and `run_one.py`

Large blocks are conceptually the same:

- Path constants and runtime environment construction.
- Manifest load/save logic.
- Attempt naming and alias naming.
- Manifest reconciliation for stale `running` records and alias normalization.
- Passive MAVLink monitor structure.
- BIN log collection idea.
- Postprocessing runner idea.
- Run-summary synthesis.
- Attempt workflow skeleton.
- CLI argument style.

The duplication is useful historically but dangerous now. The two files are no longer equivalent, so fixes can land in one and not the other.

## What `run_one.py` Adds Over `run_one_og.py`

`run_one.py` adds several important capabilities:

- `mavwp` mission parsing and upload.
- Vehicle readiness gate before auto launch.
- Mission download verification.
- Arm command support, including force-arm magic.
- AUTO mode switching.
- Static preloaded SDF wind validation.
- Optional wind topic echo verification.
- Slot-deadline clamping.
- Isolated SITL log directory support.
- Campaign summary generation.
- `require_analysis` retry semantics.
- More detailed analysis summary fields, especially SIM position source and loiter after-capture metrics.

These are real improvements. The problem is that they were added into the same giant workflow instead of behind separately testable interfaces.

## Difference Between `run_matrix.py` and `run_matrix_round_robin.py`

`run_matrix.py`:

- Sequential by combo.
- Finishes one combo before moving to the next.
- Has `--max-attempts-per-combo`.
- Wipe EEPROM is off by default.
- Uses the global log-dir strategy indirectly.
- Simpler slot and timeout model.

`run_matrix_round_robin.py`:

- One attempt per pending combo per pass.
- Better for long or flaky high-wind cases.
- Has `--max-passes`, not a per-combo attempt limit.
- Wipe EEPROM is on by default.
- Uses isolated SITL `--use-dir`.
- Passes a slot deadline into `run_one.py`.
- Can require analysis completion before counting a run.

The round-robin version is closer to the desired future scheduler, but it still imports and reuses process launch functions from `run_matrix.py`, which makes boundaries fuzzy.

## Shared Responsibilities That Should Become Modules

These responsibilities are shared or reused enough to deserve single owners:

- Path and experiment configuration.
- Runtime environment assembly.
- Naming and directory layout.
- Manifest persistence and reconciliation.
- Campaign summary generation.
- Process launch and cleanup.
- SDF wind rendering and validation.
- Gazebo topic wind publish and echo verify.
- MAVLink connection and readiness.
- Mission upload and mission identity verification.
- Vehicle arm/mode control.
- Mission progress monitoring.
- BIN log discovery/copy.
- Analysis subprocess execution.
- Run-summary construction.
- Attempt orchestration.
- Campaign scheduling.

## Different Responsibilities That Should Stay Separate

These should not be merged together:

- "Run one attempt" and "decide which attempt to run next".
- "Launch SITL/Gazebo" and "control the vehicle over MAVLink".
- "Publish or preload wind" and "analyze the resulting flight".
- "Classify mission success" and "parse analysis metrics".
- "Update manifest" and "do physical simulation side effects".

Keeping those apart is what will make failures local and testable.

