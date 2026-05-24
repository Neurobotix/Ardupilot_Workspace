# Phase 0 Baseline - Foundation Freeze

Date/time: 2026-05-20T12:21:40+03:00

Timezone: Africa/Cairo

## Scope

Phase 0 establishes `/home/ahmed/ardupilot_workspace` as the read-only
production reference and records the baseline that
`/home/ahmed/ardupilot_workspace_next` must match or intentionally replace.

Production workspace was inspected only. No edit command was run in
`/home/ahmed/ardupilot_workspace`.

## Commands Run

- `sed -n '1,240p' governance/runbooks/full_migration_plan.md`
- `sed -n '1,260p' governance/runbooks/phase_0_foundation_freeze.md`
- `sed -n '1,260p' governance/standards/change_control.md`
- `sed -n '1,240p' .ai/index.md`
- `sed -n '1,240p' .ai/current.md`
- `git status --porcelain=v1 --untracked-files=all`
- `git rev-parse HEAD`
- `git branch --show-current`
- `git submodule status --recursive`
- `git -C src/ardupilot rev-parse HEAD`
- `git -C src/ardupilot status --porcelain=v1 --untracked-files=all`
- `git -C src/SIM_ARD_GAW rev-parse HEAD`
- `git -C src/SIM_ARD_GAW status --porcelain=v1 --untracked-files=all`
- `git -C src/ardupilot_gazebo rev-parse --show-toplevel`
- `git -C src/SITL_Models rev-parse --show-toplevel`
- `find src -maxdepth 4 -name .git -type d -print`
- `du -sh ...` for important roots listed below
- `wc -l governance/audits/migration_inventory.csv`
- `make doctor`
- `find . -xtype l -print`
- `find . ... -name '*.BIN' ... -name '*.tlog.raw' ...`
- `find config -path '*/.private' -print -o -path '*/.private/*' -print`
- `find .private -type f -print`
- `git check-ignore -v .private/README.md .private/config/plane_params.local.parm var/logs/example.BIN`

## Root Git Baseline

| Workspace | Branch | Root commit | Status |
| --- | --- | --- | --- |
| `/home/ahmed/ardupilot_workspace` | `main` | `a483a534fac1755ea9ba9a007f062981913366d6` | Dirty: `M .private/backup.log` |
| `/home/ahmed/ardupilot_workspace_next` | `main` | `UNKNOWN` | Bootstrap repo has no `HEAD`; 462 non-ignored files were untracked before this Phase 0 report was added. |

`workspace_next` root commit command:

```text
$ git rev-parse HEAD
fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree.
HEAD
```

Production root status command:

```text
$ git status --porcelain=v1 --untracked-files=all
 M .private/backup.log

$ git status --porcelain=v1 --untracked-files=all | sha256sum
f9ce222036c3d6bda7a4584a4f9f8df4bad1b3671b8f44bab8534476bd30e0b4  -
```

`workspace_next` root status summary:

```text
$ git status --short
?? .ai/
?? .gitignore
?? CHANGELOG.md
?? Makefile
?? README.md
?? assets/
?? config/
?? docs/
?? evidence/
?? governance/
?? pyproject.toml
?? requirements.txt
?? scripts/
?? setup.bash
?? src/
?? tests/
```

## Dependency Commits

| Dependency | Production value | `workspace_next` value | Evidence |
| --- | --- | --- | --- |
| Root workspace | `a483a534fac1755ea9ba9a007f062981913366d6` | `UNKNOWN` | `git rev-parse HEAD`; next has no `HEAD` commit. |
| `src/ardupilot` | `f198baa9c5609a292e6576bce832e66b30cfe0c0` | `UNKNOWN` | next command failed: `fatal: cannot change to 'src/ardupilot': No such file or directory`. |
| `src/SIM_ARD_GAW` | `fac4746653fb50d088a5c9209c80d0e5fda6b958` | `UNKNOWN` | next path is symlink-only compatibility, not a nested git checkout. |
| `src/ardupilot_gazebo` | `UNKNOWN` | `UNKNOWN` | `git -C src/ardupilot_gazebo rev-parse --show-toplevel` resolves to the workspace root in both workspaces. |
| `src/SITL_Models` | `UNKNOWN` | `UNKNOWN` | production resolves to root workspace; next path is absent. |

