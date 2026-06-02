"""sensor_failure — Phase 4 second test_suite plugin (GPS fault injection).

This plugin proves the test_suite framework is genuinely generic: it adds a
sensor maximally different from wind (GPS, no Gazebo wind at all; fault is a
mid-flight SITL parameter change, not a startup world condition) with ZERO
framework-core edits.

It CHARACTERIZES BEHAVIOR — "if GPS is corrupted mid-flight, what does the
vehicle do?" — rather than gating pass/fail against guessed safety bounds. A
`gps_baseline` no-fault control run captures the normal envelope; each fault run
records the response as a DEVIATION from the pre-fault / baseline envelope and is
classified `nominal` / `safe_degraded` / `unsafe`. A run is "accepted" (counts
toward repeats) when it produced a clean measurement (fault applied + enough
post-trigger samples); the behavior class is the scientific result, not an
acceptance gate.

Scope is GPS only: a baseline plus two faults (`gps_disable`, `gps_glitch_50m`).
The plugin is architected to extend to the other 021 sensor families by adding
records to `cases.py`, but those are intentionally not built here.
"""
from .plugin import build_plugin

__all__ = ["build_plugin"]
