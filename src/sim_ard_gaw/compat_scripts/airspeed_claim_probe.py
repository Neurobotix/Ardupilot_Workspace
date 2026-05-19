#!/usr/bin/env python3
"""Compatibility wrapper for the owned airspeed probe."""

from _owned_wrapper import export_owned_module, run_owned_script

export_owned_module("analysis/airspeed_claim_probe.py", globals())

if __name__ == "__main__":
    run_owned_script("analysis/airspeed_claim_probe.py")
