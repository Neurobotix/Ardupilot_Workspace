# Presentation Template Plan

## Summary

Maintain a reusable Reveal/reveal-md presentation template for producing
briefing decks from workspace evidence.

The template and its Node tooling live under `docs/presentations/`, which is
**local-only and deliberately untracked**. `.gitignore` excludes that directory
in full, by decision and not by oversight. The tooling exists on an operator's
machine, is not distributed with the repository, and **a fresh clone will not
contain it**.

Nothing under `docs/presentations/` is canonical repository content. Decks
built there are presentation packaging of evidence that is already tracked
elsewhere; the tracked evidence report is always the citable source, never the
deck.

## Scope

- Keep the template and Node tooling under local-only `docs/presentations/`.
- Provide placeholder slides, shared theme CSS, Reveal config, and usage docs
  on the operator's machine.
- Exclude completed desktop presentations, generated output, screenshots,
  summaries, `node_modules/`, and any source-project-specific deck content.

## Local Layout

The following exist on an operator's machine only and are not tracked:

- a contained package manifest in `docs/presentations/` with `dev`, `build`,
  and `pdf` scripts;
- `docs/presentations/reveal_md_template/` with `slides.md`, `theme.css`,
  `reveal-md.json`, and `README.md`.

## Referencing Briefs From Tracked Documents

A tracked document may record that a briefing deck was produced, but must not
present it as a resolvable repository file. Cite the tracked evidence report as
the source and mark the deck path explicitly as local-only, so a reader does
not go looking for a file that a clone will never contain.

`evidence/reports/features/2026-06-02_pillar_a_flight_results.md` is the
existing precedent for that labelling.

## Local Workflow

These are how an operator uses the template on their own machine. They are not
repository build steps and do not run in a fresh clone:

- Run `npm install --package-lock-only` from `docs/presentations/`.
- Run `npm run build` from `docs/presentations/`.

## Checks

- Run `make doctor` from the workspace root.
- Confirm `git ls-files docs/presentations/` still returns nothing. Any tracked
  file under that path contradicts this plan.
