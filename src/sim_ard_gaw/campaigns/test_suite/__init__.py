"""Reusable automated test-suite framework.

The framework lives in `core/`. Plugins describe a sensor or subsystem
test family and live in `plugins/`. CLI entry points live in `cli/`.
"""

from . import cli, core, plugins

__all__ = ["core", "plugins", "cli"]
