# Troubleshooting Guide

> **ARCHIVED — superseded.** Canonical troubleshooting reference for
> `workspace_next` is `docs/operations/troubleshooting.md`. Errata:
> `governance/audits/2026-05-20_phase3_docs_errata.md`.

Common issues when running ArduPilot SITL with Gazebo Sim.

## Connection Issues

### No GPS Fix
Check JSON backend configuration and ArduPilot parameters. Verify data flow between Gazebo and SITL.

### RC Failures
Ensure proper communication link between simulator and flight controller. Check plugin loading status.

### Connection Refused
SITL process may have terminated. Restart simulation components.

## Arming Failures

### Frame Configuration Errors
Verify frame class and type parameters match your aircraft configuration.

### Sensor Health Checks
Ensure all required sensors are reporting healthy status before arming. May require parameter adjustments.

## Gazebo Issues

### Duplicate World Instance
Previous Gazebo process may still be running. Terminate all related processes before restarting.

### Plugin Loading Failures
Check that required plugins are installed and environment paths are configured correctly.

### Model Not Found
Verify models are installed in expected locations and resource paths include model directories.

## Environment Configuration

Check that environment variables are set correctly and no conflicts exist from previous installations.

## Performance

Simulation performance depends on system resources and configuration. Adjust settings as needed for your hardware.

## Additional Resources

- ArduPilot Documentation
- Gazebo Documentation  
- Community forums
