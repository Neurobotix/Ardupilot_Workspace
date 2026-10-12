from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = ROOT / "scripts" / "dev" / "decision_page"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import build_decision_page as bdp  # noqa: E402

EXAMPLE = json.loads((TOOL_DIR / "example_spec.json").read_text())


class ValidateTests(unittest.TestCase):
    def test_example_spec_is_valid(self) -> None:
        bdp.validate(EXAMPLE)

    def test_rec_must_be_an_option_key(self) -> None:
        spec = copy.deepcopy(EXAMPLE)
        spec["cards"][0]["rec"] = "archive"
        with self.assertRaisesRegex(bdp.SpecError, "rec 'archive' is not one of"):
            bdp.validate(spec)

    def test_duplicate_card_ids_and_unknown_section_are_reported_together(self) -> None:
        spec = copy.deepcopy(EXAMPLE)
        spec["cards"][1]["id"] = "D01"
        spec["cards"][1]["section"] = "nowhere"
        with self.assertRaises(bdp.SpecError) as ctx:
            bdp.validate(spec)
        self.assertIn("duplicate id", str(ctx.exception))
        self.assertIn("section 'nowhere' is not defined", str(ctx.exception))

    def test_chip_tone_is_checked(self) -> None:
        spec = copy.deepcopy(EXAMPLE)
        spec["cards"][0]["chips"] = [["loud", "red"]]
        with self.assertRaisesRegex(bdp.SpecError, "chips must be"):
            bdp.validate(spec)


class PrepareAndRenderTests(unittest.TestCase):
    def test_prepare_fills_size_label_and_size_placeholder(self) -> None:
        data = bdp.prepare(copy.deepcopy(EXAMPLE))
        card = data["cards"][0]
        self.assertEqual(card["size_label"], "3.1G")
        self.assertEqual(card["if_yes"], "3.1G freed.")
        self.assertEqual(data["cards"][1]["size_label"], "")
        self.assertEqual(data["export_name"], "example-cleanup-decisions.json")

    def test_measure_root_fills_missing_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "blob.bin").write_bytes(b"x" * 10000)
            spec = copy.deepcopy(EXAMPLE)
            spec["cards"][1]["paths"] = ["*.bin"]
            data = bdp.prepare(spec, Path(tmp))
        self.assertGreater(data["cards"][1]["size"], 0)
        self.assertNotEqual(data["cards"][1]["size_label"], "")

    def test_render_embeds_data_and_cannot_close_the_script_tag(self) -> None:
        spec = copy.deepcopy(EXAMPLE)
        spec["cards"][0]["what"] = "tricky </script><b>text"
        html = bdp.render(bdp.prepare(spec))
        self.assertNotIn(bdp.DATA_PLACEHOLDER, html)
        self.assertNotIn("tricky </script>", html)
        self.assertIn("<title>Example cleanup decisions</title>", html)

    def test_main_writes_page_and_rejects_bad_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "page.html"
            self.assertEqual(bdp.main([str(TOOL_DIR / "example_spec.json"), "-o", str(out)]), 0)
            self.assertIn("Example cleanup decisions", out.read_text())
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps({"title": "x", "sections": [], "cards": []}))
            self.assertEqual(bdp.main([str(bad), "-o", str(Path(tmp) / "bad.html")]), 2)


if __name__ == "__main__":
    unittest.main()
