---
title: <feature title>
subtitle: <one-sentence summary of the feature>
author: AI agent
date: <YYYY-MM-DD>
feature_type: Feature report
project: <project or subsystem name>
tags:
  - <tag one>
  - <tag two>
  - <tag three>
---

# Authoring Instructions

This file is the canonical report template. Fill it with the actual evidence
from the feature you finished.

Rules:

- Use the exact feature title in the `title` field.
- Keep the report factual and artifact-driven.
- Do not invent measurements or claims.
- If something is missing, mark it `N/A` and explain why.
- Keep the section order unless a section truly does not apply.
- Use markdown images for plots and screenshots.

## Executive Summary

Write a short summary that answers:

- What was built?
- Why did it matter?
- What is the main outcome?

## Problem Statement

Describe the problem the feature solved and the gap it closed.

## Goals

- State the primary goal.
- State the secondary goals if there are any.
- State the constraints or assumptions that mattered.

## Implementation

Explain how the feature works.

- Include the main files or modules changed.
- Include the architecture or data flow.
- Include the important algorithms, interfaces, or design decisions.

## Validation

Explain how the feature was tested or verified.

- List the test cases or scenarios.
- Mention the commands, scripts, or runs that were used.
- Mention any edge cases, regressions, or known limitations.

## Key Results

Use short metric-style bullets here so the renderer can promote them into cards.

- Success rate: <value>
- Test count: <value>
- Runtime: <value>
- Latency: <value>

## Artifacts

Add the important plots, screenshots, diagrams, or logs here.

![<caption>](path/to/plot.png)

![<caption>](path/to/screenshot.png)

## Risks And Follow-Up

List anything incomplete, risky, or worth future work.

- Current risk:
- Follow-up item:
- Future improvement:

## Appendix

Use this section for any extra notes, file references, or implementation details
that do not fit elsewhere.

