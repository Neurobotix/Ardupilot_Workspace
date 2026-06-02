"""Phase 4 genericity + zero-core-edit proof for the sensor_failure plugin.

The Phase 4 thesis: a second, maximally-different plugin (GPS fault injection)
ships with ZERO edits to test_suite/core/*.py. These tests are that proof:

1. `test_core_files_unchanged_vs_phase4_base`: every core/*.py file is
   byte-identical to the Phase 4 branch base commit. If a core file changed to
   make this plugin work, the abstractions were leaking and this fails.

2. `test_staged_attempt_runs_without_legacy_run_imports`: a full staged attempt
   for a GPS case runs with the environment/MAVLink boundary mocked and the
   legacy `run_one`/`run_matrix`/`run_matrix_round_robin` modules blocked from
   import. This proves the new plugin's staged path is zero-legacy.

3. `test_plugin_does_not_import_legacy_runner_modules`: the plugin package and
   its CLI do not statically import the legacy runner modules.
"""
from __future__ import annotations

# pyright: reportMissingImports=false

import builtins
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCRIPTS = SRC / "sim_ard_gaw" / "compat_scripts"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))

CORE_DIR = (
    SRC / "sim_ard_gaw" / "campaigns" / "test_suite" / "core"
)
PLUGIN_DIR = (
    SRC / "sim_ard_gaw" / "campaigns" / "test_suite" / "plugins" / "sensor_failure"
)

# The commit the Phase 4 branch was created from (gps_lane HEAD == accepted
# Phase 3G tip). core/*.py must be byte-identical to this commit.
PHASE4_BASE_COMMIT = "c10b490"

LEGACY_RUNNER_MODULES = ("run_one", "run_matrix", "run_matrix_round_robin")


class ZeroCoreEditProofTests(unittest.TestCase):
    def test_core_files_unchanged_vs_phase4_base(self) -> None:
        core_files = sorted(CORE_DIR.glob("*.py"))
        self.assertTrue(core_files, "expected core/*.py files to exist")
        rel_core = (
            "src/sim_ard_gaw/campaigns/test_suite/core"
        )
        # `git diff --stat <base> -- core/` must be empty for the Phase 4 thesis.
        result = subprocess.run(
            ["git", "diff", "--stat", PHASE4_BASE_COMMIT, "--", rel_core],
            cwd=str(ROOT), capture_output=True, text=True, check=False,
        )
        self.assertEqual(
            0, result.returncode,
            msg=f"git diff failed: {result.stderr}",
        )
        self.assertEqual(
            "", result.stdout.strip(),
            msg=(
                "Phase 4 thesis violated: test_suite/core/*.py changed vs the "
                f"branch base {PHASE4_BASE_COMMIT}:\n{result.stdout}"
            ),
        )

    def test_plugin_does_not_import_legacy_runner_modules(self) -> None:
        offenders: list[str] = []
        for py in sorted(PLUGIN_DIR.glob("*.py")):
            text = py.read_text(encoding="utf-8")
            for mod in LEGACY_RUNNER_MODULES:
                if (
                    f"import {mod}" in text
                    or f"from {mod}" in text
                    or f".{mod}_module" in text
                ):
                    offenders.append(f"{py.name}: references {mod}")
        self.assertEqual([], offenders, msg="\n".join(offenders))


