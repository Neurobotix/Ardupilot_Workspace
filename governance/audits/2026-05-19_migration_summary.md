# Migration Summary

This workspace was created as a structured sibling, not a production rewrite.

Key choices:

- Current production workspace was read as source material only.
- Runtime compatibility is preserved through symlinks and wrappers.
- Old `src/SIM_ARD_GAW` exists as a compatibility path made of symlinks.
- Canonical docs were rewritten instead of bulk copied.
- Original docs were archived under `docs/archive/src_docs/` for review.
- Raw logs were not migrated; curated manifests and reports were copied to
  `evidence/curated_logs/`.
- `.private/` migrated only local overlays, notes, and backup material.