Nested git directories discovered in production:

```text
src/SIM_ARD_GAW/.git
src/ardupilot/.git
```

Nested git directories discovered in `workspace_next`: none.

## Nested Dirty State

Production `src/ardupilot`:

```text
$ git -C src/ardupilot status --porcelain=v1 --untracked-files=all
 M .gitignore
?? Tools/scripts/airspeed_vfrhud_bin_test.py
```

Production `src/SIM_ARD_GAW`:

```text
$ git -C src/SIM_ARD_GAW branch --show-current
testing-automation-reconstructed-history

$ git -C src/SIM_ARD_GAW status --porcelain=v1 --untracked-files=all
R  "models/mini_talon_backup/assets/Screencast from 2026-01-18 10-26-34.mp4" -> "archive/models/mini_talon_backup/assets/Screencast from 2026-01-18 10-26-34.mp4"
R  "models/mini_talon_backup/assets/image copy 2.png" -> "archive/models/mini_talon_backup/assets/image copy 2.png"
R  "models/mini_talon_backup/assets/image copy.png" -> "archive/models/mini_talon_backup/assets/image copy.png"
R  models/mini_talon_backup/assets/image.png -> archive/models/mini_talon_backup/assets/image.png
R  models/mini_talon_backup/assets/original.png -> archive/models/mini_talon_backup/assets/original.png
R  models/mini_talon_backup/meshes/ardupilot_logo.png -> archive/models/mini_talon_backup/meshes/ardupilot_logo.png
R  models/mini_talon_backup/meshes/icon.jpg -> archive/models/mini_talon_backup/meshes/icon.jpg
R  models/mini_talon_backup/meshes/iris_prop_cw.dae -> archive/models/mini_talon_backup/meshes/iris_prop_cw.dae
R  models/mini_talon_backup/meshes/mini_talon_forward_deck.dae -> archive/models/mini_talon_backup/meshes/mini_talon_forward_deck.dae
R  models/mini_talon_backup/meshes/mini_talon_fuselage.dae -> archive/models/mini_talon_backup/meshes/mini_talon_fuselage.dae
R  models/mini_talon_backup/meshes/mini_talon_fuselage_collision.stl -> archive/models/mini_talon_backup/meshes/mini_talon_fuselage_collision.stl
R  models/mini_talon_backup/meshes/mini_talon_fuselage_logos.dae -> archive/models/mini_talon_backup/meshes/mini_talon_fuselage_logos.dae
R  models/mini_talon_backup/meshes/mini_talon_left_aileron.dae -> archive/models/mini_talon_backup/meshes/mini_talon_left_aileron.dae
R  models/mini_talon_backup/meshes/mini_talon_left_ruddervator.dae -> archive/models/mini_talon_backup/meshes/mini_talon_left_ruddervator.dae
R  models/mini_talon_backup/meshes/mini_talon_left_tail.dae -> archive/models/mini_talon_backup/meshes/mini_talon_left_tail.dae
R  models/mini_talon_backup/meshes/mini_talon_left_tail_collision.stl -> archive/models/mini_talon_backup/meshes/mini_talon_left_tail_collision.stl
R  models/mini_talon_backup/meshes/mini_talon_left_wing.dae -> archive/models/mini_talon_backup/meshes/mini_talon_left_wing.dae
R  models/mini_talon_backup/meshes/mini_talon_left_wing_collision.stl -> archive/models/mini_talon_backup/meshes/mini_talon_left_wing_collision.stl
R  models/mini_talon_backup/meshes/mini_talon_left_wing_logo.dae -> archive/models/mini_talon_backup/meshes/mini_talon_left_wing_logo.dae
R  models/mini_talon_backup/meshes/mini_talon_main_wheel.dae -> archive/models/mini_talon_backup/meshes/mini_talon_main_wheel.dae
R  models/mini_talon_backup/meshes/mini_talon_main_wheel_collision.stl -> archive/models/mini_talon_backup/meshes/mini_talon_main_wheel_collision.stl
R  models/mini_talon_backup/meshes/mini_talon_right_aileron.dae -> archive/models/mini_talon_backup/meshes/mini_talon_right_aileron.dae
R  models/mini_talon_backup/meshes/mini_talon_right_ruddervator.dae -> archive/models/mini_talon_backup/meshes/mini_talon_right_ruddervator.dae
R  models/mini_talon_backup/meshes/mini_talon_right_tail.dae -> archive/models/mini_talon_backup/meshes/mini_talon_right_tail.dae
R  models/mini_talon_backup/meshes/mini_talon_right_tail_collision.stl -> archive/models/mini_talon_backup/meshes/mini_talon_right_tail_collision.stl
R  models/mini_talon_backup/meshes/mini_talon_right_wing.dae -> archive/models/mini_talon_backup/meshes/mini_talon_right_wing.dae
R  models/mini_talon_backup/meshes/mini_talon_right_wing_collision.stl -> archive/models/mini_talon_backup/meshes/mini_talon_right_wing_collision.stl
R  models/mini_talon_backup/meshes/propdrive_3536_frontplate.dae -> archive/models/mini_talon_backup/meshes/propdrive_3536_frontplate.dae
R  models/mini_talon_backup/meshes/propdrive_3536_motor_can.dae -> archive/models/mini_talon_backup/meshes/propdrive_3536_motor_can.dae
R  models/mini_talon_backup/model.config -> archive/models/mini_talon_backup/model.config
R  models/mini_talon_backup/model.sdf -> archive/models/mini_talon_backup/model.sdf
 M logs/017_params_old_009_matrix_r3_plugin_fixed/HIGH_WIND_OLD_PARAM_FAILURE_ANALYSIS.md
 D logs/Reports/automation_report.pdf
 D logs/Reports/feature_report.pdf
 M scripts/audit_bin_internal_wind.py
 M scripts/compare_campaign_mission_window.py
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/executive_summary.md
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/final_analysis_report.md
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/metadata.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/metrics_glossary.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/metrics_glossary.md
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/campaign_outcome_heatmap.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/combo_distribution_square_metrics.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/corner_performance_heatmap.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/directional_asymmetry_by_heading.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/directional_heading_heatmap.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/headtohead_envelope_split.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/headtohead_rms_vs_wind.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/lap_repeatability_by_combo.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/loiter_after_capture_heatmap.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/loiter_vs_square_scatter.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/per_combo_variability.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/replicate_strip_square_metrics.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/square_max_heatmap.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/square_p95_heatmap.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/square_rms_heatmap.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/plots/wind_magnitude_trends.png
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/presentation_recommendations.md
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/scientific_summary.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_accepted_runs_summary.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_accepted_runs_summary.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_accepted_runs_summary_sim.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_accepted_runs_summary_sim.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_campaign_outcome_summary.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_campaign_outcome_summary.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_combo_summary.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_combo_summary.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_failure_envelope_attempts.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_failure_envelope_attempts.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_loiter_summary.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_loiter_summary.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_loiter_summary_sim.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_loiter_summary_sim.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_mission_validation_summary.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_mission_validation_summary.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_position_source_summary.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/corrected_position_source_summary.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/old_vs_high_wind_param_stack.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/old_vs_high_wind_param_stack.json
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/square_corner_metrics_all.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/square_edge_metrics_all.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/tables/square_lap_metrics_all.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/postprocessing_input_manifest.csv
?? logs/020_Old_Param_Fixed_CTE_Report/summary/rejected_manifest_rows.csv
?? logs/021_Sensor_Failure_Injection/ARCHITECTURE.md
?? logs/phase1_live_rr_parity_test/manifest.csv
?? logs/phase1_live_rr_parity_test/manifest.json
?? logs/phase1_live_rr_parity_test/scripts/round_robin_logs/wind_x_04_y_04__rep_01__pass_001__20260519T115412Z_sitl_state/logs/LASTLOG.TXT
?? logs/phase1_live_rr_parity_test/scripts/round_robin_logs/wind_x_04_y_04__rep_01__pass_001__20260519T115412Z_sitl_state/mav.parm
?? logs/phase1_live_rr_parity_test/scripts/round_robin_logs/wind_x_04_y_04__rep_01__pass_001__20260519T115412Z_sitl_state/terrain/S36E149.DAT
?? logs/phase1_live_rr_parity_test/scripts/round_robin_logs/wind_x_04_y_04__rep_01__pass_001__20260519T115412Z_world.sdf
?? logs/phase1_live_rr_parity_test/summary/campaign_summary.csv
?? logs/phase1_live_rr_parity_test/summary/campaign_summary.json
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/run_config.json
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/run_summary.json
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_500m_five_laps_loiter5_land.waypoints
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_loiter_samples.csv
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_loiter_turn_profiles.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_loiter_xy_radius.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_square_corner_metrics.csv
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_square_corners.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_square_direction_bias.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_square_edge_metrics.csv
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_square_lap_metrics.csv
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_square_lap_summary.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_square_loiter_summary.json
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/square_loiter_mission_metrics/wind_x_04_y_04__rep_01__attempt_001_square_progress_overlays.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/true_path_deviation/wind_x_04_y_04__rep_01__attempt_001_true_path_deviation.csv
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/true_path_deviation/wind_x_04_y_04__rep_01__attempt_001_true_path_deviation_longest_legs.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/true_path_deviation/wind_x_04_y_04__rep_01__attempt_001_true_path_deviation_map.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/true_path_deviation/wind_x_04_y_04__rep_01__attempt_001_true_path_deviation_summary.json
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/true_path_deviation/wind_x_04_y_04__rep_01__attempt_001_true_path_deviation_vs_ntun.png
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/wind_injection.json
?? logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/run_01
?? tests/test_phase1_parity.py
```

