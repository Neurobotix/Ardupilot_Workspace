"""Plugin registry.

A flat dict keeps things blunt; real discovery (entry points or package
iteration) is not needed while the lane set is this small.

This is the single source of truth for which lane names the CLI accepts.
`cli/_plugin_select.py` resolves names through it, so a lane is reachable
as soon as it is registered here.
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
