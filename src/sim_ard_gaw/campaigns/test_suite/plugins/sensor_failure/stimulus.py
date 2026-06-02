"""sensor_failure stimulus adapter.

Design decision (per the Phase 4 brief): the stimulus stage establishes a CLEAN
GPS baseline and writes provenance, while the ACTUAL mid-flight fault is set by
the resilience monitor when the trigger waypoint is reached. This keeps the
fault genuinely mid-flight (the difference from wind, which is set before the
mission), and keeps the provenance (intended fault) recorded up front.

Concretely, `apply()`:
  (a) asserts the healthy baseline SIM_GPS1_* params pre-arm (so a previous
      attempt's fault can't leak in), confirmed by readback,
  (b) writes run_config.json (reproducibility) and fault_injection.json
      (the intended fault + trigger waypoint), and
  (c) snapshots the pre-fault GPS params for provenance.

No legacy runner import. No framework-core edit.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Any

from sim_ard_gaw.campaigns.mission_contract import validate_square_wind_mission_contract
from sim_ard_gaw.campaigns.provenance import parameter_file_provenance

from ...core.models import AttemptContext, TestCase
from ...core.stimulus import StimulusAdapter
from . import cases, defaults, mavlink_fault
from .config import SensorFailureConfig


# The SIM_GPS1_* params we read back for provenance (pre- and post-fault).
_PROVENANCE_PARAMS = (
    defaults.SIM_GPS1_ENABLE,
    defaults.SIM_GPS1_GLTCH_X,
    defaults.SIM_GPS1_GLTCH_Y,
    defaults.SIM_GPS1_GLTCH_Z,
    defaults.SIM_GPS1_NUMSATS,
)


@dataclass
class SensorFailureStimulus(StimulusAdapter):
    config: SensorFailureConfig

    def apply(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        self._ensure_attempt_dir(ctx)
        fault_case = cases.CASES_BY_ID[case.case_id]

        master = ctx.extra.get("mavlink_master")
        baseline_confirmed: dict[str, float] = {}
        pre_fault_snapshot: dict[str, Any] = {}
        if master is not None and fault_case.baseline:
            # Re-assert the healthy baseline so a prior attempt cannot leak a
            # fault into this run. Confirmed by readback.
            baseline_confirmed = mavlink_fault.set_params(
                master, fault_case.baseline,
            )
        if master is not None:
            pre_fault_snapshot = mavlink_fault.snapshot_params(
                master, _PROVENANCE_PARAMS,
            )

        self._write_run_config(case, ctx, fault_case)

        fault_record = {
            **cases.case_inject_as_jsonable(fault_case),
            "injection_waypoint": self.config.injection_waypoint,
            "post_inject_window_s": self.config.post_inject_window_s,
            "injection_method": "mavlink_param_set_at_trigger_waypoint",
            "applied_at": "monitor_stage",  # the monitor does the live set
            "baseline_asserted_pre_arm": bool(baseline_confirmed),
            "baseline_confirmed_values": baseline_confirmed,
            "pre_fault_param_snapshot": pre_fault_snapshot,
        }
        defaults.write_json(ctx.attempt_dir / "fault_injection.json", fault_record)
        ctx.extra["fault_injection_artifact"] = ctx.attempt_dir / "fault_injection.json"
        ctx.extra["fault_case"] = fault_case

        return {
            "kind": "sim_gps_param_fault",
            "sensor": fault_case.sensor,
            "mode": fault_case.mode,
            "verdict_mode": fault_case.verdict_mode,
            "inject_params": dict(fault_case.inject),
            "injection_waypoint": self.config.injection_waypoint,
            "applied_at": "monitor_stage",
        }

    def _ensure_attempt_dir(self, ctx: AttemptContext) -> None:
        expected = defaults.attempt_dir(
            self.config.campaign_root, ctx.case.case_id, ctx.attempt_index,
        )
        if ctx.attempt_dir != expected:
            raise RuntimeError(
                "Attempt directory mismatch: expected "
                f"{expected} but got {ctx.attempt_dir}"
            )
        ctx.attempt_dir.mkdir(parents=True, exist_ok=True)

    def _write_run_config(
        self,
        case: TestCase,
        ctx: AttemptContext,
        fault_case: cases.GpsFaultCase,
    ) -> None:
        mission_contract = validate_square_wind_mission_contract(
            self.config.mission_file,
        )
        param_stack = defaults.normalize_param_file_stack(self.config.param_file_stack)
        param_provenance = parameter_file_provenance(param_stack)
        copied_bin_name = defaults.named_bin_filename(
            case.case_id, ctx.target_run_index, ctx.attempt_index,
        )
        bin_search_dir = defaults.sitl_bin_dir(ctx.extra.get("sitl_log_dir"))
        defaults.write_json(ctx.attempt_dir / "run_config.json", {
            "attempt_id": defaults.attempt_id(
                case.case_id, ctx.target_run_index, ctx.attempt_index,
            ),
            "suite_name": "sensor_failure",
            "experiment_lane": "GPS Fault Injection (021 GPS subset)",
            "case_id": case.case_id,
            "sensor": fault_case.sensor,
            "fault_mode": fault_case.mode,
            "verdict_mode": fault_case.verdict_mode,
            "fault_description": fault_case.description,
            "inject_params": dict(fault_case.inject),
            "baseline_params": dict(fault_case.baseline),
            "injection_waypoint": self.config.injection_waypoint,
            "post_inject_window_s": self.config.post_inject_window_s,
            "injection_method": "mavlink_param_set_at_trigger_waypoint",
            "target_run_index": ctx.target_run_index,
            "attempt_index": ctx.attempt_index,
            "mission_file": str(self.config.mission_file),
            "mission_contract": mission_contract.as_dict(),
            "expected_named_bin_file": copied_bin_name,
            "bin_collection_method": (
                "isolated_sitl_use_dir"
                if ctx.extra.get("sitl_log_dir") is not None
                else "launcher_var_use_dir_snapshot_with_mtime_fallback"
            ),
            "mavlink_addr": self.config.mavlink_addr,
            "mission_timeout_s": self.config.mission_timeout_s,
            "sitl_use_dir": (
                str(ctx.extra.get("sitl_log_dir"))
                if ctx.extra.get("sitl_log_dir") is not None else None
            ),
            "sitl_bin_dir": str(bin_search_dir),
            "gazebo_world_wind": {"x": 0.0, "y": 0.0, "z": 0.0},
            "gazebo_world_note": (
                "Calm world; GPS faults come from SITL SIM_GPS1_* params, "
                "not Gazebo wind."
            ),
            "gazebo_plugin_runtime": defaults.gazebo_plugin_diagnostics(),
            "sitl_wipe_eeprom_expected": self.config.wipe_eeprom,
            "param_files_loaded_at_sitl_start": param_stack,
            "param_file_provenance": param_provenance,
            "param_stack_order_note": (
                "Files are applied in listed order; later files override earlier ones."
            ),
            "force_arm": self.config.force_arm,
            "auto_control": self.config.auto_control,
            "sim_gps1_param_ground_truth": {
                "verified_against": "src/ardupilot/libraries/SITL/SIM_GPS.cpp + live SITL",
                "subgroup_prefix": defaults.SIM_GPS1_PREFIX,
                "glitch_units": {
                    "SIM_GPS1_GLTCH_X": "latitude offset in degrees",
                    "SIM_GPS1_GLTCH_Y": "longitude offset in degrees",
                    "SIM_GPS1_GLTCH_Z": "altitude offset in metres",
                },
                "home_lat_deg": defaults.SITL_HOME_LAT_DEG,
            },
        })
        shutil.copy2(
            self.config.mission_file, ctx.attempt_dir / self.config.mission_file.name
        )
