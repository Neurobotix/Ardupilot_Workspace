from __future__ import annotations

# pyright: reportMissingImports=false

import json
import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sim_ard_gaw.campaigns.wind_matrix import run_one  # noqa: E402
from sim_ard_gaw.campaigns.manifest_safety import (  # noqa: E402
    CampaignManifestLockError,
    campaign_manifest_lock,
)
from sim_ard_gaw.campaigns.status import (  # noqa: E402
    annotate_terminal_status,
    legacy_analysis_succeeded,
    terminal_status_for_legacy,
)


def _manifest_transaction_writer(
    root_text: str,
    hold_lock: bool,
    acquired: Any,
    release: Any,
    results: Any,
) -> None:
    root = Path(root_text)
    try:
        with campaign_manifest_lock(root):
            manifest = run_one.load_manifest(root)
            key = "wind_x_00_y_00"
            attempt_index = run_one.next_attempt_index(root, manifest, key)
            manifest["attempts"].append({
                "attempt_id": f"{key}__rep_01__attempt_{attempt_index:03d}",
                "attempt_index": attempt_index,
                "combo_key": key,
                "status": "running",
                "analysis_status": "pending",
                "notes": [],
            })
            run_one.save_manifest(root, manifest)
            acquired.set()
            if hold_lock:
                release.wait(timeout=5.0)
        results.put("saved")
    except Exception as exc:
        results.put(type(exc).__name__)


class CampaignManifestSafetyTests(unittest.TestCase):
    def test_root_lock_rejects_conflicting_manifest_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ctx = multiprocessing.get_context("fork")
            first_acquired = ctx.Event()
            second_acquired = ctx.Event()
            release = ctx.Event()
            results = ctx.Queue()
            first = ctx.Process(
                target=_manifest_transaction_writer,
                args=(str(root), True, first_acquired, release, results),
            )
            second = ctx.Process(
                target=_manifest_transaction_writer,
                args=(str(root), False, second_acquired, release, results),
            )

            first.start()
            self.assertTrue(first_acquired.wait(timeout=5.0))
            second.start()
            second.join(timeout=5.0)
            release.set()
            first.join(timeout=5.0)

            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            self.assertEqual(
                {"saved", CampaignManifestLockError.__name__},
                {results.get(timeout=1.0), results.get(timeout=1.0)},
            )
            saved = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(1, len(saved["attempts"]))
            self.assertEqual(1, saved["attempts"][0]["attempt_index"])

    def test_terminal_status_taxonomy_is_deterministic(self) -> None:
        self.assertEqual("success", terminal_status_for_legacy("success_full"))
        self.assertEqual("partial", terminal_status_for_legacy("success_square_only"))
        self.assertEqual("failed", terminal_status_for_legacy("failed"))
        self.assertEqual(
            "failed_analysis",
            terminal_status_for_legacy("failed_analysis"),
        )
        self.assertEqual("error", terminal_status_for_legacy("error"))
        self.assertEqual("interrupted", terminal_status_for_legacy("interrupted"))
        self.assertIsNone(terminal_status_for_legacy("running"))

    def test_save_manifest_adds_failed_analysis_terminal_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = run_one.load_manifest(root)
            manifest["attempts"].append({
                "attempt_id": "wind_x_00_y_00__rep_01__attempt_001",
                "combo_key": "wind_x_00_y_00",
                "status": "failed_analysis",
                "analysis_status": "failed: analyzer crashed",
                "notes": [],
            })
            run_one.save_manifest(root, manifest)
            saved = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "failed_analysis",
                saved["attempts"][0]["terminal_status"],
            )
            self.assertIn("terminal_status", (root / "manifest.csv").read_text())

    def test_annotation_keeps_legacy_status_unchanged(self) -> None:
        record = {"status": "success_square_only"}
        annotate_terminal_status(record)
        self.assertEqual("success_square_only", record["status"])
        self.assertEqual("partial", record["terminal_status"])

    def test_only_done_legacy_analysis_is_successful(self) -> None:
        self.assertTrue(legacy_analysis_succeeded("done"))
        self.assertFalse(legacy_analysis_succeeded("failed: analyzer crashed"))
        self.assertFalse(legacy_analysis_succeeded("partial: run_summary_failed"))
        self.assertFalse(legacy_analysis_succeeded("not_run"))


if __name__ == "__main__":
    unittest.main()
