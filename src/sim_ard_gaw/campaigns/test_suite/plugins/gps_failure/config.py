"""Configuration for the gps_failure plugin."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Sequence

from . import defaults


@dataclass
class GpsFailureConfig:
    drift_rates_mps: tuple[float, ...] = defaults.DRIFT_RATES_MPS
    glitch_magnitudes_m: tuple[float, ...] = defaults.GLITCH_MAGNITUDES_M
    denial_durations_s: tuple[float, ...] = defaults.DENIAL_DURATIONS_S
    glitch_hold_durations_s: tuple[float, ...] = defaults.GLITCH_HOLD_DURATIONS_S
    bounded_glitch_magnitude_m: float = defaults.BOUNDED_GLITCH_MAGNITUDE_M
    jamming_repeats: int = defaults.JAMMING_REPEAT_COUNT
    jamming_duration_s: float = defaults.JAMMING_DURATION_S
    runs_per_case: int = 1
    campaign_root: Path = field(default_factory=defaults.default_campaign_root)
    mission_file: Path = field(default_factory=lambda: defaults.MISSION_FILE)
    param_file_stack: Sequence[Path] | None = None
    extra_param_files: Sequence[Path] = ()
    envelope_name: str = defaults.BASELINE_ENVELOPE_NAME
    mavlink_addr: str = "udpin:0.0.0.0:14551"
    launch_stack: bool = False
    mission_timeout_s: float = defaults.PHASE2_MONITOR_TIMEOUT_S
    upload_timeout_s: float = defaults.UPLOAD_TIMEOUT_S
    arm_timeout_s: float = defaults.ARM_TIMEOUT_S
    mode_timeout_s: float = defaults.MODE_TIMEOUT_S
    cleanup_timeout_s: float = defaults.CLEANUP_TIMEOUT_S
    heartbeat_timeout_s: float = defaults.HEARTBEAT_TIMEOUT_S
    ready_timeout_s: float = defaults.VEHICLE_READY_TIMEOUT_S
    force_arm: bool = True
    nominal_observation_s: float = defaults.NOMINAL_MIN_POST_INJECTION_S

    def __post_init__(self) -> None:
        self.envelope_name = str(self.envelope_name)
        defaults.envelope_metadata(self.envelope_name)
        if Path(self.mission_file) == defaults.MISSION_FILE:
            self.mission_file = defaults.mission_file_for_envelope(self.envelope_name)
        self.extra_param_files = tuple(Path(path) for path in self.extra_param_files)
        self.runs_per_case = _positive_int("runs_per_case", self.runs_per_case, minimum=1)
        self.jamming_repeats = _positive_int(
            "jamming_repeats",
            self.jamming_repeats,
            minimum=defaults.JAMMING_REPEAT_COUNT,
        )
        self.jamming_duration_s = _positive_finite(
            "jamming_duration_s",
            self.jamming_duration_s,
        )
        self.drift_rates_mps = _positive_ladder(
            "drift_rates_mps",
            self.drift_rates_mps,
            drift_rate_token,
        )
        self.glitch_magnitudes_m = _positive_ladder(
            "glitch_magnitudes_m",
            self.glitch_magnitudes_m,
            glitch_magnitude_token,
        )
        self.denial_durations_s = _positive_ladder(
            "denial_durations_s",
            self.denial_durations_s,
            denial_duration_token,
        )
        self.glitch_hold_durations_s = _positive_ladder(
            "glitch_hold_durations_s",
            self.glitch_hold_durations_s,
            glitch_hold_duration_token,
        )
        self.bounded_glitch_magnitude_m = _positive_finite(
            "bounded_glitch_magnitude_m",
            self.bounded_glitch_magnitude_m,
        )
        self.mission_timeout_s = _positive_finite(
            "mission_timeout_s",
            self.mission_timeout_s,
        )
        self.upload_timeout_s = _positive_finite(
            "upload_timeout_s",
            self.upload_timeout_s,
        )
        self.arm_timeout_s = _positive_finite(
            "arm_timeout_s",
            self.arm_timeout_s,
        )
        self.mode_timeout_s = _positive_finite(
            "mode_timeout_s",
            self.mode_timeout_s,
        )
        self.cleanup_timeout_s = _positive_finite(
            "cleanup_timeout_s",
            self.cleanup_timeout_s,
        )
        self.heartbeat_timeout_s = _positive_finite(
            "heartbeat_timeout_s",
            self.heartbeat_timeout_s,
        )
        self.ready_timeout_s = _positive_finite(
            "ready_timeout_s",
            self.ready_timeout_s,
        )
        self.nominal_observation_s = _positive_finite(
            "nominal_observation_s",
            self.nominal_observation_s,
        )

    @property
    def effective_param_stack(self) -> list[Path]:
        if self.param_file_stack is None:
            stack = defaults.param_files_for_envelope(self.envelope_name)
        else:
            stack = [Path(path) for path in self.param_file_stack]
        return [*stack, *self.extra_param_files]

    @property
    def envelope_metadata(self) -> dict[str, object]:
        metadata = defaults.envelope_metadata(self.envelope_name)
        metadata["mission_file"] = str(self.mission_file)
        metadata["param_files"] = [str(path) for path in self.effective_param_stack]
        return metadata

    @property
    def sitl_target(self) -> str:
        return defaults.sitl_target_for_envelope(self.envelope_name)

    @property
    def gazebo_target(self) -> str:
        return defaults.gazebo_target_for_envelope(self.envelope_name)

    @property
    def gazebo_world_file(self) -> Path:
        return defaults.gazebo_world_file_for_envelope(self.envelope_name)

    @property
    def source_contract_expected_knee_readbacks(self) -> dict[str, float]:
        return defaults.expected_knee_readbacks_for_envelope(self.envelope_name)

    @property
    def source_contract_expected_airspeed_readbacks(self) -> dict[str, float]:
        return defaults.expected_airspeed_readbacks_for_envelope(self.envelope_name)


def _positive_int(name: str, value: object, *, minimum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer >= {minimum}") from None
    if not math.isfinite(numeric) or not numeric.is_integer():
        raise ValueError(f"{name} must be an integer >= {minimum}")
    parsed = int(numeric)
    if parsed < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return parsed


def _positive_ladder(
    name: str,
    values: Sequence[float],
    token_func: Callable[[float], str],
) -> tuple[float, ...]:
    normalized = tuple(_positive_finite(f"{name} value", value) for value in values)
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    seen: dict[str, float] = {}
    for value in normalized:
        token = token_func(value)
        if token in seen:
            raise ValueError(
                f"{name} contains duplicate/colliding value {value} "
                f"for canonical token {token}"
            )
        seen[token] = value
    return normalized


def _positive_finite(name: str, value: object) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number > 0") from None
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    if parsed <= 0:
        raise ValueError(f"{name} must be > 0")
    return parsed


def _format_number_token(value: float) -> str:
    raw = f"{value:.12g}"
    return raw.replace("-", "m").replace(".", "p")


def drift_rate_token(value: float) -> str:
    if value in defaults.DRIFT_RATES_MPS:
        return f"{value:.1f}".replace(".", "p")
    return _format_number_token(value)


def glitch_magnitude_token(value: float) -> str:
    if value in defaults.GLITCH_MAGNITUDES_M:
        return f"{int(value):03d}"
    return _format_number_token(value)


def denial_duration_token(value: float) -> str:
    if value in defaults.DENIAL_DURATIONS_S:
        return f"{int(value):02d}"
    return _format_number_token(value)


def glitch_hold_duration_token(value: float) -> str:
    if value in defaults.GLITCH_HOLD_DURATIONS_S:
        return f"{int(value):02d}"
    return _format_number_token(value)
