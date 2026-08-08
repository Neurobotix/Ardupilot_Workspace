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

from sim_ard_gaw.campaigns.provenance import (
    file_provenance,
    parameter_file_provenance,
    source_tree_snapshot,
)

from ...core.environment import EnvironmentAdapter
from ...core.models import AttemptContext, TestCase
from .config import GpsFailureConfig
from . import defaults
from .mavlink import MavlinkConnectionFactory, connect_mavlink


class LaunchFunction(Protocol):
    def __call__(self, command: list[str], *, log_path: Path) -> Any:
        ...


class VehicleReadinessFunction(Protocol):
    def __call__(self, master: Any, timeout_s: float, *, force_arm: bool) -> None:
        ...


class GovernedCleanupFunction(Protocol):
    def __call__(self, *, timeout_s: float) -> dict[str, Any]:
        ...


class ProcessScanner(Protocol):
    def __call__(self) -> list[str]:
        ...


@dataclass(frozen=True)
class GpsLaunchPlan:
    sitl_command: list[str]
    gazebo_command: list[str]
    runtime_root: Path
    sitl_state_dir: Path
    expected_bin_dir: Path
    param_file_stack: list[Path]
    sitl_target: str
    gazebo_target: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "sitl_command": list(self.sitl_command),
            "gazebo_command": list(self.gazebo_command),
            "runtime_root": str(self.runtime_root),
            "sitl_state_dir": str(self.sitl_state_dir),
            "expected_bin_dir": str(self.expected_bin_dir),
            "sitl_target": self.sitl_target,
            "gazebo_target": self.gazebo_target,
            "param_file_stack": [str(path) for path in self.param_file_stack],
            "bin_selection": "new .BIN files only; names snapshotted before launch",
        }


def build_launch_plan(
    ctx: AttemptContext,
    config: GpsFailureConfig | None = None,
) -> GpsLaunchPlan:
    runtime_root = ctx.attempt_dir / "runtime"
    sitl_state_dir = defaults.sitl_state_dir(
        ctx.campaign_root,
        ctx.case.case_id,
        ctx.attempt_index,
    )
    param_file_stack = (
        config.effective_param_stack if config is not None else defaults.default_param_files()
    )
    sitl_target = config.sitl_target if config is not None else defaults.SITL_TARGET
    gazebo_target = (
        config.gazebo_target if config is not None else defaults.GAZEBO_TARGET
    )
    param_stack_env = ":".join(str(path) for path in param_file_stack)
    return GpsLaunchPlan(
        sitl_command=[
            "env",
            f"SIM_ARD_GAW_SITL_USE_DIR={sitl_state_dir}",
            f"SIM_ARD_GAW_GPS_PARAM_FILES={param_stack_env}",
            str(defaults.WORKSPACE_ROOT / "scripts" / "ops" / "launch.sh"),
            sitl_target,
        ],
        gazebo_command=[
            str(defaults.WORKSPACE_ROOT / "scripts" / "ops" / "launch.sh"),
            gazebo_target,
        ],
        runtime_root=runtime_root,
        sitl_state_dir=sitl_state_dir,
        expected_bin_dir=sitl_state_dir / "logs",
        param_file_stack=list(param_file_stack),
        sitl_target=sitl_target,
        gazebo_target=gazebo_target,
    )


