# sim_ard_gaw Runtime

`sim_ard_gaw` is the owned runtime package for this workspace's ArduPilot +
Gazebo launch, bridge, analysis, campaign, and test-suite code:

- `launch/` owns launch and cleanup shell entrypoints.
- `bridges/` owns bridge and wind-publisher scripts.
- `analysis/` owns analysis, logging, and probe helpers.
  `analysis/real_flight/` analyzes real-flight DataFlash logs from
  `var/real_flights/` (IMU vibration, redundant IMUs, EKF3).
- `campaigns/wind_matrix/` owns the wind-matrix runners.
- `campaigns/test_suite/` owns the campaign test-suite package.

The former `compat_scripts/` wrapper layer was fully removed on 2026-06-30 and
is preserved only in dated migration evidence. The retained wind-matrix runner
modules under `campaigns/wind_matrix/` are live operator entry points.
