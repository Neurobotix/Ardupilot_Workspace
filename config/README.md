# Config Inputs

Shared runtime configuration lives under explicit subhomes:

## Shared Config Homes

- `vehicles/`: vehicle base parameters and standalone vehicle lane stacks.
- `overlays/`: feature overlays applied after a vehicle base.
- `campaigns/`: campaign or integrated-lane parameter files.
- `archive/`: superseded snapshots retained for comparison only.

`.private/config/*.local.parm` is optional local overlay space. It is not shared
canonical config. Historical recovered parameter stacks live under
`evidence/curated_logs/recovered_param_stacks/`, not active `config/`.

Canonical inventory and stack membership are indexed in
`evidence/indexes/parameter_config_index.md`.

## Archive

Legacy all-in-one plane parameter files live in `archive/`.
They are retained for historical comparison only and are not part of the
current launcher's default working set.
