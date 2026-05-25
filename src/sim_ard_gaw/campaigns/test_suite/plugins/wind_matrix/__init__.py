"""Wind matrix — first reference plugin.

Phase-1 strategy: every adapter delegates into the legacy
`run_one.py` / `run_matrix.py` modules so behavior is byte-for-byte
identical to the current scripts. The plugin's value at this phase is
that it forces the boundary: nothing in `core/` knows the words "wind",
"square", "CTE", or "MAVLink".

Phase 3 will pull the wind/square logic out of `run_one.py` and into
this package, leaving `run_one.py` as a thin wrapper.
"""
from .plugin import build_plugin

__all__ = ["build_plugin"]
