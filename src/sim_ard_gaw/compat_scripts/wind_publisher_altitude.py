#!/usr/bin/env python3
"""Compatibility wrapper for the owned altitude wind publisher."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("bridges/wind_publisher_altitude.py", globals())

if __name__ == "__main__":
    run_owned_script("bridges/wind_publisher_altitude.py")
