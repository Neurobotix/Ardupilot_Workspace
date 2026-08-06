"""Wind-matrix plugin for CTE wind campaign attempts.

The plugin wires wind case generation, SITL/Gazebo environment control, wind
stimulus, square-mission monitoring, analysis, and manifest emission into the
generic test-suite lifecycle.
"""
from .plugin import build_plugin

__all__ = ["build_plugin"]
