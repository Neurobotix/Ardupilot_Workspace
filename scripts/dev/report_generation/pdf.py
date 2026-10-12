"""
Generic AI Report PDF Generator

Usage:
    python pdf.py path/to/feature_report.md
    python pdf.py path/to/feature_report.md -o path/to/output.pdf
    python pdf.py path/to/feature_report.md --theme path/to/theme.md

This renderer reads:
    - a report markdown file containing front matter and sectioned content
    - a theme markdown file containing a JSON design spec inside a fenced block

The rendering logic is intentionally separate from the content contract so
feature reports stay generic and reusable. Beyond plain markdown, the renderer
understands a small set of authoring conventions for professional reports:

    - `# PART n: Title`  ->  full-page section divider (H1 after the cover)
    - `> [!key] Title`   ->  callout box (key / warning / verdict / definition)
    - `> [!cards]`       ->  metric / status card row (Label: Value lines)
    - markdown tables    ->  styled tables
    - `![Figure N - cap](path)` -> large captioned figure

See `theme.md` -> "Authoring Directives" for the full list.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_THEME_PATH = BASE_DIR / "theme.md"

CALLOUT_TYPES = {
    "key": ("KEY IDEA", "key_bg", "key_border", "key_text"),
    "warning": ("WARNING", "warn_bg", "warn_border", "warn_text"),
    "verdict": ("VERDICT", "verdict_bg", "verdict_border", "verdict_text"),
    "definition": ("DEFINITION", "def_bg", "def_border", "def_text"),
}


@dataclass
class Block:
    kind: str
    text: str = ""
    level: int = 0
    path: str = ""
    alt: str = ""
    # callout / table / cards payloads
    variant: str = ""
    title: str = ""
    lines: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


def hex_color(value: str):
    return HexColor(value)


def first_fenced_json_block(text: str) -> dict[str, Any]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S | re.I)
    if not match:
        raise ValueError("Theme markdown must contain one fenced JSON block.")
    return json.loads(match.group(1))


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() == "null":
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    raw = text[4:end]
    body = text[end + 5:]

    meta: dict[str, Any] = {}
    current_key: str | None = None

    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        if line.startswith("  - "):
            if current_key is None:
                continue
            meta.setdefault(current_key, [])
            if not isinstance(meta[current_key], list):
                meta[current_key] = [meta[current_key]]
            meta[current_key].append(parse_scalar(line[4:]))
            continue

        if ": " in line:
            key, value = line.split(": ", 1)
            current_key = key.strip()
            if value.strip() == "":
                meta[current_key] = []
            else:
                meta[current_key] = parse_scalar(value)
            continue

        if line.endswith(":"):
            current_key = line[:-1].strip()
            meta[current_key] = []
            continue

        if current_key and isinstance(meta.get(current_key), list):
            meta[current_key].append(parse_scalar(line.strip()))

    return meta, body.lstrip("\n")


def clean_inline_markdown(text: str) -> str:
    code_spans: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_spans.append(match.group(1))
        return f"\u0000CODE{len(code_spans) - 1}\u0000"

    text = re.sub(r"`([^`]*)`", stash_code, text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"(?<![A-Za-z0-9_])__(.*?)__(?![A-Za-z0-9_])", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<![A-Za-z0-9_])_([^_\n]+)_(?![A-Za-z0-9_])", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    for index, value in enumerate(code_spans):
        text = text.replace(f"\u0000CODE{index}\u0000", value)
    return text.strip()


def _split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [clean_inline_markdown(cell.strip()) for cell in line.split("|")]


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped or "-" not in stripped:
        return False
    body = stripped.strip("|")
    return bool(body) and all(set(cell.strip()) <= set(":- ") and cell.strip()
                              for cell in body.split("|"))


def parse_markdown_blocks(body: str) -> list[Block]:
    blocks: list[Block] = []
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    lines_iter = body.splitlines()
    i = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        text = " ".join(line.strip() for line in paragraph_lines if line.strip())
        if text:
            blocks.append(Block(kind="paragraph", text=clean_inline_markdown(text)))
        paragraph_lines = []

    def flush_code() -> None:
        nonlocal code_lines
        text = "\n".join(code_lines).rstrip()
        if text:
            blocks.append(Block(kind="code", text=text))
        code_lines = []

    while i < len(lines_iter):
        raw_line = lines_iter[i]
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(raw_line)
            i += 1
            continue

        stripped = line.strip()

        # --- Callout / cards blocks: a run of "> ..." lines ---
        callout_match = re.match(r"^>\s*\[!(\w+)\]\s*(.*)$", stripped)
        if callout_match:
            flush_paragraph()
            variant = callout_match.group(1).lower()
            title = clean_inline_markdown(callout_match.group(2))
            collected: list[str] = []
            i += 1
            while i < len(lines_iter):
                nxt = lines_iter[i].rstrip()
                if nxt.strip().startswith(">"):
                    content = nxt.strip()[1:].lstrip()
                    collected.append(content)
                    i += 1
                else:
                    break
            if variant == "cards":
                blocks.append(Block(kind="cards", lines=collected))
            elif variant in CALLOUT_TYPES:
                blocks.append(Block(
                    kind="callout", variant=variant, title=title,
                    lines=[clean_inline_markdown(c) for c in collected if c.strip()],
                ))
            else:
                # unknown directive -> render as quote text
                blocks.append(Block(kind="quote", text=clean_inline_markdown(
                    " ".join([title] + collected))))
            continue

        # --- Tables ---
        if stripped.startswith("|") and i + 1 < len(lines_iter) and \
                _is_table_separator(lines_iter[i + 1]):
            flush_paragraph()
            header = _split_table_row(stripped)
            rows: list[list[str]] = []
            i += 2  # skip header + separator
            while i < len(lines_iter) and lines_iter[i].strip().startswith("|"):
                rows.append(_split_table_row(lines_iter[i]))
                i += 1
            blocks.append(Block(kind="table", rows=[header] + rows))
            continue

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            blocks.append(
                Block(kind="heading", level=level,
                      text=clean_inline_markdown(heading.group(2)))
            )
            i += 1
            continue

        image = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", stripped)
        if image:
            flush_paragraph()
            alt, path = image.groups()
            blocks.append(Block(kind="image", alt=alt.strip(), path=path.strip()))
            i += 1
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            flush_paragraph()
            blocks.append(Block(kind="bullet", text=clean_inline_markdown(stripped[2:])))
            i += 1
            continue

        ordered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ordered:
            flush_paragraph()
            blocks.append(Block(kind="bullet", text=clean_inline_markdown(ordered.group(1))))
            i += 1
            continue

        if stripped.startswith("> "):
            flush_paragraph()
            blocks.append(Block(kind="quote", text=clean_inline_markdown(stripped[2:])))
            i += 1
            continue

        paragraph_lines.append(stripped)
        i += 1

    flush_paragraph()
    if in_code:
        flush_code()

    return blocks


def wrap_text(text: str, font_name: str, font_size: float, width: float,
              c: canvas.Canvas) -> list[str]:
    words = clean_inline_markdown(text).split()
    if not words:
        return [""]

    lines: list[str] = []
    line = words[0]
    for word in words[1:]:
        candidate = f"{line} {word}"
        if c.stringWidth(candidate, font_name, font_size) <= width:
            line = candidate
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def image_size(path: Path, max_w: float, max_h: float) -> tuple[float, float]:
    reader = ImageReader(str(path))
    width, height = reader.getSize()
    if width <= 0 or height <= 0:
        return max_w, max_h
    scale = min(max_w / width, max_h / height)
    return width * scale, height * scale


def default_theme() -> dict[str, Any]:
    raw = (BASE_DIR / "theme.md")
    if raw.exists():
        try:
            return first_fenced_json_block(raw.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Minimal safe fallback if the theme file is unreadable.
    return {
        "palette": {
            "ink": "#15212e", "ink_soft": "#22303f", "steel": "#2f5d7c",
            "rule": "#c2cdd6", "rule_soft": "#dde4ea", "text_dark": "#1d2a36",
            "text_mid": "#3f4d59", "text_light": "#7b8893", "paper": "#ffffff",
            "panel": "#f3f6f8", "tag_bg": "#e3eaf0",
            "cover_bg": "#15212e", "cover_panel": "#1d2c3b",
            "cover_accent": "#5b94bb", "cover_text": "#e8eef3",
            "cover_text_soft": "#9fb2c1",
            "key_bg": "#eaf1f6", "key_border": "#2f5d7c", "key_text": "#1d3a4f",
            "warn_bg": "#fbf3e6", "warn_border": "#b9842f", "warn_text": "#6e4d15",
            "verdict_bg": "#e9f1ec", "verdict_border": "#3f7a5b",
            "verdict_text": "#234435", "def_bg": "#eef0f4",
            "def_border": "#5a6b86", "def_text": "#2e3a4f",
            "card_value": "#2f5d7c", "card_label": "#7b8893",
            "table_head_bg": "#22303f", "table_head_text": "#ffffff",
            "table_row_alt": "#f3f6f8", "table_border": "#c2cdd6",
            "divider_bg": "#1a2836", "divider_panel": "#24384a",
            "divider_accent": "#5b94bb", "divider_text": "#eef3f7",
            "divider_text_soft": "#9fb2c1", "placeholder_bg": "#f3f6f8",
            "border": "#c2cdd6", "section_bg": "#f3f6f8",
        },
        "fonts": {
            "cover_kicker": {"name": "Helvetica-Bold", "size": 11},
            "cover_title": {"name": "Helvetica-Bold", "size": 31},
            "cover_subtitle": {"name": "Helvetica", "size": 13},
            "cover_meta_label": {"name": "Helvetica-Bold", "size": 8},
            "cover_meta": {"name": "Helvetica", "size": 10},
            "divider_index": {"name": "Helvetica-Bold", "size": 13},
            "divider_title": {"name": "Helvetica-Bold", "size": 26},
            "divider_sub": {"name": "Helvetica", "size": 12},
            "header_kicker": {"name": "Helvetica-Bold", "size": 7.5},
            "page_title": {"name": "Helvetica-Bold", "size": 16},
            "section_label": {"name": "Helvetica-Bold", "size": 9},
            "subheading": {"name": "Helvetica-Bold", "size": 11.5},
            "body": {"name": "Helvetica", "size": 10},
            "bullet": {"name": "Helvetica", "size": 9.8},
            "quote": {"name": "Helvetica-Oblique", "size": 9.8},
            "code": {"name": "Courier", "size": 8.5},
            "caption": {"name": "Helvetica-Oblique", "size": 8.5},
            "caption_label": {"name": "Helvetica-Bold", "size": 8.5},
            "callout_label": {"name": "Helvetica-Bold", "size": 8.5},
            "callout_body": {"name": "Helvetica", "size": 9.6},
            "card_value": {"name": "Helvetica-Bold", "size": 17},
            "card_label": {"name": "Helvetica", "size": 7.5},
            "table": {"name": "Helvetica", "size": 8.8},
            "table_head": {"name": "Helvetica-Bold", "size": 8.8},
            "small": {"name": "Helvetica", "size": 8},
        },
        "layout": {
            "page_size": "A4",
            "margins": {"left": 46, "right": 46, "top": 30, "bottom": 40},
            "header_height": 22,
            "running_title": "Technical Reference",
            "running_kicker": "TECHNICAL REFERENCE",
        },
    }


def load_theme(theme_path: Path) -> dict[str, Any]:
    if not theme_path.exists():
        return default_theme()
    raw = theme_path.read_text(encoding="utf-8")
    try:
        return first_fenced_json_block(raw)
    except Exception:
        return default_theme()


def theme_value(theme: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = theme
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def pal(theme: dict[str, Any], key: str, default: str = "#000000"):
    return hex_color(theme_value(theme, "palette", key, default=default))


def font(theme: dict[str, Any], key: str) -> tuple[str, float]:
    spec = theme_value(theme, "fonts", key, default={"name": "Helvetica", "size": 10})
    return spec["name"], spec["size"]


def report_title(meta: dict[str, Any], blocks: list[Block]) -> str:
    title = str(meta.get("title") or "").strip()
    if title:
        return title
    for block in blocks:
        if block.kind == "heading" and block.level == 1:
            return block.text.strip()
    return "Feature Report"


# --------------------------------------------------------------------------- #
# Cover
# --------------------------------------------------------------------------- #
def render_cover(c: canvas.Canvas, theme: dict[str, Any], meta: dict[str, Any],
                 title: str, page_w: float, page_h: float) -> None:
    bg = pal(theme, "cover_bg")
    panel = pal(theme, "cover_panel")
    accent = pal(theme, "cover_accent")
    text_c = pal(theme, "cover_text")
    soft = pal(theme, "cover_text_soft")

    c.setFillColor(bg)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # quiet structural panel on the right edge
    c.setFillColor(panel)
    c.rect(page_w - 150, 0, 150, page_h, fill=1, stroke=0)

    margin = 52
    # top kicker rule
    c.setStrokeColor(accent)
    c.setLineWidth(2)
    c.line(margin, page_h - 70, margin + 54, page_h - 70)
    kf, ks = font(theme, "cover_kicker")
    c.setFillColor(accent)
    c.setFont(kf, ks)
    kicker = str(meta.get("feature_type") or "Technical Reference").upper()
    c.drawString(margin + 64, page_h - 74, kicker)

    # title
    title_y = page_h * 0.60
    tf, ts = font(theme, "cover_title")
    c.setFillColor(text_c)
    c.setFont(tf, ts)
    cursor_y = title_y
    for line in wrap_text(title, tf, ts, page_w - margin - 170, c):
        c.drawString(margin, cursor_y, line)
        cursor_y -= ts + 6

    # accent rule under title
    cursor_y -= 6
    c.setStrokeColor(accent)
    c.setLineWidth(3)
    c.line(margin, cursor_y, margin + 90, cursor_y)
    cursor_y -= 22

    subtitle = str(meta.get("subtitle") or meta.get("summary") or "").strip()
    if subtitle:
        sf, ss = font(theme, "cover_subtitle")
        c.setFont(sf, ss)
        c.setFillColor(soft)
        for line in wrap_text(subtitle, sf, ss, page_w - margin - 180, c):
            c.drawString(margin, cursor_y, line)
            cursor_y -= ss + 5

    # metadata grid near the bottom
    meta_y = 150
    lf, ls = font(theme, "cover_meta_label")
    mf, ms = font(theme, "cover_meta")

    def meta_pair(x: float, y: float, label: str, value: str) -> None:
        c.setFont(lf, ls)
        c.setFillColor(accent)
        c.drawString(x, y, label.upper())
        c.setFont(mf, ms)
        c.setFillColor(text_c)
        for vi, vline in enumerate(wrap_text(value, mf, ms, 200, c)[:2]):
            c.drawString(x, y - 14 - vi * 12, vline)

    col1 = margin
    col2 = margin + 250
    meta_pair(col1, meta_y + 44, "Author", str(meta.get("author", "AI agent")))
    meta_pair(col2, meta_y + 44, "Date", str(meta.get("date", "auto")))
    meta_pair(col1, meta_y, "Project",
              str(meta.get("project", "Generated from supplied artifacts")))

    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tags_text = "   /   ".join(str(t).strip() for t in tags if str(t).strip())
    if tags_text:
        meta_pair(col2, meta_y, "Tags", tags_text)

    # thin rule above footer
    c.setStrokeColor(pal(theme, "cover_panel"))
    c.setLineWidth(0.8)
    c.line(margin, 70, page_w - 60, 70)
    sf, sfs = font(theme, "small")
    c.setFont(sf, sfs)
    c.setFillColor(soft)
    c.drawString(margin, 52, "Rendered from a markdown source and theme spec.")

    c.showPage()


# --------------------------------------------------------------------------- #
# Section divider page
# --------------------------------------------------------------------------- #
def render_divider(c: canvas.Canvas, theme: dict[str, Any], title: str,
                   subtitle: str, index_label: str,
                   page_w: float, page_h: float) -> None:
    bg = pal(theme, "divider_bg")
    panel = pal(theme, "divider_panel")
    accent = pal(theme, "divider_accent")
    text_c = pal(theme, "divider_text")
    soft = pal(theme, "divider_text_soft")

    c.setFillColor(bg)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # left structural stripe
    c.setFillColor(panel)
    c.rect(0, 0, 10, page_h, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(0, page_h * 0.5 - 60, 10, 120, fill=1, stroke=0)

    margin = 64
    mid = page_h * 0.56

    if index_label:
        idf, ids = font(theme, "divider_index")
        c.setFont(idf, ids)
        c.setFillColor(accent)
        c.drawString(margin, mid + 46, index_label.upper())

    c.setStrokeColor(accent)
    c.setLineWidth(2)
    c.line(margin, mid + 34, margin + 60, mid + 34)

    tf, ts = font(theme, "divider_title")
    c.setFont(tf, ts)
    c.setFillColor(text_c)
    cursor_y = mid
    for line in wrap_text(title, tf, ts, page_w - margin * 2, c):
        c.drawString(margin, cursor_y, line)
        cursor_y -= ts + 4

    if subtitle:
        cursor_y -= 12
        sf, ss = font(theme, "divider_sub")
        c.setFont(sf, ss)
        c.setFillColor(soft)
        for line in wrap_text(subtitle, sf, ss, page_w - margin * 2 - 40, c):
            c.drawString(margin, cursor_y, line)
            cursor_y -= ss + 5

    c.showPage()


# --------------------------------------------------------------------------- #
# Running header
# --------------------------------------------------------------------------- #
def draw_page_header(c: canvas.Canvas, theme: dict[str, Any], page_num: int,
                     page_w: float, page_h: float) -> None:
    soft = pal(theme, "text_light")
    accent = pal(theme, "steel")
    kf, ks = font(theme, "header_kicker")
    kicker = theme_value(theme, "layout", "running_kicker", default="TECHNICAL REFERENCE")
    running = theme_value(theme, "layout", "running_title", default="")

    top = page_h - 30
    c.setFillColor(accent)
    c.setFont(kf, ks)
    c.drawString(46, top, kicker)
    if running:
        c.setFillColor(soft)
        c.setFont("Helvetica", 7.5)
        c.drawRightString(page_w - 46, top, running)

    c.setStrokeColor(pal(theme, "rule_soft"))
    c.setLineWidth(0.6)
    c.line(46, top - 6, page_w - 46, top - 6)


def draw_page_footer(c: canvas.Canvas, theme: dict[str, Any], page_num: int,
                     page_w: float, page_h: float) -> None:
    soft = pal(theme, "text_light")
    c.setStrokeColor(pal(theme, "rule_soft"))
    c.setLineWidth(0.6)
    c.line(46, 30, page_w - 46, 30)
    c.setFillColor(soft)
    c.setFont("Helvetica", 7.5)
    c.drawRightString(page_w - 46, 18, str(page_num))
    c.setFont("Helvetica", 7.5)
    running = theme_value(theme, "layout", "running_title", default="")
    if running:
        c.drawString(46, 18, running)


# --------------------------------------------------------------------------- #
# Content drawers
# --------------------------------------------------------------------------- #
def draw_section_label(c: canvas.Canvas, theme: dict[str, Any], label: str,
                       x: float, y: float, width: float) -> float:
    accent = pal(theme, "steel")
    f, s = font(theme, "section_label")
    c.setFillColor(accent)
    c.setFont(f, s)
    c.drawString(x, y, label.upper())
    text_w = c.stringWidth(label.upper(), f, s)
    c.setStrokeColor(pal(theme, "rule_soft"))
    c.setLineWidth(0.8)
    c.line(x + text_w + 10, y + 2, x + width, y + 2)
    return y - 18


def draw_subheading(c: canvas.Canvas, theme: dict[str, Any], text: str,
                    x: float, y: float) -> float:
    f, s = font(theme, "subheading")
    c.setFillColor(pal(theme, "text_dark"))
    c.setFont(f, s)
    c.drawString(x, y, text)
    return y - 16


def draw_body_paragraph(c: canvas.Canvas, theme: dict[str, Any], text: str,
                        x: float, y: float, width: float) -> float:
    f, s = font(theme, "body")
    line_gap = 14
    lines = wrap_text(text, f, s, width, c)
    c.setFillColor(pal(theme, "text_mid"))
    c.setFont(f, s)
    cur = y
    for line in lines:
        c.drawString(x, cur, line)
        cur -= line_gap
    return cur


def draw_bullet(c: canvas.Canvas, theme: dict[str, Any], text: str,
                x: float, y: float, width: float) -> float:
    f, s = font(theme, "bullet")
    line_gap = 12.5
    indent = x + 14
    lines = wrap_text(text, f, s, width - 14, c)
    c.setFillColor(pal(theme, "steel"))
    c.setFont("Helvetica-Bold", s)
    c.drawString(x + 2, y, "—")  # em dash marker
    c.setFillColor(pal(theme, "text_mid"))
    c.setFont(f, s)
    cur = y
    for line in lines:
        c.drawString(indent, cur, line)
        cur -= line_gap
    return cur


def draw_quote(c: canvas.Canvas, theme: dict[str, Any], text: str,
               x: float, y: float, width: float) -> float:
    f, s = font(theme, "quote")
    lines = wrap_text(text, f, s, width - 14, c)
    cur = y
    c.setStrokeColor(pal(theme, "steel_soft"))
    c.setLineWidth(2)
    c.line(x, cur + 4, x, cur - len(lines) * 12.5 + 6)
    c.setFillColor(pal(theme, "text_light"))
    c.setFont(f, s)
    for line in lines:
        c.drawString(x + 12, cur, line)
        cur -= 12.5
    return cur


def draw_code_block(c: canvas.Canvas, theme: dict[str, Any], text: str,
                    x: float, y: float, width: float) -> float:
    f, s = font(theme, "code")
    line_gap = 11
    lines = text.splitlines() or [""]
    height = len(lines) * line_gap + 16
    c.setFillColor(pal(theme, "panel"))
    c.setStrokeColor(pal(theme, "rule"))
    c.setLineWidth(0.6)
    c.rect(x, y - height + 8, width, height, fill=1, stroke=1)
    # accent edge
    c.setFillColor(pal(theme, "steel"))
    c.rect(x, y - height + 8, 3, height, fill=1, stroke=0)
    c.setFillColor(pal(theme, "text_dark"))
    c.setFont(f, s)
    cur = y - 4
    for line in lines:
        c.drawString(x + 12, cur, line.rstrip()[:130])
        cur -= line_gap
    return y - height - 4


def callout_height(c: canvas.Canvas, theme: dict[str, Any], block: Block,
                   width: float) -> float:
    bf, bs = font(theme, "callout_body")
    inner_w = width - 36
    n = 0
    for line in block.lines:
        n += len(wrap_text(line, bf, bs, inner_w, c))
    title_h = 16 if block.title else 6
    return title_h + n * 12.6 + 18


def draw_callout(c: canvas.Canvas, theme: dict[str, Any], block: Block,
                 x: float, y: float, width: float) -> float:
    label, bg_key, border_key, text_key = CALLOUT_TYPES[block.variant]
    bg = pal(theme, bg_key)
    border = pal(theme, border_key)
    text_c = pal(theme, text_key)

    h = callout_height(c, theme, block, width)
    top = y
    bottom = y - h

    c.setFillColor(bg)
    c.rect(x, bottom, width, h, fill=1, stroke=0)
    c.setFillColor(border)
    c.rect(x, bottom, 4, h, fill=1, stroke=0)

    inner_x = x + 16
    inner_w = width - 36
    cur = top - 16

    lf, ls = font(theme, "callout_label")
    c.setFillColor(border)
    c.setFont(lf, ls)
    head = label if not block.title else f"{label}  ·  {block.title}"
    c.drawString(inner_x, cur, head)
    cur -= 16 if block.title or True else 0
    cur -= 2

    bf, bs = font(theme, "callout_body")
    c.setFillColor(text_c)
    c.setFont(bf, bs)
    for line in block.lines:
        for wl in wrap_text(line, bf, bs, inner_w, c):
            c.drawString(inner_x, cur, wl)
            cur -= 12.6
    return bottom - 8


def parse_cards(lines: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in lines:
        item = item.strip().lstrip("-* ").strip()
        if not item:
            continue
        if ":" in item:
            label, value = item.split(":", 1)
            pairs.append((label.strip(), value.strip()))
        else:
            pairs.append((item, ""))
    return pairs


def draw_card_row(c: canvas.Canvas, theme: dict[str, Any],
                  pairs: list[tuple[str, str]], x: float, y: float,
                  width: float) -> float:
    if not pairs:
        return y
    per_row = 4 if len(pairs) >= 4 else len(pairs)
    per_row = max(1, per_row)
    gap = 12
    card_h = 54
    vf, vs = font(theme, "card_value")
    lf, ls = font(theme, "card_label")
    cur_y = y
    for start in range(0, len(pairs), per_row):
        chunk = pairs[start:start + per_row]
        n = len(chunk)
        card_w = (width - gap * (per_row - 1)) / per_row
        box_y = cur_y - card_h
        for k, (label, value) in enumerate(chunk):
            bx = x + k * (card_w + gap)
            c.setFillColor(pal(theme, "panel"))
            c.setStrokeColor(pal(theme, "rule"))
            c.setLineWidth(0.6)
            c.rect(bx, box_y, card_w, card_h, fill=1, stroke=1)
            c.setFillColor(pal(theme, "steel"))
            c.rect(bx, box_y + card_h - 3, card_w, 3, fill=1, stroke=0)
            # value
            c.setFillColor(pal(theme, "card_value"))
            c.setFont(vf, vs)
            val = value or "—"
            # shrink to fit
            fsz = vs
            while c.stringWidth(val, vf, fsz) > card_w - 14 and fsz > 9:
                fsz -= 1
            c.setFont(vf, fsz)
            c.drawCentredString(bx + card_w / 2, box_y + 28, val)
            # label
            c.setFillColor(pal(theme, "card_label"))
            c.setFont(lf, ls)
            lbl = label.upper()
            for li, ll in enumerate(wrap_text(lbl, lf, ls, card_w - 10, c)[:1]):
                c.drawCentredString(bx + card_w / 2, box_y + 11, ll)
        cur_y = box_y - 12
    return cur_y


def table_dims(c: canvas.Canvas, theme: dict[str, Any], rows: list[list[str]],
               width: float) -> tuple[list[float], list[float], float]:
    ncols = max(len(r) for r in rows)
    tf, ts = font(theme, "table")
    # weight columns by content length, clamp
    maxlens = [1.0] * ncols
    for r in rows:
        for ci in range(ncols):
            cell = r[ci] if ci < len(r) else ""
            maxlens[ci] = max(maxlens[ci], c.stringWidth(cell, tf, ts) + 14)
    total = sum(maxlens)
    col_w = [max(width * 0.10, (m / total) * width) for m in maxlens]
    # normalize to width
    scale = width / sum(col_w)
    col_w = [w * scale for w in col_w]

    row_h: list[float] = []
    pad = 5
    for ri, r in enumerate(rows):
        maxlines = 1
        for ci in range(ncols):
            cell = r[ci] if ci < len(r) else ""
            lines = wrap_text(cell, tf, ts, col_w[ci] - 10, c)
            maxlines = max(maxlines, len(lines))
        row_h.append(maxlines * (ts + 3) + pad * 2)
    return col_w, row_h, sum(row_h)


def draw_table(c: canvas.Canvas, theme: dict[str, Any], rows: list[list[str]],
               x: float, y: float, width: float,
               col_w: list[float], row_h: list[float]) -> float:
    tf, ts = font(theme, "table")
    hf, hs = font(theme, "table_head")
    ncols = len(col_w)
    cur_y = y
    for ri, r in enumerate(rows):
        h = row_h[ri]
        row_top = cur_y
        row_bot = cur_y - h
        if ri == 0:
            c.setFillColor(pal(theme, "table_head_bg"))
            c.rect(x, row_bot, width, h, fill=1, stroke=0)
        elif ri % 2 == 0:
            c.setFillColor(pal(theme, "table_row_alt"))
            c.rect(x, row_bot, width, h, fill=1, stroke=0)
        # cell text
        cx = x
        for ci in range(ncols):
            cell = r[ci] if ci < len(r) else ""
            if ri == 0:
                c.setFillColor(pal(theme, "table_head_text"))
                c.setFont(hf, hs)
            else:
                c.setFillColor(pal(theme, "text_mid"))
                c.setFont(tf, ts)
            lines = wrap_text(cell, tf, ts, col_w[ci] - 10, c)
            ty = row_top - 5 - ts
            for line in lines:
                c.drawString(cx + 6, ty, line)
                ty -= ts + 3
            cx += col_w[ci]
        cur_y = row_bot
    # outer + column borders
    c.setStrokeColor(pal(theme, "table_border"))
    c.setLineWidth(0.6)
    c.rect(x, cur_y, width, y - cur_y, fill=0, stroke=1)
    cx = x
    for ci in range(ncols - 1):
        cx += col_w[ci]
        c.line(cx, cur_y, cx, y)
    # horizontal rule under header
    c.line(x, y - row_h[0], x + width, y - row_h[0])
    return cur_y - 6


def draw_placeholder_box(c: canvas.Canvas, theme: dict[str, Any], x: float,
                         y: float, w: float, h: float, label: str,
                         sublabel: str = "") -> None:
    c.setFillColor(pal(theme, "placeholder_bg"))
    c.setStrokeColor(pal(theme, "rule"))
    c.setDash(3, 3)
    c.setLineWidth(1)
    c.rect(x, y, w, h, fill=1, stroke=1)
    c.setDash()
    c.setFillColor(pal(theme, "text_light"))
    bf, bs = font(theme, "body")
    c.setFont(bf, bs)
    c.drawCentredString(x + w / 2, y + h / 2 + 8, label)
    if sublabel:
        sf, ss = font(theme, "small")
        c.setFont(sf, ss)
        c.drawCentredString(x + w / 2, y + h / 2 - 8, sublabel)


def render_image(c: canvas.Canvas, theme: dict[str, Any], path_value: str,
                 alt: str, x: float, y: float, width: float,
                 max_h: float, base_dir: Path) -> float:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()

    # caption: split "Figure N - rest"
    fig_label = ""
    caption = clean_inline_markdown(alt)
    m = re.match(r"^(Figure\s+[\w.\-]+)\s*[—\-:]\s*(.*)$", caption)
    if m:
        fig_label = m.group(1)
        caption = m.group(2)

    if not path.exists():
        draw_placeholder_box(c, theme, x, y - 120, width, 120,
                             caption or "[IMAGE NOT FOUND]", str(path_value))
        return y - 132

    img_w, img_h = image_size(path, width, max_h)
    img_x = x + (width - img_w) / 2  # center
    c.drawImage(str(path), img_x, y - img_h, width=img_w, height=img_h,
                preserveAspectRatio=True, mask="auto")
    bottom = y - img_h - 6

    # caption line
    cf, cs = font(theme, "caption")
    lf, ls = font(theme, "caption_label")
    caption_y = bottom - 4
    if fig_label:
        c.setFillColor(pal(theme, "steel"))
        c.setFont(lf, ls)
        c.drawString(x, caption_y, fig_label + ".")
        offset = c.stringWidth(fig_label + ". ", lf, ls)
    else:
        offset = 0
    if caption:
        c.setFillColor(pal(theme, "text_light"))
        c.setFont(cf, cs)
        wrapped = wrap_text(caption, cf, cs, width - offset, c)
        c.drawString(x + offset, caption_y, wrapped[0])
        caption_y -= cs + 3
        for line in wrapped[1:4]:
            c.drawString(x, caption_y, line)
            caption_y -= cs + 3
    return caption_y - 8


# --------------------------------------------------------------------------- #
# Body renderer
# --------------------------------------------------------------------------- #
def render_body(c: canvas.Canvas, theme: dict[str, Any], blocks: list[Block],
                title: str, page_w: float, page_h: float,
                meta: dict[str, Any], base_dir: Path,
                state: dict[str, int]) -> None:
    margins = theme_value(theme, "layout", "margins",
                          default={"left": 46, "right": 46, "top": 30, "bottom": 40})
    bottom_margin = margins["bottom"] + 18
    content_x = margins["left"]
    content_w = page_w - margins["left"] - margins["right"]
    top_y = page_h - 56

    y = top_y
    section_name = ""
    metrics_buffer: list[str] = []
    in_metrics_section = False

    def begin_page() -> None:
        nonlocal y
        state["page"] += 1
        draw_page_header(c, theme, state["page"], page_w, page_h)
        draw_page_footer(c, theme, state["page"], page_w, page_h)
        y = top_y

    def new_page() -> None:
        c.showPage()
        begin_page()

    def ensure(req: float) -> None:
        nonlocal y
        if y - req < bottom_margin:
            new_page()

    def flush_metrics() -> None:
        nonlocal y, metrics_buffer, in_metrics_section
        if metrics_buffer and in_metrics_section:
            pairs = parse_cards(metrics_buffer)
            rows = (len(pairs) + 3) // 4
            ensure(rows * 66 + 6)
            y = draw_card_row(c, theme, pairs, content_x, y, content_w)
        metrics_buffer = []
        in_metrics_section = False

    begin_page()

    for block in blocks:
        if block.kind == "heading":
            if block.level == 1:
                # H1 == part divider, handled by caller flow; skip here
                continue
            if block.level == 2:
                flush_metrics()
                ensure(46)
                y -= 12
                y = draw_section_label(c, theme, block.text, content_x, y, content_w)
                y -= 4
                section_name = block.text
                continue
            if block.level >= 3:
                flush_metrics()
                ensure(28)
                y -= 6
                y = draw_subheading(c, theme, block.text, content_x, y)
                continue

        if block.kind == "paragraph":
            f, s = font(theme, "body")
            needed = max(20, len(wrap_text(block.text, f, s, content_w, c)) * 14)
            ensure(needed)
            y = draw_body_paragraph(c, theme, block.text, content_x, y, content_w)
            y -= 6
            continue

        if block.kind == "bullet":
            if section_name.lower() in {"key results", "metrics", "status"}:
                in_metrics_section = True
                metrics_buffer.append(block.text)
                continue
            f, s = font(theme, "bullet")
            needed = max(15, len(wrap_text(block.text, f, s, content_w - 14, c)) * 12.5)
            ensure(needed)
            y = draw_bullet(c, theme, block.text, content_x, y, content_w)
            y -= 4
            continue

        if block.kind == "callout":
            h = callout_height(c, theme, block, content_w)
            ensure(h + 8)
            y = draw_callout(c, theme, block, content_x, y, content_w)
            y -= 6
            continue

        if block.kind == "cards":
            pairs = parse_cards(block.lines)
            rows = (len(pairs) + 3) // 4
            ensure(rows * 66 + 6)
            y = draw_card_row(c, theme, pairs, content_x, y, content_w)
            y -= 4
            continue

        if block.kind == "table":
            col_w, row_h, total = table_dims(c, theme, block.rows, content_w)
            # keep header with at least 2 rows if possible
            if total <= (top_y - bottom_margin):
                ensure(total + 8)
            else:
                ensure(row_h[0] + row_h[1] + 8 if len(row_h) > 1 else row_h[0] + 8)
            y = draw_table(c, theme, block.rows, content_x, y, content_w, col_w, row_h)
            y -= 8
            continue

        if block.kind == "quote":
            f, s = font(theme, "quote")
            needed = max(14, len(wrap_text(block.text, f, s, content_w - 14, c)) * 12.5)
            ensure(needed)
            y = draw_quote(c, theme, block.text, content_x, y, content_w)
            y -= 6
            continue

        if block.kind == "code":
            needed = len(block.text.splitlines()) * 11 + 22
            ensure(min(needed, top_y - bottom_margin))
            y = draw_code_block(c, theme, block.text, content_x, y, content_w)
            y -= 8
            continue

        if block.kind == "image":
            # Large figures: use the remaining column space, only breaking to a
            # new page when too little room is left for a readable figure.
            avail = y - bottom_margin - 50
            if avail < 200:
                new_page()
                avail = y - bottom_margin - 50
            max_h = min(avail, 540)
            y = render_image(c, theme, block.path, block.alt, content_x, y,
                             content_w, max_h, base_dir)
            y -= 14
            continue

    flush_metrics()
    c.showPage()


# --------------------------------------------------------------------------- #
# Document assembly: split body into parts on H1 dividers
# --------------------------------------------------------------------------- #
def split_into_parts(blocks: list[Block]) -> list[tuple[Block | None, str, list[Block]]]:
    """Return list of (divider_heading_block_or_None, subtitle, content_blocks)."""
    parts: list[tuple[Block | None, str, list[Block]]] = []
    current_divider: Block | None = None
    current_sub = ""
    current: list[Block] = []
    title_seen = False

    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b.kind == "heading" and b.level == 1:
            # The very first H1 is the document title (front-matter already has it).
            if not title_seen and not current and not parts:
                title_seen = True
                i += 1
                continue
            # close previous part
            parts.append((current_divider, current_sub, current))
            current = []
            current_divider = b
            current_sub = ""
            # optional italic subtitle = next quote/paragraph that is short
            if i + 1 < len(blocks) and blocks[i + 1].kind in {"quote", "paragraph"}:
                nxt = blocks[i + 1]
                if len(nxt.text) < 160:
                    current_sub = nxt.text
                    i += 2
                    continue
            i += 1
            continue
        current.append(b)
        i += 1

    parts.append((current_divider, current_sub, current))
    # drop empty leading part with no content and no divider
    return [p for p in parts if p[0] is not None or p[2]]


def build_pdf(input_md: Path, output_pdf: Path, theme_path: Path) -> None:
    theme = load_theme(theme_path)
    raw = input_md.read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)
    layout = theme.setdefault("layout", {})
    if meta.get("running_title"):
        layout["running_title"] = str(meta["running_title"])
    if meta.get("running_kicker"):
        layout["running_kicker"] = str(meta["running_kicker"])
    blocks = parse_markdown_blocks(body)
    title = report_title(meta, blocks)
    page_w, page_h = A4

    c = canvas.Canvas(str(output_pdf), pagesize=A4)
    render_cover(c, theme, meta, title, page_w, page_h)

    parts = split_into_parts(blocks)
    state = {"page": 1}  # cover is page 1
    part_index = 0
    for divider, subtitle, content in parts:
        if divider is not None:
            part_index += 1
            # allow explicit "PART n:" already in title; else add index
            dtitle = divider.text
            index_label = ""
            m = re.match(r"^(PART\s+[\w.]+)\s*[:\-—]\s*(.*)$", dtitle, re.I)
            if m:
                index_label = m.group(1)
                dtitle = m.group(2)
            else:
                index_label = f"PART {part_index}"
            state["page"] += 1
            render_divider(c, theme, dtitle, subtitle, index_label, page_w, page_h)
        if content:
            render_body(c, theme, content, title, page_w, page_h, meta,
                        input_md.parent, state)

    c.save()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a PDF report from markdown.")
    parser.add_argument("input", type=Path, help="Path to the feature report markdown file.")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Output PDF path. Defaults to the input name with .pdf.")
    parser.add_argument("--theme", type=Path, default=DEFAULT_THEME_PATH,
                        help="Path to the theme markdown file with the JSON style spec.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_md: Path = args.input
    output_pdf: Path = args.output or input_md.with_suffix(".pdf")
    build_pdf(input_md, output_pdf, args.theme)
    print(f"Report PDF created: {output_pdf}")


if __name__ == "__main__":
    main()
