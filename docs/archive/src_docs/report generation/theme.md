# Report Theme Spec

The PDF renderer reads the JSON block below as the single source of truth for
colors, typography, spacing, and cover/header styling.

```json
{
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
    "placeholder_bg": "#f8f9fa"
  },
  "fonts": {
    "cover_title": { "name": "Helvetica-Bold", "size": 34 },
    "cover_subtitle": { "name": "Helvetica", "size": 16 },
    "cover_tagline": { "name": "Helvetica", "size": 11 },
    "cover_meta": { "name": "Helvetica", "size": 10 },
    "page_title": { "name": "Helvetica-Bold", "size": 22 },
    "section_label": { "name": "Helvetica-Bold", "size": 9 },
    "body": { "name": "Helvetica", "size": 10 },
    "bullet": { "name": "Helvetica", "size": 9.5 },
    "quote": { "name": "Helvetica-Oblique", "size": 9.5 },
    "code": { "name": "Courier", "size": 8.5 },
    "small": { "name": "Helvetica", "size": 8 }
  },
  "layout": {
    "page_size": "A4",
    "margins": { "left": 30, "right": 30, "top": 30, "bottom": 34 },
    "header_height": 28,
    "cover_title_y_ratio": 0.72,
    "cover_contact_y_ratio": 0.28
  }
}
```

## Visual Direction

- Keep the dark cover background and red accent stripe.
- Keep the page header bar with a dark strip, white page number, and bold title.
- Keep the section labels in uppercase with the highlight color.
- Use light grey cards and thin borders for metrics, callouts, and placeholders.
- Use Helvetica-family fonts only so the output is stable across systems.

## Layout Rules

- A4 page size.
- Left and right margins are 30 points.
- The cover page is full-bleed dark with a large title and short metadata block.
- Content pages use a single-column flow so the report can adapt to any feature length.
- Images should preserve aspect ratio and sit inline with captions.

