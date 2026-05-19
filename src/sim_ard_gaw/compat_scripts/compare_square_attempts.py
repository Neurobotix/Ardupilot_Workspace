#!/usr/bin/env python3
"""Compatibility wrapper for the owned square-attempt comparator."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("analysis/compare_square_attempts.py", globals())

if __name__ == "__main__":
    run_owned_script("analysis/compare_square_attempts.py")
