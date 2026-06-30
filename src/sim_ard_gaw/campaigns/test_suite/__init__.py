"""Reusable automated test-suite framework.

The framework lives in `core/`. Plugins describe a sensor or subsystem
test family and live in `plugins/`. CLI entry points live in `cli/`.

Nothing in this package modifies the standalone operator/campaign runners
(`run_one.py`, `run_matrix.py`, `run_matrix_round_robin.py`) under
`campaigns/wind_matrix/`. They are retained as the direct operator launch
path (see `launch/launch.sh`), but the wind_matrix plugin no longer
delegates into them: the staged strategy is the only supported attempt
path and the legacy delegate has been retired.
"""

from . import cli, core, plugins

__all__ = ["core", "plugins", "cli"]
