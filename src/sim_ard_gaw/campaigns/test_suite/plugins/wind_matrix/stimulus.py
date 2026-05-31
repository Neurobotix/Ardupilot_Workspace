"""Wind-matrix stimulus adapters."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Any

from sim_ard_gaw.campaigns.mission_contract import validate_square_wind_mission_contract
from sim_ard_gaw.campaigns.provenance import parameter_file_provenance

from . import defaults, legacy
from ...core.models import AttemptContext, TestCase
from ...core.stimulus import StimulusAdapter
from .config import WindMatrixConfig


@dataclass
class WindMatrixStimulus(StimulusAdapter):
    config: WindMatrixConfig

    def apply(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        x_mps = float(case.parameters["wind_x_mps"])
        y_mps = float(case.parameters["wind_y_mps"])
        self._ensure_attempt_dir(ctx)
        self._write_run_config(case, ctx)
        run_one = legacy.run_one_module()

        if self.config.auto_control and self.config.auto_wind_phase == "after-takeoff":
            raise RuntimeError(
                "The staged wind_matrix strategy does not yet support "
                "auto_wind_phase='after-takeoff'. Use --attempt-strategy legacy "
                "or choose --auto-wind-phase before-arm."
            )

        preloaded_world = ctx.extra.get(
            "preloaded_wind_world", self.config.preloaded_wind_world,
        )
        preloaded_refresh = ctx.extra.get(
            "preloaded_wind_refresh", self.config.preloaded_wind_refresh,
        )
        archived_world = None
        if preloaded_world is not None:
            archived_world = ctx.attempt_dir / "gazebo_world.sdf"
            if not preloaded_world.exists():
                raise FileNotFoundError(
                    f"Preloaded wind world does not exist: {preloaded_world}"
                )
            shutil.copy2(preloaded_world, archived_world)
            result = run_one.preloaded_wind_artifact(
                x_mps,
                y_mps,
                source_world=preloaded_world,
                archived_world=archived_world,
                refresh_runtime_wind=preloaded_refresh,
                refresh_strict_echo_verify=defaults.STRICT_WIND_ECHO_VERIFY,
                timeout_s=defaults.remaining_deadline_s(
                    ctx.slot_deadline_monotonic_s,
                ),
            )
        else:
            result = run_one.inject_wind(
                x_mps,
                y_mps,
                timeout_s=defaults.remaining_deadline_s(
                    ctx.slot_deadline_monotonic_s,
                ),
            )

        result["application_phase"] = (
            "auto-before-arm" if self.config.auto_control else
            "manual-before-user-mission-control"
        )
        result["auto_wind_phase"] = (
            self.config.auto_wind_phase if self.config.auto_control else None
        )
        defaults.write_json(ctx.attempt_dir / "wind_injection.json", result)
        ctx.extra["wind_injection_artifact"] = ctx.attempt_dir / "wind_injection.json"
        return result

    def _ensure_attempt_dir(self, ctx: AttemptContext) -> None:
        expected = (
            defaults.combo_runs_dir(self.config.campaign_root, ctx.case.case_id)
            / defaults.attempt_key(ctx.attempt_index)
        )
        expected.mkdir(parents=True, exist_ok=True)
        ctx.attempt_dir = expected

    def _write_run_config(self, case: TestCase, ctx: AttemptContext) -> None:
        mission_contract = validate_square_wind_mission_contract(
            self.config.mission_file,
        )
        param_stack = defaults.normalize_param_file_stack(self.config.param_file_stack)
        param_provenance = parameter_file_provenance(param_stack)
        x_mps = float(case.parameters["wind_x_mps"])
        y_mps = float(case.parameters["wind_y_mps"])
        preloaded_world = ctx.extra.get(
            "preloaded_wind_world", self.config.preloaded_wind_world,
        )
        copied_bin_name = defaults.named_bin_filename(
            case.case_id, ctx.target_run_index, ctx.attempt_index,
        )
        bin_search_dir = defaults.sitl_bin_dir(ctx.extra.get("sitl_log_dir"))
        defaults.write_json(ctx.attempt_dir / "run_config.json", {
            "attempt_id": defaults.attempt_id(
                case.case_id, ctx.target_run_index, ctx.attempt_index,
            ),
            "experiment_lane": defaults.CTE_LANE_NAME,
            "x_wind_mps": x_mps,
            "y_wind_mps": y_mps,
            "target_run_index": ctx.target_run_index,
            "attempt_index": ctx.attempt_index,
            "world_name": defaults.WORLD_NAME,
            "wind_topic": defaults.WIND_TOPIC,
            "wind_info_topic": defaults.WIND_INFO_TOPIC,
            "wind_frame": defaults.WIND_FRAME_NOTE,
            "world_default_wind_mps": (
                {"x": x_mps, "y": y_mps, "z": 0.0}
                if preloaded_world is not None else
                {"x": 0.0, "y": 0.0, "z": 0.0}
            ),
            "wind_injection_source": (
                "test_suite staged wind_matrix stimulus adapter"
            ),
            "gazebo_world_file": str(preloaded_world) if preloaded_world else None,
            "archived_gazebo_world_file": (
                str(ctx.attempt_dir / "gazebo_world.sdf")
                if preloaded_world is not None else None
            ),
            "preloaded_wind_refresh": (
                self.config.preloaded_wind_refresh
                if preloaded_world is not None else None
            ),
            "mission_file": str(self.config.mission_file),
            "mission_contract": mission_contract.as_dict(),
            "analysis_position_source": defaults.ANALYSIS_POSITION_SOURCE,
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
            "gazebo_plugin_runtime": defaults.gazebo_plugin_diagnostics(),
            "param_files_loaded_at_sitl_start": param_stack,
            "param_file_provenance": param_provenance,
            "param_stack_order_note": (
                "Files are applied in listed order; later files override earlier ones."
            ),
            "manual_control": not self.config.auto_control,
            "force_arm": self.config.force_arm,
            "auto_wind_phase": (
                self.config.auto_wind_phase if self.config.auto_control else None
            ),
            "attempt_strategy": self.config.attempt_strategy,
        })
        shutil.copy2(self.config.mission_file, ctx.attempt_dir / self.config.mission_file.name)
