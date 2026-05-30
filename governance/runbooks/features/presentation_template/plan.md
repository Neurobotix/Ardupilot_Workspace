# Presentation Template Plan

## Summary

Adopt a reusable Reveal/reveal-md presentation template as shared
human-facing documentation tooling under `docs/presentations/`.

## Scope

- Keep the canonical template and local Node tooling under `docs/presentations/`.
- Provide placeholder slides, shared theme CSS, Reveal config, and usage docs.
- Exclude completed desktop presentations, generated output, screenshots,
  summaries, `node_modules/`, and any source-project-specific deck content.

## Implementation

- Add a contained package manifest in `docs/presentations/` with `dev`,
  `build`, and `pdf` scripts.
- Add `docs/presentations/reveal_md_template/` with `slides.md`, `theme.css`,
  `reveal-md.json`, and `README.md`.
- Link the template from `docs/README.md`, `.ai/index.md`, and
  `docs/architecture/workspace_map.md`.
- Ignore local presentation dependencies and generated `dist/` output.

## Checks

- Run `npm install --package-lock-only` from `docs/presentations/`.
- Run `npm run build` from `docs/presentations/`.
- Run `make doctor` from the workspace root.
