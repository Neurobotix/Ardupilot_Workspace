"""Plugin-owned MAVLink parameter fault injection for sensor_failure.

This is the net-new mechanic the GPS plugin needs and the wind plugin never did:
setting SITL SIM_* parameters mid-flight over MAVLink (`PARAM_SET`) and verifying
the change took effect with a `PARAM_VALUE` readback. It is sensor-agnostic at
the MAVLink level (it sets any param by name), but lives in the plugin because
fault injection is plugin-owned per the framework contract.

Resilience properties (these matter for a live mid-flight injector):
- `set_param` retries the PARAM_SET and confirms with a readback that matches the
  intended value within a tolerance, so a single dropped packet does not leave
  the fault un-applied. It is the hard, must-succeed path.
- `read_param`/`snapshot_params` are best-effort provenance reads. They use a
  short, BOUNDED budget so a slow or absent param never stalls the run — a
  missing param maps to ``None`` rather than costing a full multi-second timeout
  per name. `snapshot_params` shares one wall-clock budget across all names.
- The wall clock is injectable so the logic is unit-testable without real time.

No legacy runner import. No framework-core edit.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from pymavlink import mavutil

from . import defaults


PARAM_SET_TOLERANCE = 1e-4
# Per-attempt readback budget for the strict confirmed set.
PARAM_SET_READBACK_TIMEOUT_S = 5.0
PARAM_SET_MAX_ATTEMPTS = 5
# Best-effort provenance reads: short and bounded so missing params do not stall.
PARAM_READ_TIMEOUT_S = 1.5
PARAM_SNAPSHOT_TOTAL_BUDGET_S = 4.0


def _encode_param_id(name: str) -> bytes:
    return name.encode("ascii")


def _decode_param_id(pid: Any) -> str:
    if isinstance(pid, bytes):
        pid = pid.decode("utf-8", "replace")
    return str(pid).strip("\x00")


def _drain_param_values(
    master: mavutil.mavfile,
    deadline: float,
    *,
    clock: Callable[[], float],
) -> dict[str, float]:
    """Consume whatever PARAM_VALUE messages are available up to `deadline`.

    Returns the latest value seen per param id. Resilient to interleaved
    telemetry: `recv_match(type="PARAM_VALUE")` leaves non-matching messages in
    the buffer (pymavlink semantics), so this does not drop flight telemetry.
    """
    seen: dict[str, float] = {}
    while clock() < deadline:
        remaining = max(0.0, deadline - clock())
        msg = master.recv_match(
            type="PARAM_VALUE", blocking=True, timeout=min(1.0, remaining) or 0.01,
        )
        if msg is None:
            # No more buffered/incoming PARAM_VALUE right now.
            break
        seen[_decode_param_id(msg.param_id)] = float(msg.param_value)
    return seen


def set_param(
    master: mavutil.mavfile,
    name: str,
    value: float,
    *,
    timeout_s: float = PARAM_SET_READBACK_TIMEOUT_S,
    max_attempts: int = PARAM_SET_MAX_ATTEMPTS,
    tolerance: float = PARAM_SET_TOLERANCE,
    clock: Callable[[], float] = time.time,
) -> float:
    """Set a SITL parameter and confirm it with a PARAM_VALUE readback.

    Returns the confirmed value. Raises TimeoutError if the readback never
    matches the intended value within the given attempts/timeout. This is the
    hard path: the fault must be confirmed applied.
    """
    last_seen: float | None = None
    for attempt in range(1, max_attempts + 1):
        master.mav.param_set_send(
            master.target_system,
            master.target_component,
            _encode_param_id(name),
            float(value),
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
        )
        # Also explicitly request the value back to provoke a PARAM_VALUE even if
        # the broadcast after PARAM_SET was missed.
        master.mav.param_request_read_send(
            master.target_system,
            master.target_component,
            _encode_param_id(name),
            -1,
        )
        deadline = clock() + timeout_s
        while clock() < deadline:
            seen = _drain_param_values(master, deadline, clock=clock)
            if name in seen:
                last_seen = seen[name]
                if abs(last_seen - float(value)) <= tolerance:
                    defaults.log(
                        f"PARAM_SET confirmed {name}={last_seen} "
                        f"(attempt {attempt}/{max_attempts})."
                    )
                    return last_seen
            if not seen:
                break
        defaults.log(
            f"PARAM_SET {name}={value} not yet confirmed "
            f"(last_seen={last_seen}); retrying."
        )
    raise TimeoutError(
        f"Failed to confirm {name}={value} within {max_attempts} attempts "
        f"(last readback value={last_seen})."
    )


def set_params(
    master: mavutil.mavfile,
    params: dict[str, float],
    *,
    timeout_s: float = PARAM_SET_READBACK_TIMEOUT_S,
    clock: Callable[[], float] = time.time,
) -> dict[str, float]:
    """Set several params, each confirmed by readback. Returns confirmed values."""
    confirmed: dict[str, float] = {}
    for name, value in params.items():
        confirmed[name] = set_param(master, name, value, timeout_s=timeout_s, clock=clock)
    return confirmed


def read_param(
    master: mavutil.mavfile,
    name: str,
    *,
    timeout_s: float = PARAM_READ_TIMEOUT_S,
    clock: Callable[[], float] = time.time,
) -> float | None:
    """Best-effort single-param readback. Returns None if not seen in budget."""
    master.mav.param_request_read_send(
        master.target_system,
        master.target_component,
        _encode_param_id(name),
        -1,
    )
    seen = _drain_param_values(master, clock() + timeout_s, clock=clock)
    return seen.get(name)


def snapshot_params(
    master: mavutil.mavfile,
    names: list[str] | tuple[str, ...],
    *,
    total_budget_s: float = PARAM_SNAPSHOT_TOTAL_BUDGET_S,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Read back a set of params for provenance under ONE shared wall-clock
    budget, so a slow/absent param never costs a full timeout per name.

    Requests are all sent up front, then PARAM_VALUEs are drained until the
    shared budget elapses or every name is seen. Missing params map to None.
    """
    snapshot: dict[str, Any] = {name: None for name in names}
    for name in names:
        master.mav.param_request_read_send(
            master.target_system,
            master.target_component,
            _encode_param_id(name),
            -1,
        )
    deadline = clock() + total_budget_s
    wanted = set(names)
    while clock() < deadline and any(snapshot[n] is None for n in wanted):
        seen = _drain_param_values(master, deadline, clock=clock)
        if not seen:
            break
        for pid, value in seen.items():
            if pid in snapshot:
                snapshot[pid] = value
    return snapshot