Status snapshot hash:

```text
$ git -C src/SIM_ARD_GAW status --porcelain=v1 --untracked-files=all | sha256sum
f6b0e88ea40059d4081da87701393b1e12a232164899ae825eaea353014dc6f9  -
```

## External Dependency Presence

| Path | Production | `workspace_next` |
| --- | --- | --- |
| `src/ardupilot/` | present | absent |
| `src/SITL_Models/` | present | absent |
| `src/ardupilot_gazebo/` | present | present |

## Important Directory Sizes

Refreshed after Phase 0 audit rework at 2026-05-20T12:47:11+03:00.

| Path | Production | `workspace_next` |
| --- | ---: | ---: |
| `.` | 23G | 157M |
| `src` | 17G | 84M |
| `src/SIM_ARD_GAW` | 15G | 4.0K |
| `src/ardupilot` | 1.6G | absent |
| `src/SITL_Models` | 1.1G | absent |
| `src/ardupilot_gazebo` | 83M | 83M |
| `assets` | not applicable | 64M |
| `config` | absent at production root | 84K |
| `evidence` | not measured | 448K |
| `governance` | not measured | 8.1M |
| `docs` | not measured | 412K |
| `logs` | 4.0K at production root | symlinked through `var/logs`; no files |
| `archive` | 281M | absent |
| `var` | absent | 20K |
| `.private` | 184K | 80K |

