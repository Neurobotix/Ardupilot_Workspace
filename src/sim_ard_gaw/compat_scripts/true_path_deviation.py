#!/usr/bin/env python3
"""Compatibility wrapper for the owned true-path deviation analyzer."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("analysis/true_path_deviation.py", globals())

if __name__ == "__main__":
    run_owned_script("analysis/true_path_deviation.py")
