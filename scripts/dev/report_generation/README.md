# Report Generation Workflow

Development helper. Moved here from `var/reports/report generation/` on
2026-10-12. It renders human-facing PDF reports; it is not the governed
evidence workflow (see `governance/standards/evidence.md`). An older, different
version is archived at `docs/archive/src_docs/report generation/`.

This folder defines the full report system for AI-generated feature reports and
technical references.

## Files

- `theme.md`: the visual design system for the PDF. It holds the color palette,
  typography, spacing, and cover/header/divider/callout/figure styling in a
  machine-readable JSON block, plus the authoring directives the renderer
  understands.
- `report_template.md`: the content contract to fill in for each report.
- `pdf.py`: the renderer that turns a filled report markdown file into a PDF.

## Workflow

1. Start from `report_template.md`.
2. Fill in the front matter with the real title, subtitle, author, date, and
   tags.
3. Replace the placeholder sections with the actual content. Use the authoring
   conventions below to get section dividers, callouts, cards, tables, and large
   captioned figures.
4. Attach diagrams/screenshots with markdown image syntax.
5. Run:

```bash
python pdf.py path/to/feature_report.md
```

The output PDF uses the exact style defined in `theme.md`.

## Authoring Conventions

The renderer accepts plain markdown plus a few professional-report directives:

| Want | Write |
| --- | --- |
| Normal content section | `## Section Heading` |
| Full-page section divider | `# PART n: Title` (any H1 after the title) followed by one optional italic subtitle line |
| Sub-heading | `### Sub Heading` |
| Key-idea callout | `> [!key] Optional title` then `> body lines` |
| Warning callout | `> [!warning] ...` |
| Verdict callout | `> [!verdict] ...` |
| Definition callout | `> [!definition] ...` |
| Metric / status cards | `> [!cards]` then `> Label: Value` lines (or a `## Key Results` section with `Label: Value` bullets) |
| Styled table | a markdown table with a `|---|` separator row |
| Large captioned figure | `![Figure N — caption](path.png)` (the `Figure N` prefix becomes a styled label) |

Notes:

- The first `# Heading` (or the front-matter `title`) is the document title and
  is rendered on the cover, not as a divider.
- Each `# PART ...` heading starts a new full-page slate divider. Keep parts in
  the intended reading order.
- Callout bodies are tinted with a restrained left bar; pick the type by meaning,
  not decoration.
- Figures are centered and sized to the available column; very tall diagrams get
  most of a page automatically.

## Authoring Rules For The AI Agent

- Use the real feature/report title as the title.
- Do not invent metrics, test counts, or results. If a number is unavailable,
  write `N/A` and explain what is missing.
- Mark uncertain technical claims as "needs technical review" rather than
  inventing or restating them as fact.
- Prefer concise, factual phrasing over marketing language.
- Use supplied diagrams/artifacts directly. Do not replace them with placeholders
  in the final report.
- Prefer tables and callouts over long bullet walls when a comparison or a single
  key point is involved.
