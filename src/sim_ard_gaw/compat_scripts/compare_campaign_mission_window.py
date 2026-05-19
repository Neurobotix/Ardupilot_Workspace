#!/usr/bin/env python3
"""Compatibility wrapper for the owned campaign mission-window comparator."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("analysis/compare_campaign_mission_window.py", globals())

if __name__ == "__main__":
    run_owned_script("analysis/compare_campaign_mission_window.py")
