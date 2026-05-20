# ADR-0004: Clean Run And Workspace Gazebo Plugin Policy

Status: Accepted

Simulation entrypoints use broad cleanup as an intentional clean-run safety
policy. Before new SITL vehicle runs, the compatibility launcher may terminate
Gazebo, ArduPilot vehicle binaries, MAVProxy, `sim_vehicle.py`, and LiDAR bridge
processes by process class so stale simulation state does not leak into the new
run. Operators must treat this workspace as owning the simulator session when
they start a governed run.

Gazebo plugin execution is workspace-build-only. The only allowed plugin binary
for workspace launch and campaign runtime is:

```text
build/ardupilot_gazebo/libArduPilotPlugin.so
```

Installed plugin directories such as `/usr/local/lib/ardupilot_gazebo` are not
runtime fallback paths. Launchers and wind-matrix runtime must fail closed when
the workspace plugin binary is missing. Runtime evidence records the selected
workspace plugin path and hash where the claim depends on plugin behavior.

The Phase 5 plugin fallback incident remains retained evidence of the failure
class this policy prevents.
