"""
Generic AI Report PDF Generator

Usage:
    python pdf.py path/to/feature_report.md
    python pdf.py path/to/feature_report.md -o path/to/output.pdf
    python pdf.py path/to/feature_report.md --theme path/to/theme.md

This renderer reads:
    - a report markdown file containing front matter and sectioned content
    - a theme markdown file containing a JSON design spec inside a fenced block

The markdown files in this folder are the source of truth for style and report
structure. The generator intentionally keeps the rendering logic separate from
the content contract so feature reports stay generic and reusable.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_THEME_PATH = BASE_DIR / "theme.md"


@dataclass
class Block:
    kind: str
    text: str = ""
    level: int = 0
    path: str = ""
    alt: str = ""


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
    body = text[end + 5 :]

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
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    return text.strip()


def parse_markdown_blocks(body: str) -> list[Block]:
    blocks: list[Block] = []
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

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

    for raw_line in body.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                in_code = True
            continue

        if in_code:
            code_lines.append(raw_line)
            continue

        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            blocks.append(
                Block(
                    kind="heading",
                    level=level,
                    text=clean_inline_markdown(heading.group(2)),
                )
            )
            continue

        image = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", stripped)
        if image:
            flush_paragraph()
            alt, path = image.groups()
            blocks.append(
                Block(
                    kind="image",
                    alt=clean_inline_markdown(alt),
                    path=path.strip(),
                )
            )
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            flush_paragraph()
            blocks.append(Block(kind="bullet", text=clean_inline_markdown(stripped[2:])))
            continue

        if stripped.startswith("> "):
            flush_paragraph()
            blocks.append(Block(kind="quote", text=clean_inline_markdown(stripped[2:])))
            continue

        paragraph_lines.append(stripped)

    flush_paragraph()
    if in_code:
        flush_code()

    return blocks


def wrap_text(text: str, font_name: str, font_size: float, width: float, c: canvas.Canvas) -> list[str]:
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


def draw_lines(
    c: canvas.Canvas,
    x: float,
    y: float,
    lines: Iterable[str],
    font_name: str,
    font_size: float,
    color: Any,
    line_gap: float,
) -> float:
    c.setFillColor(color)
    c.setFont(font_name, font_size)
    current_y = y
    for line in lines:
        c.drawString(x, current_y, line)
        current_y -= line_gap
    return current_y


def image_size(path: Path, max_w: float, max_h: float) -> tuple[float, float]:
    reader = ImageReader(str(path))
    width, height = reader.getSize()
    if width <= 0 or height <= 0:
        return max_w, max_h
    scale = min(max_w / width, max_h / height)
    return width * scale, height * scale


def default_theme() -> dict[str, Any]:
    return {
        "palette": {
            "dark_bg": "#1a1a2e",
            "accent": "#0f3460",
            "highlight": "#e94560",
            "text_dark": "#1a1a2e",
            "text_mid": "#444444",
            "text_light": "#888888",
            "section_bg": "#f0f4f8",
            "tag_bg": "#e8eef4",
            "border": "#d0d8e0",
            "paper": "#ffffff",
            "placeholder_bg": "#f8f9fa",
        },
        "fonts": {
            "cover_title": {"name": "Helvetica-Bold", "size": 34},
            "cover_subtitle": {"name": "Helvetica", "size": 16},
            "cover_tagline": {"name": "Helvetica", "size": 11},
            "cover_meta": {"name": "Helvetica", "size": 10},
            "page_title": {"name": "Helvetica-Bold", "size": 22},
            "section_label": {"name": "Helvetica-Bold", "size": 9},
            "body": {"name": "Helvetica", "size": 10},
            "bullet": {"name": "Helvetica", "size": 9.5},
            "quote": {"name": "Helvetica-Oblique", "size": 9.5},
            "code": {"name": "Courier", "size": 8.5},
            "small": {"name": "Helvetica", "size": 8},
        },
        "layout": {
            "page_size": "A4",
            "margins": {"left": 30, "right": 30, "top": 30, "bottom": 34},
            "header_height": 28,
            "cover_title_y_ratio": 0.72,
            "cover_contact_y_ratio": 0.28,
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


def report_title(meta: dict[str, Any], blocks: list[Block]) -> str:
    title = str(meta.get("title") or "").strip()
    if title:
        return title
    for block in blocks:
        if block.kind == "heading" and block.level == 1:
            return block.text.strip()
    return "Feature Report"


def section_title_text(block: Block) -> str:
    return block.text.strip()


def render_cover(c: canvas.Canvas, theme: dict[str, Any], meta: dict[str, Any], title: str, page_w: float, page_h: float) -> None:
    palette = theme["palette"]
    fonts = theme["fonts"]
    layout = theme["layout"]

    dark_bg = hex_color(palette["dark_bg"])
    accent = hex_color(palette["accent"])
    highlight = hex_color(palette["highlight"])
    white_bg = white

    c.setFillColor(dark_bg)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    c.setFillColor(highlight)
    c.rect(0, page_h * 0.55, page_w, 4, fill=1, stroke=0)

    c.saveState()
    c.setFillColor(accent)
    c.setFillAlpha(0.28)
    c.rect(0, page_h * 0.35, page_w * 0.4, page_h * 0.2, fill=1, stroke=0)
    c.restoreState()

    c.setFillColor(white_bg)
    c.setFont(fonts["cover_title"]["name"], fonts["cover_title"]["size"])
    c.drawString(40, page_h * layout["cover_title_y_ratio"], title)

    subtitle = str(meta.get("subtitle") or meta.get("summary") or "").strip()
    if subtitle:
        c.setFont(fonts["cover_subtitle"]["name"], fonts["cover_subtitle"]["size"])
        c.setFillColor(hex_color("#aabbcc"))
        c.drawString(40, page_h * layout["cover_title_y_ratio"] - 35, subtitle)

    feature_type = str(meta.get("feature_type") or "AI-generated feature report").strip()
    c.setFont(fonts["cover_tagline"]["name"], fonts["cover_tagline"]["size"])
    c.setFillColor(hex_color("#8899aa"))
    c.drawString(40, page_h * layout["cover_title_y_ratio"] - 60, feature_type)

    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tags_text = "  |  ".join(str(tag).strip() for tag in tags if str(tag).strip())
    if tags_text:
        c.setStrokeColor(highlight)
        c.setLineWidth(2)
        c.line(40, page_h * layout["cover_title_y_ratio"] - 75, min(40 + max(260, len(tags_text) * 6), page_w - 40), page_h * layout["cover_title_y_ratio"] - 75)

    contact_y = page_h * layout["cover_contact_y_ratio"]
    c.setFont(fonts["cover_meta"]["name"], 13)
    c.setFillColor(highlight)
    c.drawString(40, contact_y + 30, "FEATURE REPORT")

    c.setFont(fonts["cover_meta"]["name"], fonts["cover_meta"]["size"])
    c.setFillColor(hex_color("#8899aa"))
    c.drawString(40, contact_y, f"Author: {meta.get('author', 'AI agent')}")
    c.drawString(40, contact_y - 18, f"Date: {meta.get('date', 'auto')}")
    c.drawString(40, contact_y - 36, f"Feature: {meta.get('title', title)}")
    c.drawString(40, contact_y - 54, str(meta.get("project", "Generated from supplied artifacts")))

    if tags_text:
        c.drawString(40, contact_y - 84, tags_text)

    c.setFont(fonts["small"]["name"], fonts["small"]["size"])
    c.setFillColor(hex_color("#667788"))
    c.drawString(40, 40, "Generated from a markdown template and theme spec.")

    c.showPage()


def draw_page_header(c: canvas.Canvas, theme: dict[str, Any], title: str, page_num: int, page_w: float, page_h: float) -> None:
    palette = theme["palette"]
    fonts = theme["fonts"]
    header_h = theme_value(theme, "layout", "header_height", default=28)
    dark_bg = hex_color(palette["dark_bg"])
    highlight = hex_color(palette["highlight"])
    text_dark = hex_color(palette["text_dark"])

    c.setFillColor(dark_bg)
    c.rect(0, page_h - header_h, page_w, header_h, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont(fonts["small"]["name"], fonts["small"]["size"])
    c.drawString(20, page_h - 20, "AI REPORT TEMPLATE")
    c.drawRightString(page_w - 20, page_h - 20, f"{page_num}")

    c.setFillColor(text_dark)
    c.setFont(fonts["page_title"]["name"], fonts["page_title"]["size"])
    c.drawString(30, page_h - 65, title)

    c.setStrokeColor(highlight)
    c.setLineWidth(3)
    c.line(30, page_h - 72, min(30 + len(title) * 10.5, page_w - 30), page_h - 72)


def draw_section_label(c: canvas.Canvas, theme: dict[str, Any], label: str, x: float, y: float) -> float:
    c.setFillColor(hex_color(theme["palette"]["highlight"]))
    c.setFont(theme["fonts"]["section_label"]["name"], theme["fonts"]["section_label"]["size"])
    c.drawString(x, y, label.upper())
    return y - 18


def draw_body_paragraph(
    c: canvas.Canvas,
    theme: dict[str, Any],
    text: str,
    x: float,
    y: float,
    width: float,
) -> float:
    fonts = theme["fonts"]
    palette = theme["palette"]
    font_name = fonts["body"]["name"]
    font_size = fonts["body"]["size"]
    line_gap = 14
    lines = wrap_text(text, font_name, font_size, width, c)
    c.setFillColor(hex_color(palette["text_mid"]))
    c.setFont(font_name, font_size)
    current_y = y
    for line in lines:
        c.drawString(x, current_y, line)
        current_y -= line_gap
    return current_y


def draw_bullet(
    c: canvas.Canvas,
    theme: dict[str, Any],
    text: str,
    x: float,
    y: float,
    width: float,
) -> float:
    fonts = theme["fonts"]
    palette = theme["palette"]
    font_name = fonts["bullet"]["name"]
    font_size = fonts["bullet"]["size"]
    line_gap = 12
    indent = x + 12
    bullet_width = max(40, width - 12)
    lines = wrap_text(text, font_name, font_size, bullet_width, c)

    c.setFillColor(hex_color(palette["highlight"]))
    c.setFont(fonts["bullet"]["name"], font_size)
    c.drawString(x, y, ">")

    c.setFillColor(hex_color(palette["text_mid"]))
    c.setFont(font_name, font_size)
    current_y = y
    for line in lines:
        c.drawString(indent, current_y, line)
        current_y -= line_gap
    return current_y


def draw_quote(
    c: canvas.Canvas,
    theme: dict[str, Any],
    text: str,
    x: float,
    y: float,
    width: float,
) -> float:
    palette = theme["palette"]
    font_name = theme["fonts"]["quote"]["name"]
    font_size = theme["fonts"]["quote"]["size"]
    lines = wrap_text(text, font_name, font_size, width - 10, c)
    current_y = y
    c.setStrokeColor(hex_color(palette["border"]))
    c.setLineWidth(2)
    c.line(x, current_y + 2, x, current_y - len(lines) * 12)
    c.setFillColor(hex_color(palette["text_light"]))
    c.setFont(font_name, font_size)
    for line in lines:
        c.drawString(x + 10, current_y, line)
        current_y -= 12
    return current_y


def draw_code_block(
    c: canvas.Canvas,
    theme: dict[str, Any],
    text: str,
    x: float,
    y: float,
    width: float,
) -> float:
    palette = theme["palette"]
    font_name = theme["fonts"]["code"]["name"]
    font_size = theme["fonts"]["code"]["size"]
    line_gap = 10
    lines = text.splitlines() or [""]
    height = max(18, len(lines) * line_gap + 12)
    c.setFillColor(hex_color(palette["section_bg"]))
    c.setStrokeColor(hex_color(palette["border"]))
    c.setLineWidth(0.5)
    c.roundRect(x, y - height + 6, width, height, 4, fill=1, stroke=1)
    c.setFillColor(hex_color(palette["text_mid"]))
    c.setFont(font_name, font_size)
    current_y = y - 2
    for line in lines:
        c.drawString(x + 8, current_y, line.rstrip())
        current_y -= line_gap
    return y - height - 6


def draw_placeholder_box(
    c: canvas.Canvas,
    theme: dict[str, Any],
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    sublabel: str = "",
) -> None:
    palette = theme["palette"]
    fonts = theme["fonts"]
    c.setFillColor(hex_color(palette["placeholder_bg"]))
    c.setStrokeColor(hex_color(palette["border"]))
    c.setDash(3, 3)
    c.setLineWidth(1)
    c.rect(x, y, w, h, fill=1, stroke=1)
    c.setDash()

    c.setFillColor(hex_color(palette["text_light"]))
    c.setFont(fonts["body"]["name"], fonts["body"]["size"])
    c.drawCentredString(x + w / 2, y + h / 2 + 8, label)
    if sublabel:
        c.setFont(fonts["small"]["name"], fonts["small"]["size"])
        c.drawCentredString(x + w / 2, y + h / 2 - 8, sublabel)


def draw_metric_box(
    c: canvas.Canvas,
    theme: dict[str, Any],
    x: float,
    y: float,
    value: str,
    label: str,
    w: float = 120,
) -> None:
    palette = theme["palette"]
    fonts = theme["fonts"]
    c.setFillColor(hex_color(palette["section_bg"]))
    c.setStrokeColor(hex_color(palette["border"]))
    c.setLineWidth(0.5)
    c.roundRect(x, y, w, 50, 4, fill=1, stroke=1)
    c.setFillColor(hex_color(palette["highlight"]))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(x + w / 2, y + 28, value)
    c.setFillColor(hex_color(palette["text_light"]))
    c.setFont(fonts["small"]["name"], 7.5)
    c.drawCentredString(x + w / 2, y + 10, label)


def draw_metric_grid(
    c: canvas.Canvas,
    theme: dict[str, Any],
    metrics: list[str],
    x: float,
    y: float,
    width: float,
) -> float:
    pairs: list[tuple[str, str]] = []
    for item in metrics:
        if ":" in item:
            label, value = item.split(":", 1)
            pairs.append((label.strip(), value.strip()))
        else:
            pairs.append((item.strip(), ""))

    if not pairs:
        return y

    card_w = min(125, max(100, (width - 30) / 4))
    gap = 10
    current_y = y
    count = 0
    row_start_y = y

    for label, value in pairs[:4]:
        box_x = x + count * (card_w + gap)
        draw_metric_box(c, theme, box_x, current_y, value or "-", label, w=card_w)
        count += 1

    return current_y - 60


def should_start_new_page(y: float, bottom_margin: float, required_height: float = 0) -> bool:
    return y - required_height < bottom_margin


def render_image(
    c: canvas.Canvas,
    theme: dict[str, Any],
    path_value: str,
    alt: str,
    x: float,
    y: float,
    width: float,
    bottom_margin: float,
    base_dir: Path,
) -> float:
    palette = theme["palette"]
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    max_h = 180
    if path.exists():
        img_w, img_h = image_size(path, width, max_h)
        c.drawImage(str(path), x, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask="auto")
        caption = alt or path.name
        c.setFillColor(hex_color(palette["text_light"]))
        c.setFont(theme["fonts"]["small"]["name"], theme["fonts"]["small"]["size"])
        c.drawString(x, y - img_h - 12, caption)
        return y - img_h - 24

    draw_placeholder_box(c, theme, x, y - 120, width, 120, alt or "[IMAGE NOT FOUND]", str(path_value))
    return y - 132


def render_body(
    c: canvas.Canvas,
    theme: dict[str, Any],
    blocks: list[Block],
    title: str,
    page_w: float,
    page_h: float,
    meta: dict[str, Any],
    base_dir: Path,
) -> None:
    margins = theme["layout"]["margins"]
    bottom_margin = margins["bottom"]
    content_x = margins["left"]
    content_w = page_w - margins["left"] - margins["right"]
    y = page_h - 88
    page_num = 2
    section_name = ""
    metrics_buffer: list[str] = []
    in_metrics_section = False

    def new_page() -> None:
        nonlocal y, page_num, section_name, in_metrics_section, metrics_buffer
        c.showPage()
        page_num += 1
        draw_page_header(c, theme, title, page_num, page_w, page_h)
        y = page_h - 88
        section_name = ""
        in_metrics_section = False
        metrics_buffer = []

    draw_page_header(c, theme, title, page_num, page_w, page_h)

    for block in blocks:
        if block.kind == "heading":
            if block.level == 1 and not section_name:
                continue

            if block.level == 2:
                if metrics_buffer and in_metrics_section:
                    required = 70
                    if should_start_new_page(y, bottom_margin, required):
                        new_page()
                    y = draw_metric_grid(c, theme, metrics_buffer, content_x, y, content_w)
                    metrics_buffer = []
                    in_metrics_section = False

                section_name = section_title_text(block)
                if should_start_new_page(y, bottom_margin, 40):
                    new_page()
                y -= 10
                y = draw_section_label(c, theme, section_name, content_x, y)
                continue

            if block.level >= 3:
                if should_start_new_page(y, bottom_margin, 24):
                    new_page()
                c.setFillColor(hex_color(theme["palette"]["text_dark"]))
                c.setFont("Helvetica-Bold", 12)
                c.drawString(content_x, y, block.text)
                y -= 16
                continue

        if block.kind == "paragraph":
            needed = max(24, len(wrap_text(block.text, theme["fonts"]["body"]["name"], theme["fonts"]["body"]["size"], content_w, c)) * 14)
            if should_start_new_page(y, bottom_margin, needed):
                new_page()
            y = draw_body_paragraph(c, theme, block.text, content_x, y, content_w)
            y -= 4
            continue

        if block.kind == "bullet":
            if section_name.lower() in {"key results", "metrics"}:
                in_metrics_section = True
                metrics_buffer.append(block.text)
                continue
            needed = max(18, len(wrap_text(block.text, theme["fonts"]["bullet"]["name"], theme["fonts"]["bullet"]["size"], content_w - 12, c)) * 12)
            if should_start_new_page(y, bottom_margin, needed):
                new_page()
            y = draw_bullet(c, theme, block.text, content_x, y, content_w)
            y -= 3
            continue

        if block.kind == "quote":
            needed = max(16, len(wrap_text(block.text, theme["fonts"]["quote"]["name"], theme["fonts"]["quote"]["size"], content_w - 10, c)) * 12)
            if should_start_new_page(y, bottom_margin, needed):
                new_page()
            y = draw_quote(c, theme, block.text, content_x, y, content_w)
            y -= 4
            continue

        if block.kind == "code":
            needed = max(30, len(block.text.splitlines()) * 10 + 18)
            if should_start_new_page(y, bottom_margin, needed):
                new_page()
            y = draw_code_block(c, theme, block.text, content_x, y, content_w)
            y -= 6
            continue

        if block.kind == "image":
            if should_start_new_page(y, bottom_margin, 150):
                new_page()
            y = render_image(c, theme, block.path, block.alt, content_x, y, content_w, bottom_margin, base_dir)
            y -= 12
            continue

    if metrics_buffer and in_metrics_section:
        if should_start_new_page(y, bottom_margin, 70):
            new_page()
        draw_metric_grid(c, theme, metrics_buffer, content_x, y, content_w)

    c.showPage()


def build_pdf(input_md: Path, output_pdf: Path, theme_path: Path) -> None:
    theme = load_theme(theme_path)
    raw = input_md.read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)
    blocks = parse_markdown_blocks(body)
    title = report_title(meta, blocks)
    page_w, page_h = A4

    c = canvas.Canvas(str(output_pdf), pagesize=A4)
    render_cover(c, theme, meta, title, page_w, page_h)
    render_body(c, theme, blocks, title, page_w, page_h, meta, input_md.parent)
    c.save()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a PDF report from markdown.")
    parser.add_argument("input", type=Path, help="Path to the feature report markdown file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path. Defaults to the input name with a .pdf suffix.",
    )
    parser.add_argument(
        "--theme",
        type=Path,
        default=DEFAULT_THEME_PATH,
        help="Path to the theme markdown file that contains the JSON style spec.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_md: Path = args.input
    output_pdf: Path = args.output or input_md.with_suffix(".pdf")
    build_pdf(input_md, output_pdf, args.theme)
    print(f"Report PDF created: {output_pdf}")


if __name__ == "__main__":
    main()