class StagedGenericityTests(unittest.TestCase):
    def test_staged_attempt_runs_without_legacy_run_imports(self) -> None:
        """Run a staged GPS attempt end-to-end with the env/MAVLink boundary
        mocked and legacy runner imports blocked."""
        code = f'''
import builtins, sys
from pathlib import Path
SRC = Path({str(SRC)!r})
SCRIPTS = Path({str(SCRIPTS)!r})
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))

BLOCKED = set({LEGACY_RUNNER_MODULES!r})
_real_import = builtins.__import__
def _guard(name, *a, **k):
    top = name.split(".")[0]
    if top in BLOCKED or name in BLOCKED:
        raise AssertionError(f"legacy runner import blocked: {{name}}")
    return _real_import(name, *a, **k)
builtins.__import__ = _guard

import tempfile
from unittest import mock
from test_suite.plugins.sensor_failure import build_plugin
from test_suite.plugins.sensor_failure.config import SensorFailureConfig
from test_suite.core.models import TestCase

tmp = tempfile.mkdtemp()
cfg = SensorFailureConfig(campaign_root=Path(tmp), case_ids=("gps_disable",),
                          repeats=1, post_inject_window_s=1.0)
plugin = build_plugin(cfg)
case = next(iter(plugin.case_generator.iter_cases()))

# Mock the environment boundary so no SITL/Gazebo is launched and a fake master
# is injected. Mock the staged stages' external effects (param set, monitor).
from collections import deque
class _FakeMaster:
    target_system = 1
    target_component = 1
    def __init__(self):
        self.mav = self
        self._q = deque()
        self._stored = {{}}
    def param_set_send(self, t, c, pid, value, ptype):
        name = pid.decode("ascii") if isinstance(pid, bytes) else str(pid)
        self._stored[name] = float(value)
        self._q.append(("PARAM_VALUE", name, float(value)))
    def param_request_read_send(self, t, c, pid, idx):
        name = pid.decode("ascii") if isinstance(pid, bytes) else str(pid)
        # Echo the CURRENT stored value, mirroring SITL.
        self._q.append(("PARAM_VALUE", name, self._stored.get(name, 0.0)))
    def recv_match(self, type=None, blocking=False, timeout=None):
        wanted = ({{type}} if isinstance(type, str) else set(type)) if type else None
        for i, (mt, name, val) in enumerate(self._q):
            if wanted is None or mt in wanted:
                del self._q[i]
                class _M:
                    pass
                m = _M(); m.param_id = name; m.param_value = val
                m.get_type = lambda mt=mt: mt
                return m
        return None

env = plugin.environment
def _launch(c, ctx): ctx.extra["mavlink_master"] = _FakeMaster()
env.launch = _launch
env.assert_ready = lambda c, ctx: ctx.extra.__setitem__("mavlink_master", _FakeMaster())
env.cleanup = lambda c, ctx: None
env.prepare_case = lambda c: None

runner = plugin.attempt_runner()

# Mock the control stage (no real upload/arm), the monitor's fault injection and
# recv loop, and the analyzer's BIN collection.
import test_suite.plugins.sensor_failure.plugin as plug
plug.SensorFailureAutoMissionControl.execute = lambda self, c, ctx: None

import test_suite.plugins.sensor_failure.monitor as mon
def _fake_run(self, c, ctx):
    from test_suite.core.models import MonitorResult
    ctx.extra["resilience_state"] = {{
        "verdict_mode": "hard_denial", "is_baseline": False, "fault_injected": True,
        "fault_inject_seq": 6, "confirmed_inject_params": {{"SIM_GPS1_ENABLE": 0.0}},
        "mode_at_inject": "AUTO", "mode_after_inject": "RTL",
        "mode_changed_after_inject": True, "modes_seen": ["AUTO", "RTL"],
        "pre_inject_min_relalt_m": 98.0, "pre_inject_max_relalt_m": 102.0,
        "pre_inject_max_roll_deg": 25.0, "pre_inject_max_pitch_deg": 10.0,
        "pre_inject_max_groundspeed_ms": 22.0, "pre_inject_attitude_samples": 12,
        "post_inject_min_relalt_m": 95.0, "post_inject_max_relalt_m": 101.0,
        "post_inject_max_roll_deg": 30.0, "post_inject_max_pitch_deg": 12.0,
        "post_inject_max_groundspeed_ms": 23.0, "post_inject_attitude_samples": 12,
        "post_inject_max_excursion_m": 120.0, "ekf_failsafe_statustext": True,
        "disarmed": False, "timed_out": False,
        "observation_duration_s": 1.0, "stopped_reason": "post_inject_window_complete",
        "notes": [],
    }}
    return MonitorResult(completed=True, reason="fault_injected", duration_s=1.0)
mon.SensorFailureResilienceMonitor.run = _fake_run

import test_suite.plugins.sensor_failure.analyzers as anz
_real_collect = anz.collect_bin_log
anz.collect_bin_log = lambda *a, **k: None  # no BIN in this no-SITL test

attempt_dir = plugin.attempt_dir_factory()(plugin.manifest, case, 1)
record = runner.run(case=case, target_run_index=1, attempt_index=1, attempt_dir=attempt_dir)
assert record.status.value == "success", f"expected success, got {{record.status}}"
assert record.case_id == "gps_disable"
# Manifest accepted it.
assert plugin.manifest.accepted_count(case) == 1, "expected 1 accepted run"
print("STAGED_OK", record.status.value)
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, check=False,
            cwd=str(ROOT),
        )
        self.assertIn(
            "STAGED_OK success", result.stdout,
            msg=f"stdout={result.stdout}\nstderr={result.stderr}",
        )


if __name__ == "__main__":
    # silence unused import warning for builtins in some linters
    _ = builtins
    unittest.main()
