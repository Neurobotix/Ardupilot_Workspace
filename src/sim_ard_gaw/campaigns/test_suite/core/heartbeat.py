"""Operator-facing physical status heartbeat.

Procedural logging ("mission uploaded", "vehicle armed") tells the operator
that a run is *progressing*. It cannot tell the operator that the run is
*producing valid evidence*. A drift injection that silently failed, an
unverified reference wind, or an unintended GPS denial all look identical to
a procedural log right up until the post-run analysis throws the attempt away.

This module prints the physical state instead, on a fixed cadence, while the
vehicle is still flying — so an invalid attempt can be aborted rather than
completed.

The split is deliberate and is the whole point of the module:

- **Core owns cadence and shape.** One line per period, one consistent
  format, so an operator watching three different lanes reads them the same
  way.
- **The lane owns content.** Which physical quantities decide validity is a
  domain question that only the lane can answer, so the lane supplies the
  fields and this module never inspects them.

Consequently this module contains no lane names and no lane-specific
behaviour; it cannot, or the split would be broken.

Missing data must be rendered by the lane as `?` or `n/a`. A heartbeat that
prints a stale or fabricated value is worse than no heartbeat, because it
invites the operator to trust an attempt that is already invalid.

Output goes through `core.logging.log`, inheriting its timestamp. This must
never be called on a machine-readable code path (`--list-cases`,
`--dry-run`, `--probe-schema`), whose output is parsed by callers.
"""
from __future__ import annotations

from .logging import log

#: Operator-facing status cadence, in seconds. Matches the cadence the GPS
#: lane already used before this mechanism existed.
HEARTBEAT_PERIOD_S = 15.0


class OperatorHeartbeat:
    """Emits one lane-supplied status line per `period_s`.

    The caller drives this from its own message loop by calling `maybe_emit`
    with a monotonic clock reading; nothing here starts a thread or touches
    the vehicle, so a heartbeat can never perturb run timing.
    """

    def __init__(
        self,
        *,
        prefix: str,
        case_id: str,
        started_monotonic_s: float,
        period_s: float = HEARTBEAT_PERIOD_S,
    ) -> None:
        self._prefix = prefix
        self._case_id = case_id
        self._started_monotonic_s = started_monotonic_s
        self._period_s = period_s
        self._last_emit_s = started_monotonic_s

    def maybe_emit(self, now_s: float, fields: dict[str, str]) -> bool:
        """Emit a status line if a full period has elapsed.

        Returns whether a line was printed, so callers can fold any extra
        per-period reporting into the same tick.
        """
        if now_s - self._last_emit_s < self._period_s:
            return False
        self._last_emit_s = now_s
        self.emit(now_s, fields)
        return True

    def emit(self, now_s: float, fields: dict[str, str]) -> None:
        """Emit a status line immediately, ignoring the cadence."""
        elapsed_s = max(0.0, now_s - self._started_monotonic_s)
        rendered = " ".join(f"{key}={value}" for key, value in fields.items())
        line = f"[{self._prefix}] {self._case_id}: t={elapsed_s:.0f}s"
        if rendered:
            line = f"{line} {rendered}"
        log(line)
