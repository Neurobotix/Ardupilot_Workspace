"""Reusable automated test-suite framework.

The framework lives in `core/`. Plugins describe a sensor or subsystem
test family and live in `plugins/`. CLI entry points live in `cli/`.

Nothing in this package modifies the legacy scripts (`run_one.py`,
`run_one_og.py`, `run_matrix.py`, `run_matrix_round_robin.py`); they
remain the source of truth for current behavior. The wind_matrix plugin
delegates into them during the Phase-1 wrap.
"""

from . import cli, core, plugins

__all__ = ["core", "plugins", "cli"]
