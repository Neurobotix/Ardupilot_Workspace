from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sim_ard_gaw.campaigns.mission_contract import (  # noqa: E402
    MissionContractError,
    validate_square_wind_mission_contract,
)
from sim_ard_gaw.campaigns.provenance import (  # noqa: E402
    parameter_file_provenance,
    relative_file_provenance,
)


MISSION = ROOT / "assets" / "missions" / "square_500m_five_laps_loiter5_land.waypoints"


class CampaignContractTests(unittest.TestCase):
    def test_parameter_provenance_hashes_effective_stack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir) / "base.parm"
            overlay = Path(temp_dir) / "overlay.parm"
            base.write_text("ARSPD_TYPE 0\n", encoding="ascii")
            overlay.write_text("ARSPD_TYPE 100\n", encoding="ascii")
            rows = parameter_file_provenance([base, overlay])
            self.assertEqual([str(base.resolve()), str(overlay.resolve())], [
                row["path"] for row in rows
            ])
            self.assertEqual(64, len(str(rows[0]["sha256"])))
            self.assertNotEqual(rows[0]["sha256"], rows[1]["sha256"])

    def test_relative_file_provenance_hashes_untracked_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "new_input.txt"
            path.write_text("tailwind input\n", encoding="utf-8")
            rows = relative_file_provenance(root, ["new_input.txt"])
            self.assertEqual("new_input.txt", rows[0]["path"])
            self.assertEqual(path.stat().st_size, rows[0]["size_bytes"])
            self.assertEqual(64, len(str(rows[0]["sha256"])))

    def test_square_mission_contract_accepts_canonical_mission(self) -> None:
        validated = validate_square_wind_mission_contract(MISSION)
        self.assertEqual(30, validated.item_count)
        self.assertEqual(
            "square_500m_five_laps_loiter5_land",
            validated.contract.name,
        )

    def test_square_mission_contract_rejects_loiter_layout_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "invalid.waypoints"
            text = MISSION.read_text(encoding="utf-8")
            invalid.write_text(
                text.replace("23\t0\t3\t18\t", "23\t0\t3\t16\t", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MissionContractError, "seq 23"):
                validate_square_wind_mission_contract(invalid)

    def test_square_mission_contract_rejects_square_geometry_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "invalid_geometry.waypoints"
            text = MISSION.read_text(encoding="utf-8")
            invalid.write_text(
                text.replace("-35.3587704\t149.1707448\t100.00", "-35.3500000\t149.1707448\t100.00", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MissionContractError, "side length"):
                validate_square_wind_mission_contract(invalid)

    def test_square_mission_contract_rejects_unsupported_location_frame(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "invalid_frame.waypoints"
            text = MISSION.read_text(encoding="utf-8")
            invalid.write_text(
                text.replace("3\t0\t3\t16\t", "3\t0\t2\t16\t", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MissionContractError, "unsupported location frames"):
                validate_square_wind_mission_contract(invalid)


if __name__ == "__main__":
    unittest.main()
