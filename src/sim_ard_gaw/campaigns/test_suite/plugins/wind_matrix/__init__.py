"""Wind matrix — first reference plugin.

Default strategy: delegate into the legacy `run_one.py` / `run_matrix.py`
modules so the campaign runtime keeps the proven compatibility path.

Feature Phase 3 adds an opt-in staged strategy that pulls wind/square
logic into this package and framework stage adapters. It is not the
default until live parity evidence exists.
"""
from .plugin import build_plugin

__all__ = ["build_plugin"]
