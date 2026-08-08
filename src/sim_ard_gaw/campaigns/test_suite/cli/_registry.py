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


def _airspeed_failure_factory(**kwargs):
    from ..plugins.airspeed_failure import build_plugin
    from ..plugins.airspeed_failure.config import AirspeedFailureConfig
    return build_plugin(AirspeedFailureConfig(**kwargs))


def _gps_failure_factory(**kwargs):
    from ..plugins.gps_failure import build_plugin
    from ..plugins.gps_failure.config import GpsFailureConfig
    return build_plugin(GpsFailureConfig(**kwargs))


PLUGINS: dict[str, Callable[..., object]] = {
    "airspeed_failure": _airspeed_failure_factory,
    "gps_failure": _gps_failure_factory,
    "wind_matrix": _wind_matrix_factory,
}
