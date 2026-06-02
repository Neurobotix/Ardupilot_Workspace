"""sensor_failure environment adapter.

Reuses the proven, sensor-agnostic wind_matrix runtime helpers (SITL launch,
process liveness, stack cleanup, world writing) and MAVLink readiness helpers.
Reusing them across a maximally different sensor (GPS, no Gazebo wind at all) is
itself evidence those helpers were generic. The Gazebo world is always written
CALM (zero wind): GPS faults come from SITL params, not Gazebo.

No legacy runner import. No framework-core edit.
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from datetime import datetime, timezone

from ..wind_matrix import analysis_helpers as wm_analysis_helpers
from ..wind_matrix import mavlink_control as wm_mavlink_control
from ..wind_matrix import runtime as wm_runtime
from ...core.environment import EnvironmentAdapter
from ...core.models import AttemptContext, TestCase
from . import defaults
from .config import SensorFailureConfig


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class SensorFailureEnvironment(EnvironmentAdapter):
    def __init__(self, config: SensorFailureConfig) -> None:
        self._config = config

    def prepare_case(self, case: TestCase) -> None:
        return None

    def launch(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return

        rep = ctx.target_run_index
        pass_index = ctx.extra.get("pass_index")
        pass_part = f"__pass_{int(pass_index):03d}" if pass_index is not None else ""
        prefix = f"{case.case_id}__rep_{rep:02d}{pass_part}__{_stamp()}"
        stack_log_dir = (
            self._config.campaign_root / "scripts" / self._config.stack_log_subdir
        )
        stack_log_dir.mkdir(parents=True, exist_ok=True)

        sitl_log = stack_log_dir / f"{prefix}_sitl.log"
        gazebo_log = stack_log_dir / f"{prefix}_gazebo.log"
        gazebo_world = stack_log_dir / f"{prefix}_world.sdf"
        sitl_use_dir = (
            stack_log_dir / f"{prefix}_sitl_state"
            if self._config.isolated_sitl_state else None
        )

        if sitl_use_dir is not None:
            bin_dir = defaults.sitl_bin_dir(sitl_use_dir)
            ctx.extra["before_bin_names"] = (
                {p.name for p in bin_dir.glob("*.BIN")} if bin_dir.exists() else set()
            )
            ctx.extra["sitl_log_dir"] = sitl_use_dir

        wm_runtime.cleanup_stack()

        sitl_proc, sitl_handle = wm_runtime.launch_sitl(
            sitl_log,
            no_rebuild=not self._config.rebuild,
            wipe_eeprom=self._config.wipe_eeprom,
            use_dir=sitl_use_dir,
            param_files=(
                list(self._config.param_file_stack)
                if self._config.param_file_stack is not None else None
            ),
        )
        ctx.process_handles["sitl"] = sitl_proc
        ctx.log_paths["sitl"] = sitl_log
        ctx.extra["sitl_handle"] = sitl_handle
        time.sleep(self._config.stack_settle_s)
        wm_runtime.ensure_process_alive("SITL", sitl_proc, sitl_log)

        # Always calm: GPS faults are param-driven, not Gazebo-wind-driven.
        wm_runtime.write_static_wind_world(0.0, 0.0, gazebo_world)
        gazebo_proc, gazebo_handle = wm_runtime.launch_gazebo(
            gazebo_log, world_path=gazebo_world,
        )
        ctx.process_handles["gazebo"] = gazebo_proc
        ctx.log_paths["gazebo"] = gazebo_log
        ctx.extra["gazebo_handle"] = gazebo_handle
        time.sleep(self._config.stack_settle_s)
        wm_runtime.ensure_process_alive("Gazebo", gazebo_proc, gazebo_log)

    def assert_ready(self, case: TestCase, ctx: AttemptContext) -> None:
        master = wm_mavlink_control.wait_for_heartbeat(
            self._config.mavlink_addr,
            wm_analysis_helpers.clamp_timeout_to_slot(
                self._config.heartbeat_timeout_s,
                ctx.slot_deadline_monotonic_s,
                phase="heartbeat wait",
            ),
        )
        ctx.extra["mavlink_master"] = master
        ctx.extra["attempt_start_time_utc"] = defaults.utc_now()
        if self._config.auto_control:
            wm_mavlink_control.wait_for_vehicle_ready(
                master,
                wm_analysis_helpers.clamp_timeout_to_slot(
                    self._config.ready_timeout_s,
                    ctx.slot_deadline_monotonic_s,
                    phase="vehicle readiness",
                ),
                force_arm=self._config.force_arm,
            )

    def cleanup(self, case: TestCase, ctx: AttemptContext) -> None:
        if not self._config.launch_stack:
            return
        # Reap the process GROUPS of the children we launched FIRST. sim_vehicle.py
        # spawns mavproxy in the same new session (start_new_session=True), and
        # the shared launch.sh `cleanup` does not actually kill mavproxy (its
        # `pkill -x mavproxy` never matches the real `python .../mavproxy.py`
        # process name). Killing the session/process group leader's group with
        # SIGKILL takes down sim_vehicle + arduplane + mavproxy together, which
        # is what frees udp:14551 for the next attempt and stops the orphan
        # mavproxy that otherwise corrupts the next attempt's telemetry.
        try:
            for proc_name in ("sitl", "gazebo"):
                self._reap_process_group(ctx.process_handles.pop(proc_name, None))
        finally:
            try:
                wm_runtime.cleanup_stack()
            finally:
                self._sweep_orphan_mavproxy()
                for handle_name in ("sitl_handle", "gazebo_handle"):
                    handle = ctx.extra.pop(handle_name, None)
                    if handle is not None:
                        try:
                            handle.close()
                        except Exception:
                            pass

    @staticmethod
    def _reap_process_group(proc) -> None:
        """SIGKILL the whole process group of a launched child (sim_vehicle.py
        or gz). Because we launch with start_new_session=True, the child is its
        own process-group leader, so -pgid reaps the child AND its descendants
        (arduplane, mavproxy)."""
        if proc is None:
            return
        pid = getattr(proc, "pid", None)
        if not pid:
            return
        try:
            pgid = os.getpgid(pid)
        except (ProcessLookupError, PermissionError, OSError):
            pgid = pid
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(pgid, sig)
            except (ProcessLookupError, PermissionError, OSError):
                # Fall back to killing the bare pid if the group is gone.
                try:
                    proc.kill()
                except Exception:
                    pass
                break
            time.sleep(0.3)
            if proc.poll() is not None:
                break
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

    @staticmethod
    def _sweep_orphan_mavproxy() -> None:
        """Backstop: kill any mavproxy bound to our campaign MAVLink out port
        that survived (the known orphan gap). Matches the real process command
        line (`python .../mavproxy.py ... --out udp:127.0.0.1:14551`), which the
        shared launch.sh `pkill -x mavproxy` cannot match."""
        try:
            out = subprocess.run(
                ["pgrep", "-f", "mavproxy.py"],
                capture_output=True, text=True, check=False,
            )
        except Exception:
            return
        for line in out.stdout.split():
            pid = line.strip()
            if not pid.isdigit():
                continue
            try:
                os.kill(int(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass
