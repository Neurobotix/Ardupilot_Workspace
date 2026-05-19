#!/usr/bin/env python3
"""Compatibility wrapper for the owned LiDAR bridge."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("bridges/lidar_bridge_unified.py", globals())

if __name__ == "__main__":
    run_owned_script("bridges/lidar_bridge_unified.py")
