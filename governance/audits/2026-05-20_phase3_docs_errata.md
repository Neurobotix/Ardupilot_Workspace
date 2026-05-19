# Phase 3 Documentation Errata

Date: 2026-05-20

Completion pass audited: 2026-05-21

This errata records where Phase 3 canonical docs intentionally contradict the
archived production-source docs under `docs/archive/src_docs/`. The archived
files are retained for history; the canonical docs below are authoritative for
`workspace_next`.

## Errata

| Archived doc | Issue | Canonical replacement |
| --- | --- | --- |
| `INSTALLATION.md` | Targets the production workspace and gives generic Gazebo Harmonic setup guidance. | `docs/onboarding/installation.md` — keeps install steps in onboarding, records the Phase 2 evidence boundary, and requires dated evidence before host/Python/Gazebo versions are called parity-verified. |
| `TROUBLESHOOTING.md` | Generic advice; predates the Phase 2 copter frame-param and bridge-buffering fixes. | `docs/operations/troubleshooting.md` — adds verified entries for the copter no-arm fix, the bridge `-u` fix, and the `ripgrep` dependency. |
| `SIMULATION_LANES.md` | Altitude-wind row cites `./launch.sh wind-check-altitude` for post-flight scoring. That target is **retired** in `workspace_next` (production `wind_altitude_log_check.py` never existed). | `docs/architecture/simulation_lanes.md` — drops the scoring claim, marks the target retired. |
| `FLIGHT_MODES.md` | Full ArduPilot mode reference; not workspace-specific and not stale, but not a canonical workspace doc. | `docs/architecture/simulation_lanes.md` carries a workspace-relevant mode quick reference. Archived file retained as reference. |

## Known bad references removed or qualified

- **Retired LiDAR runway world** (`plane_lidar_runway.sdf`): no occurrence in
  canonical docs; the validator blocklist guards against reintroduction.
- **Removed altitude-wind log checker** (`wind_altitude_log_check.py` /
  `wind-check-altitude` scoring): qualified as retired in
  `docs/architecture/simulation_lanes.md` and this errata.
- **Obsolete airspeed parameter claim** (`ARSPD_TYPE` set in the base plane
  stack): no occurrence in canonical docs; `plane_base.parm` is sensor-neutral.
- **Legacy flight-log directory name** (`logs/flights`): no occurrence in
  canonical docs; runtime logs route under `var/logs/`.

## Archive disposition

Disposition vocabulary follows the Phase 3 closeout rule:
`PROMOTED`, `REWRITTEN`, `ARCHIVED_ONLY`, or
`DROPPED_FROM_CANONICAL_USE`.

| Archived file | Disposition | Reason / canonical handling |
| --- | --- | --- |
| `INSTALLATION.md` | `REWRITTEN` | Replaced by the evidence-aware setup guide at `docs/onboarding/installation.md`. |
| `TROUBLESHOOTING.md` | `REWRITTEN` | Replaced by Phase 2-backed operational guidance at `docs/operations/troubleshooting.md`. |
| `SIMULATION_LANES.md` | `REWRITTEN` | Replaced by the current lane map at `docs/architecture/simulation_lanes.md`. |
| `FLIGHT_MODES.md` | `PROMOTED` | Workspace-relevant quick-reference content moved into `docs/architecture/simulation_lanes.md`; full generic reference stays archived. |
| `mini_talon_airspeed_lidar/README.md` | `ARCHIVED_ONLY` | Useful lane design note, but it names legacy homes and the integrated lane is not Phase 2 verified in `workspace_next`. |
| `wind_matrix_scripts/README.md` | `ARCHIVED_ONLY` | Historical study index; the canonical Phase 3 campaign boundary is `docs/campaigns/wind_matrix.md`. |
| `wind_matrix_scripts/00_script_inventory.md` | `ARCHIVED_ONLY` | Historical script inventory retained for Phase 5 reconciliation, not current operating guidance. |
| `wind_matrix_scripts/01_current_behavior.md` | `ARCHIVED_ONLY` | Historical behavior study predates campaign proof in `workspace_next`. |
| `wind_matrix_scripts/02_common_vs_different.md` | `ARCHIVED_ONLY` | Historical refactor analysis retained as background only. |
| `wind_matrix_scripts/03_findings.md` | `ARCHIVED_ONLY` | Trusted blocker themes were summarized in `docs/campaigns/wind_matrix.md`; detailed findings stay historical. |
| `wind_matrix_scripts/04_modularization_plan.md` | `ARCHIVED_ONLY` | Proposed campaign architecture belongs to later migration phases, not canonical Phase 3 operations. |
| `wind_matrix_scripts/05_testing_plan.md` | `ARCHIVED_ONLY` | Test plan is reference material until Phase 5 campaign validation is executed. |
| `wind_matrix_scripts/06_high_wind_12_12_debug_history.md` | `ARCHIVED_ONLY` | Debug chronology is preserved as history and is not promoted into current docs. |
| `wind_matrix_scripts/07_wind_pipeline_investigation_handoff.md` | `ARCHIVED_ONLY` | Investigation handoff contains historical probes and open hypotheses. |
| `wind_matrix_scripts/08_automated_test_suite_blueprint.md` | `ARCHIVED_ONLY` | Blueprint is design input for later campaign/test migration only. |
| `wind_matrix_scripts/09_matrix_launcher_environment_root_cause.md` | `ARCHIVED_ONLY` | Root-cause history is preserved; Phase 3 only documents the current compatibility boundary. |
| `report generation/README.md` | `DROPPED_FROM_CANONICAL_USE` | Generic archived report workflow is not the governed evidence workflow; Phase 6 owns report operations. |
| `report generation/pdf.py` | `DROPPED_FROM_CANONICAL_USE` | Archived renderer code is not a canonical docs or evidence entry point. |
| `report generation/theme.md` | `DROPPED_FROM_CANONICAL_USE` | Archived renderer theme is not adopted into canonical evidence handling. |
| `report generation/report_template.md` | `DROPPED_FROM_CANONICAL_USE` | Archived feature-report template is not the Phase 3 evidence/report contract. |
| `diagrams/Data Flow.svg` | `ARCHIVED_ONLY` | Historical diagram retained without promotion; current structure is described in `docs/architecture/`. |
| `diagrams/PostUpdate_Flow.svg` | `ARCHIVED_ONLY` | Historical diagram retained without promotion or new validity claim. |
| `diagrams/PreUpdate_Flow.svg` | `ARCHIVED_ONLY` | Historical diagram retained without promotion or new validity claim. |
| `diagrams/System Architecture.svg` | `ARCHIVED_ONLY` | Historical diagram retained without promotion; current ownership map is textual and evidence-aware. |
