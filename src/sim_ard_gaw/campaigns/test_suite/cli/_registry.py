"""Plugin registry.

Phase 4 realizes the "real plugin discovery" note: plugin selection now works
for two plugins via a flat dict of factories. A flat dict is deliberately blunt;
full entry-point discovery is still out of scope. Each factory takes plugin
config kwargs and returns a built plugin exposing `case_generator`,
`environment`, `manifest`, `attempt_runner()`, and `attempt_dir_factory()`.
"""
from __future__ import annotations

from typing import Callable


def _wind_matrix_factory(**kwargs):
    from ..plugins.wind_matrix import build_plugin
    from ..plugins.wind_matrix.config import WindMatrixConfig
    return build_plugin(WindMatrixConfig(**kwargs))


def _sensor_failure_factory(**kwargs):
    from ..plugins.sensor_failure import build_plugin
    from ..plugins.sensor_failure.config import SensorFailureConfig
    return build_plugin(SensorFailureConfig(**kwargs))


PLUGINS: dict[str, Callable[..., object]] = {
    "wind_matrix": _wind_matrix_factory,
    "sensor_failure": _sensor_failure_factory,
}


def known_plugins() -> list[str]:
    return sorted(PLUGINS)


def build_plugin(plugin_name: str, **kwargs):
    """Build a plugin by registry name from config kwargs.

    Raises ValueError for an unknown name so callers can surface a clean
    message.
    """
    try:
        factory = PLUGINS[plugin_name]
    except KeyError:
        raise ValueError(
            f"Unknown plugin {plugin_name!r}. Known plugins: {known_plugins()}"
        )
    return factory(**kwargs)
