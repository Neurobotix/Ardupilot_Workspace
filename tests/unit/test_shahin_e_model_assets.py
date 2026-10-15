"""No-SITL structural tests for the Shahin-E model assets and parameter file.

These tests never launch SITL or Gazebo. They prove:

- `config/vehicles/shahin_e.parm` has no line ArduPilot would split. AP_Param
  reads defaults files with a 100-byte buffer (`char line[100]`) and parses
  each chunk of a longer line as its own `NAME value` pair; on 2026-10-13 this
  silently set `RC3_MAX` and `LOG_FILE_BUFSIZE` to 0.
- The parameter file keeps the real aircraft's flap input and a SITL
  rangefinder.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PARM = ROOT / "config" / "vehicles" / "shahin_e.parm"

# fgets(line, sizeof(line) - 1) with char line[100]; stay well below it.
MAX_LINE_CHARS = 97


def _params(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, value = line.split()[:2]
        values[name] = value
    return values


class ShahinEParameterFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = PARM.read_text(encoding="utf-8")
        cls.params = _params(cls.text)

    def test_no_line_long_enough_to_be_split_by_ap_param(self) -> None:
        long_lines = [
            (number, len(line))
            for number, line in enumerate(self.text.splitlines(), start=1)
            if len(line) > MAX_LINE_CHARS
        ]
        self.assertEqual([], long_lines)

    def test_flap_input_matches_real_aircraft(self) -> None:
        self.assertEqual("208", self.params["RC9_OPTION"])
        self.assertEqual("1100", self.params["RC9_MIN"])
        self.assertEqual("1900", self.params["RC9_MAX"])

    def test_sitl_rangefinder_matches_real_geometry(self) -> None:
        self.assertEqual("100", self.params["RNGFND1_TYPE"])
        self.assertEqual("25", self.params["RNGFND1_ORIENT"])
        self.assertEqual("0.1", self.params["RNGFND1_MIN"])
        self.assertEqual("12", self.params["RNGFND1_MAX"])
        self.assertEqual("0.25", self.params["RNGFND1_GNDCLR"])


if __name__ == "__main__":
    unittest.main()