## Migration Inventory

Inventory file: `governance/audits/migration_inventory.csv`

```text
$ wc -l governance/audits/migration_inventory.csv
61324 governance/audits/migration_inventory.csv
```

The file has one header row, so the migration inventory contains 61,323 data
rows.

## Raw Log Migration Status

Production raw log count in `src/SIM_ARD_GAW`, root `logs`, and root `archive`:

```text
$ find src/SIM_ARD_GAW logs archive -type f \( -name '*.BIN' -o -name '*.tlog' -o -name '*.tlog.raw' \) -print | wc -l
433
```

`workspace_next` raw log count outside ignored runtime and external dependency
areas:

```text
$ find . -path './.git' -prune -o -path './var' -prune -o -path './src/ardupilot' -prune -o -path './src/SITL_Models' -prune -o -path './src/ardupilot_gazebo/build' -prune -o -type f \( -name '*.BIN' -o -name '*.tlog' -o -name '*.tlog.raw' \) -print | wc -l
0
```

`workspace_next` `var/` raw log count:

```text
$ find var -type f \( -name '*.BIN' -o -name '*.tlog' -o -name '*.tlog.raw' \) -print | wc -l
0
```

Raw log policy conclusion: PASS. Raw logs were not copied into
`workspace_next`; `var/` is present for future runtime output.

