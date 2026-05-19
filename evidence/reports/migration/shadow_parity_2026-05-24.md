# Shadow Parity Report

Date/time: 2026-05-24T12:50:00+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Status: PASS WITH ACCEPTED RESIDUALS

## Scope

This report records the final Phase 7 shadow parity review after ADR-0004 and
the 2026-05-24 cleanup fix. It supersedes
`evidence/reports/shadow_parity_2026-05-21.md`.

The old workspace was not modified.

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Environment setup | PASS | User shell output from `source setup.bash` on 2026-05-24 loaded `/home/ahmed/ardupilot_workspace_next`, `assets/`, `src/sim_ard_gaw`, `var/logs`, and `var/cache`. |
| Doctor / structure / evidence checks | PASS | `make doctor` output recorded PASS for structure validation and evidence validation in the 2026-05-24 reproof. |
| Launch help | PASS | `scripts/ops/launch.sh help` listed current targets and retained retired `wind-check-altitude` behavior. |
| Static import checks | PASS | Runtime/import smoke loaded launch, bridge, analysis, wind-matrix, and `test_suite` modules; protobuf duplicate-descriptor messages remain known non-fatal warning noise. |
| Parity tests | PASS | `make test-parity` passed six tests in the 2026-05-24 reproof; final validation reran after record updates. |
| Representative vehicle workflow | PASS | Plane smoke under `var/runs/phase7_reproof_20260524/plane_smoke/` plus decoded summary `var/working/runtime_capture/plane_capture_20260524T115831+0300.txt`: GPS, EKF, arm/AUTO, 52.371 m max relative altitude, 22.339435577392578 m/s max groundspeed. |
| Clean-run cleanup | PASS | `var/runs/phase7_final_20260524/cleanup_proof/before_cleanup_processes.txt` captured `gz sim`, `gz sim server`, and `gz sim gui`; `cleanup.log` reported success; `after_cleanup_processes.txt` is 0 bytes. |
| Workspace plugin policy | PASS | `run_one.gazebo_plugin_diagnostics()` and campaign `run_config.json` record `workspace_build_only` and only `/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo` in `GZ_SIM_SYSTEM_PLUGIN_PATH`. |
| Plugin hash | PASS | `build/ardupilot_gazebo/libArduPilotPlugin.so` SHA-256: `1d4089bb6306ecc602e484e9b4e3e77dfb7ecf6649a4292ba872f6d420415fc0`. |
| Campaign/evidence workflow | PASS WITH ACCEPTED RESIDUAL | `var/runs/phase7_final_20260524/tiny_rr_x4_y4_square/manifest.json` records `status: success_square_only`, `analysis_status: done`, square and loiter complete, no local parameter override, and raw BIN under the attempt directory. ADR-0005 accepts square-and-loiter proof for Phase 7 and does not claim full landing/disarm or full matrix readiness. |
| Wind injection | PASS | `wind_injection.json` records `status: ok`, strict echo verification, requested x=4.0/y=4.0 m/s, parsed echo x=4.0/y=4.0/z=0.0, and `enable_wind: true`. |
| Output homes | PASS | Raw runtime output stayed under `var/runs/phase7_final_20260524/`; curated reports and indexes stay under `evidence/`. |

## Accepted Residuals

- The final campaign proof is square-and-loiter evidence, not a full
  landing/disarm or full wind-matrix claim.
- Phase 2 launch-smoke evidence for the broader target set remains valid
  historical parity context; the fresh Phase 7 live proof focused on the
  representative plane and CTE campaign path required for cutover.
- Phase 8 compatibility retirement remains partial and explicitly retained by
  ADR-0005.
- Non-core lanes and `copter-lidar` obstacle return still need later dated
  evidence before those narrower claims can be upgraded.

## Conclusion

Final shadow parity is sufficient for the bounded Phase 7 cutover decision in
ADR-0005. The 2026-05-21 blocked shadow parity record is superseded, not
deleted.
