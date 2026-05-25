#!/usr/bin/env python3
"""Compatibility wrapper for the owned square post-processing report builder."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("analysis/build_square_postprocessing_report.py", globals())

if __name__ == "__main__":
    run_owned_script("analysis/build_square_postprocessing_report.py")