## Private State

Production `.private`:

- 16 files.
- Dirty root state: `M .private/backup.log`.
- Contains private docs and scripts retained only in production reference.
- Executable file found: `.private/scripts/auto_backup.sh`.

`workspace_next` `.private`:

Audit correction during Phase 0 rework: the original Phase 0 report marked
`.private` policy as PASS based on ignore/tracked/script/executable checks only.
That was incomplete. `.private/notes/local_notes.md` and
`.private/notes/root_local_notes_legacy.md` contained shared operational facts
and therefore failed the content-review portion of the policy.

Remediation:

- Promoted shared SITL/Gazebo runtime procedure to
  `docs/operations/sitl_gazebo_runtime.md`.
- Tightened private overlay policy in `docs/operations/private_overlays.md`.
- Added build dependency notes to `src/external/DEPENDENCIES.md`.
- Linked canonical runtime/private policy docs from `.ai/index.md`.
- Reduced `.private/notes/*` to local-only pointers with no required runtime
  procedure or configuration values.

```text
$ find .private -type f -print
.private/notes/local_notes.md
.private/notes/root_local_notes_legacy.md
.private/config/plane_params.local.parm
.private/README.md
.private/backups/backup.log
```

Policy checks:

```text
$ find .private -type f -perm -111 -print

$ find .private -type f -name '*.py' -print -o -name '*.sh' -print

$ git ls-files .private

$ git check-ignore -v .private/README.md .private/config/plane_params.local.parm var/logs/example.BIN
.gitignore:12:.private/	.private/README.md
.gitignore:12:.private/	.private/config/plane_params.local.parm
.gitignore:2:var/	var/logs/example.BIN
```

Content review after remediation:

```text
$ rg -n "Critical configuration values|Key Solutions|SIM_JSON_MASTER|GZ_SIM_SYSTEM_PLUGIN_PATH|GZ_SIM_RESOURCE_PATH|Tuned Parameters|Process Management|Installation Order|Test Procedure|libgz-sim8-dev|rapidjson-dev|param set|mode FBWA|Protobuf" .private
```

Result: no output; PASS.

`workspace_next` `.private` policy conclusion after rework: PASS. It is
ignored, has no tracked files, has no executable files, has no Python or shell
scripts, and content review found no hidden operational truth matching the
promoted runtime facts. The original pre-rework PASS claim was invalid.

## Structural Checks

`make doctor`:

```text
$ make doctor
./scripts/ops/doctor.sh
ok:      setup.bash
ok:      assets/models/mini_talon/model.sdf
ok:      assets/worlds/mini_talon_runway.sdf
ok:      config/vehicles/plane_base.parm
ok:      src/sim_ard_gaw/launch/launch.sh
ok:      src/SIM_ARD_GAW/config
ok:      var/logs
```

Broken symlink scan:

```text
$ find . -xtype l -print
```

Result: no output; PASS.

Active `config/` nested `.private` scan:

```text
$ find config -path '*/.private' -print -o -path '*/.private/*' -print
```

Result: no output; PASS.

Compatibility symlinks present:

```text
src/SIM_ARD_GAW/scripts -> ../sim_ard_gaw/compat_scripts
src/SIM_ARD_GAW/logs -> ../../var/logs
src/SIM_ARD_GAW/models -> ../../assets/models
src/SIM_ARD_GAW/missions -> ../../assets/missions
src/SIM_ARD_GAW/config -> ../../config
src/SIM_ARD_GAW/worlds -> ../../assets/worlds
```

## Risks And Blockers

- Production root is dirty: `.private/backup.log`.
- Production nested `src/ardupilot` is dirty: modified `.gitignore` and
  untracked `Tools/scripts/airspeed_vfrhud_bin_test.py`.
