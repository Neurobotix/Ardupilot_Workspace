# Findings

> Update:
> the highest-priority wind-matrix automation bug has now been root-caused.
> See [09 Matrix Launcher Environment Root Cause](09_matrix_launcher_environment_root_cause.md).
> The key issue was `runtime_env()` preserving inherited `GZ_SIM_*` variables
> through `setdefault()`, while the working `launch.sh` path prepended the
> required Gazebo plugin/resource paths deterministically.

## What Is Right

The scripts have several good ideas worth preserving:

- Durable attempt directories make failed attempts auditable.
- The manifest records attempt status, raw log paths, aliases, analysis status, notes, and timing.
- `reconcile_manifest_bookkeeping(...)` catches stale `running` attempts and duplicate accepted slots.
- Named BIN copies make downstream analysis independent of ArduPilot's original log names.
- `run_one.py` verifies mission upload by downloading mission items back before arming.
- Round-robin isolated SITL `--use-dir` avoids global log ambiguity.
- `run_matrix.py` and `run_matrix_round_robin.py` launch Gazebo from a generated static-wind SDF, which is more reproducible than relying only on topic publication.
- `run_one.py` archives and validates the generated SDF wind before recording a preloaded-wind attempt.
- `require_analysis` is the right idea: a mission success without usable analysis should not silently occupy a final accepted slot.
- Analysis outputs are copied into the attempt directory, which keeps provenance close to the run.

## What Is Wrong

The main wrong thing is not one bug; it is that unrelated failure domains are fused together.

- `run_one.py` is a workflow, a MAVLink client, a manifest database, a process runner, a metrics summarizer, a filesystem layout manager, and a CLI in one file.
- Functions depend heavily on global constants, so tests need the real repository layout unless refactored.
- Most functions directly touch subprocesses, time, MAVLink, files, or global directories.
- There is no manifest lock. Two runners pointed at the same campaign root can corrupt or misclassify attempts.
- `load_manifest(...)` and stale-running reconciliation can mark an actually active `running` attempt as interrupted if another process loads the same campaign.
- `save_campaign_summary(...)` always summarizes the fixed global `WIND_VALUES` matrix, even when a run is scoped to a subset or `--focus-combo`.
- `run_matrix.py` does not use isolated SITL log directories, so its log collection is less reliable than round-robin.
- `run_one.py` catches broad exceptions and converts them to an `error` record. That is useful for durability but makes orchestrator control flow less explicit.
- The status taxonomy is spread across string constants and ad hoc checks. `failed_analysis` is introduced by newer logic but not represented as a first-class terminal status set.
- The mission layout is hardcoded as sequence constants. That is acceptable for the one certified mission, but it is not safe as a reusable campaign engine.
- SDF mutation uses a regex against the first `<wind><linear_velocity>` match. It is simple, but not a real SDF/XML transform.
- Default wind topic injection verification trusts a successful publisher return unless strict echo verification is enabled by environment variable.
- `runtime_env()` uses `setdefault` for Gazebo paths. If the caller already has `GZ_SIM_RESOURCE_PATH` or `GZ_SIM_SYSTEM_PLUGIN_PATH`, required project paths may not be appended. This was later confirmed as the root cause of the automated 12/12 matrix wind mismatch; see [09 Matrix Launcher Environment Root Cause](09_matrix_launcher_environment_root_cause.md).
- CLI wrappers and library functions are mixed, which makes imports have application-level side effects such as matplotlib config setup.

## Highest-Risk Failure Modes

1. A shared campaign root is used by two live processes.

   Result: stale-running recovery and manifest writes can step on active attempts. The fix is a campaign-level lock plus atomic read-modify-write discipline.

2. A mission file changes but sequence constants do not.

   Result: monitor classification and run summaries can report square/loiter success against the wrong mission segment. The fix is mission-contract metadata parsed or validated before launch.

3. BIN log discovery uses the global ArduPilot log directory.

   Result: the wrong `.BIN` can be copied if another SITL run wrote nearby logs. The fix is to use isolated `--use-dir` for every orchestrated attempt.

4. Wind is assumed from metadata rather than independently proven.

   Result: a run can be labeled as one wind vector while Gazebo used another. Static SDF validation helps, but topic injection mode still needs default echo verification or a better simulator-side assertion.

5. Analysis failure handling is policy-dependent but embedded in the attempt workflow.

   Result: changing "accepted run" policy requires editing the giant runner. The fix is an acceptance policy module that can be tested with synthetic records.

## Keep vs Replace

Keep:

- Attempt directory layout.
- Manifest plus CSV export.
- Alias symlink idea.
- Mission verification logic.
- Round-robin scheduling behavior.
- Static wind world archive/validation.
- Isolated SITL log capture.
- Analysis provenance in attempt directories.

Replace or extract:

- Global constants as implicit configuration.
- Monolithic `run_one(...)`.
- Regex-only SDF editing as the long-term interface.
- Global log-dir fallback for orchestrated runs.
- Ad hoc status strings.
- Hardcoded mission sequence assumptions.
- Broad manifest mutation without locks.