class GpsFailureEnvironment(EnvironmentAdapter):
    def __init__(
        self,
        config: GpsFailureConfig,
        *,
        launcher: LaunchFunction | None = None,
        mavlink_factory: MavlinkConnectionFactory | None = None,
        vehicle_readiness: VehicleReadinessFunction | None = None,
        governed_cleanup: GovernedCleanupFunction | None = None,
        process_scanner: ProcessScanner | None = None,
    ) -> None:
        self._config = config
        self._launcher = launcher or _popen_launcher
        self._mavlink_factory = mavlink_factory
        self._vehicle_readiness = vehicle_readiness or _wait_for_vehicle_ready
        self._governed_cleanup = governed_cleanup or _run_governed_cleanup
        self._process_scanner = process_scanner or _remaining_simulation_processes

    def prepare_case(self, case: TestCase) -> None:
        return None

    def launch(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return None
        plan = build_launch_plan(ctx, self._config)
        if (
            plan.sitl_target != defaults.SITL_TARGET
            or plan.gazebo_target not in defaults.GAZEBO_TARGETS
        ):
            raise RuntimeError("gps_failure launch target contract violated")
        if plan.runtime_root.exists():
            shutil.rmtree(plan.runtime_root)
        plan.runtime_root.mkdir(parents=True, exist_ok=True)
        if plan.sitl_state_dir.exists():
            shutil.rmtree(plan.sitl_state_dir)
        plan.sitl_state_dir.mkdir(parents=True, exist_ok=True)
        ctx.extra["gps_before_bin_names"] = _bin_names(plan.expected_bin_dir)
        ctx.extra["gps_launch_plan"] = plan.as_dict()
        gazebo_log = ctx.attempt_dir / f"{plan.gazebo_target.replace('-', '_')}.log"
        sitl_log = ctx.attempt_dir / f"{plan.sitl_target.replace('-', '_')}.log"
        run_config = build_run_config(
            config=self._config,
            case=case,
            ctx=ctx,
            plan=plan,
            sitl_log=sitl_log,
            gazebo_log=gazebo_log,
        )
        run_config_path = ctx.attempt_dir / "run_config.json"
        defaults.write_json(run_config_path, run_config)
        ctx.artifacts["run_config.json"] = run_config_path
        ctx.extra["run_config"] = run_config
        ctx.process_handles[plan.sitl_target] = self._launcher(
            plan.sitl_command,
            log_path=sitl_log,
        )
        ctx.log_paths[plan.sitl_target] = sitl_log
        # plane-gps owns the governed broad pre-run cleanup. Do not start
        # Gazebo until that cleanup has definitely completed or the plane
        # launcher could kill the Gazebo process it is meant to use.
        _wait_for_log_marker(
            sitl_log,
            "Cleanup complete",
            ctx.process_handles[plan.sitl_target],
            timeout_s=self._config.cleanup_timeout_s,
        )
        ctx.process_handles[plan.gazebo_target] = self._launcher(
            plan.gazebo_command,
            log_path=gazebo_log,
        )
        ctx.log_paths[plan.gazebo_target] = gazebo_log

    def assert_ready(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return None
        master = connect_mavlink(
            self._config.mavlink_addr,
            timeout_s=self._config.heartbeat_timeout_s,
            factory=self._mavlink_factory,
        )
        ctx.extra["mavlink_master"] = master
        self._vehicle_readiness(
            master,
            self._config.ready_timeout_s,
            force_arm=self._config.force_arm,
        )
        ctx.extra["gps_vehicle_readiness"] = {
            "ok": True,
            "ready_timeout_s": self._config.ready_timeout_s,
            "requirements": [
                "AUTO mode available",
                "vehicle not INITIALISING",
                "GPS ready",
                "EKF active",
                "two consecutive ready heartbeats",
            ],
        }
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

        governed_cleanup_result: dict[str, Any] | None = None
        remaining_processes: list[str] = []
        if "gps_launch_plan" in ctx.extra:
            try:
                governed_cleanup_result = self._governed_cleanup(
                    timeout_s=self._config.cleanup_timeout_s,
                )
                if governed_cleanup_result.get("ok") is not True:
                    errors.append(
                        "governed_cleanup: "
                        + str(
                            governed_cleanup_result.get("error")
                            or "cleanup command did not report success"
                        )
                    )
            except Exception as exc:
                errors.append(f"governed_cleanup: {type(exc).__name__}: {exc}")
            try:
                remaining_processes = self._process_scanner()
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
            "governed_cleanup": governed_cleanup_result,
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


def build_run_config(
    *,
    config: GpsFailureConfig,
    case: TestCase,
    ctx: AttemptContext,
    plan: GpsLaunchPlan,
    sitl_log: Path,
    gazebo_log: Path,
) -> dict[str, Any]:
    """Build the sensor-neutral provenance record for one GPS attempt."""

    mission_file = (case.mission_file or config.mission_file).expanduser().resolve()
    param_stack = [
        path.expanduser().resolve() for path in config.effective_param_stack
    ]
    plugin_path = defaults.WORKSPACE_GAZEBO_PLUGIN_FILE
    plugin_provenance = file_provenance(plugin_path) if plugin_path.is_file() else None
    return {
        "created_at_utc": defaults.utc_now(),
        "timezone": "UTC",
        "case_id": case.case_id,
        "attempt_id": defaults.case_attempt_id(
            case.case_id,
            ctx.target_run_index,
            ctx.attempt_index,
        ),
        "attempt_index": ctx.attempt_index,
        "target_run_index": ctx.target_run_index,
        "campaign_root": str(config.campaign_root),
        "attempt_dir": str(ctx.attempt_dir),
        "mission_file": str(mission_file),
        "envelope": config.envelope_metadata,
        "mission_file_provenance": file_provenance(mission_file),
        "gazebo_world": str(config.gazebo_world_file),
        "gazebo_world_provenance": file_provenance(config.gazebo_world_file),
        "mavlink_addr": config.mavlink_addr,
        "launch_stack": config.launch_stack,
        "fresh_sitl_process_per_attempt": True,
        "param_files_loaded_at_sitl_start": [str(path) for path in param_stack],
        "param_file_provenance": parameter_file_provenance(param_stack),
        "param_stack_order_note": (
            "Files are applied in listed order; later files override earlier ones."
        ),
        "local_param_override_present": any(
            ".private" in path.parts for path in param_stack
        ),
        "source_tree_snapshot": source_tree_snapshot(defaults.WORKSPACE_ROOT),
        "commands": {
            "sitl": list(plan.sitl_command),
            "gazebo": list(plan.gazebo_command),
            "sitl_target": plan.sitl_target,
            "gazebo_target": plan.gazebo_target,
        },
        "runtime": plan.as_dict(),
        "logs": {
            "sitl": str(sitl_log),
            "gazebo": str(gazebo_log),
        },
        "workspace_gazebo_plugin": {
            "policy": "workspace_build_only",
            "path": str(plugin_path),
            "exists": plugin_path.is_file(),
            "provenance": plugin_provenance,
        },
    }


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


def _wait_for_vehicle_ready(
    master: Any,
    timeout_s: float,
    *,
    force_arm: bool,
) -> None:
    """Apply the GPS-owned Plane readiness gate before mission I/O."""

    from . import mavlink

    mavlink.wait_for_vehicle_ready(
        master,
        timeout_s,
        force_arm=force_arm,
    )


def _run_governed_cleanup(*, timeout_s: float) -> dict[str, Any]:
    owned_cleanup_error: str | None = None
    try:
        _cleanup_workspace_owned_processes()
    except Exception as exc:
        owned_cleanup_error = f"{type(exc).__name__}: {exc}"
    owned_cleanup = {
        "attempted": True,
        "implementation": "gps_failure.environment._cleanup_workspace_owned_processes",
        "ok": owned_cleanup_error is None,
        "error": owned_cleanup_error,
    }
    command = [
        str(defaults.WORKSPACE_ROOT / "scripts" / "ops" / "launch.sh"),
        "cleanup",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=defaults.WORKSPACE_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "attempted": True,
            "ok": False,
            "command": command,
            "returncode": None,
            "timed_out": True,
            "stdout": str(exc.stdout or ""),
            "stderr": str(exc.stderr or ""),
            "owned_cleanup": owned_cleanup,
            "error": (
                f"owned cleanup failed: {owned_cleanup_error}; "
                if owned_cleanup_error is not None
                else ""
            ) + f"canonical cleanup timed out after {timeout_s}s",
        }
    errors: list[str] = []
    if owned_cleanup_error is not None:
        errors.append(f"owned cleanup failed: {owned_cleanup_error}")
    if result.returncode != 0:
        errors.append(f"cleanup command exited with status {result.returncode}")
    return {
        "attempted": True,
        "ok": not errors,
        "command": command,
        "returncode": result.returncode,
        "timed_out": False,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "owned_cleanup": owned_cleanup,
        "error": "; ".join(errors) if errors else None,
    }


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


def _cleanup_workspace_owned_processes() -> None:
    """Terminate only GPS stack processes rooted in this workspace."""

    pids = _workspace_owned_process_pids()
    if not pids:
        return
    remaining = pids
    for sig in (signal.SIGTERM, signal.SIGKILL):
        signaled: list[int] = []
        for pid in remaining:
            try:
                os.kill(pid, sig)
                signaled.append(pid)
            except ProcessLookupError:
                continue
            except PermissionError:
                signaled.append(pid)
        if sig == signal.SIGTERM:
            time.sleep(1.0)
            remaining = [pid for pid in signaled if _pid_exists(pid)]


def _workspace_owned_process_pids() -> list[int]:
    root = str(defaults.WORKSPACE_ROOT)
    world = defaults.GAZEBO_WORLD_FILE
    markers = (
        "Tools/autotest/sim_vehicle.py -v ArduPlane -f JSON",
        "build/sitl/bin/arduplane -w --model JSON",
        "env/bin/mavproxy.py --retries",
        f"gz sim -v4 -r {world}",
    )
    pids: list[int] = []
    self_pid = os.getpid()
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        pid = int(proc.name)
        if pid == self_pid:
            continue
        try:
            cmdline = (
                proc.joinpath("cmdline")
                .read_bytes()
                .replace(b"\0", b" ")
                .decode("utf-8", errors="ignore")
            )
        except OSError:
            continue
        if not cmdline or root not in cmdline:
            continue
        if "xterm" in cmdline and "ArduPlane" in cmdline:
            pids.append(pid)
            continue
        if any(marker in cmdline for marker in markers):
            pids.append(pid)
    return sorted(set(pids), reverse=True)


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


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
