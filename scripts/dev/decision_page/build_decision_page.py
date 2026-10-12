#!/usr/bin/env python3
"""Build a self-contained HTML decision page from a JSON spec.

Each card in the spec is one decision with a recommended option. The page lets
the reader pick an option per card (or accept every recommendation), keeps the
choices in browser storage, and exports them as a JSON download plus a short
text block copied to the clipboard ("<ID> <choice> — <note>" per line).

Usage:
    python3 scripts/dev/decision_page/build_decision_page.py spec.json -o page.html
    python3 scripts/dev/decision_page/build_decision_page.py spec.json -o page.html \
        --measure-root /path/to/workspace

See README.md in this folder for the spec format.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).resolve().parent / "template.html"
DATA_PLACEHOLDER = "/*DATA*/null"
CHIP_TONES = {"ok", "warn", "neutral"}
DEFAULT_INTRO = [
    "Every card is <b>one decision</b>. Pick an option. The <b>recommended</b> tag shows the suggestion.",
    "Anything not on a card stays as it is.",
    "When done, press <b>Save decisions</b>. It downloads a small file and copies the answers to the clipboard.",
]


class SpecError(ValueError):
    """Raised when a decision spec is malformed."""


def human_size(n: int) -> str:
    """Format a byte count with binary units, switching to G at 1000 M."""
    value = float(n)
    for unit in ("B", "K", "M", "G"):
        limit = 1000 if unit == "M" else 1024
        if value < limit:
            return f"{value:.0f}{unit}" if unit in ("B", "K") else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}T"


def measure(paths: list[str], root: Path) -> int | None:
    """Return disk usage in bytes of the existing paths/globs under root."""
    found: list[str] = []
    for pattern in paths:
        found += glob.glob(str(root / pattern))
    if not found:
        return None
    out = subprocess.run(["du", "-sc", "-B1", *found], capture_output=True, text=True, check=True).stdout
    return int(out.strip().splitlines()[-1].split()[0])


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "decisions"


def validate(spec: dict[str, Any]) -> None:
    """Check the spec shape; raise SpecError with every problem found."""
    problems: list[str] = []
    if not isinstance(spec.get("title"), str) or not spec["title"].strip():
        problems.append("title: required non-empty string")
    sections = spec.get("sections") or []
    section_ids = [s.get("id") for s in sections if isinstance(s, dict)]
    if not sections:
        problems.append("sections: at least one section is required")
    if len(section_ids) != len(set(section_ids)):
        problems.append("sections: ids must be unique")
    cards = spec.get("cards") or []
    if not cards:
        problems.append("cards: at least one card is required")
    seen: set[str] = set()
    for i, card in enumerate(cards):
        where = f"cards[{i}]"
        if not isinstance(card, dict):
            problems.append(f"{where}: must be an object")
            continue
        cid = card.get("id")
        where = f"card {cid!r}" if cid else where
        if not isinstance(cid, str) or not cid:
            problems.append(f"{where}: id is required")
        elif cid in seen:
            problems.append(f"{where}: duplicate id")
        else:
            seen.add(cid)
        for key in ("title", "what"):
            if not isinstance(card.get(key), str) or not card[key].strip():
                problems.append(f"{where}: {key} is required")
        if card.get("section") not in section_ids:
            problems.append(f"{where}: section {card.get('section')!r} is not defined")
        options = card.get("options")
        if not isinstance(options, list) or len(options) < 2:
            problems.append(f"{where}: options needs at least two [key, label] pairs")
            continue
        keys = [o[0] for o in options if isinstance(o, list) and len(o) >= 2]
        if len(keys) != len(options):
            problems.append(f"{where}: each option must be [key, label] or [key, label, tone]")
        if len(keys) != len(set(keys)):
            problems.append(f"{where}: option keys must be unique")
        if card.get("rec") not in keys:
            problems.append(f"{where}: rec {card.get('rec')!r} is not one of {keys}")
        for chip in card.get("chips") or []:
            if not (isinstance(chip, list) and len(chip) == 2 and chip[1] in CHIP_TONES):
                problems.append(f"{where}: chips must be [label, tone] with tone in {sorted(CHIP_TONES)}")
        for pair in card.get("mapping") or []:
            if not (isinstance(pair, list) and len(pair) == 2):
                problems.append(f"{where}: mapping entries must be [old, new]")
    table = spec.get("table")
    if table is not None:
        if not isinstance(table.get("columns"), list) or not table["columns"]:
            problems.append("table: columns must be a non-empty list")
        if not isinstance(table.get("rows"), list):
            problems.append("table: rows must be a list")
    if problems:
        raise SpecError("invalid decision spec:\n  - " + "\n  - ".join(problems))


def prepare(spec: dict[str, Any], measure_root: Path | None = None) -> dict[str, Any]:
    """Validate, fill derived fields, and return the data embedded in the page."""
    validate(spec)
    data = json.loads(json.dumps(spec))
    for card in data["cards"]:
        if card.get("size") is None and measure_root is not None and card.get("paths"):
            card["size"] = measure(card["paths"], measure_root)
        if not card.get("size_label"):
            card["size_label"] = human_size(card["size"]) if card.get("size") else ""
        if card.get("size") is None:
            card["size"] = 0
        card.setdefault("paths", [])
        card.setdefault("chips", [])
        if card.get("if_yes"):
            card["if_yes"] = card["if_yes"].replace("{size}", card["size_label"] or "space")
    data.setdefault("intro", DEFAULT_INTRO)
    data.setdefault("storage_key", "decision-page-" + slug(data["title"]))
    data.setdefault("export_name", slug(data["title"]) + ".json")
    return data


def render(data: dict[str, Any], template: str | None = None) -> str:
    template = template if template is not None else TEMPLATE_PATH.read_text()
    if DATA_PLACEHOLDER not in template:
        raise SpecError("template is missing the data placeholder")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = data["title"].replace("&", "&amp;").replace("<", "&lt;")
    return template.replace(DATA_PLACEHOLDER, payload).replace("<title>Decisions</title>", f"<title>{title}</title>")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path, help="JSON decision spec")
    parser.add_argument("-o", "--output", type=Path, required=True, help="HTML file to write")
    parser.add_argument("--measure-root", type=Path,
                        help="fill missing card sizes by measuring card paths (globs) under this directory")
    args = parser.parse_args(argv)
    try:
        spec = json.loads(args.spec.read_text())
        data = prepare(spec, args.measure_root)
    except (SpecError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 2
    args.output.write_text(render(data))
    print(f"wrote {args.output} ({len(data['cards'])} decisions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
