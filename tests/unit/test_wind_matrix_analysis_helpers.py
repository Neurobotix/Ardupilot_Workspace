"""Tests for plugins/wind_matrix/analysis_helpers.py (H-B coverage).

Two test classes:
  TestCollectBinLogBehavior  — pure-filesystem collect_bin_log behavior + legacy parity
  TestAnalysisHelperRealLog  — real-log parity for run_analysis + build_run_summary
"""
from __future__ import annotations

# pyright: reportMissingImports=false

import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sim_ard_gaw.campaigns.wind_matrix import run_one  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import analysis_helpers  # noqa: E402


# ---------------------------------------------------------------------------
# Real-log anchor (H-B)
# ---------------------------------------------------------------------------
_REAL_BIN = (
    ROOT
    / "var/runs/phase5_live_rr_workspace_plugin_recheck_20260521"
    / "wind_x_04_y_04/runs/run_01"
    / "wind_x_04_y_04__rep_01__attempt_002.BIN"
)
_REAL_BIN_SHA256 = "771fa52785154b215e9650adfd3971f2077299a8fc1dbbfa9aedf8cfd62b5711"

_SHARED_RECORD: dict = {
    "attempt_id": "wind_x_04_y_04__rep_01__attempt_002",
    "combo_key": "wind_x_04_y_04",
    "x_wind_mps": 4,
    "y_wind_mps": 4,
    "run_alias": "run_01",
    "status": "success_full",
    "mission_completed_full": True,
    "square_completed": True,
    "loiter_completed": True,
}


class TestCollectBinLogBehavior(unittest.TestCase):
    """Pure-filesystem behavior tests for collect_bin_log; parity against legacy."""

    def _write_bin(self, directory: Path, name: str) -> Path:
        path = directory / name
        path.write_bytes(b"\x00")
        return path

    def test_strict_single_new_bin_returns_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            before = set()
            path = self._write_bin(log_dir, "00000001.BIN")

            result = analysis_helpers.collect_bin_log(
                before, time.time(), log_dir=log_dir, strict_new_names=True
            )
            self.assertEqual(result, path)

            legacy = run_one.collect_bin_log(
                before, time.time(), log_dir=log_dir, strict_new_names=True
            )
            self.assertEqual(legacy, path)

    def test_strict_multiple_new_bins_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            before: set[str] = set()
            self._write_bin(log_dir, "00000001.BIN")
            self._write_bin(log_dir, "00000002.BIN")

            with self.assertRaisesRegex(RuntimeError, "[Mm]ultiple new"):
                analysis_helpers.collect_bin_log(
                    before, time.time(), log_dir=log_dir, strict_new_names=True
                )

            with self.assertRaisesRegex(RuntimeError, "[Mm]ultiple new"):
                run_one.collect_bin_log(
                    before, time.time(), log_dir=log_dir, strict_new_names=True
                )

    def test_strict_no_new_bins_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            path = self._write_bin(log_dir, "00000001.BIN")
            before = {path.name}

            result = analysis_helpers.collect_bin_log(
                before, time.time(), log_dir=log_dir, strict_new_names=True
            )
            self.assertIsNone(result)

            legacy = run_one.collect_bin_log(
                before, time.time(), log_dir=log_dir, strict_new_names=True
            )
            self.assertIsNone(legacy)

    def test_non_strict_mtime_fallback_within_window_returns_newest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            path = self._write_bin(log_dir, "00000001.BIN")
            before = {path.name}
            started_wall = time.time()

            result = analysis_helpers.collect_bin_log(
                before, started_wall, log_dir=log_dir, strict_new_names=False
            )
            self.assertEqual(result, path)

            legacy = run_one.collect_bin_log(
                before, started_wall, log_dir=log_dir, strict_new_names=False
            )
            self.assertEqual(legacy, path)

    def test_empty_dir_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            before: set[str] = set()

            result = analysis_helpers.collect_bin_log(
                before, time.time(), log_dir=log_dir
            )
            self.assertIsNone(result)

            legacy = run_one.collect_bin_log(before, time.time(), log_dir=log_dir)
            self.assertIsNone(legacy)

    def test_missing_dir_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "nonexistent"
            before: set[str] = set()

            result = analysis_helpers.collect_bin_log(
                before, time.time(), log_dir=log_dir
            )
            self.assertIsNone(result)

            legacy = run_one.collect_bin_log(before, time.time(), log_dir=log_dir)
            self.assertIsNone(legacy)


class TestAnalysisHelperRealLog(unittest.TestCase):
    """Real-log parity: run_analysis + build_run_summary must be byte-equal to legacy.

    The real .BIN is at var/runs/.../wind_x_04_y_04__rep_01__attempt_002.BIN
    (sha256: 771fa52785154b215e9650adfd3971f2077299a8fc1dbbfa9aedf8cfd62b5711).
    When that file is absent (e.g. clean checkout) the test is skipped.
    """

    def setUp(self) -> None:
        if not _REAL_BIN.exists():
            raise unittest.SkipTest(
                f"Real flight log absent — skipping real-log analysis parity test. "
                f"Expected path: {_REAL_BIN}"
            )

    def _verify_sha256(self) -> None:
        import hashlib
        h = hashlib.sha256(_REAL_BIN.read_bytes()).hexdigest()
        self.assertEqual(
            _REAL_BIN_SHA256,
            h,
            f"SHA256 mismatch for {_REAL_BIN}: expected {_REAL_BIN_SHA256}, got {h}",
        )

    def test_build_run_summary_is_byte_equal_to_legacy_on_real_log(self) -> None:
        """Run both paths on the same real BIN into separate temp dirs and deep-compare."""
        self._verify_sha256()

        with tempfile.TemporaryDirectory() as tmp:
            dir_legacy = Path(tmp) / "legacy"
            dir_migrated = Path(tmp) / "migrated"
            dir_legacy.mkdir()
            dir_migrated.mkdir()

            record = dict(_SHARED_RECORD)

            # Legacy path.
            run_one.run_analysis(_REAL_BIN, dir_legacy, analysis_position_source="sim")
            summary_legacy = run_one.build_run_summary(record, _REAL_BIN, dir_legacy)

            # Migrated path.
            analysis_helpers.run_analysis(
                _REAL_BIN, dir_migrated, analysis_position_source="sim"
            )
            summary_migrated = analysis_helpers.build_run_summary(
                record, _REAL_BIN, dir_migrated
            )

            # Normalize artifact paths before comparison — they point to different
            # temp subdirs by construction but otherwise must be structurally identical.
            def _strip_artifacts(d: dict) -> dict:
                out = dict(d)
                if "artifacts" in out:
                    out = dict(out)
                    out["artifacts"] = {
                        k: Path(v).name for k, v in out["artifacts"].items()
                    }
                if "raw_log_path" in out:
                    out["raw_log_path"] = Path(out["raw_log_path"]).name
                return out

            self.assertEqual(
                _strip_artifacts(summary_legacy),
                _strip_artifacts(summary_migrated),
                "build_run_summary output differs between legacy and migrated paths on "
                f"the real flight log {_REAL_BIN.name}",
            )


if __name__ == "__main__":
    unittest.main()
