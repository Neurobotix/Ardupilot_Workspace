"""Phase-1 integration-readiness report for the gps_failure lane.

Chunk 6 proves the GPS lane is wired into the shared suite path far enough to
run — without launching SITL/Gazebo and without any evidence claim. The report
is a deterministic, no-SITL snapshot of what a suite run *would* schedule: the
full case catalog, the manifest/artifact contract, the effective parameter
stack, and the explicit live-run blockers that still gate Phase 2.

Nothing here opens a MAVLink connection, starts a stack, or reads a BIN log.
"""
from __future__ import annotations

from typing import Any

from ...core.models import TestCase
from . import analyzers, defaults
from .config import GpsFailureConfig
from .plugin import GpsFailurePlugin, build_plugin


# The three adapters that still hard-stub any live behavior. Preflight reports
# them as blockers so "readiness" never reads as "ready to fly".
LIVE_BLOCKERS: tuple[dict[str, str], ...] = (
    {
        "component": "environment.GpsFailureEnvironment",
        "blocker": "launch/assert_ready raise for launch_stack=True",
        "phase": "phase2_live_smoke",
    },
    {
        "component": "control.GpsFailureMissionControl",
        "blocker": "live mission control raises for launch_stack=True",
        "phase": "phase2_live_smoke",
    },
    {
        "component": "monitor.GpsFailureMonitor",
        "blocker": "live monitor raises for launch_stack=True",
        "phase": "phase2_live_smoke",
    },
    {
        "component": "mavlink/runtime",
        "blocker": "no real MAVLink connection or live parameter readback",
        "phase": "phase2_live_smoke",
    },
    {
        "component": "mechanism_gate",
        "blocker": "synthetic records only; no BIN/log innovation extraction",
        "phase": "phase3_full_campaign",
    },
)


def build_readiness_report(
    plugin: GpsFailurePlugin | None = None,
    config: GpsFailureConfig | None = None,
) -> dict[str, Any]:
    """Assemble the full no-SITL integration-readiness report.

    Passing ``plugin`` reuses an already-built plugin (so the report reflects
    exactly what a caller wired up); otherwise a default plugin is built from
    ``config`` (or plugin defaults).
    """
    if plugin is None:
        plugin = build_plugin(config)
    config = plugin.config

    cases = list(plugin.case_generator.iter_cases())
    return {
        "phase": "phase1_no_sitl",
        "lane": defaults.LANE_NAME,
        "suite_name": defaults.SUITE_NAME,
        "plugin_constructed": True,
        "launch_stack": bool(config.launch_stack),
        "launch_performed": False,
        "live_readback_performed": False,
        "suite_path": _suite_path_readiness(plugin, cases),
        "case_catalog": _case_catalog(cases),
        "manifest_contract": _manifest_contract(plugin),
        "artifact_contract": _artifact_contract(),
        "parameter_stack": _parameter_stack(config),
        "trigger": dict(defaults.INJECTION_TRIGGER),
        "live_blockers": [dict(item) for item in LIVE_BLOCKERS],
        "ready_for_live_run": False,
    }


def _suite_path_readiness(
    plugin: GpsFailurePlugin,
    cases: list[TestCase],
) -> dict[str, Any]:
    """Prove the plugin exposes every seam the shared SuiteRunner drives."""
    runner = plugin.attempt_runner()
    attempt_dir_factory = plugin.attempt_dir_factory()
    return {
        "registry_key": defaults.SUITE_NAME,
        "attempt_runner_built": runner is not None,
        "attempt_dir_factory_built": callable(attempt_dir_factory),
        "case_generator": type(plugin.case_generator).__name__,
        "manifest": type(plugin.manifest).__name__,
        "scheduled_case_count": len(cases),
        "scheduled_case_ids": [case.case_id for case in cases],
        "all_cases_share_mission": len(
            {str(case.mission_file) for case in cases}
        )
        == 1,
        "mission_file": str(plugin.config.mission_file),
    }


def _case_catalog(cases: list[TestCase]) -> dict[str, Any]:
    by_fault: dict[str, int] = {fault: 0 for fault in defaults.FAULT_TYPES}
    by_fault["nominal"] = 0
    for case in cases:
        fault = str(case.parameters.get("fault_type", "nominal"))
        by_fault[fault] = by_fault.get(fault, 0) + 1
    return {
        "total": len(cases),
        "by_fault_type": by_fault,
        "fault_types": list(defaults.FAULT_TYPES),
        "behavior_classes": list(defaults.BEHAVIOR_CLASSES),
        "analysis_state_classes": list(defaults.ANALYSIS_STATE_CLASSES),
    }


def _manifest_contract(plugin: GpsFailurePlugin) -> dict[str, Any]:
    """Surface the manifest shape without writing anything to disk."""
    empty = plugin.manifest.load()
    return {
        "adapter": type(plugin.manifest).__name__,
        "top_level_keys": sorted(empty.keys()),
        "attempts_initially_empty": empty.get("attempts") == [],
        "acceptance_rule": (
            "measurement validity only; all terminal/verdict/analysis signals "
            "must agree; contradictory or missing analysis fails closed"
        ),
    }


def _artifact_contract() -> dict[str, Any]:
    required = list(defaults.REQUIRED_ATTEMPT_ARTIFACTS)
    schema = analyzers.artifact_schema()
    # Every required attempt artifact must have a schema entry; report any that
    # do not so a missing schema (e.g. the historical gps_injection.json gap)
    # is visible in the readiness report instead of silently accepted.
    required_without_schema = [name for name in required if name not in schema]
    return {
        "required_attempt_artifacts": required,
        "artifact_schema": schema,
        "artifact_schema_names": sorted(schema.keys()),
        "required_artifacts_without_schema": required_without_schema,
        "schema_covers_required_artifacts": not required_without_schema,
        "min_post_injection_s": defaults.MIN_POST_INJECTION_S,
    }


def _parameter_stack(config: GpsFailureConfig) -> dict[str, Any]:
    return {
        "effective_param_stack": [str(path) for path in config.effective_param_stack],
        "required_sim_gps_params": list(defaults.REQUIRED_SIM_GPS_PARAMS),
        "phase1_probe_mode": (
            "name-existence validation only; live SITL probe is Phase 2"
        ),
    }
