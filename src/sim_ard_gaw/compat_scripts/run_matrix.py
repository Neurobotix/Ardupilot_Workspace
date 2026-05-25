#!/usr/bin/env python3
"""Compatibility wrapper for the owned wind-matrix sequential runner."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("campaigns/wind_matrix/run_matrix.py", globals())

if __name__ == "__main__":
    run_owned_script("campaigns/wind_matrix/run_matrix.py")
