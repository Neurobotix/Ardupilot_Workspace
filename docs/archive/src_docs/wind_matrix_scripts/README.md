# Wind Matrix Script Study

This documentation studies the four campaign runner scripts:

- [`run_one.py`](../../scripts/run_one.py)
- [`run_one_og.py`](../../scripts/run_one_og.py)
- [`run_matrix.py`](../../scripts/run_matrix.py)
- [`run_matrix_round_robin.py`](../../scripts/run_matrix_round_robin.py)

The short version: these scripts are doing too many jobs at once. The core ideas are useful, and several newer protections are good, but the implementation has grown into a single operational knot where launch, wind setup, MAVLink control, mission monitoring, log collection, analysis, campaign bookkeeping, and scheduling all share global constants and direct filesystem/subprocess side effects.

## Document Set

- [00 Script Inventory](00_script_inventory.md): size, ownership, and function-level map of the four files.
- [01 Current Behavior](01_current_behavior.md): what each script does today, and how data flows through a run.
- [02 Common vs Different](02_common_vs_different.md): what is duplicated, shared, and genuinely different across the scripts.
- [03 Findings](03_findings.md): what is right, what is wrong, and the highest-risk failure modes.
- [04 Modularization Plan](04_modularization_plan.md): concrete modules to extract, with interfaces and migration order.
- [05 Testing Plan](05_testing_plan.md): reproducible tests for each module, from pure unit tests up to SITL smoke tests.
- [06 High-Wind 12/12 Debug History](06_high_wind_12_12_debug_history.md): manual 12/12 wind run, failures, parameter changes, final working setup, and commands.
- [07 Wind Pipeline Investigation Handoff](07_wind_pipeline_investigation_handoff.md): historical investigation of wind, airspeed, and preloaded-world validation layers. Superseded for the matrix automation root cause by document 09.
- [08 Automated Test Suite Blueprint](08_automated_test_suite_blueprint.md): proposed test coverage for the wind matrix tooling.
- [09 Matrix Launcher Environment Root Cause](09_matrix_launcher_environment_root_cause.md): resolved cause of the automated 12/12 wind mismatch; matrix launched Gazebo with drift-prone inherited `GZ_SIM_*` paths instead of the deterministic `launch.sh` environment.

## Practical Goal

The target architecture is not "make it pretty". The target is:

1. Every behavior has one owner module.
2. Every owner module has tests that can run without Gazebo/SITL where possible.
3. The expensive SITL/Gazebo path becomes a small integration layer, not the only way to know whether the code works.
4. The CLI scripts become thin wrappers around tested modules.

That gives you a way to say: wind rendering passed, manifest reconciliation passed, monitor classification passed, mission upload passed against a fake MAVLink stream, and only then spend time running a full aircraft simulation.
