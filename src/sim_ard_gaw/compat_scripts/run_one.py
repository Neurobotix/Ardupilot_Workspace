#!/usr/bin/env python3
"""Compatibility wrapper for the owned wind-matrix single-runner."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("campaigns/wind_matrix/run_one.py", globals())

if __name__ == "__main__":
    run_owned_script("campaigns/wind_matrix/run_one.py")
