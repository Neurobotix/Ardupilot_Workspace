#!/usr/bin/env python3
"""Compatibility wrapper for the owned flight logger."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("analysis/log_flight_data.py", globals())

if __name__ == "__main__":
    run_owned_script("analysis/log_flight_data.py")
