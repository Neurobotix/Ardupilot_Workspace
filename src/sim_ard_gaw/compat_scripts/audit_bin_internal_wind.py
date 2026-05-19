#!/usr/bin/env python3
"""Compatibility wrapper for the owned internal-wind BIN audit."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("analysis/audit_bin_internal_wind.py", globals())

if __name__ == "__main__":
    run_owned_script("analysis/audit_bin_internal_wind.py")
