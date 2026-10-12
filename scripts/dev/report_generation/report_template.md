---
title: <report title>
subtitle: <one-sentence summary>
author: AI agent
date: <YYYY-MM-DD>
feature_type: Technical Reference
project: <project or subsystem name>
tags:
  - <tag one>
  - <tag two>
  - <tag three>
---

# <Report Title>

This file is the canonical report template. Fill it with the actual evidence from
the work you finished. The renderer (`pdf.py`) understands the authoring
directives shown below — see `README.md` and `theme.md` for the full list.

Rules:

- Use the exact title in the `title` field.
- Keep the report factual and artifact-driven; do not invent measurements.
- Mark unclear claims as "needs technical review" instead of restating them as
  fact.
- If something is missing, mark it `N/A` and explain why.
- Use markdown images for plots, diagrams, and screenshots.
- Prefer callouts and tables over long bullet walls.

> [!key] Lead with the single most important takeaway
> Put the one idea the reader must leave with here.

## How To Read This Report

A short orienting table or paragraph so a reader can jump to what they need.

| Read for | Go to |
| --- | --- |
| The big picture | Part 1 |
| The detail | Appendix |

# PART 1: <First Major Part>
*Optional one-line subtitle for the divider page.*

## <Section>

Body text. Use `### Sub Heading` for finer structure.

![Figure 1.1 — caption that actually helps the reader.](path/to/diagram.png)

> [!warning] Use a warning callout for a real pitfall
> Body of the warning.

> [!definition] Use a definition callout for a precise term
> The definition.

## Key Results

Use `Label: Value` bullets here; they render as metric/status cards.

- Success rate: <value>
- Test count: <value>
- Runtime: <value>
- Latency: <value>

# PART 2: <Second Major Part>

## <Section>

Use tables for comparisons:

| Option | Role | Status |
| --- | --- | --- |
| A | ... | ... |

> [!verdict] State the conclusion plainly
> The verdict.

# Appendix
*Detailed source/evidence references and supporting figures.*

## Source Anchors

- `path/to/file`

## Supporting Diagrams

![Figure A.1 — caption.](path/to/extra_diagram.png)
