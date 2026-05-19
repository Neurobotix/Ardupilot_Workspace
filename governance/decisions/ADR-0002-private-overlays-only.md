# ADR-0002: Private Directory Is Local Overlays Only

Status: Accepted

`.private/` is gitignored and may contain local params, local environment files,
personal notes, and backups. It must not contain canonical operator docs or
duplicate runnable logic.
