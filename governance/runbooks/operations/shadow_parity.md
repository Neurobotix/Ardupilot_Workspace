# Shadow Parity Runbook

The new workspace is not production until all gates pass.

This runbook is the runtime proof gate for Phase 2 and Phase 7 of
`governance/runbooks/migration/full_migration_plan.md`.

1. `source setup.bash`
2. `scripts/ops/doctor.sh`
3. `scripts/ops/launch.sh help`
4. Static import checks for campaign tools.
5. Launch smoke: copter, copter-lidar, plane, plane-lidar, plane-cte.
6. Bridge smoke: plane LiDAR bridge connects to expected MAVLink port.
7. Verify clean-run cleanup happens before governed runtime proof and leaves no
   stale simulator process state that contaminates the next run.
8. Verify Gazebo runtime uses
   `build/ardupilot_gazebo/libArduPilotPlugin.so` only and fails closed if the
   workspace build is missing.
9. Wind/CTE single-case parity against production reference.
10. Tiny matrix/parity run updates manifest correctly.
11. Evidence/report generation writes only under `evidence/` or `var/`.

Record each result in `evidence/reports/migration/shadow_parity_<date>.md`.
