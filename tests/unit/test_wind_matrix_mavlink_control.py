from __future__ import annotations

# pyright: reportMissingImports=false

import sys
import tempfile
import unittest
from collections import deque
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sim_ard_gaw.campaigns.wind_matrix import run_one  # noqa: E402
from sim_ard_gaw.campaigns.wind_matrix import run_one as run_one_impl  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import defaults  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import mavlink_control  # noqa: E402
from pymavlink import mavwp  # noqa: E402


class _FakeMessage:
    def __init__(self, msg_type: str, **fields: Any) -> None:
        self._msg_type = msg_type
        for key, value in fields.items():
            setattr(self, key, value)

    def get_type(self) -> str:
        return self._msg_type

    def to_dict(self) -> dict[str, Any]:
        payload = {
            key: value for key, value in self.__dict__.items() if key != "_msg_type"
        }
        payload["mavpackettype"] = self._msg_type
        return payload


class _FakeMaster:
    def __init__(self, messages: list[_FakeMessage]) -> None:
        self._messages = deque(messages)

    def recv_match(self, type=None, blocking=False, timeout=None):  # noqa: ANN001
        if self._messages:
            return self._messages.popleft()
        return None


class WindMatrixMavlinkControlParityTests(unittest.TestCase):
    def test_mission_item_count_matches_legacy(self) -> None:
        mission_file = defaults.MISSION_FILE
        self.assertEqual(
            run_one.mission_item_count(mission_file),
            mavlink_control.mission_item_count(mission_file),
        )

    def test_mission_item_int_matches_legacy(self) -> None:
        mission_file = defaults.MISSION_FILE
        loader = mavwp.MAVWPLoader()
        loader.load(str(mission_file))

        for idx in range(loader.count()):
            wp = loader.wp(idx)
            left = run_one.mission_item_int(wp, 1, 1)
            right = mavlink_control.mission_item_int(wp, 1, 1)
            self.assertEqual(int(left.target_system), int(right.target_system))
            self.assertEqual(int(left.target_component), int(right.target_component))
            self.assertEqual(int(left.seq), int(right.seq))
            self.assertEqual(int(left.frame), int(right.frame))
            self.assertEqual(int(left.command), int(right.command))
            self.assertEqual(int(left.current), int(right.current))
            self.assertEqual(int(left.autocontinue), int(right.autocontinue))
            self.assertEqual(float(left.param1), float(right.param1))
            self.assertEqual(float(left.param2), float(right.param2))
            self.assertEqual(float(left.param3), float(right.param3))
            self.assertEqual(float(left.param4), float(right.param4))
            self.assertEqual(int(left.x), int(right.x))
            self.assertEqual(int(left.y), int(right.y))
            self.assertEqual(float(left.z), float(right.z))

    def _run_monitor_both(
        self,
        messages: list[_FakeMessage],
        *,
        timeout_s: float,
        mission_pre_loaded: bool = False,
        stop_on_square_loiter: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left_master = _FakeMaster(list(messages))
            right_master = _FakeMaster(list(messages))
            left_log = root / "legacy_monitor.log"
            right_log = root / "migrated_monitor.log"

            with (
                patch.object(run_one_impl, "utc_now", return_value="2026-06-01T00:00:00+00:00"),
                patch.object(defaults, "utc_now", return_value="2026-06-01T00:00:00+00:00"),
                patch.object(run_one_impl.mavutil, "mode_string_v10", side_effect=lambda msg: getattr(msg, "mode_name", "UNKNOWN")),
                patch.object(mavlink_control.mavutil, "mode_string_v10", side_effect=lambda msg: getattr(msg, "mode_name", "UNKNOWN")),
            ):
                left_state = run_one_impl.monitor_until_disarm(
                    left_master,
                    left_log,
                    timeout_s=timeout_s,
                    mission_pre_loaded=mission_pre_loaded,
                    stop_on_square_loiter=stop_on_square_loiter,
                )
                right_state = mavlink_control.monitor_until_disarm(
                    right_master,
                    right_log,
                    timeout_s=timeout_s,
                    mission_pre_loaded=mission_pre_loaded,
                    stop_on_square_loiter=stop_on_square_loiter,
                )
        return left_state, right_state

    def test_monitor_until_disarm_full_mission_matches_legacy(self) -> None:
        armed = run_one.mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
        messages = [
            _FakeMessage("HEARTBEAT", base_mode=armed, mode_name="AUTO"),
            _FakeMessage("MISSION_CURRENT", seq=3, total=29),
            _FakeMessage("MISSION_ITEM_REACHED", seq=23),
            _FakeMessage("MISSION_ITEM_REACHED", seq=25),
            _FakeMessage("MISSION_ITEM_REACHED", seq=29),
            _FakeMessage("HEARTBEAT", base_mode=0, mode_name="MANUAL"),
        ]
        left, right = self._run_monitor_both(messages, timeout_s=5.0)
        self.assertEqual(left, right)

    def test_monitor_until_disarm_square_loiter_early_stop_matches_legacy(self) -> None:
        armed = run_one.mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
        messages = [
            _FakeMessage("HEARTBEAT", base_mode=armed, mode_name="AUTO"),
            _FakeMessage("MISSION_CURRENT", seq=3, total=29),
            _FakeMessage("MISSION_ITEM_REACHED", seq=25),
        ]
        left, right = self._run_monitor_both(
            messages,
            timeout_s=5.0,
            stop_on_square_loiter=True,
        )
        self.assertEqual(left, right)

    def test_monitor_until_disarm_invalid_start_reason_matches_legacy(self) -> None:
        armed = run_one.mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
        messages = [
            _FakeMessage("HEARTBEAT", base_mode=armed, mode_name="AUTO"),
            _FakeMessage("MISSION_CURRENT", seq=23, total=29),
        ]
        left, right = self._run_monitor_both(messages, timeout_s=5.0)
        self.assertEqual(left, right)
        self.assertIsNotNone(right.get("invalid_start_reason"))

    def test_monitor_until_disarm_timeout_matches_legacy(self) -> None:
        left, right = self._run_monitor_both([], timeout_s=0.0)
        self.assertEqual(left, right)
        self.assertTrue(right.get("timed_out"))


class WindMatrixHeartbeatTests(unittest.TestCase):
    """The heartbeat names the commanded wind and admits what it cannot see."""

    def _messages(self) -> list[_FakeMessage]:
        return [
            _FakeMessage("MISSION_CURRENT", seq=seq, total=12)
            for seq in range(1, 5)
        ]

    def _run(self, **kwargs: Any) -> list[str]:
        # Advance the clock 8 s per message so the 15 s cadence fires.
        ticks = {"n": 0}

        def fake_time() -> float:
            ticks["n"] += 1
            return 1_000.0 + ticks["n"] * 8.0

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "monitor.log"
            with patch.object(mavlink_control.time, "time", fake_time), patch(
                "sim_ard_gaw.campaigns.test_suite.core.heartbeat.log"
            ) as log:
                mavlink_control.monitor_until_disarm(
                    _FakeMaster(self._messages()),
                    log_path,
                    120.0,
                    mission_pre_loaded=True,
                    **kwargs,
                )
        return [str(call.args[0]) for call in log.call_args_list]

    def test_heartbeat_reports_commanded_wind_for_the_cell(self) -> None:
        messages = self._run(
            case_id="wind_x_04_y_08", commanded_wind_mps=(4.0, 8.0)
        )

        self.assertTrue(messages)
        for msg in messages:
            self.assertIn("wind_x_04_y_08", msg)
            self.assertIn("wind_cmd=(+4,+8)", msg)

    def test_heartbeat_marks_unreachable_response_fields_unavailable(self) -> None:
        """This lane subscribes to no VFR_HUD/NAV_CONTROLLER_OUTPUT.

        Groundspeed and cross-track error are the response side of the
        experiment, but sourcing them would require new telemetry, so they
        must be reported as unavailable rather than invented.
        """
        messages = self._run(
            case_id="wind_x_00_y_00", commanded_wind_mps=(0.0, 0.0)
        )

        self.assertTrue(messages)
        for msg in messages:
            self.assertIn("GS=unavailable", msg)
            self.assertIn("CTE=unavailable", msg)

    def test_heartbeat_reports_unknown_wind_without_defaulting_to_zero(self) -> None:
        messages = self._run(case_id="wind_unknown", commanded_wind_mps=None)

        self.assertTrue(messages)
        for msg in messages:
            self.assertIn("wind_cmd=?", msg)


if __name__ == "__main__":
    unittest.main()
