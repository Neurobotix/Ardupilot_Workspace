# Report Generation Workflow

This folder defines the full report system for AI-generated feature reports.

## Files

- `theme.md`: the visual design system for the PDF. It contains the color palette, font choices, layout margins, and cover/header styling in a machine-readable JSON block.
- `report_template.md`: the content contract the AI agent should fill in for each feature report.
- `pdf.py`: the renderer that turns a filled report markdown file into a PDF.

## Workflow

1. Start from `report_template.md`.
2. Fill in the front matter with the real feature title, subtitle, author, date, and tags.
3. Replace the placeholder sections with the actual findings, implementation notes, results, plots, and follow-ups for the feature.
4. Attach plots or screenshots with markdown image syntax.
5. Run:

```bash
python pdf.py path/to/feature_report.md
```

The output PDF will use the exact style defined in `theme.md`.

## Authoring Rules For The AI Agent

- Use the feature title as the report title.
- Do not invent metrics, test counts, or results.
- If a number or figure is unavailable, write `N/A` and explain what is missing.
- Prefer concise, factual phrasing over marketing language.
- Keep the section order from the template unless a section is truly not applicable.
- Use supplied plots and artifacts directly. Do not replace them with placeholders in the final report.

