# Open Issues

## Current Evidence Gaps

- Wider wind-matrix evidence, non-core launch target runtime evidence, and
  `copter-lidar` obstacle return remain open until dated evidence promotes
  them.

## Phase 0 Baseline Blockers

- Production root has pre-existing dirty private state: `.private/backup.log`.
- Production nested `src/ardupilot` is dirty: modified `.gitignore` and
  untracked `Tools/scripts/airspeed_vfrhud_bin_test.py`.
- Production nested `src/SIM_ARD_GAW` is dirty with 115 status entries.
- At Phase 0, `workspace_next` had no root commit yet; later migration commits
  supersede that bootstrap state.
- `workspace_next` now has ignored local `src/ardupilot/` and
  `src/SITL_Models/` runtime dependency checkouts provisioned for Phase 2, but
  they are not canonical evidence homes.
- `src/ardupilot_gazebo` and `src/SITL_Models` have no discoverable nested
  source commit metadata.

## Existing Platform Issues

- `copter-lidar` proved the SITL/Gazebo/MAVLink/bridge handshake but the
  forward LiDAR captured no obstacle return (the copter flew above the 3 m
  obstacle band). Obstacle detection is unproven.
- Non-core launch targets remain not-yet-tested: `plane-airspeed-lidar`,
  `plane-altitude-wind`, `plane-rebuild`, `plane-staircase`, and matching
  Gazebo worlds.
- Gazebo/Python import paths emit protobuf duplicate-descriptor warnings on
  stderr; noisy but non-fatal (bridge imports verified to succeed).
- Plane launchers and current CTE campaign callers append
  `.private/config/plane_params.local.parm` when it exists. Treat runs using
  that file as local-stack-dependent until their effective stack and hashes are
  recorded with evidence.
- Non-core assets/config stacks remain indexed but not runtime-verified for
  `plane-airspeed-lidar`, `plane-altitude-wind`, `plane-rebuild`, and
  `plane-staircase`.
- `wind-check-altitude` retired until a real validator is implemented.
- Full wind-matrix campaign evidence beyond the bounded Phase 5 one-case parity
  proof is not yet captured.
- The old workspace is deprecated fallback/reference after ADR-0005. Do not
  edit it without explicit operator authorization.

## Tooling Notes

- `make doctor` requires `ripgrep` (`rg`); the structure validator uses it for
  `.private` policy and workspace-status-link checks. Install with
  `sudo apt install ripgrep` if `make doctor` reports spurious missing
  references.

## Closed Phase 2 Items

- Phase 2 runtime parity is PASS:
  `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`.
- Every required runtime smoke target was run with direct evidence:
  `copter`, `copter-lidar`, `plane`, `plane-lidar`, `plane-cte`, the matching
  `gazebo-*` worlds, `bridge-plane`, `bridge-copter`, `logger`, `cleanup`.
- `plane-cte`, `plane-lidar`, `copter`, `copter-lidar` proved airborne flight.
- `bridge-plane` proved an end-to-end LiDAR path with real terrain returns;
  `bridge-copter` proved the bridge MAVLink path (922 `DISTANCE_SENSOR` msgs).
- `logger` connected to a live MAVLink source and wrote a flight log under
  `var/logs/flight_logger/`.
- Copter no-arm defect fixed: copter launchers load
  `config/vehicles/copter_params.parm` with `--wipe-eeprom`.
- Bridge observability defect fixed: bridge launchers run `python3 -u`.

## Closed Phase 3 Items

- Phase 3 documentation rebuild is PASS:
  `evidence/reports/migration/PHASE_3_DOCS_2026-05-20.md`.
- Every archived source-doc file has an explicit disposition in
  `governance/audits/2026-05-20_phase3_docs_errata.md`.
- Audit remediation removed duplicate runtime-note install guidance, narrowed
  install evidence wording, and closed the Phase 3 runbook checklist.
- No Phase 3 documentation blocker remains open; later runtime and campaign
  proof must update docs when evidence changes.

## Closed Phase 5 Items

- Phase 5 Campaign And Test Migration is PASS:
  `evidence/reports/migration/PHASE_5_CAMPAIGN_TESTS_2026-05-21.md`.
- Wind-matrix manifest locking, terminal status taxonomy with
  `failed_analysis`, mission-contract validation, XML/SDF wind transforms,
  strict wind verification defaults, and parameter hash provenance are
  implemented and tested.
- The bounded `wind_x_00_y_00` `test_suite` round-robin tiny campaign case
  completed with analysis and curated evidence under
  `evidence/curated_logs/phase5_tiny_rr_20260521/`.
- The first bounded `wind_x_04_y_04` production-reference round-robin
  remediation under
  `evidence/curated_logs/phase5_live_rr_parity_remediation_20260521/` is
  retained as plugin-fallback diagnostic evidence, not ArduPilot-side wind
  parity proof. The corrected workspace-plugin recheck completed at
  `var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/wind_x_04_y_04/runs/attempt_002/`.

## Closed Phase 6 Items

- Phase 6 Evidence And Operations is PASS:
  `evidence/reports/migration/PHASE_6_EVIDENCE_OPS_2026-05-21.md`.
- Human promotion workflow, report templates, and the cross-phase catalog now
  live under `docs/operations/evidence_workflow.md`, `evidence/templates/`,
  and `evidence/indexes/evidence_catalog.md`.
- `scripts/maintenance/validate_evidence.sh` is called by `make doctor` and
  covers raw output leakage, raw run directories, evidence homes, template
  inventory, report placement, and catalog sanity.

## Closed Phase 7 Policy Items

- Broad launcher cleanup is governed clean-run safety policy under
  `governance/decisions/ADR-0004-clean-run-and-workspace-plugin-policy.md`.
  Operators must not run it beside another simulator session they need to keep
  alive.
- Governed Gazebo runtime now uses
  `build/ardupilot_gazebo/libArduPilotPlugin.so` only. Setup, launch, and
  wind-matrix runtime no longer accept installed plugin fallback.
- Phase 7 cutover passed on 2026-05-24 with accepted residuals under
  `governance/decisions/ADR-0005-workspace-next-cutover.md`.

## Closed Phase 1 Items

- Structure validator added at `scripts/maintenance/validate_structure.sh`.
- `make doctor` passes through the structure validator.
- Phase 1 evidence report exists:
  `evidence/reports/migration/PHASE_1_STRUCTURE_2026-05-20.md`.
- No Phase 1 structure-hardening blockers remain.
