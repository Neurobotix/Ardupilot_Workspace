"""Environment adapter for gps_failure.

Phase 1 Chunk 1 intentionally does not launch SITL or Gazebo.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import signal
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Protocol

from ...core.environment import EnvironmentAdapter
from ...core.models import AttemptContext, TestCase
from .config import GpsFailureConfig
from . import defaults
from .mavlink import MavlinkConnectionFactory, connect_mavlink


class LaunchFunction(Protocol):
    def __call__(self, command: list[str], *, log_path: Path) -> Any:
        ...


@dataclass(frozen=True)
class GpsLaunchPlan:
    sitl_command: list[str]
    gazebo_command: list[str]
    runtime_root: Path
    sitl_state_dir: Path
    expected_bin_dir: Path

    def as_dict(self) -> dict[str, Any]:
        return {
            "sitl_command": list(self.sitl_command),
            "gazebo_command": list(self.gazebo_command),
            "runtime_root": str(self.runtime_root),
            "sitl_state_dir": str(self.sitl_state_dir),
            "expected_bin_dir": str(self.expected_bin_dir),
            "sitl_target": defaults.SITL_TARGET,
            "gazebo_target": defaults.GAZEBO_TARGET,
            "bin_selection": "new .BIN files only; names snapshotted before launch",
        }


def build_launch_plan(ctx: AttemptContext) -> GpsLaunchPlan:
    runtime_root = ctx.attempt_dir / "runtime"
    sitl_state_dir = defaults.VAR_ROOT / "runs" / "sitl" / defaults.SITL_TARGET
    return GpsLaunchPlan(
        sitl_command=[str(defaults.WORKSPACE_ROOT / "scripts" / "ops" / "launch.sh"), defaults.SITL_TARGET],
        gazebo_command=[
            str(defaults.WORKSPACE_ROOT / "scripts" / "ops" / "launch.sh"),
            defaults.GAZEBO_TARGET,
        ],
        runtime_root=runtime_root,
        sitl_state_dir=sitl_state_dir,
        expected_bin_dir=sitl_state_dir / "logs",
    )


class GpsFailureEnvironment(EnvironmentAdapter):
    def __init__(
        self,
        config: GpsFailureConfig,
        *,
        launcher: LaunchFunction | None = None,
        mavlink_factory: MavlinkConnectionFactory | None = None,
    ) -> None:
        self._config = config
        self._launcher = launcher or _popen_launcher
        self._mavlink_factory = mavlink_factory

    def prepare_case(self, case: TestCase) -> None:
        return None

    def launch(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return None
        plan = build_launch_plan(ctx)
        if defaults.SITL_TARGET != "plane-gps" or defaults.GAZEBO_TARGET != "gazebo-plane-gps":
            raise RuntimeError("gps_failure launch target contract violated")
        if plan.runtime_root.exists():
            shutil.rmtree(plan.runtime_root)
        plan.runtime_root.mkdir(parents=True, exist_ok=True)
        ctx.extra["gps_before_bin_names"] = _bin_names(plan.expected_bin_dir)
        ctx.extra["gps_launch_plan"] = plan.as_dict()
        gazebo_log = ctx.attempt_dir / "gazebo_plane_gps.log"
        sitl_log = ctx.attempt_dir / "plane_gps.log"
        ctx.process_handles["plane-gps"] = self._launcher(
            plan.sitl_command,
            log_path=sitl_log,
        )
        ctx.log_paths["plane-gps"] = sitl_log
        # plane-gps owns the governed broad pre-run cleanup. Do not start
        # Gazebo until that cleanup has definitely completed or the plane
        # launcher could kill the Gazebo process it is meant to use.
        _wait_for_log_marker(
            sitl_log,
            "Cleanup complete",
            ctx.process_handles["plane-gps"],
            timeout_s=self._config.cleanup_timeout_s,
        )
        ctx.process_handles["gazebo-plane-gps"] = self._launcher(
            plan.gazebo_command,
            log_path=gazebo_log,
        )
        ctx.log_paths["gazebo-plane-gps"] = gazebo_log

    def assert_ready(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return None
        master = connect_mavlink(
            self._config.mavlink_addr,
            factory=self._mavlink_factory,
        )
        ctx.extra["mavlink_master"] = master
        from .control import build_mission_adapter

        ctx.extra["mission_adapter"] = build_mission_adapter(master, self._config)

    def cleanup(self, case: TestCase, ctx: AttemptContext) -> None:
        errors: list[str] = []
        for name, proc in list(ctx.process_handles.items()):
            try:
                _terminate_process(proc, timeout_s=self._config.cleanup_timeout_s)
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
            finally:
                log_handle = getattr(proc, "_gps_log_handle", None)
                if log_handle is not None:
                    try:
                        log_handle.close()
                    except Exception as exc:
                        errors.append(f"{name} log: {type(exc).__name__}: {exc}")
                ctx.process_handles.pop(name, None)

        master = ctx.extra.pop("mavlink_master", None)
        if master is not None:
            close = getattr(master, "close", None)
            if not callable(close):
                errors.append("mavlink_master: missing close()")
            else:
                try:
                    close()
                except Exception as exc:
                    errors.append(f"mavlink_master: {type(exc).__name__}: {exc}")

        remaining_processes: list[str] = []
        if "gps_launch_plan" in ctx.extra:
            try:
                remaining_processes = _remaining_simulation_processes()
            except Exception as exc:
                errors.append(f"process_scan: {type(exc).__name__}: {exc}")
            if remaining_processes:
                errors.append(
                    "process_scan: simulation processes remain: "
                    + " | ".join(remaining_processes)
                )

        cleanup_payload = {
            "ok": not errors,
            "errors": list(errors),
            "remaining_process_handles": sorted(ctx.process_handles),
            "remaining_simulation_processes": remaining_processes,
            "mavlink_closed": master is None or not any(
                error.startswith("mavlink_master") for error in errors
            ),
        }
        ctx.extra["gps_cleanup"] = cleanup_payload
        ctx.extra["cleanup_result"] = cleanup_payload
        cleanup_path = ctx.attempt_dir / "gps_cleanup.json"
        try:
            defaults.write_json(cleanup_path, cleanup_payload)
            ctx.artifacts["gps_cleanup.json"] = cleanup_path
        except Exception as exc:
            errors.append(f"cleanup_artifact: {type(exc).__name__}: {exc}")
            cleanup_payload["ok"] = False
            cleanup_payload["errors"] = list(errors)
        if errors:
            raise RuntimeError("GPS cleanup failed: " + "; ".join(errors))


def identify_attempt_bin(ctx: AttemptContext) -> Path | None:
    """Return the one new BIN for this attempt, never a stale fallback."""

    plan = ctx.extra.get("gps_launch_plan")
    if not isinstance(plan, dict):
        return None
    bin_dir = Path(str(plan.get("expected_bin_dir", "")))
    before = set(ctx.extra.get("gps_before_bin_names") or set())
    candidates = [
        path for path in bin_dir.glob("*.BIN") if path.name not in before
    ] if bin_dir.exists() else []
    if len(candidates) != 1:
        return None
    return candidates[0]


def _bin_names(bin_dir: Path) -> set[str]:
    if not bin_dir.exists():
        return set()
    return {path.name for path in bin_dir.glob("*.BIN")}


def _popen_launcher(command: list[str], *, log_path: Path) -> subprocess.Popen[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            command,
            cwd=defaults.WORKSPACE_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    except Exception:
        log_file.close()
        raise
    setattr(proc, "_gps_log_handle", log_file)
    return proc


def _wait_for_log_marker(
    log_path: Path,
    marker: str,
    proc: Any,
    *,
    timeout_s: float,
) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if log_path.exists() and marker in log_path.read_text(
                encoding="utf-8",
                errors="replace",
            ):
                return
        except OSError:
            pass
        poll = getattr(proc, "poll", None)
        if callable(poll):
            status = poll()
            if status is not None:
                raise RuntimeError(
                    f"plane-gps exited with status {status} before cleanup barrier"
                )
        time.sleep(0.05)
    raise TimeoutError(
        f"timed out waiting for plane-gps cleanup barrier in {log_path}"
    )


def _terminate_process(proc: Any, *, timeout_s: float) -> None:
    terminate = getattr(proc, "terminate", None)
    pid = getattr(proc, "pid", None)
    if isinstance(pid, int) and pid > 0:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            return
        except Exception:
            if callable(terminate):
                terminate()
    elif callable(terminate):
        terminate()

    wait = getattr(proc, "wait", None)
    if not callable(wait):
        raise RuntimeError("process handle does not provide wait() for cleanup verification")
    try:
        wait(timeout=timeout_s)
        return
    except TypeError:
        wait()
        return
    except subprocess.TimeoutExpired:
        pass

    kill = getattr(proc, "kill", None)
    if isinstance(pid, int) and pid > 0:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except ProcessLookupError:
            return
        except Exception:
            if callable(kill):
                kill()
    elif callable(kill):
        kill()

    try:
        wait(timeout=timeout_s)
    except TypeError:
        wait()
    except subprocess.TimeoutExpired:
        raise RuntimeError("process remained alive after SIGKILL") from None


def _remaining_simulation_processes() -> list[str]:
    pattern = (
        "[g]z sim|[g]z-sim|[r]uby .*/gz|[a]rduplane|[a]rducopter|"
        "[m]avproxy|[s]im_vehicle.py|[l]idar_bridge"
    )
    result = subprocess.run(
        ["pgrep", "-af", pattern],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"pgrep failed with status {result.returncode}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
