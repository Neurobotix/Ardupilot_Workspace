# Report Theme Spec

The PDF renderer reads the JSON block below as the single source of truth for
colors, typography, spacing, and the cover/header/callout/figure styling. The
palette is intentionally restrained and engineering-professional: a deep slate
ink, a steel-blue structural accent, and a small set of muted semantic colors
for callouts. No toy colors.

```json
{
  "palette": {
    "ink": "#15212e",
    "ink_soft": "#22303f",
    "steel": "#2f5d7c",
    "steel_soft": "#4c7a98",
    "rule": "#c2cdd6",
    "rule_soft": "#dde4ea",
    "text_dark": "#1d2a36",
    "text_mid": "#3f4d59",
    "text_light": "#7b8893",
    "paper": "#ffffff",
    "panel": "#f3f6f8",
    "panel_alt": "#eef2f5",
    "tag_bg": "#e3eaf0",

    "cover_bg": "#15212e",
    "cover_panel": "#1d2c3b",
    "cover_accent": "#5b94bb",
    "cover_text": "#e8eef3",
    "cover_text_soft": "#9fb2c1",

    "key_bg": "#eaf1f6",
    "key_border": "#2f5d7c",
    "key_text": "#1d3a4f",

    "warn_bg": "#fbf3e6",
    "warn_border": "#b9842f",
    "warn_text": "#6e4d15",

    "verdict_bg": "#e9f1ec",
    "verdict_border": "#3f7a5b",
    "verdict_text": "#234435",

    "def_bg": "#eef0f4",
    "def_border": "#5a6b86",
    "def_text": "#2e3a4f",

    "card_value": "#2f5d7c",
    "card_label": "#7b8893",

    "table_head_bg": "#22303f",
    "table_head_text": "#ffffff",
    "table_row_alt": "#f3f6f8",
    "table_border": "#c2cdd6",

    "divider_bg": "#1a2836",
    "divider_panel": "#24384a",
    "divider_accent": "#5b94bb",
    "divider_text": "#eef3f7",
    "divider_text_soft": "#9fb2c1",

    "placeholder_bg": "#f3f6f8",
    "border": "#c2cdd6",
    "section_bg": "#f3f6f8"
  },
  "fonts": {
    "cover_kicker": { "name": "Helvetica-Bold", "size": 11 },
    "cover_title": { "name": "Helvetica-Bold", "size": 31 },
    "cover_subtitle": { "name": "Helvetica", "size": 13 },
    "cover_meta_label": { "name": "Helvetica-Bold", "size": 8 },
    "cover_meta": { "name": "Helvetica", "size": 10 },

    "divider_index": { "name": "Helvetica-Bold", "size": 13 },
    "divider_title": { "name": "Helvetica-Bold", "size": 26 },
    "divider_sub": { "name": "Helvetica", "size": 12 },

    "header_kicker": { "name": "Helvetica-Bold", "size": 7.5 },
    "page_title": { "name": "Helvetica-Bold", "size": 16 },
    "section_label": { "name": "Helvetica-Bold", "size": 9 },
    "subheading": { "name": "Helvetica-Bold", "size": 11.5 },
    "body": { "name": "Helvetica", "size": 10 },
    "bullet": { "name": "Helvetica", "size": 9.8 },
    "quote": { "name": "Helvetica-Oblique", "size": 9.8 },
    "code": { "name": "Courier", "size": 8.5 },
    "caption": { "name": "Helvetica-Oblique", "size": 8.5 },
    "caption_label": { "name": "Helvetica-Bold", "size": 8.5 },
    "callout_label": { "name": "Helvetica-Bold", "size": 8.5 },
    "callout_body": { "name": "Helvetica", "size": 9.6 },
    "card_value": { "name": "Helvetica-Bold", "size": 17 },
    "card_label": { "name": "Helvetica", "size": 7.5 },
    "table": { "name": "Helvetica", "size": 8.8 },
    "table_head": { "name": "Helvetica-Bold", "size": 8.8 },
    "small": { "name": "Helvetica", "size": 8 }
  },
  "layout": {
    "page_size": "A4",
    "margins": { "left": 46, "right": 46, "top": 30, "bottom": 40 },
    "header_height": 22,
    "running_title": "Airspeed Failure Technical Reference",
    "running_kicker": "SIM_ARD_GAW / TECHNICAL REFERENCE"
  }
}
```

## Visual Direction

- Aerospace/simulation technical-appendix feel: deep slate ink, steel-blue
  structural accent, generous white space, quiet semantic colors.
- The cover is a full-bleed slate page with a kicker, large title, subtitle,
  and a clean metadata grid. No marketing language.
- Section dividers are short slate cards that give each major part its own
  identity and reset the reader.
- Callouts carry meaning through a restrained left-bar + tint:
  - key idea (steel blue), warning (muted amber), verdict (muted green),
    definition (slate grey).
- Figures are first-class: large, centered, with a bold figure label and an
  explanatory caption.
- Tables replace dense bullet walls where a comparison is involved.
- Helvetica/Courier only, so output is stable across systems.

## Authoring Directives (markdown conventions the renderer understands)

- `## Heading` starts a normal content section.
- `# PART n: Title` (an H1 after the cover) renders a full section-divider page.
  Optionally follow with a single italic line for the divider subtitle.
- Callout block:
  ```
  > [!key] Title text
  > Body line one.
  > Body line two.
  ```
  Types: `key`, `warning`, `verdict`, `definition`. Title is optional.
- Status/metric cards: a `## Key Results` (or `## Metrics`) section turns its
  `Label: Value` bullets into cards, as before. You can also use a
  `> [!cards]` block with `Label: Value` lines anywhere.
- Markdown tables (`| a | b |` with a `|---|` separator) render as styled
  tables.
- Figures: `![Caption](path.png)` renders a large captioned figure. Prefix the
  caption with `Figure N —` to get an auto-styled figure label.
