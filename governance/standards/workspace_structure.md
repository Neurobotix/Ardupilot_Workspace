# Workspace Structure Standard

`src/` contains code only. `assets/` contains SDF models, worlds, and missions.
`config/` contains reproducible shared defaults. `var/` is disposable runtime
output and is ignored by git. `evidence/` contains curated reports, manifests,
and indexes only. `.private/` is local-only and must not contain canonical docs
or duplicate runnable logic.

External dependency trees under `src/ardupilot/` and `src/SITL_Models/` are
ignored local checkouts used for runtime parity. They are not canonical
workspace evidence, and validator raw-log checks prune them while continuing to
scan tracked workspace homes.
