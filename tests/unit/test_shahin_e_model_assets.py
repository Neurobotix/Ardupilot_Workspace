"""No-SITL structural tests for the Shahin-E model assets and parameter file.

These tests never launch SITL or Gazebo. They prove:

- `config/vehicles/shahin_e.parm` has no line ArduPilot would split. AP_Param
  reads defaults files with a 100-byte buffer (`char line[100]`) and parses
  each chunk of a longer line as its own `NAME value` pair; on 2026-10-13 this
  silently set `RC3_MAX` and `LOG_FILE_BUFSIZE` to 0.
- The parameter file keeps the real aircraft's flap input and a SITL
  rangefinder.
- The model carries a downward gpu_lidar rangefinder wired to the
  ArduPilotPlugin as range sensor 1 (sent to SITL as `rng_1`), mounted so it
  reads `RNGFND1_GNDCLR` on the ground, and the world loads the Sensors system
  that renders it. With the JSON backend, `RNGFND1_TYPE 100` gets data only
  from that sensor (Gate 1 run 2: `PreArm: Rangefinder 1: No Data`).
"""
from __future__ import annotations

import math
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PARM = ROOT / "config" / "vehicles" / "shahin_e.parm"
MODEL = ROOT / "assets" / "models" / "shahin_e" / "model.sdf"
WORLD = ROOT / "assets" / "worlds" / "shahin_e_runway.sdf"

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


class ShahinERangefinderAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = ET.parse(MODEL).getroot().find("model")
        cls.params = _params(PARM.read_text(encoding="utf-8"))

    def _rangefinder(self) -> ET.Element:
        sensors = self.model.findall("./link[@name='base_link']/sensor[@name='rangefinder']")
        self.assertEqual(1, len(sensors))
        return sensors[0]

    def test_rangefinder_is_single_downward_ray(self) -> None:
        sensor = self._rangefinder()
        self.assertEqual("gpu_lidar", sensor.get("type"))
        roll, pitch, yaw = [float(v) for v in sensor.findtext("pose").split()[3:]]
        self.assertAlmostEqual(0.0, roll)
        self.assertAlmostEqual(math.pi / 2, pitch, places=5)  # +x rotated to -z
        self.assertAlmostEqual(0.0, yaw)
        self.assertEqual("1", sensor.findtext("ray/scan/horizontal/samples"))
        self.assertAlmostEqual(
            float(self.params["RNGFND1_MIN"]), float(sensor.findtext("ray/range/min"))
        )
        self.assertAlmostEqual(
            float(self.params["RNGFND1_MAX"]), float(sensor.findtext("ray/range/max"))
        )

    def test_rangefinder_reads_ground_clearance_on_the_gear(self) -> None:
        sensor_z = float(self._rangefinder().findtext("pose").split()[2])
        gear_bottoms = []
        for collision in self.model.findall("./link[@name='base_link']/collision"):
            radius = collision.findtext("geometry/sphere/radius")
            if radius is not None:
                gear_bottoms.append(
                    float(collision.findtext("pose").split()[2]) - float(radius)
                )
        self.assertEqual(3, len(gear_bottoms))
        ground_z = min(gear_bottoms)
        self.assertAlmostEqual(
            float(self.params["RNGFND1_GNDCLR"]), sensor_z - ground_z, places=3
        )

    def test_rangefinder_ray_clears_the_fuselage(self) -> None:
        sensor_y = float(self._rangefinder().findtext("pose").split()[1])
        fuselage = self.model.find(
            "./link[@name='base_link']/visual[@name='fuselage_visual']"
        )
        half_width = float(fuselage.findtext("geometry/box/size").split()[1]) / 2
        self.assertGreater(abs(sensor_y), half_width)

    def test_plugin_sends_rangefinder_as_range_sensor_1(self) -> None:
        topic = self._rangefinder().findtext("topic")
        plugin = self.model.find("./plugin[@name='ArduPilotPlugin']")
        wired = plugin.findall("sensor")
        self.assertEqual(1, len(wired))
        self.assertEqual("1", wired[0].findtext("index"))
        self.assertEqual(topic, wired[0].findtext("topic"))

    def test_world_loads_sensors_system(self) -> None:
        world = ET.parse(WORLD).getroot().find("world")
        filenames = [p.get("filename") for p in world.findall("plugin")]
        self.assertIn("gz-sim-sensors-system", filenames)


if __name__ == "__main__":
    unittest.main()
