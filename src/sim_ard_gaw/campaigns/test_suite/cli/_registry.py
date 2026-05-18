"""Phase-1 plugin registry.

A flat dict keeps things blunt. Phase 4 will introduce real plugin
discovery (entry points or package iteration).
"""
from __future__ import annotations

from typing import Callable


def _wind_matrix_factory(**kwargs):
    from ..plugins.wind_matrix import build_plugin
    from ..plugins.wind_matrix.config import WindMatrixConfig
    return build_plugin(WindMatrixConfig(**kwargs))


PLUGINS: dict[str, Callable[..., object]] = {
    "wind_matrix": _wind_matrix_factory,
}
