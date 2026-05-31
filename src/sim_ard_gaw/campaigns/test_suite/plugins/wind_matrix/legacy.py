"""Lazy import shim for retained wind-matrix runner modules."""
from __future__ import annotations

import importlib
from types import ModuleType


_RUNNER_PACKAGE = "sim_ard_gaw.campaigns.wind_matrix"


def run_one_module() -> ModuleType:
    return importlib.import_module(f"{_RUNNER_PACKAGE}.run_one")


def run_matrix_module() -> ModuleType:
    return importlib.import_module(f"{_RUNNER_PACKAGE}.run_matrix")


def run_matrix_round_robin_module() -> ModuleType:
    return importlib.import_module(f"{_RUNNER_PACKAGE}.run_matrix_round_robin")
