#!/usr/bin/env python3
"""Compatibility wrapper for the owned square/loiter metrics analyzer."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("analysis/square_loiter_mission_metrics.py", globals())

if __name__ == "__main__":
    run_owned_script("analysis/square_loiter_mission_metrics.py")
