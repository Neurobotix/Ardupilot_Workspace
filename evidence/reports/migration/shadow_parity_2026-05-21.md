# Shadow Parity - Phase 7 Final Check

Date/time: 2026-05-21T21:44:11+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Status: BLOCKED

## 2026-05-22 Policy Update

This report preserves the shadow-parity result from the 2026-05-21 blocked
cutover attempt. `ADR-0004` now treats broad pre-run cleanup as governed
clean-run policy and requires workspace-only Gazebo plugin loading with
fail-closed behavior when
`build/ardupilot_gazebo/libArduPilotPlugin.so` is missing.

Final Phase 7 shadow parity is still `BLOCKED` until the runtime proof rows
below are rerun under that current policy.

Current post-`ADR-0004` blocker set:

1. rerun final Phase 7 shadow parity under the current clean-run and
   workspace-plugin policy;
2. record fresh representative vehicle workflow proof under that policy;
3. record fresh representative campaign/evidence workflow proof under that
   policy.

The table below preserves the historical 2026-05-21 attempt. Rows that describe
the former cleanup or installed-plugin policy gap are historical, not live
post-policy blockers.

## Scope

This Phase 7 pass rechecked the safe shadow-parity surface in
`/home/ahmed/ardupilot_workspace_next` before any production-status edit. The
old workspace was read only for the production-reference status check and was
not modified.

## Historical 2026-05-21 Results

| Shadow parity item | Result | Evidence |
| --- | --- | --- |
| Setup/environment check | PASS | `bash -lc 'source setup.bash'` printed the workspace, assets, runtime, logs, and cache homes under `workspace_next`. |
| Doctor and structure/evidence guardrails | PASS | Final `make doctor`, `scripts/maintenance/validate_structure.sh`, and `scripts/maintenance/validate_evidence.sh` passes are recorded in `evidence/reports/CUTOVER_2026-05-21.md`. |
| Launch surface | PASS | `scripts/ops/launch.sh help` listed the expected launch surface. `scripts/ops/launch.sh wind-check-altitude` exited 2 with the documented retired-target message. |
| Static campaign/runtime imports | PASS with known warning noise | Direct imports of `lidar_bridge_unified`, `log_flight_data`, `wind_publisher_altitude`, and `test_suite.cli.run_round_robin` completed; protobuf duplicate-descriptor warnings remain tracked as non-fatal stderr noise. |
| Launch smoke: vehicle lanes | BLOCKED for fresh Phase 7 proof | Phase 2 direct smoke evidence exists for `copter`, `copter-lidar`, `plane`, `plane-lidar`, and `plane-cte`, but fresh Phase 7 proof has not yet been rerun under the post-`ADR-0004` policy. |
| Plane LiDAR bridge smoke | BLOCKED for fresh Phase 7 proof | Phase 2 bridge evidence exists, but Phase 7 has not yet rerun the production-promotion bridge round under the post-`ADR-0004` policy. |
| Wind/CTE single-case parity | HISTORICAL BLOCKED at 2026-05-21 attempt | Phase 5 had the corrected workspace-plugin recheck, but the original Phase 7 attempt stopped while installed-plugin fallback policy was still open. `ADR-0004` now supersedes that policy gap; fresh proof is still required. |
| Tiny matrix/parity workflow | VERIFIED, not rerun as a new campaign | `make test-parity` passed and the Phase 5 tiny round-robin manifest under `evidence/curated_logs/phase5_tiny_rr_20260521/` records the bounded campaign provenance and raw `var/` locations. |
| Output location and evidence promotion | PASS | `scripts/ops/capture_round.sh plane` wrote a working capture to `var/working/runtime_capture/`; `scripts/ops/capture_round.sh --promote-reviewed plane` refused unversioned promotion without `--evidence-id`. |
| Cleanup/process hygiene | HISTORICAL BLOCKED at 2026-05-21 attempt | The original Phase 7 attempt stopped before the broad cleanup behavior was governed. `ADR-0004` now defines it as clean-run policy; current cutover proof still needs a fresh cleanup/process-hygiene result under that policy. |

## Conclusion

Final Phase 7 shadow parity is `BLOCKED`. Safe setup, guardrail, parity, help,
import, and evidence-routing checks passed in the historical attempt, and the
cleanup/plugin policy questions were superseded by `ADR-0004`. The live gate is
now missing post-policy final shadow parity plus fresh representative vehicle
and campaign/evidence workflow proof.

Compatibility retirement remains Phase 8.