- Production nested `src/SIM_ARD_GAW` is dirty with 115 status entries.
- `workspace_next` has no root commit yet, so its root commit is `UNKNOWN`.
- `workspace_next` intentionally lacks `src/ardupilot/` and `src/SITL_Models/`;
  parity work must install or point to those dependencies before runtime claims.
- `src/ardupilot_gazebo` and `src/SITL_Models` have no discoverable nested
  source commits; they are pinned by workspace presence and root state only.

## Phase 0 Conclusion

Phase 0 status after audit rework: PASS for the Foundation Freeze exit gate.

Audit correction: the original report conclusion was not audit-clean because it
claimed `.private` policy PASS before reviewing private-note content, and it
used only a count for production `src/SIM_ARD_GAW` dirty state. Those findings
were treated as FAIL until this report was amended.

The baseline report exists, dependency values are pinned or explicitly marked
`UNKNOWN`, basic `workspace_next` structural checks pass, raw logs were not
copied into `workspace_next`, hidden operational facts were promoted out of
private notes, private-note content review now passes, and production dirty
state is recorded with exact output and hashes.

This does not mean `workspace_next` is production-ready. The blockers above
remain open for later phases.

## Production Modification Statement

Production workspace modification status: NOT MODIFIED BY PHASE 0.

Evidence: the initial production root status was `M .private/backup.log`.
Phase 0 used read-only inspection commands in `/home/ahmed/ardupilot_workspace`.
Final validation returned the same production root status:

```text
$ git status --porcelain=v1 --untracked-files=all
 M .private/backup.log
```

Final nested production checks also matched the initial baseline:

```text
$ git -C src/ardupilot status --porcelain=v1 --untracked-files=all
 M .gitignore
?? Tools/scripts/airspeed_vfrhud_bin_test.py

$ git -C src/ardupilot status --porcelain=v1 --untracked-files=all | sha256sum
bbd65f3b223402021d0b1964a761210e6b45e9a051c7f6ba8e6286930f950220  -

$ git -C src/SIM_ARD_GAW status --porcelain=v1 --untracked-files=all | wc -l
115

$ git -C src/SIM_ARD_GAW status --porcelain=v1 --untracked-files=all | sha256sum
f6b0e88ea40059d4081da87701393b1e12a232164899ae825eaea353014dc6f9  -
```

The production root had one status entry before and after Phase 0. Production
`src/ardupilot` had two status entries before and after Phase 0. Production
`src/SIM_ARD_GAW` had 115 status entries before and after Phase 0, with exact
status hash `f6b0e88ea40059d4081da87701393b1e12a232164899ae825eaea353014dc6f9`
recorded from the full porcelain output above.

## Final Validation

After the report and required updates were written, Phase 0 was re-read and the
exit checks were re-run.

```text
$ make doctor
./scripts/ops/doctor.sh
ok:      setup.bash
ok:      assets/models/mini_talon/model.sdf
ok:      assets/worlds/mini_talon_runway.sdf
ok:      config/vehicles/plane_base.parm
ok:      src/sim_ard_gaw/launch/launch.sh
ok:      src/SIM_ARD_GAW/config
ok:      var/logs

$ find . -xtype l -print

$ find config -path '*/.private' -print -o -path '*/.private/*' -print

$ find . -path './.git' -prune -o -path './var' -prune -o -path './src/ardupilot' -prune -o -path './src/SITL_Models' -prune -o -path './src/ardupilot_gazebo/build' -prune -o -type f \( -name '*.BIN' -o -name '*.tlog' -o -name '*.tlog.raw' \) -print | wc -l
0

$ find var -type f \( -name '*.BIN' -o -name '*.tlog' -o -name '*.tlog.raw' \) -print | wc -l
0

$ find .private -type f -perm -111 -print

$ find .private -type f -name '*.py' -print -o -name '*.sh' -print

$ git ls-files .private

$ git check-ignore -v .private/README.md .private/config/plane_params.local.parm var/logs/example.BIN
.gitignore:12:.private/	.private/README.md
.gitignore:12:.private/	.private/config/plane_params.local.parm
.gitignore:2:var/	var/logs/example.BIN
```

Final validation conclusion: PASS. Empty command blocks above indicate no
findings from the scan.
