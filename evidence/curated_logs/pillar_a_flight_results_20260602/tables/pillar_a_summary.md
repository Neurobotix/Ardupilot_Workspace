# Pillar A Flight-Lane And Analysis Summary

Scope: rollup of already-reviewed flight-lane and analysis evidence. No new SITL/Gazebo runs.

## Verified Core Flight Lanes

| Lane | Targets | Proof | Heartbeats | Max altitude m | Max groundspeed m/s | Evidence |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Base plane | `plane + gazebo-plane` | SITL/Gazebo/MAVLink handshake, GPS, EKF3, armed, physics coupling | 256 | 0.20 | 17.33 | evidence/curated_logs/phase_2_runtime_2026-05-20/plane_evidence.txt |
| CTE / airspeed | `plane-cte + gazebo-plane-cte` | SITL/Gazebo/MAVLink handshake, GPS, EKF3, Armed AUTO, airborne CTE lane | 126 | 46.86 | 23.06 | evidence/curated_logs/phase_2_runtime_2026-05-20/plane-cte_evidence.txt |
| Plane LiDAR | `plane-lidar + gazebo-plane-lidar + bridge-plane` | Airborne plane LiDAR lane plus Gazebo /lidar -> bridge -> MAVLink -> ArduPilot AGL readings | 199 | 52.51 | 22.37 | evidence/curated_logs/phase_2_runtime_2026-05-20/plane-lidar_evidence.txt; evidence/curated_logs/phase_2_runtime_2026-05-20/bridge-plane_console.txt |
| Copter base | `copter + gazebo-copter` | SITL/Gazebo/MAVLink handshake, GPS, EKF3, armed, takeoff 10 reached | 201 | 10.02 | 0.04 | evidence/curated_logs/phase_2_runtime_2026-05-20/copter_evidence.txt |
| Copter LiDAR | `copter-lidar + gazebo-copter-lidar + bridge-copter` | Copter LiDAR handshake and flight; bridge streamed 922 DISTANCE_SENSOR messages; obstacle return not captured | 793 | 4.04 | 2.46 | evidence/curated_logs/phase_2_runtime_2026-05-20/copter-lidar_evidence.txt; evidence/curated_logs/phase_2_runtime_2026-05-20/bridge-copter_console.txt |

## Expansion Lane Boundary

| Lane | Targets | Current status | Boundary |
| --- | --- | --- | --- |
| Staircase | `plane-staircase + gazebo-plane-staircase + bridge-plane` | not yet tested | Expansion lane present in lane map; no dated runtime proof yet |
| Integrated airspeed+LiDAR | `plane-airspeed-lidar + gazebo-plane-airspeed-lidar + bridge-plane` | not yet tested | Expansion lane present in lane map; no dated runtime proof yet |
| Altitude-wind | `plane-altitude-wind + gazebo-plane-altitude-wind + wind-publisher-altitude` | not yet tested | Expansion lane present in lane map; no dated runtime proof yet |
| Rebuild | `plane-rebuild + gazebo-plane-rebuild` | not yet tested | Expansion lane present in lane map; no dated runtime proof yet |
| Bench | `gazebo-plane-bench and related` | not a flight lane | Bench worlds are isolation harnesses, not flight-ready operating worlds |

## Analysis Result

| Result | Status | Headline | Evidence |
| --- | --- | --- | --- |
| CTE wind-envelope | verified | 32 accepted runs, 13/16 cells accepted, 3 envelope-edge no-accepted cells, calm RMS 7.15 m, worst accepted RMS 17.99 m, component+interaction R2 0.751. | evidence/reports/features/2026-06-02_cte_wind_envelope_result.md |
