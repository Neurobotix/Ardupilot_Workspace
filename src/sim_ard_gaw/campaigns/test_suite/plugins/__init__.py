"""Sensor/test-family plugins.

Each plugin sub-package exports a `plugin` factory (see
`wind_matrix.plugin`) that wires together the adapters required by the
core lifecycle. The CLI looks plugins up by name through `cli/_registry.py`.
"""
